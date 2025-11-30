from .base import BaseValidator, ValidationError
from typing import List
import pandas as pd


class CalculationValidator(BaseValidator):
    """
    Validator for verifying the integrity of calculated fields.

    Primary Check:
    Market Value = Quantity * Price * Exchange Rate

    This validator ensures that the 'Value in USD' column matches the theoretical value
    derived from the underlying components.

    Methodology:
    1.  **Theoretical Calculation**: Computes Expected Value = Qty * Price * FX.
    2.  **Statistical Analysis**: Calculates Z-Scores of the percentage difference between
        Reported Value and Theoretical Value.
    3.  **Pattern Recognition**: Identifies systematic multipliers (e.g., x100, x0.01) or
        consistent additive shifts (e.g. +500) per ticker.
    4.  **Hybrid Thresholds**:
        -   **High Severity**: Extreme outlier (Z > 5) OR Extreme deviation (> 30%) OR Sign Mismatch.
        -   **Medium Severity**: Significant outlier (Z > 3) OR Significant deviation (> 15%).
        -   **Low Severity**: Minor outlier OR Explained Multiplier/Shift.
    """

    def validate(self) -> List[ValidationError]:
        """
        Executes the calculation validation logic.

        Returns:
            List[ValidationError]: A list of detected calculation errors.
        """
        required_cols = [
            "Close Quantity",
            "Price",
            "Exchange Rate",
            "Value in USD",
            "P_Ticker",
            "Date",
        ]

        # Check for missing columns
        missing = [col for col in required_cols if col not in self.positions_df.columns]
        if missing:
            # If critical columns are missing, we can't validate.
            # In a stricter system, this might raise an error, but here we just return empty
            # or log a warning.
            return []

        df = self.positions_df.copy()

        # Ensure numeric types for calculation
        numeric_cols = ["Close Quantity", "Price", "Exchange Rate", "Value in USD"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # 1. Calculate Theoretical Value
        # Value = Quantity * Price * FX
        df["Theoretical_Value"] = (
            df["Close Quantity"] * df["Price"] * df["Exchange Rate"]
        )

        # 2. Calculate Difference
        df["Diff"] = df["Value in USD"] - df["Theoretical_Value"]
        df["Abs_Diff"] = df["Diff"].abs()

        # Calculate Percentage Difference (Error) for Z-Score
        # We use a small epsilon to avoid division by zero
        # This is signed (+/-) to detect bias, though for Z-score magnitude we'll take abs later
        df["Pct_Diff"] = df["Diff"] / df["Theoretical_Value"].replace(0, 1)

        # Calculate Z-Scores for the percentage difference
        # This helps identify statistical outliers in calculation errors
        df["Z_Score"] = self.calculate_z_scores(df["Pct_Diff"])

        # Pre-calculate systematic multipliers
        # We calculate the ratio for all rows to find consistent offsets per ticker
        # Use 0 for invalid ratios so we can filter them out easily
        df["Ratio"] = df.apply(
            lambda x: (
                x["Value in USD"] / x["Theoretical_Value"]
                if abs(x["Theoretical_Value"]) > 0.01
                else 0
            ),
            axis=1,
        )

        systematic_map = {}
        for ticker, group in df.groupby("P_Ticker"):
            if len(group) < 3:
                continue  # Need enough data points

            ratios = group["Ratio"]
            # Filter out 0s (missing data or invalid calc) for stats
            valid_ratios = ratios[ratios != 0]
            if valid_ratios.empty:
                continue

            median = valid_ratios.median()
            std = valid_ratios.std()

            # Handle case where std is NaN (e.g. only 1 valid value)
            if pd.isna(std):
                std = 0

            # If stable (low std) and offset (median != 1)
            # StdDev < 0.2 implies consistent ratio (relaxed from 0.1 to handle FX fluctuations)
            # Abs(Median - 1) > 0.05 implies it's not just rounding error
            if std < 0.2 and abs(median - 1.0) > 0.05:
                systematic_map[ticker] = median

        # Pre-calculate systematic shifts (additive)
        # We calculate the diff for all rows to find consistent offsets per ticker
        systematic_shift_map = {}
        for ticker, group in df.groupby("P_Ticker"):
            if len(group) < 3:
                continue

            diffs = group["Diff"]
            # Filter out 0s
            valid_diffs = diffs[diffs.abs() > 0.01]
            if valid_diffs.empty:
                continue

            median_diff = valid_diffs.median()
            std_diff = valid_diffs.std()

            if pd.isna(std_diff):
                std_diff = 0

            # If stable (low std relative to magnitude) and offset (median != 0)
            # CV < 0.1 implies consistent shift
            if abs(median_diff) > 1.0 and (std_diff / abs(median_diff)) < 0.1:
                systematic_shift_map[ticker] = median_diff

        # 3. Define Thresholds
        # We use a combination of absolute dollar amount and percentage difference
        # to avoid flagging rounding errors on small positions or tiny diffs on large positions.

        # Tolerance: $1.00 (for rounding) OR 0.01% (1 basis point)
        # We flag if it exceeds BOTH (to be safe) or just one?
        # Usually, if it's off by > $1 AND > 0.01%, it's an error.
        # If it's off by $0.05, it's rounding.
        # If it's off by $1000 but that's 0.00001% of a billion dollar position, it might be rounding too.

        # Let's use a tiered approach for severity.

        # Filter potential errors (Absolute diff > 1.0 USD)
        potential_errors = df[df["Abs_Diff"] > 1.0].copy()

        if potential_errors.empty:
            return []

        # Calculate Implied Multiplier
        # Ratio = Value / Theoretical
        # We only calculate multiplier if Theoretical is not zero to avoid misleading "xValue" multipliers
        potential_errors["Implied_Mult"] = potential_errors.apply(
            lambda x: (
                x["Value in USD"] / x["Theoretical_Value"]
                if abs(x["Theoretical_Value"]) > 0.01
                else 0
            ),
            axis=1,
        )

        for _, row in potential_errors.iterrows():
            diff = row["Abs_Diff"]
            pct = abs(row["Pct_Diff"])  # Use the pre-calculated signed % diff
            z_score = abs(row["Z_Score"])
            mult = row["Implied_Mult"]
            theo_val = row["Theoretical_Value"]

            # Check for common multipliers (e.g., 5, 10, 100, 1000) or 0.01 (cents/pence)
            # We check if the multiplier is close to an integer (except 0 and 1)
            # Tolerance: +/- 5%

            is_multiplier_explained = False
            is_shift_explained = False
            explanation = ""

            # Only check multiplier if we have a valid theoretical value
            if abs(theo_val) > 0.01:
                # Check for systematic multiplier first
                if row["P_Ticker"] in systematic_map:
                    sys_mult = systematic_map[row["P_Ticker"]]
                    # Check if THIS row matches the systematic multiplier
                    # Relaxed tolerance to 0.25 to handle FX volatility
                    if abs(mult - sys_mult) < 0.25:
                        is_multiplier_explained = True
                        explanation = f" (Systematic Multiplier: x{sys_mult:.2f})"

                # Check for systematic shift
                if (
                    not is_multiplier_explained
                    and row["P_Ticker"] in systematic_shift_map
                ):
                    sys_shift = systematic_shift_map[row["P_Ticker"]]
                    # Check if THIS row matches the systematic shift
                    if abs(row["Diff"] - sys_shift) / abs(sys_shift) < 0.1:
                        is_shift_explained = True
                        explanation = f" (Systematic Shift: {sys_shift:+.2f})"

                # Check for integer multipliers (e.g. 5, 10, 100)
                if (
                    not is_multiplier_explained
                    and not is_shift_explained
                    and abs(mult) > 1.5
                ):
                    nearest_int = round(mult)
                    if abs(mult - nearest_int) / abs(nearest_int) < 0.05:
                        is_multiplier_explained = True
                        explanation = f" (Likely missing multiplier: x{nearest_int})"

                # Check for reciprocal multipliers (e.g. 0.2, 0.25, 0.5, 0.01)
                elif (
                    not is_multiplier_explained
                    and not is_shift_explained
                    and abs(mult) < 0.9
                ):
                    # Check 1/N
                    recip = 1.0 / mult if mult != 0 else 0
                    nearest_recip = round(recip)
                    if (
                        nearest_recip != 0
                        and abs(recip - nearest_recip) / abs(nearest_recip) < 0.05
                    ):
                        is_multiplier_explained = True
                        explanation = f" (Likely missing multiplier: x{1/nearest_recip:.4g} or 1/{nearest_recip})"

                    # Special case for 0.01 (already covered by 1/100 but explicit check is nice)
                    if abs(mult - 0.01) < 0.001:
                        is_multiplier_explained = True
                        explanation = " (Likely unit mismatch: x0.01)"

            # Ignore small errors (< 10%) unless they are statistical outliers OR systematic
            # Hybrid Logic:
            # If Z > 3 (Outlier) AND Pct > 5% (Floor) -> Flag
            # If Pct > 10% (Absolute) -> Flag
            # If Systematic -> Flag (even if Z is low)

            is_outlier = z_score > 3 and pct > 0.05
            is_large = pct > 0.10
            is_systematic = is_multiplier_explained or is_shift_explained

            if not (is_outlier or is_large or is_systematic):
                continue

            # Severity Logic
            if is_systematic:
                # If explained by a multiplier/shift, we downgrade to Low (or ignore, but user wants to know)
                # User said "those are not errors", so let's treat them as Low severity info
                severity = "Low"
            elif abs(theo_val) < 0.01:
                # Theoretical is 0 (Missing Price/Qty/FX).
                # User requested to "not compute if impossible" and "forget the missing errors".
                continue
            elif (row["Value in USD"] * theo_val) < 0:
                # Sign Mismatch (Positive vs Negative)
                severity = "High"
                explanation = (
                    " (Sign Mismatch: Reported vs Calculated have opposite signs)"
                )
            # High: Extreme outlier (> 5 sigma) OR Extreme magnitude (> 30%)
            elif (z_score > 5 and pct > 0.05) or pct > 0.30:
                severity = "High"
            # Medium: Significant outlier (> 3 sigma) OR Significant magnitude (> 15%)
            elif (z_score > 3 and pct > 0.05) or pct > 0.15:
                severity = "Medium"
            else:  # Low
                severity = "Low"

            # Construct detailed description
            reason = []
            if explanation:
                reason.append(explanation.strip(" ()"))

            if pct > 0.30:
                reason.append(f"Absolute Diff > 30% ({pct:.1%})")
            elif pct > 0.15:
                reason.append(f"Absolute Diff > 15% ({pct:.1%})")

            if z_score > 5:
                reason.append(f"Extreme Statistical Outlier (Z={z_score:.1f} > 5)")
            elif z_score > 3:
                reason.append(f"Statistical Outlier (Z={z_score:.1f} > 3)")

            reason_str = " | ".join(reason)

            self.add_error(
                date=row["Date"],
                ticker=row["P_Ticker"],
                error_type="Calculation Error",
                description=f"Value Mismatch: Reported {row['Value in USD']:.2f} vs Calc {row['Theoretical_Value']:.2f}. Flagged due to: {reason_str}",
                severity=severity,
            )

        return self.errors
