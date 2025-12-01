import pandas as pd
from datetime import datetime
from src.validators.fx_consistency import FXConsistencyValidator


def test_fx_consistency_validator_no_errors():
    data = {
        "Date": [datetime(2023, 1, 1)] * 3,
        "P_Ticker": ["A", "B", "C"],
        "Currency": ["EUR", "EUR", "USD"],
        "Exchange Rate": [1.1, 1.1, 1.0],
    }
    df = pd.DataFrame(data)
    validator = FXConsistencyValidator(df, pd.DataFrame())
    errors = validator.validate()
    assert len(errors) == 0


def test_fx_consistency_validator_detects_error():
    data = {
        "Date": [datetime(2023, 1, 1)] * 3,
        "P_Ticker": ["A", "B", "C"],
        "Currency": ["EUR", "EUR", "EUR"],
        "Exchange Rate": [1.1, 1.1, 1.2],  # C is deviant
    }
    df = pd.DataFrame(data)
    validator = FXConsistencyValidator(df, pd.DataFrame())
    errors = validator.validate()

    assert len(errors) == 1
    assert errors[0].ticker == "C"
    assert errors[0].error_type == "FX Inconsistency"
    assert "deviates from daily consensus 1.1" in errors[0].description
    assert errors[0].severity == "High"  # (1.2 - 1.1)/1.1 ~ 9% > 1%


def test_fx_consistency_validator_minor_deviation():
    data = {
        "Date": [datetime(2023, 1, 1)] * 3,
        "P_Ticker": ["A", "B", "C"],
        "Currency": ["EUR", "EUR", "EUR"],
        "Exchange Rate": [1.100, 1.100, 1.105],  # C is deviant by < 1%
    }
    df = pd.DataFrame(data)
    validator = FXConsistencyValidator(df, pd.DataFrame())
    errors = validator.validate()

    assert len(errors) == 1
    assert errors[0].ticker == "C"
    assert errors[0].severity == "Medium"


def test_fx_consistency_validator_ignores_single_entry():
    data = {
        "Date": [datetime(2023, 1, 1)],
        "P_Ticker": ["A"],
        "Currency": ["GBP"],
        "Exchange Rate": [1.3],
    }
    df = pd.DataFrame(data)
    validator = FXConsistencyValidator(df, pd.DataFrame())
    errors = validator.validate()
    assert len(errors) == 0
