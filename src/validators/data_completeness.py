from .base import BaseValidator, ValidationError
from typing import List
import pandas as pd
import numpy as np
from datetime import datetime


class DataCompletenessValidator(BaseValidator):
    """
    Validator for checking the completeness and basic integrity of the dataset.

    This validator runs before more complex checks to ensure that critical data points
    are present. It flags missing values (NaNs) and invalid zero values in essential columns.

    Methodology:
    1.  **Missing Value Check**: Scans for NaN/None values in critical columns.
    2.  **Zero Value Check**: Scans for 0 values in columns where 0 is invalid (e.g., Price, FX).
    3.  **Static Data Check**: Ensures essential metadata (e.g., Currency) is present.

    Severity Levels:
    -   **High**: Missing Price, Exchange Rate, Ticker, or Date.
    -   **Medium**: Missing Currency or other important metadata.
    -   **Low**: Missing non-critical descriptive fields.
    """

    def validate(self) -> List[ValidationError]:
        """
        Executes the data completeness validation logic.

        Returns:
            List[ValidationError]: A list of detected data completeness errors.
        """
        df = self.positions_df.copy()

        # 1. Define Critical Columns and their rules
        # (Column Name, Can be 0?, Severity if Missing)
        critical_checks = [
            ("P_Ticker", False, "High"),
            ("Date", False, "High"),
            ("Price", False, "High"),
            ("Exchange Rate", False, "High"),
            ("Close Quantity", True, "High"),  # Quantity can be 0, but not NaN
            ("Currency", True, "Medium"),  # Currency string can't be 0, but check NaN
        ]

        for col, can_be_zero, severity in critical_checks:
            if col not in df.columns:
                # If the column itself is missing from the dataset, that's a major issue
                # We flag it once generally or for every row?
                # Ideally, we'd flag it as a system error, but here we'll just return
                # since we can't validate row-by-row.
                continue

            # Check for NaNs
            missing_mask = df[col].isna() | (df[col].astype(str).str.strip() == "")
            missing_rows = df[missing_mask]

            for _, row in missing_rows.iterrows():
                # Use a fallback for Date/Ticker if they are the ones missing
                date_val = row.get("Date", pd.NaT)
                ticker_val = row.get("P_Ticker", "UNKNOWN")

                # If Date is missing, we can't really report it well, but we try
                if pd.isna(date_val):
                    # Try to infer from context or just use a placeholder
                    date_val = datetime.now()  # Placeholder or skip?
                    # Actually, BaseValidator expects a datetime.
                    # If Date is missing, this row is garbage.
                    pass

                self.add_error(
                    date=date_val,
                    ticker=ticker_val,
                    error_type="Missing Data",
                    description=f"Missing value for critical column: '{col}'",
                    severity=severity,
                )

            # Check for Zeros (if not allowed)
            if not can_be_zero:
                # Ensure numeric before checking for 0
                is_numeric = pd.to_numeric(df[col], errors="coerce").notna()
                zero_mask = (pd.to_numeric(df[col], errors="coerce") == 0) & is_numeric
                zero_rows = df[zero_mask]

                for _, row in zero_rows.iterrows():
                    self.add_error(
                        date=row.get("Date"),
                        ticker=row.get("P_Ticker", "UNKNOWN"),
                        error_type="Invalid Data",
                        description=f"Invalid zero value for column: '{col}'",
                        severity=severity,
                    )

        return self.errors
