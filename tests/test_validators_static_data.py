import pandas as pd
from datetime import datetime
from src.validators.static_data import StaticDataValidator


def test_static_data_validator_no_errors():
    data = {
        "Date": [datetime(2023, 1, 1)] * 2,
        "P_Ticker": ["A", "A"],
        "Currency": ["USD", "USD"],
        "Sector": ["Tech", "Tech"],
    }
    df = pd.DataFrame(data)
    validator = StaticDataValidator(df, pd.DataFrame())
    errors = validator.validate()
    assert len(errors) == 0


def test_static_data_validator_detects_currency_change():
    data = {
        "Date": [datetime(2023, 1, 1), datetime(2023, 1, 2)],
        "P_Ticker": ["A", "A"],
        "Currency": ["USD", "EUR"],  # Change!
        "Sector": ["Tech", "Tech"],
    }
    df = pd.DataFrame(data)
    validator = StaticDataValidator(df, pd.DataFrame())
    errors = validator.validate()

    assert (
        len(errors) == 1
    )  # One of them is the deviant from the mode (if 2, mode is ambiguous, usually first)
    # With 2 values, mode might be the first one (USD). So EUR is deviant.
    assert errors[0].ticker == "A"
    assert errors[0].error_type == "Static Data Inconsistency"
    assert "Currency" in errors[0].description
    assert errors[0].severity == "High"


def test_static_data_validator_detects_sector_change():
    data = {
        "Date": [datetime(2023, 1, 1), datetime(2023, 1, 2), datetime(2023, 1, 3)],
        "P_Ticker": ["A", "A", "A"],
        "Currency": ["USD", "USD", "USD"],
        "Sector": ["Tech", "Tech", "Energy"],  # Energy is deviant
    }
    df = pd.DataFrame(data)
    validator = StaticDataValidator(df, pd.DataFrame())
    errors = validator.validate()

    assert len(errors) == 1
    assert errors[0].severity == "Medium"
    assert "Energy" in errors[0].description


def test_static_data_validator_ignores_nans():
    data = {
        "Date": [datetime(2023, 1, 1), datetime(2023, 1, 2)],
        "P_Ticker": ["A", "A"],
        "Currency": ["USD", None],  # None is ignored
        "Sector": ["Tech", "Tech"],
    }
    df = pd.DataFrame(data)
    validator = StaticDataValidator(df, pd.DataFrame())
    errors = validator.validate()
    assert len(errors) == 0
