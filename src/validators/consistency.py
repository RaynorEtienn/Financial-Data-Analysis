from .base import BaseValidator, ValidationError
from typing import List
import pandas as pd


class ConsistencyValidator(BaseValidator):
    """
    Validator for checking cross-referencing data consistency.

    Primary Check:
    Trade Price vs. Market Price Consistency

    This validator compares the price at which a trade was executed ('Trade Price')
    against the market price ('Price') reported for that day.

    Methodology:
    1.  **Statistical Analysis**: Calculates the Z-Score of the percentage difference between
        Trade Price and Market Price across the dataset.
    2.  **Hybrid Thresholds**: Flags errors based on a combination of statistical significance
        (Z-Score) and absolute magnitude (Percentage Difference).
        -   **High Severity**: Extreme outlier (Z > 5) OR Extreme deviation (> 20%).
        -   **Medium Severity**: Significant outlier (Z > 3) OR Significant deviation (> 10%).
        -   **Low Severity**: Minor outlier (Z > 2) OR Minor deviation (> 5%).
    3.  **Minimum Floor**: Ignores statistical outliers if the absolute difference is negligible (< 5%).
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

        # Calculate Z-Scores for the percentage difference
        # This helps identify statistical outliers relative to the dataset's volatility
        trades_df["Z_Score"] = self.calculate_z_scores(trades_df["Pct_Diff"])

        for _, row in trades_df.iterrows():
            pct = row["Pct_Diff"]
            z_score = abs(row["Z_Score"])

            # Hybrid Approach:
            # We flag an error if it is BOTH a statistical outlier (Z > 3)
            # AND has a minimum material deviation (Floor > 5%).
            # This prevents flagging tiny deviations in very clean datasets.

            severity = None

            # High Severity: Extreme outlier (> 5 sigma) OR Extreme absolute deviation (> 20%)
            if (z_score > 5 and pct > 0.05) or (pct > 0.20):
                severity = "High"
            # Medium Severity: Significant outlier (> 3 sigma) OR Significant absolute deviation (> 10%)
            elif (z_score > 3 and pct > 0.05) or (pct > 0.10):
                severity = "Medium"
            # Low Severity: Minor outlier (> 2 sigma) OR Minor absolute deviation (> 5%)
            elif (z_score > 2 and pct > 0.05) or (pct > 0.05):
                severity = "Low"

            if severity:
                # Construct detailed description
                reason = []
                if pct > 0.20:
                    reason.append(f"Absolute Diff > 20% ({pct:.1%})")
                elif pct > 0.10:
                    reason.append(f"Absolute Diff > 10% ({pct:.1%})")

                if z_score > 5:
                    reason.append(f"Extreme Statistical Outlier (Z={z_score:.1f} > 5)")
                elif z_score > 3:
                    reason.append(f"Statistical Outlier (Z={z_score:.1f} > 3)")

                reason_str = " | ".join(reason)

                self.add_error(
                    date=row["Date"],
                    ticker=row["P_Ticker"],
                    error_type="Consistency Error (Trade vs Market)",
                    description=f"Price Mismatch: Trade Price {row['Trade Price']:.2f} vs Market Price {row['Price']:.2f}. Diff: {pct:.1%} (Z={z_score:.1f}). Flagged due to: {reason_str}",
                    severity=severity,
                )

        return self.errors
