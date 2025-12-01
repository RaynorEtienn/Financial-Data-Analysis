import pandas as pd
from datetime import datetime
from src.validators.weight import WeightValidator


def test_weight_validator_no_errors():
    data = {
        "Date": [datetime(2023, 1, 1)] * 2,
        "P_Ticker": ["A", "B"],
        "Value in USD": [50.0, 50.0],
        "Closing Weights": [0.5, 0.5],  # 50/100 = 0.5
    }
    df = pd.DataFrame(data)
    validator = WeightValidator(df, pd.DataFrame())
    errors = validator.validate()
    assert len(errors) == 0


def test_weight_validator_detects_error():
    data = {
        "Date": [datetime(2023, 1, 1)] * 2,
        "P_Ticker": ["A", "B"],
        "Value in USD": [50.0, 50.0],  # Total 100
        "Closing Weights": [0.8, 0.2],  # Wrong! Should be 0.5, 0.5
    }
    df = pd.DataFrame(data)
    validator = WeightValidator(df, pd.DataFrame())
    errors = validator.validate()

    assert len(errors) == 2
    assert errors[0].ticker == "A"
    assert errors[0].error_type == "Weight Mismatch"
    assert errors[0].severity == "High"  # Diff 0.3 > 0.01


def test_weight_validator_handles_percentage_strings():
    data = {
        "Date": [datetime(2023, 1, 1)] * 2,
        "P_Ticker": ["A", "B"],
        "Value in USD": [25.0, 75.0],  # Total 100
        "Closing Weights": ["25%", "75%"],  # Strings
    }
    df = pd.DataFrame(data)
    validator = WeightValidator(df, pd.DataFrame())
    errors = validator.validate()
    assert len(errors) == 0


def test_weight_validator_minor_deviation():
    data = {
        "Date": [datetime(2023, 1, 1)] * 2,
        "P_Ticker": ["A", "B"],
        "Value in USD": [50.0, 50.0],  # Total 100
        "Closing Weights": [
            0.502,
            0.498,
        ],  # Diff 0.002 (20 bps) -> Low (since > 10bps but < 100bps)
    }
    df = pd.DataFrame(data)
    validator = WeightValidator(df, pd.DataFrame())
    errors = validator.validate()

    assert len(errors) == 2
    assert errors[0].severity == "Low"


def test_weight_validator_z_score_outlier():
    # Create a dataset with many small errors and one huge outlier
    # 10 points with 0 diff, 1 point with huge diff
    dates = [datetime(2023, 1, 1)] * 11
    tickers = [f"T{i}" for i in range(11)]
    values = [10.0] * 11  # Total 110
    # Implied weight = 10/110 = 0.0909

    # Closing weights: 10 are correct, 1 is way off
    closing_weights = [10.0 / 110.0] * 10 + [0.2]  # Last one is ~20% instead of 9%

    data = {
        "Date": dates,
        "P_Ticker": tickers,
        "Value in USD": values,
        "Closing Weights": closing_weights,
    }
    df = pd.DataFrame(data)
    validator = WeightValidator(df, pd.DataFrame())
    errors = validator.validate()

    # The outlier should be caught
    assert len(errors) >= 1
    # Find the error for T10
    t10_error = next((e for e in errors if e.ticker == "T10"), None)
    assert t10_error is not None
    assert "Outlier" in t10_error.description or "Diff" in t10_error.description


def test_weight_validator_ignores_missing_data():
    data = {
        "Date": [datetime(2023, 1, 1)],
        "P_Ticker": ["A"],
        "Value in USD": [0.0],  # Missing value/quantity
        "Closing Weights": [0.5],  # Stale weight
    }
    df = pd.DataFrame(data)
    validator = WeightValidator(df, pd.DataFrame())
    errors = validator.validate()
    assert len(errors) == 0  # Should be ignored


def test_weight_validator_ignores_nan_weights():
    data = {
        "Date": [datetime(2023, 1, 1)],
        "P_Ticker": ["A"],
        "Value in USD": [100.0],
        "Closing Weights": [float("nan")],
    }
    df = pd.DataFrame(data)
    validator = WeightValidator(df, pd.DataFrame())
    errors = validator.validate()
    assert len(errors) == 0
