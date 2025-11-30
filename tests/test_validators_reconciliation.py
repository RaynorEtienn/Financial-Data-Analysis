import pandas as pd
from datetime import datetime
from src.validators.reconciliation import ReconciliationValidator


def test_reconciliation_validator_intra_day_success():
    data = {
        "Date": [datetime(2023, 1, 1)],
        "P_Ticker": ["AAPL"],
        "Open Quantity": [100],
        "Traded Today": [50],
        "Close Quantity": [150],  # 100 + 50 = 150
    }
    df = pd.DataFrame(data)
    validator = ReconciliationValidator(df, pd.DataFrame())
    errors = validator.validate()
    assert len(errors) == 0


def test_reconciliation_validator_intra_day_failure():
    data = {
        "Date": [datetime(2023, 1, 1)],
        "P_Ticker": ["AAPL"],
        "Open Quantity": [100],
        "Traded Today": [50],
        "Close Quantity": [140],  # Should be 150. Diff 10. Pct = 10/140 = 7% -> Low
    }
    df = pd.DataFrame(data)
    validator = ReconciliationValidator(df, pd.DataFrame())
    errors = validator.validate()
    assert len(errors) == 1
    assert errors[0].error_type == "Reconciliation Error (Intra-day)"
    assert errors[0].severity == "Low"


def test_reconciliation_validator_intra_day_failure_high_severity():
    data = {
        "Date": [datetime(2023, 1, 1)],
        "P_Ticker": ["AAPL"],
        "Open Quantity": [100],
        "Traded Today": [50],
        "Close Quantity": [200],  # Should be 150. Diff 50.
        # Old Logic: Pct = 50/200 = 25% -> Low
        # New Logic: Min_Base = min(200, 150) = 150. Pct = 50/150 = 33.3% -> Medium (>30%)
    }
    df = pd.DataFrame(data)
    validator = ReconciliationValidator(df, pd.DataFrame())
    errors = validator.validate()
    assert len(errors) == 1
    assert errors[0].severity == "Medium"


def test_reconciliation_validator_intra_day_failure_medium_severity():
    data = {
        "Date": [datetime(2023, 1, 1)],
        "P_Ticker": ["AAPL"],
        "Open Quantity": [100],
        "Traded Today": [50],
        "Close Quantity": [
            300
        ],  # Should be 150. Diff 150. Pct = 150/300 = 50% -> Medium (>30%)
    }
    df = pd.DataFrame(data)
    validator = ReconciliationValidator(df, pd.DataFrame())
    errors = validator.validate()
    assert len(errors) == 1
    assert errors[0].severity == "Medium"


def test_reconciliation_validator_intra_day_failure_real_high_severity():
    data = {
        "Date": [datetime(2023, 1, 1)],
        "P_Ticker": ["AAPL"],
        "Open Quantity": [100],
        "Traded Today": [50],
        "Close Quantity": [
            2000
        ],  # Should be 150. Diff 1850. Pct = 1850/2000 = 92.5% -> Medium (Wait, >1000% is High)
        # Let's make it > 1000%
        # Expected 150. Actual 2000. Diff 1850. Pct 92%.
        # Let's try Expected 10. Actual 200. Diff 190. Pct 190/200 = 95%.
        # We need > 1000% (10x).
        # Expected 10. Actual 1000. Diff 990. Pct 990/1000 = 99%.
        # Wait, Pct is Diff / Close.
        # If Diff is 10x Close, then Close must be small? No.
        # If Close = 1000. Expected = 100. Diff = 900. Pct = 0.9 (90%).
        # If Close = 1000. Expected = 10. Diff = 990. Pct = 0.99 (99%).
        # Max Pct is 1.0 (100%) if Expected is 0.
        # Ah, the formula is Diff / Close.
        # If I have 100 shares and I am missing 1000 shares.
        # Close = 1100. Expected = 100. Diff = 1000. Pct = 1000/1100 = 0.9.
        # My formula `pct > 10.0` (1000%) is impossible if denominator is Close Quantity and Diff is part of it?
        # No, Diff = Close - Expected.
        # If Close = 100. Expected = 10000. Diff = -9900.
        # Pct = 9900 / 100 = 99.0 (9900%).
        # So High Severity is when Expected is HUGE compared to Close.
        "Close Quantity": [10],
        "Open Quantity": [1000],
        "Traded Today": [0],
        # Expected = 1000. Close = 10. Diff = -990.
        # Pct = 990 / 10 = 99.0 (> 10.0). -> High
    }
    df = pd.DataFrame(data)
    validator = ReconciliationValidator(df, pd.DataFrame())
    errors = validator.validate()
    assert len(errors) == 1
    assert errors[0].severity == "High"


