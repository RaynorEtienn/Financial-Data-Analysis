from .base import BaseValidator, ValidationError
from typing import List
import pandas as pd


class ReconciliationValidator(BaseValidator):
    """
    Validator for reconciling positions and trades.

    Checks:
    1. Intra-day: Close Quantity = Open Quantity + Traded Today
    2. Inter-day: Open Quantity(T) = Close Quantity(T-1)
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

        # 2. Inter-day Reconciliation
        # Sort
        df = df.sort_values(by=["P_Ticker", "Date"])
        df["Prev_Close"] = df.groupby("P_Ticker")["Close Quantity"].shift(1)
        df["Diff_Inter"] = df["Open Quantity"] - df["Prev_Close"]

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

            # Severity Logic (Updated Thresholds)
            # High: > 1000% (Factor 10)
            # Medium: > 30% (Previous High)
            # Low: <= 30% (Previous Medium + Low)
            if pct > 10.0:
                severity = "High"
            elif pct > 0.30:
                severity = "Medium"
            else:
                severity = "Low"

            self.add_error(
                date=row["Date"],
                ticker=row["P_Ticker"],
                error_type="Reconciliation Error (Intra-day)",
                description=f"Intra-day Mismatch: Open {row['Open Quantity']:.2f} + Traded {row['Traded Today']:.2f} != Close {row['Close Quantity']:.2f}. Diff: {row['Diff_Intra']:.2f}",
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

            # Severity Logic (Updated Thresholds)
            if pct > 10.0:
                severity = "High"
            elif pct > 0.30:
                severity = "Medium"
            else:
                severity = "Low"

            self.add_error(
                date=row["Date"],
                ticker=row["P_Ticker"],
                error_type="Reconciliation Error (Inter-day)",
                description=f"Inter-day Mismatch: Open {row['Open Quantity']:.2f} != Prev Close {row['Prev_Close']:.2f}. Diff: {row['Diff_Inter']:.2f}",
                severity=severity,
            )

        return self.errors
