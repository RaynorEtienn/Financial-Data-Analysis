import pandas as pd
from datetime import datetime
from src.validators.data_completeness import DataCompletenessValidator


def test_data_completeness_validator_no_errors():
    data = {
        "Date": [datetime(2023, 1, 1)],
        "P_Ticker": ["AAPL"],
        "Close Quantity": [10],
        "Price": [150.0],
        "Exchange Rate": [1.0],
        "Currency": ["USD"],
    }
    df = pd.DataFrame(data)
    validator = DataCompletenessValidator(df, pd.DataFrame())
    errors = validator.validate()
    assert len(errors) == 0


def test_data_completeness_validator_missing_price():
    data = {
        "Date": [datetime(2023, 1, 1)],
        "P_Ticker": ["AAPL"],
        "Close Quantity": [10],
        "Price": [None],  # Missing
        "Exchange Rate": [1.0],
        "Currency": ["USD"],
    }
    df = pd.DataFrame(data)
    validator = DataCompletenessValidator(df, pd.DataFrame())
    errors = validator.validate()

    assert len(errors) == 1
    assert errors[0].ticker == "AAPL"
    assert errors[0].error_type == "Missing Data"
    assert "Price" in errors[0].description
    assert errors[0].severity == "Medium"


def test_data_completeness_validator_zero_price():
    data = {
        "Date": [datetime(2023, 1, 1)],
        "P_Ticker": ["AAPL"],
        "Close Quantity": [10],
        "Price": [0.0],  # Invalid Zero
        "Exchange Rate": [1.0],
        "Currency": ["USD"],
    }
    df = pd.DataFrame(data)
    validator = DataCompletenessValidator(df, pd.DataFrame())
    errors = validator.validate()

    assert len(errors) == 1
    assert errors[0].ticker == "AAPL"
    assert errors[0].error_type == "Invalid Data"
    assert "Price" in errors[0].description
    assert errors[0].severity == "Medium"


def test_data_completeness_validator_missing_currency():
    data = {
        "Date": [datetime(2023, 1, 1)],
        "P_Ticker": ["AAPL"],
        "Close Quantity": [10],
        "Price": [150.0],
        "Exchange Rate": [1.0],
        "Currency": [None],  # Missing
    }
    df = pd.DataFrame(data)
    validator = DataCompletenessValidator(df, pd.DataFrame())
    errors = validator.validate()

    assert len(errors) == 1
    assert errors[0].ticker == "AAPL"
    assert errors[0].error_type == "Missing Data"
    assert "Currency" in errors[0].description
    assert errors[0].severity == "Medium"


def test_data_completeness_validator_zero_quantity_allowed():
    """
    Quantity can be 0 (flat position), so this should NOT be an error.
    """
    data = {
        "Date": [datetime(2023, 1, 1)],
        "P_Ticker": ["AAPL"],
        "Close Quantity": [0],  # Allowed
        "Price": [150.0],
        "Exchange Rate": [1.0],
        "Currency": ["USD"],
    }
    df = pd.DataFrame(data)
    validator = DataCompletenessValidator(df, pd.DataFrame())
    errors = validator.validate()
    assert len(errors) == 0
