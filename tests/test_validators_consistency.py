import unittest
import pandas as pd
import numpy as np
from src.validators.consistency import ConsistencyValidator


class TestConsistencyValidator(unittest.TestCase):
    def validate(self, df):
        # Helper to initialize and run validator
        # We pass df as positions_df. trades_df is not used by this validator, so we pass empty.
        validator = ConsistencyValidator(df, pd.DataFrame())
        return validator.validate()

    def test_no_trades_ignored(self):
        """Test that rows where 'Traded Today' is 0 or missing are ignored."""
        df = pd.DataFrame(
            {
                "Date": [pd.Timestamp("2023-01-01"), pd.Timestamp("2023-01-02")],
                "P_Ticker": ["AAPL", "GOOG"],
                "Traded Today": [0, 0],
                "Trade Price": [100.0, 100.0],
                "Price": [150.0, 200.0],  # Huge difference, but should be ignored
            }
        )

        issues = self.validate(df)
        self.assertEqual(len(issues), 0, "Should ignore rows with no trades today")

    def test_perfect_match(self):
        """Test that matching prices produce no errors."""
        df = pd.DataFrame(
            {
                "Date": [pd.Timestamp("2023-01-01")],
                "P_Ticker": ["AAPL"],
                "Traded Today": [100],
                "Trade Price": [100.0],
                "Price": [100.0],
            }
        )

        issues = self.validate(df)
        self.assertEqual(len(issues), 0, "Should find no issues for matching prices")

    def test_small_deviation_ignored(self):
        """Test that deviations below 5% are ignored."""
        df = pd.DataFrame(
            {
                "Date": [pd.Timestamp("2023-01-01")],
                "P_Ticker": ["AAPL"],
                "Traded Today": [100],
                "Trade Price": [100.0],
                "Price": [104.0],  # 4% difference
            }
        )

        issues = self.validate(df)
        self.assertEqual(len(issues), 0, "Should ignore deviations < 5%")

    def test_low_severity(self):
        """Test detection of Low severity (5-10%)."""
        df = pd.DataFrame(
            {
                "Date": [pd.Timestamp("2023-01-01")],
                "P_Ticker": ["AAPL"],
                "Traded Today": [100],
                "Trade Price": [108.0],  # 8% difference relative to Price 100
                "Price": [100.0],
            }
        )

        issues = self.validate(df)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, "Low")
        self.assertIn("8.0%", issues[0].description)

    def test_medium_severity(self):
        """Test detection of Medium severity (10-20%)."""
        df = pd.DataFrame(
            {
                "Date": [pd.Timestamp("2023-01-01")],
                "P_Ticker": ["AAPL"],
                "Traded Today": [100],
                "Trade Price": [115.0],  # 15% difference relative to Price 100
                "Price": [100.0],
            }
        )

        issues = self.validate(df)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, "Medium")

    def test_high_severity(self):
        """Test detection of High severity (>20%)."""
        df = pd.DataFrame(
            {
                "Date": [pd.Timestamp("2023-01-01")],
                "P_Ticker": ["AAPL"],
                "Traded Today": [100],
                "Trade Price": [130.0],  # 30% difference relative to Price 100
                "Price": [100.0],
            }
        )

        issues = self.validate(df)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, "High")

    def test_missing_data_handling(self):
        """Test handling of missing price data."""
        df = pd.DataFrame(
            {
                "Date": [pd.Timestamp("2023-01-01"), pd.Timestamp("2023-01-02")],
                "P_Ticker": ["AAPL", "GOOG"],
                "Traded Today": [100, 100],
                "Trade Price": [100.0, np.nan],
                "Price": [np.nan, 100.0],
            }
        )

        issues = self.validate(df)
        self.assertEqual(len(issues), 0, "Should ignore rows with missing data")

    def test_zero_price_handling(self):
        """Test handling of zero price to avoid division by zero."""
        df = pd.DataFrame(
            {
                "Date": [pd.Timestamp("2023-01-01")],
                "P_Ticker": ["AAPL"],
                "Traded Today": [100],
                "Trade Price": [100.0],
                "Price": [0.0],
            }
        )

        issues = self.validate(df)
        self.assertEqual(len(issues), 0)


if __name__ == "__main__":
    unittest.main()
