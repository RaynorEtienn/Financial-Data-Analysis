import unittest
import pandas as pd
import numpy as np
from src.validators.consistency import ConsistencyValidator


class TestConsistencyValidator(unittest.TestCase):
    def validate(self, df):
        # Helper to initialize and run validator
        validator = ConsistencyValidator(df, pd.DataFrame())
        return validator.validate()

    def test_no_trades_ignored(self):
        """Test that rows where 'Traded Today' is 0 or missing are ignored."""
        # Create enough data to avoid empty dataframe issues, though logic filters them out first
        df = pd.DataFrame(
            {
                "Date": [pd.Timestamp("2023-01-01")] * 5,
                "P_Ticker": ["AAPL"] * 5,
                "Traded Today": [0, 0, 0, 0, 0],
                "Trade Price": [100.0] * 5,
                "Price": [150.0] * 5,  # Huge difference, but should be ignored
            }
        )

        issues = self.validate(df)
        self.assertEqual(len(issues), 0, "Should ignore rows with no trades today")

    def test_statistical_outlier_detection(self):
        """Test that a statistical outlier (high Z-score) is detected."""
        # Create a dataset with low variance (normal trades)
        # Most trades have ~1% difference
        data = {
            "Date": [pd.Timestamp("2023-01-01")] * 20,
            "P_Ticker": ["AAPL"] * 20,
            "Traded Today": [100] * 20,
            "Trade Price": [100.0] * 20,
            "Price": [101.0] * 19
            + [115.0],  # 19 normal (1% diff), 1 outlier (15% diff)
        }
        df = pd.DataFrame(data)

        # The last row has 15% diff.
        # Mean diff is slightly > 1%. Std dev is small.
        # 15% should be a massive Z-score (> 3).
        # It is also > 5% floor.

        issues = self.validate(df)

        # Should find at least 1 error (the outlier)
        self.assertTrue(len(issues) >= 1)

        # Check the outlier
        outlier_issue = issues[-1]
        self.assertIn("Price Mismatch", outlier_issue.description)
        self.assertIn("Z=", outlier_issue.description)
        # 15% diff is likely Medium or High depending on exact Z-score calculation
        self.assertTrue(outlier_issue.severity in ["Medium", "High"])

    def test_minimum_floor_logic(self):
        """Test that high Z-scores are ignored if the absolute difference is below the floor (5%)."""
        # Very tight dataset: 0.1% differences
        # One "outlier" with 2% difference.
        # Z-score will be huge (2.0 is 20x the mean of 0.1).
        # But 2% < 5% floor.

        data = {
            "Date": [pd.Timestamp("2023-01-01")] * 20,
            "P_Ticker": ["AAPL"] * 20,
            "Traded Today": [100] * 20,
            "Trade Price": [100.0] * 20,
            "Price": [100.1] * 19 + [102.0],  # 19 normal (0.1%), 1 outlier (2.0%)
        }
        df = pd.DataFrame(data)

        issues = self.validate(df)
        self.assertEqual(
            len(issues), 0, "Should ignore statistical outliers below 5% absolute floor"
        )

    def test_absolute_threshold_fallback(self):
        """Test that massive absolute deviations are caught even if Z-score logic is weird or if it's the only data."""
        # If we have a high variance dataset, Z-scores might be lower.
        # But > 20% should always be High.

        # Create a chaotic dataset where everything is all over the place, so std dev is high.
        # But one is 50% off.
        prices = [100.0 + i for i in range(20)]  # 100 to 119
        trade_prices = [100.0] * 20

        # Add one massive error
        prices.append(200.0)  # 100% diff
        trade_prices.append(100.0)

        df = pd.DataFrame(
            {
                "Date": [pd.Timestamp("2023-01-01")] * 21,
                "P_Ticker": ["AAPL"] * 21,
                "Traded Today": [100] * 21,
                "Trade Price": trade_prices,
                "Price": prices,
            }
        )

        issues = self.validate(df)

        # The last one is 100% diff. Should be High.
        found_high = False
        for issue in issues:
            if "100.0%" in issue.description or "High" == issue.severity:
                found_high = True

        self.assertTrue(
            found_high, "Should detect massive absolute deviation as High severity"
        )

    def test_missing_data_handling(self):
        """Test handling of missing price data."""
        df = pd.DataFrame(
            {
                "Date": [pd.Timestamp("2023-01-01")] * 5,
                "P_Ticker": ["AAPL"] * 5,
                "Traded Today": [100] * 5,
                "Trade Price": [100.0, np.nan, 100.0, 100.0, 100.0],
                "Price": [np.nan, 100.0, 100.0, 100.0, 100.0],
            }
        )

        issues = self.validate(df)
        self.assertEqual(len(issues), 0, "Should ignore rows with missing data")


if __name__ == "__main__":
    unittest.main()
