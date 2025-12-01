from .base import BaseValidator, ValidationError
from typing import List
import pandas as pd


class FXConsistencyValidator(BaseValidator):
    """
    Validator for ensuring consistent exchange rates across the portfolio.

    This validator checks that all assets denominated in the same currency use the
    same exchange rate on any given day.

    Methodology:
    1.  **Grouping**: Groups data by `Date` and `Currency`.
    2.  **Variance Check**: Checks if there are multiple unique `Exchange Rate` values for a group.
    3.  **Outlier Detection**: If multiple rates exist, identifies the most common rate (mode)
        and flags rows that deviate from it.

    Severity Levels:
    -   **High**: Deviation > 1% from the daily mode.
    -   **Medium**: Deviation <= 1% (minor inconsistency).
    """

    def validate(self) -> List[ValidationError]:
        """
        Executes the FX consistency validation logic.

        Returns:
            List[ValidationError]: A list of detected FX consistency errors.
        """
        df = self.positions_df.copy()

        required_cols = ["Date", "Currency", "Exchange Rate", "P_Ticker"]
        if not all(col in df.columns for col in required_cols):
            return []

        # Filter out rows with missing or zero FX/Currency
        df = df.dropna(subset=["Exchange Rate", "Currency"])
        df = df[df["Exchange Rate"] != 0]

        # Group by Date and Currency
        grouped = df.groupby(["Date", "Currency"])

        for (date, currency), group in grouped:
            # Skip if only one record
            if len(group) < 2:
                continue

            unique_rates = group["Exchange Rate"].unique()

            # If only one unique rate, we are good
            if len(unique_rates) == 1:
                continue

            # If multiple rates, find the mode (most common rate)
            mode_rate = group["Exchange Rate"].mode()[0]

            # Identify deviants
            deviants = group[group["Exchange Rate"] != mode_rate]

            for _, row in deviants.iterrows():
                rate = row["Exchange Rate"]

                # Calculate deviation percentage
                deviation = abs(rate - mode_rate) / mode_rate

                if deviation > 0.01:
                    severity = "High"
                else:
                    severity = "Medium"

                self.add_error(
                    date=date,
                    ticker=row["P_Ticker"],
                    error_type="FX Inconsistency",
                    description=f"FX Rate {rate} deviates from daily consensus {mode_rate} for {currency}. Deviation: {deviation:.2%}",
                    severity=severity,
                )

        return self.errors