def test_reconciliation_validator_inter_day_failure():
    data = {
        "Date": [datetime(2023, 1, 1), datetime(2023, 1, 2)],
        "P_Ticker": ["AAPL", "AAPL"],
        "Open Quantity": [
            100,
            160,
        ],  # Day 2 Open is 160, but Day 1 Close was 150. Diff 10. Pct 10/160 = 6% -> Low
        "Traded Today": [50, 0],
        "Close Quantity": [150, 160],
    }
    df = pd.DataFrame(data)
    validator = ReconciliationValidator(df, pd.DataFrame())
    errors = validator.validate()

    # Should have 1 error (Inter-day)
    assert len(errors) == 1
    assert errors[0].error_type == "Reconciliation Error (Inter-day)"
    assert errors[0].severity == "Low"
    assert "Diff: 10.00" in errors[0].description


def test_reconciliation_validator_inter_day_success():
    data = {
        "Date": [datetime(2023, 1, 1), datetime(2023, 1, 2)],
        "P_Ticker": ["AAPL", "AAPL"],
        "Open Quantity": [100, 150],
        "Traded Today": [50, 0],
        "Close Quantity": [150, 150],
    }
    # Day 1: Open 100 + Trade 50 = Close 150. (Intra OK)
    # Day 2: Open 150 == Prev Close 150. (Inter OK)
    df = pd.DataFrame(data)
    validator = ReconciliationValidator(df, pd.DataFrame())
    errors = validator.validate()
    assert len(errors) == 0


def test_reconciliation_validator_inter_day_failure_2():
    data = {
        "Date": [datetime(2023, 1, 1), datetime(2023, 1, 2)],
        "P_Ticker": ["AAPL", "AAPL"],
        "Open Quantity": [
            100,
            160,
        ],  # Day 2 Open is 160, but Day 1 Close was 150. Diff 10. Pct 10/160 = 6% -> Low
        "Traded Today": [50, 0],
        "Close Quantity": [150, 160],
    }
    df = pd.DataFrame(data)
    validator = ReconciliationValidator(df, pd.DataFrame())
    errors = validator.validate()

    # Should have 1 error (Inter-day)
    assert len(errors) == 1
    assert errors[0].error_type == "Reconciliation Error (Inter-day)"
    assert errors[0].severity == "Low"
    assert "Diff: 10.00" in errors[0].description


def test_reconciliation_validator_mixed_errors():
    data = {
        "Date": [datetime(2023, 1, 1), datetime(2023, 1, 2)],
        "P_Ticker": ["AAPL", "AAPL"],
        "Open Quantity": [100, 150],
        "Traded Today": [50, 10],
        "Close Quantity": [140, 160],
    }
    # Day 1: Open 100 + Trade 50 = 150. Actual 140. -> Intra-day Error.
    # Day 2: Open 150. Prev Close 140. -> Inter-day Error (150 != 140).
    # Day 2: Open 150 + Trade 10 = 160. Actual 160. -> Intra-day OK.

    df = pd.DataFrame(data)
    validator = ReconciliationValidator(df, pd.DataFrame())
    errors = validator.validate()

    assert len(errors) == 2

    intra = next(e for e in errors if "Intra-day" in e.error_type)
    inter = next(e for e in errors if "Inter-day" in e.error_type)

    assert intra.date == datetime(2023, 1, 1)
    assert inter.date == datetime(2023, 1, 2)


def test_reconciliation_validator_ignores_missing_data():
    data = {
        "Date": [datetime(2023, 1, 1), datetime(2023, 1, 2)],
        "P_Ticker": ["AAPL", "AAPL"],
        "Open Quantity": [100, 150],
        "Traded Today": [None, 0],  # Missing trade data on Day 1
        "Close Quantity": [150, 150],
    }
    # Day 1: Open 100. Traded NaN. Close 150.
    # Expected Close = 100 + NaN = NaN.
    # Diff = 150 - NaN = NaN.
    # Should be ignored.

    df = pd.DataFrame(data)
    validator = ReconciliationValidator(df, pd.DataFrame())
    errors = validator.validate()

    # Should have 0 errors
    assert len(errors) == 0
