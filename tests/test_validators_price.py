import pytest
import pandas as pd
from datetime import datetime
from src.validators.price import PriceValidator


@pytest.fixture
def sample_data():
    # Spike case: 100 -> 150 -> 100
    dates = [datetime(2023, 1, 1), datetime(2023, 1, 2), datetime(2023, 1, 3)]
    data = {
        "Date": dates,
        "P_Ticker": ["AAPL", "AAPL", "AAPL"],
        "Price": [100.0, 150.0, 100.0],
    }
    return pd.DataFrame(data)


def test_price_validator_detects_spike(sample_data):
    validator = PriceValidator(sample_data, pd.DataFrame())
    errors = validator.validate()

    assert len(errors) == 1
    assert errors[0].ticker == "AAPL"
    assert errors[0].error_type == "Price Spike"
    assert "150.0" in errors[0].description


def test_price_validator_ignores_sustained_jump():
    dates = [datetime(2023, 1, 1), datetime(2023, 1, 2), datetime(2023, 1, 3)]
    data = {
        "Date": dates,
        "P_Ticker": ["GOOG", "GOOG", "GOOG"],
        "Price": [100.0, 150.0, 155.0],  # Sustained jump, should be ignored
    }
    df = pd.DataFrame(data)
    validator = PriceValidator(df, pd.DataFrame())
    errors = validator.validate()

    assert len(errors) == 0


def test_price_validator_detects_dip():
    dates = [datetime(2023, 1, 1), datetime(2023, 1, 2), datetime(2023, 1, 3)]
    data = {
        "Date": dates,
        "P_Ticker": ["MSFT", "MSFT", "MSFT"],
        "Price": [100.0, 50.0, 95.0],  # Dip, should be flagged
    }
    df = pd.DataFrame(data)
    validator = PriceValidator(df, pd.DataFrame())
    errors = validator.validate()

    assert len(errors) == 1
    assert errors[0].ticker == "MSFT"
    assert errors[0].error_type == "Price Spike"
    assert errors[0].severity == "High"  # ~50% change, so High (> 0.3)


def test_price_validator_severity_levels():
    # We need enough data points to establish a low standard deviation
    # so that small jumps are considered statistical outliers (Z > 3).
    dates = [datetime(2023, 1, i) for i in range(1, 21)]  # 20 days

    # Low severity: 6% change.
    # Z > 3 (outlier), but Magnitude (6%) < 10%. -> Low
    prices_low = [100.0] * 20
    prices_low[10] = 106.0

    data_low = {
        "Date": dates,
        "P_Ticker": ["LOW"] * 20,
        "Price": prices_low,
    }

    # Medium severity: 12% change.
    # Z > 3 (outlier), Magnitude (12%) > 10%. -> Medium
    prices_med = [100.0] * 20
    prices_med[10] = 112.0

    data_med = {
        "Date": dates,
        "P_Ticker": ["MED"] * 20,
        "Price": prices_med,
    }

    # High severity: 35% change.
    # Magnitude > 30%. -> High
    prices_high = [100.0] * 20
    prices_high[10] = 135.0

    data_high = {
        "Date": dates,
        "P_Ticker": ["HIGH"] * 20,
        "Price": prices_high,
    }

    df = pd.concat(
        [pd.DataFrame(data_low), pd.DataFrame(data_med), pd.DataFrame(data_high)]
    )
    validator = PriceValidator(df, pd.DataFrame())
    errors = validator.validate()

    low_error = next(e for e in errors if e.ticker == "LOW")
    med_error = next(e for e in errors if e.ticker == "MED")
    high_error = next(e for e in errors if e.ticker == "HIGH")

    assert low_error.severity == "Low"
    assert med_error.severity == "Medium"
    assert high_error.severity == "High"


def test_price_validator_ignores_sparse_data_jump():
    dates = [datetime(2023, 1, 1), datetime(2023, 1, 11), datetime(2023, 1, 21)]
    data = {
        "Date": dates,
        "P_Ticker": ["AMZN", "AMZN", "AMZN"],
        "Price": [100.0, 150.0, 100.0],  # 50% jump but over 10 days (5% daily avg)
    }
    df = pd.DataFrame(data)
    validator = PriceValidator(df, pd.DataFrame())
    errors = validator.validate()

    assert len(errors) == 0
