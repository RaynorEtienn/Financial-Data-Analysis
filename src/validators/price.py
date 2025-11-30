from .base import BaseValidator, ValidationError
from typing import List


class PriceValidator(BaseValidator):
    """
    Checks for inconsistent prices (jumping day to day).
    """

    def validate(self) -> List[ValidationError]:
        # Ensure we have necessary columns
        if (
            "P_Ticker" not in self.positions_df.columns
            or "Price" not in self.positions_df.columns
        ):
            return []

        # Sort by Ticker and Date
        df = self.positions_df.sort_values(by=["P_Ticker", "Date"])

        # Group by Ticker
        for ticker, group in df.groupby("P_Ticker"):
            group = group.sort_values("Date")

            # Shift to get neighbors
            group["Prev_Price"] = group["Price"].shift(1)
            group["Next_Price"] = group["Price"].shift(-1)

            # Calculate time diffs to normalize changes
            group["Prev_Date"] = group["Date"].shift(1)
            group["Next_Date"] = group["Date"].shift(-1)

            group["Days_Diff_Prev"] = (group["Date"] - group["Prev_Date"]).dt.days
            group["Days_Diff_Next"] = (group["Next_Date"] - group["Date"]).dt.days

            # Handle edge cases (first/last rows or duplicates)
            group["Days_Diff_Prev"] = group["Days_Diff_Prev"].replace(0, 1).fillna(1)
            group["Days_Diff_Next"] = group["Days_Diff_Next"].replace(0, 1).fillna(1)

            # Calculate Geometric Daily Returns (Industrial Grade)
            # Formula: (Price / Base_Price)^(1/Days) - 1
            # This accounts for compounding over time gaps.

            # 1. Compare with Previous
            ratio_prev = group["Price"] / group["Prev_Price"]
            group["Daily_Change_Prev"] = ratio_prev.pow(1 / group["Days_Diff_Prev"]) - 1

            # 2. Compare with Next
            ratio_next = group["Price"] / group["Next_Price"]
            group["Daily_Change_Next"] = ratio_next.pow(1 / group["Days_Diff_Next"]) - 1

            threshold = 0.10

            # Check for spikes
            # 1. Significant change from previous (normalized)
            cond1 = group["Daily_Change_Prev"].abs() > threshold
            # 2. Significant change from next (normalized)
            cond2 = group["Daily_Change_Next"].abs() > threshold
            # 3. Direction consistency (Peak or Valley)
            # (Price - Prev) and (Price - Next) should have same sign
            # Which is equivalent to Pct_Change_Prev and Pct_Change_Next having same sign
            # (since Prices are positive)
            cond3 = (group["Daily_Change_Prev"] * group["Daily_Change_Next"]) > 0

            outliers = group[cond1 & cond2 & cond3]

            for _, row in outliers.iterrows():
                # Determine severity based on the magnitude of the spike (average daily change)
                mag_prev = abs(row["Daily_Change_Prev"])
                mag_next = abs(row["Daily_Change_Next"])
                magnitude = (mag_prev + mag_next) / 2

                if magnitude > 0.3:  # > 30% daily change
                    severity = "High"
                elif magnitude > 0.15:  # > 15% daily change
                    severity = "Medium"
                else:
                    severity = "Low"

                self.add_error(
                    date=row["Date"],
                    ticker=ticker,
                    error_type="Price Spike",
                    description=f"Price spike detected: {row['Price']} (Prev: {row['Prev_Price']}, Next: {row['Next_Price']})",
                    severity=severity,
                )

        return self.errors
