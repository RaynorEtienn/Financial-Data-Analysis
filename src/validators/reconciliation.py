from .base import BaseValidator, ValidationError
from typing import List
import pandas as pd


class ReconciliationValidator(BaseValidator):
    """
    Validator for reconciling positions and trades.

    Checks:
    1.  **Intra-day**: Close Quantity = Open Quantity + Traded Today
    2.  **Inter-day**: Open Quantity(T) = Close Quantity(T-1)

    Methodology:
    1.  **Accounting Identity Check**: Verifies that the fundamental accounting equations hold.
    2.  **Statistical Analysis**: Calculates Z-Scores of the percentage difference (break size)
        relative to the position size.
    3.  **Hybrid Thresholds**:
        -   **High Severity**: Massive break (> 1000%) OR Extreme outlier (Z > 5).
        -   **Medium Severity**: Significant break (> 30%) OR Significant outlier (Z > 3).
        -   **Low Severity**: Minor break.
    """

    def validate(self) -> List[ValidationError]:
        required_cols = [
            "Date",
            "P_Ticker",
            "Close Quantity",
            "Open Quantity",
            "Traded Today",
        ]
        # Check if columns exist
        missing = [col for col in required_cols if col not in self.positions_df.columns]
        if missing:
            return []

        df = self.positions_df.copy()

        # Ensure numeric
        # We do NOT fillna(0) for any column. Missing data implies we cannot validate.
        # This includes Traded Today - if it's missing, we cannot assume it's 0.
        for col in ["Close Quantity", "Open Quantity", "Traded Today"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # 1. Intra-day Reconciliation
        # Close = Open + Traded
        df["Expected_Close"] = df["Open Quantity"] + df["Traded Today"]
        df["Diff_Intra"] = df["Close Quantity"] - df["Expected_Close"]

        # Calculate % Diff for Z-Score
        # Use Expected_Close as base, handle 0
        df["Pct_Diff_Intra"] = df["Diff_Intra"] / df["Expected_Close"].replace(0, 1)
        df["Z_Score_Intra"] = self.calculate_z_scores(df["Pct_Diff_Intra"])

        # 2. Inter-day Reconciliation
        # Sort
        df = df.sort_values(by=["P_Ticker", "Date"])
        df["Prev_Close"] = df.groupby("P_Ticker")["Close Quantity"].shift(1)
        df["Diff_Inter"] = df["Open Quantity"] - df["Prev_Close"]

        # Calculate % Diff for Z-Score
        # Use Prev_Close as base, handle 0
        df["Pct_Diff_Inter"] = df["Diff_Inter"] / df["Prev_Close"].replace(0, 1)
        df["Z_Score_Inter"] = self.calculate_z_scores(df["Pct_Diff_Inter"])

        # Filter errors
        tolerance = 1e-6

        # Intra-day errors
        intra_errors = df[df["Diff_Intra"].abs() > tolerance].copy()

        # Calculate severity based on % error relative to position size
        # Use min(abs(Actual), abs(Expected)) as denominator to handle asymmetry (e.g. 1 -> 100 vs 100 -> 1)
        intra_errors["Min_Base"] = (
            intra_errors[["Close Quantity", "Expected_Close"]]
            .abs()
            .min(axis=1)
            .replace(0, 1)
        )
        intra_errors["Pct_Error"] = (
            intra_errors["Diff_Intra"].abs() / intra_errors["Min_Base"]
        )

        for _, row in intra_errors.iterrows():
            pct = row["Pct_Error"]
            z_score = abs(row["Z_Score_Intra"])

            # Severity Logic (Hybrid)
            # High: > 1000% (Factor 10) OR (Z > 5 AND > 5%)
            # Medium: > 30% OR (Z > 3 AND > 5%)
            # Low: <= 30%

            if pct > 10.0 or (z_score > 5 and pct > 0.05):
                severity = "High"
            elif pct > 0.30 or (z_score > 3 and pct > 0.05):
                severity = "Medium"
            else:
                severity = "Low"

            # Construct detailed description
            reason = []
            if pct > 10.0:
                reason.append(f"Massive Break > 1000% ({pct:.1%})")
            elif pct > 0.30:
                reason.append(f"Significant Break > 30% ({pct:.1%})")

            if z_score > 5:
                reason.append(f"Extreme Statistical Outlier (Z={z_score:.1f} > 5)")
            elif z_score > 3:
                reason.append(f"Statistical Outlier (Z={z_score:.1f} > 3)")

            if not reason:
                reason.append("Minor Break")

            reason_str = " | ".join(reason)

            self.add_error(
                date=row["Date"],
                ticker=row["P_Ticker"],
                error_type="Reconciliation Error (Intra-day)",
                description=f"Intra-day Mismatch: Open {row['Open Quantity']:.2f} + Traded {row['Traded Today']:.2f} != Close {row['Close Quantity']:.2f}. Diff: {row['Diff_Intra']:.2f}. Flagged due to: {reason_str}",
                severity=severity,
            )

        # Inter-day errors
        # Ignore first day (Prev_Close is NaN)
        inter_errors = df[
            df["Diff_Inter"].notna() & (df["Diff_Inter"].abs() > tolerance)
        ].copy()

        inter_errors["Min_Base"] = (
            inter_errors[["Open Quantity", "Prev_Close"]]
            .abs()
            .min(axis=1)
            .replace(0, 1)
        )
        inter_errors["Pct_Error"] = (
            inter_errors["Diff_Inter"].abs() / inter_errors["Min_Base"]
        )

        for _, row in inter_errors.iterrows():
            pct = row["Pct_Error"]
            z_score = abs(row["Z_Score_Inter"])

            # Severity Logic (Hybrid)
            if pct > 10.0 or (z_score > 5 and pct > 0.05):
                severity = "High"
            elif pct > 0.30 or (z_score > 3 and pct > 0.05):
                severity = "Medium"
            else:
                severity = "Low"

            # Construct detailed description
            reason = []
            if pct > 10.0:
                reason.append(f"Massive Break > 1000% ({pct:.1%})")
            elif pct > 0.30:
                reason.append(f"Significant Break > 30% ({pct:.1%})")

            if z_score > 5:
                reason.append(f"Extreme Statistical Outlier (Z={z_score:.1f} > 5)")
            elif z_score > 3:
                reason.append(f"Statistical Outlier (Z={z_score:.1f} > 3)")

            if not reason:
                reason.append("Minor Break")

            reason_str = " | ".join(reason)

            self.add_error(
                date=row["Date"],
                ticker=row["P_Ticker"],
                error_type="Reconciliation Error (Inter-day)",
                description=f"Inter-day Mismatch: Open {row['Open Quantity']:.2f} != Prev Close {row['Prev_Close']:.2f}. Diff: {row['Diff_Inter']:.2f}. Flagged due to: {reason_str}",
                severity=severity,
            )

        return self.errors
