from .base import BaseValidator, ValidationError
from typing import List
import pandas as pd


class ConsistencyValidator(BaseValidator):
    """
    Validator for checking cross-referencing data consistency.

    Primary Check:
    Trade Price vs. Market Price Consistency

    This validator compares the price at which a trade was executed ('Trade Price')
    against the market price ('Price') reported for that day. Significant deviations
    suggest either a bad trade entry, a bad market price, or a timing mismatch.
    """

    def validate(self) -> List[ValidationError]:
        """
        Executes the consistency validation logic.

        Returns:
            List[ValidationError]: A list of detected consistency errors.
        """
        required_cols = [
            "Date",
            "P_Ticker",
            "Price",
            "Trade Price",
            "Traded Today",
        ]

        # Check for missing columns
        missing = [col for col in required_cols if col not in self.positions_df.columns]
        if missing:
            return []

        df = self.positions_df.copy()

        # Ensure numeric types
        numeric_cols = ["Price", "Trade Price", "Traded Today"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # Filter for rows where a trade actually occurred
        # We only care about consistency if there was a trade
        trades_df = df[df["Traded Today"].abs() > 0].copy()

        if trades_df.empty:
            return []

        # Calculate deviation
        # Deviation = |Trade Price - Market Price| / Market Price
        # We use Market Price as the base. If Market Price is 0/NaN, we skip.

        # Filter out invalid prices
        trades_df = trades_df[
            (trades_df["Price"].notna())
            & (trades_df["Price"] != 0)
            & (trades_df["Trade Price"].notna())
            & (trades_df["Trade Price"] != 0)
        ].copy()

        trades_df["Diff"] = (trades_df["Trade Price"] - trades_df["Price"]).abs()
        trades_df["Pct_Diff"] = trades_df["Diff"] / trades_df["Price"].abs()

        for _, row in trades_df.iterrows():
            pct = row["Pct_Diff"]

            # Thresholds
            # Market prices are usually closing prices. Trade prices are averages over the day.
            # Some deviation is expected (intraday volatility).
            # However, large deviations (>10-20%) are suspicious for liquid assets.

            # Severity Logic
            if pct > 0.20:  # > 20% deviation -> High
                severity = "High"
            elif pct > 0.10:  # > 10% deviation -> Medium
                severity = "Medium"
            elif pct > 0.05:  # > 5% deviation -> Low
                severity = "Low"
            else:
                continue

            self.add_error(
                date=row["Date"],
                ticker=row["P_Ticker"],
                error_type="Consistency Error (Trade vs Market)",
                description=f"Price Mismatch: Trade Price {row['Trade Price']:.2f} vs Market Price {row['Price']:.2f}. Diff: {pct:.1%}",
                severity=severity,
            )

        return self.errors
