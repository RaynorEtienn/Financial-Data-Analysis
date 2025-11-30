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
    dates = [datetime(2023, 1, 1), datetime(2023, 1, 2), datetime(2023, 1, 3)]

    # Low severity: ~12% change (Threshold is 10%, Low is <= 15%)
    data_low = {
        "Date": dates,
        "P_Ticker": ["LOW", "LOW", "LOW"],
        "Price": [100.0, 112.0, 100.0],
    }

    # Medium severity: ~25% change (Medium is > 15% and <= 30%)
    data_med = {
        "Date": dates,
        "P_Ticker": ["MED", "MED", "MED"],
        "Price": [100.0, 125.0, 100.0],
    }

    df = pd.concat([pd.DataFrame(data_low), pd.DataFrame(data_med)])
    validator = PriceValidator(df, pd.DataFrame())
    errors = validator.validate()

    low_error = next(e for e in errors if e.ticker == "LOW")
    med_error = next(e for e in errors if e.ticker == "MED")

    assert low_error.severity == "Low"
    assert med_error.severity == "Medium"


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
