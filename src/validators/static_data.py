from .base import BaseValidator, ValidationError
from typing import List
import pandas as pd


class StaticDataValidator(BaseValidator):
    """
    Validator for ensuring the consistency of static reference data.

    This validator checks that fields which should remain constant for a given ticker
    (e.g., Currency, Sector, Country) do not change over time.

    Methodology:
    1.  **Grouping**: Groups data by `P_Ticker`.
    2.  **Uniqueness Check**: For each static field, checks if there is more than one unique value.
    3.  **Reporting**: Flags tickers where static data flips or changes.

    Severity Levels:
    -   **High**: Currency change (fundamental break).
    -   **Medium**: Sector/Industry/Country change.
    -   **Low**: Name change (could be a corporate action or rebranding).
    """

    def validate(self) -> List[ValidationError]:
        """
        Executes the static data validation logic.

        Returns:
            List[ValidationError]: A list of detected static data errors.
        """
        df = self.positions_df.copy()

        # Define static columns and their severity if changed
        static_cols = {
            "Currency": "High",
            "Country": "Medium",
            "Sector": "Medium",
            "Industry": "Medium",
            "Short_Name": "Low",
        }

        # Filter only columns present in the dataframe
        present_cols = {k: v for k, v in static_cols.items() if k in df.columns}

        if not present_cols:
            return []

        # Group by Ticker
        for ticker, group in df.groupby("P_Ticker"):
            for col, severity in present_cols.items():
                unique_vals = group[col].unique()

                # Filter out NaNs/None/Empty strings if we want to be lenient about missing data
                # (DataCompletenessValidator handles missing data, here we check for CONFLICTS)
                # But if it flips from "USD" to NaN to "USD", is that a conflict? No.
                # If it flips from "USD" to "EUR", yes.
                valid_vals = [
                    v for v in unique_vals if pd.notna(v) and str(v).strip() != ""
                ]

                if len(valid_vals) > 1:
                    # We have a conflict
                    # We report it on the dates where the value changes?
                    # Or just report it generally for the ticker?
                    # Let's report it on the first date where a new value appears.

                    # Sort by date
                    group = group.sort_values("Date")
                    first_val = valid_vals[
                        0
                    ]  # Take the first valid value encountered as "Truth" (arbitrary but simple)

                    # Or better: find the mode
                    mode_val = pd.Series(valid_vals).mode()[
                        0
                    ]  # Not weighted by days, just values present
                    # Actually, let's weight by occurrence in the group
                    mode_val = group[col].mode()[0]

                    deviants = group[group[col] != mode_val]
                    # Filter out NaNs again from deviants
                    deviants = deviants[
                        deviants[col].notna()
                        & (deviants[col].astype(str).str.strip() != "")
                    ]

                    for _, row in deviants.iterrows():
                        self.add_error(
                            date=row["Date"],
                            ticker=ticker,
                            error_type="Static Data Inconsistency",
                            description=f"Static field '{col}' changed. Found '{row[col]}', expected consensus '{mode_val}'.",
                            severity=severity,
                        )

        return self.errors
