from .base import BaseValidator, ValidationError
from typing import List
import pandas as pd


class CalculationValidator(BaseValidator):
    """
    Validator for verifying the integrity of calculated fields.

    Primary Check:
    Market Value = Quantity * Price * Exchange Rate

    This validator ensures that the 'Value in USD' column matches the theoretical value
    derived from the underlying components. Discrepancies suggest data corruption,
    manual overrides, or formula errors in the source system.
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
            # StdDev < 0.1 implies very consistent ratio
            # Abs(Median - 1) > 0.05 implies it's not just rounding error
            if std < 0.1 and abs(median - 1.0) > 0.05:
                systematic_map[ticker] = median

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

        # Calculate % error for severity
        # Avoid division by zero
        potential_errors["Pct_Error"] = (
            potential_errors["Abs_Diff"]
            / potential_errors["Value in USD"].replace(0, 1)
        ).abs()

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

        for idx, row in potential_errors.iterrows():
            diff = row["Abs_Diff"]
            pct = row["Pct_Error"]
            mult = row["Implied_Mult"]
            theo_val = row["Theoretical_Value"]

            # Check for common multipliers (e.g., 5, 10, 100, 1000) or 0.01 (cents/pence)
            # We check if the multiplier is close to an integer (except 0 and 1)
            # Tolerance: +/- 5%

            is_multiplier_explained = False
            explanation = ""

            # Only check multiplier if we have a valid theoretical value
            if abs(theo_val) > 0.01:
                # Check for systematic multiplier first
                if row["P_Ticker"] in systematic_map:
                    sys_mult = systematic_map[row["P_Ticker"]]
                    # Check if THIS row matches the systematic multiplier
                    if abs(mult - sys_mult) < 0.1:
                        is_multiplier_explained = True
                        explanation = f" (Systematic Multiplier: x{sys_mult:.2f})"

                # Check for integer multipliers (e.g. 5, 10, 100)
                if not is_multiplier_explained and abs(mult) > 1.5:
                    nearest_int = round(mult)
                    if abs(mult - nearest_int) / abs(nearest_int) < 0.05:
                        is_multiplier_explained = True
                        explanation = f" (Likely missing multiplier: x{nearest_int})"

                # Check for reciprocal multipliers (e.g. 0.2, 0.25, 0.5, 0.01)
                elif not is_multiplier_explained and abs(mult) < 0.9:
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

            # Ignore small errors (< 10%)
            if pct <= 0.10 and not is_multiplier_explained:
                continue

            # Severity Logic
            if is_multiplier_explained:
                # If explained by a multiplier, we downgrade to Low (or ignore, but user wants to know)
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
            elif pct > 0.30:  # > 30% error
                severity = "High"
            elif pct > 0.15:  # > 15% error
                severity = "Medium"
            else:  # 10% < pct <= 15%
                severity = "Low"

            self.add_error(
                date=row["Date"],
                ticker=row["P_Ticker"],
                error_type="Calculation Error",
                description=f"Value Mismatch: Reported {row['Value in USD']:.2f} vs Calc {row['Theoretical_Value']:.2f}{explanation}",
                severity=severity,
            )

        return self.errors
