from .base import BaseValidator, ValidationError
from typing import List


class PriceValidator(BaseValidator):
    """
    Validator for detecting price anomalies in the portfolio data.

    This validator implements a "Spike Detection" algorithm to identify isolated price errors
    while ignoring sustained market movements. It uses Geometric Daily Returns (Compound Daily Growth Rate)
    to normalize price changes across varying time gaps.

    Methodology:
    1.  **Time Normalization**: Calculates 'Implied Daily Return' to handle irregular time gaps.
        Formula: (Price_t / Price_{t-1})^(1 / Days_Diff) - 1
    2.  **Statistical Analysis**: Calculates Z-Scores for these daily returns per ticker.
    3.  **Hybrid Spike Detection**: Flags a record if:
        -   It represents a significant change from BOTH the previous and next record.
        -   The direction is consistent (e.g., Up-then-Down or Down-then-Up).
        -   The change is a statistical outlier (Z > 3) OR a massive absolute change (> 20%).
        -   The change exceeds a minimum floor (5%) to filter noise.

    Severity Levels:
    -   **High**: Extreme outlier (Z > 5) OR Extreme magnitude (> 30%).
    -   **Medium**: Significant outlier (Z > 3) OR Significant magnitude (> 15%).
    -   **Low**: Minor outlier.
    """

    def validate(self) -> List[ValidationError]:
        """
        Executes the price validation logic.

        Returns:
            List[ValidationError]: A list of detected price spikes.
        """
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

            # Calculate Z-Scores for the daily changes
            # This adapts to the volatility of the specific ticker
            group["Z_Score_Prev"] = self.calculate_z_scores(group["Daily_Change_Prev"])
            group["Z_Score_Next"] = self.calculate_z_scores(group["Daily_Change_Next"])

            # Hybrid Approach for Spike Detection
            # We flag a spike if:
            # 1. The change is a statistical outlier (Z > 3) OR a massive absolute change (> 20%)
            # 2. The change exceeds a minimum floor (5%) to avoid noise in stable assets
            # 3. This happens on BOTH sides (Prev and Next)
            # 4. The direction is consistent (Up-Down or Down-Up)

            floor = 0.05

            # Condition 1: Significant change from previous
            is_outlier_prev = group["Z_Score_Prev"].abs() > 3
            is_large_prev = group["Daily_Change_Prev"].abs() > 0.20
            above_floor_prev = group["Daily_Change_Prev"].abs() > floor
            cond1 = (is_outlier_prev & above_floor_prev) | is_large_prev

            # Condition 2: Significant change from next
            is_outlier_next = group["Z_Score_Next"].abs() > 3
            is_large_next = group["Daily_Change_Next"].abs() > 0.20
            above_floor_next = group["Daily_Change_Next"].abs() > floor
            cond2 = (is_outlier_next & above_floor_next) | is_large_next

            # Condition 3: Direction consistency (Peak or Valley)
            cond3 = (group["Daily_Change_Prev"] * group["Daily_Change_Next"]) > 0

            outliers = group[cond1 & cond2 & cond3]

            for _, row in outliers.iterrows():
                # Determine severity based on Z-Score and Magnitude
                mag_prev = abs(row["Daily_Change_Prev"])
                mag_next = abs(row["Daily_Change_Next"])
                magnitude = (mag_prev + mag_next) / 2

                z_prev = abs(row["Z_Score_Prev"])
                z_next = abs(row["Z_Score_Next"])
                z_score = (z_prev + z_next) / 2

                # High: Extreme outlier (> 5 sigma) OR Extreme magnitude (> 30%)
                if (z_score > 5 and magnitude > 0.10) or magnitude > 0.30:
                    severity = "High"
                # Medium: Significant outlier (> 3 sigma) OR Significant magnitude (> 15%)
                elif (z_score > 3 and magnitude > 0.10) or magnitude > 0.15:
                    severity = "Medium"
                # Low: Minor outlier
                else:
                    severity = "Low"

                # Construct detailed description
                reason = []
                if magnitude > 0.20:
                    reason.append(f"Absolute Change > 20% ({magnitude:.1%})")

                if z_score > 5:
                    reason.append(f"Extreme Statistical Outlier (Z={z_score:.1f} > 5)")
                elif z_score > 3:
                    reason.append(f"Statistical Outlier (Z={z_score:.1f} > 3)")

                reason_str = " | ".join(reason)

                self.add_error(
                    date=row["Date"],
                    ticker=ticker,
                    error_type="Price Spike",
                    description=f"Price spike detected: {row['Price']} (Prev: {row['Prev_Price']}, Next: {row['Next_Price']}). Flagged due to: {reason_str}",
                    severity=severity,
                )

        return self.errors
