from .base import BaseValidator, ValidationError
from typing import List
import pandas as pd
import numpy as np


class WeightValidator(BaseValidator):
    """
    Validator for verifying portfolio weight calculations.

    This validator ensures that the reported 'Closing Weights' match the weights implied
    by the 'Value in USD' relative to the total portfolio value.

    Methodology:
    1.  **Total Value Calculation**: Sums 'Value in USD' for each date to get the daily NAV.
    2.  **Implied Weight Calculation**: Computes Weight = Value / Total Value.
    3.  **Statistical Analysis**: Calculates Z-Scores of the weight differences.
    4.  **Hybrid Thresholds**:
        -   **High Severity**: Extreme outlier (Z > 5) OR Extreme deviation (> 5%).
        -   **Medium Severity**: Significant outlier (Z > 3) OR Significant deviation (> 1%).
        -   **Low Severity**: Minor deviation (> 0.1%).

    Severity Levels:
    -   **High**: Z > 5 or Diff > 5%
    -   **Medium**: Z > 3 or Diff > 1%
    -   **Low**: Diff > 0.1%
    """

    def validate(self) -> List[ValidationError]:
        """
        Executes the weight validation logic.

        Returns:
            List[ValidationError]: A list of detected weight errors.
        """
        df = self.positions_df.copy()

        required_cols = ["Date", "Value in USD", "Closing Weights", "P_Ticker"]
        if not all(col in df.columns for col in required_cols):
            return []

        # Ensure numeric types
        df["Value in USD"] = pd.to_numeric(df["Value in USD"], errors="coerce").fillna(
            0
        )

        # Handle percentage strings in Closing Weights if necessary
        if df["Closing Weights"].dtype == "object":
            df["Closing Weights"] = (
                df["Closing Weights"]
                .astype(str)
                .str.replace("%", "")
                .str.replace(",", "")
            )
            df["Closing Weights"] = (
                pd.to_numeric(df["Closing Weights"], errors="coerce") / 100.0
            )
        else:
            df["Closing Weights"] = pd.to_numeric(
                df["Closing Weights"], errors="coerce"
            )

        # Detect if Closing Weights are in 0-100 scale (percentages) or 0-1 scale (decimals)
        daily_weight_sums = df.groupby("Date")["Closing Weights"].sum()
        median_sum = daily_weight_sums.median()

        if (
            median_sum > 10.0
        ):  # If sum is ~100 (or even > 10), it's definitely percentage scale
            df["Closing Weights"] = df["Closing Weights"] / 100.0

        # Calculate Daily Total Value
        daily_totals = df.groupby("Date")["Value in USD"].transform("sum")

        # Calculate Implied Weight
        df["Implied_Weight"] = df["Value in USD"] / daily_totals.replace(
            0, 1
        )  # replace 0 to avoid inf

        # Compare
        df["Diff"] = df["Implied_Weight"] - df["Closing Weights"]
        df["Abs_Diff"] = df["Diff"].abs()

        # Calculate Z-Scores for the differences
        df["Z_Score"] = self.calculate_z_scores(df["Diff"])

        # Filter errors
        # We only care if the difference is statistically significant OR large in magnitude
        # Threshold: Z > 3 OR Abs_Diff > 0.001 (0.1%)
        # EXCLUSION: Ignore rows where Value in USD is 0 (likely missing data/quantity) or Closing Weights is NaN
        # The user explicitly requested to let MissingDataValidator handle missing data issues.
        valid_data_mask = (df["Value in USD"] != 0) & (df["Closing Weights"].notna())

        potential_errors = df[
            ((df["Z_Score"].abs() > 3) | (df["Abs_Diff"] > 0.001)) & valid_data_mask
        ]

        for _, row in potential_errors.iterrows():
            diff = row["Abs_Diff"]
            z_score = abs(row["Z_Score"])

            # Severity Logic
            if z_score > 5 or diff > 0.05:  # > 5% or 5 sigma
                severity = "High"
            elif z_score > 3 or diff > 0.01:  # > 1% or 3 sigma
                severity = "Medium"
            else:
                severity = "Low"

            # Construct reason
            reason = []
            if diff > 0.05:
                reason.append(f"Absolute Diff > 5% ({diff:.1%})")
            elif diff > 0.01:
                reason.append(f"Absolute Diff > 1% ({diff:.1%})")

            if z_score > 5:
                reason.append(f"Extreme Statistical Outlier (Z={z_score:.1f})")
            elif z_score > 3:
                reason.append(f"Statistical Outlier (Z={z_score:.1f})")

            reason_str = " | ".join(reason)

            self.add_error(
                date=row["Date"],
                ticker=row["P_Ticker"],
                error_type="Weight Mismatch",
                description=f"Reported Weight {row['Closing Weights']:.4%} vs Implied {row['Implied_Weight']:.4%}. Flagged due to: {reason_str}",
                severity=severity,
            )

        return self.errors
