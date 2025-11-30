import pandas as pd
from datetime import datetime
from src.validators.calculation import CalculationValidator


def test_calculation_validator_no_errors():
    data = {
        "Date": [datetime(2023, 1, 1)],
        "P_Ticker": ["AAPL"],
        "Close Quantity": [10],
        "Price": [150.0],
        "Exchange Rate": [1.0],
        "Value in USD": [1500.0],  # 10 * 150 * 1 = 1500
    }
    df = pd.DataFrame(data)
    validator = CalculationValidator(df, pd.DataFrame())
    errors = validator.validate()
    assert len(errors) == 0


def test_calculation_validator_detects_error():
    data = {
        "Date": [datetime(2023, 1, 1)],
        "P_Ticker": ["AAPL"],
        "Close Quantity": [10],
        "Price": [150.0],
        "Exchange Rate": [1.0],
        "Value in USD": [2000.0],  # Should be 1500, Diff is 500. Pct = 500/2000 = 25%
    }
    df = pd.DataFrame(data)
    validator = CalculationValidator(df, pd.DataFrame())
    errors = validator.validate()

    assert len(errors) == 1
    assert errors[0].ticker == "AAPL"
    assert errors[0].error_type == "Calculation Error"
    assert "Value Mismatch" in errors[0].description
    assert errors[0].severity == "Medium"  # 25% is Medium (15-30%)


def test_calculation_validator_severity_levels():
    dates = [datetime(2023, 1, 1)] * 3
    data = {
        "Date": dates,
        "P_Ticker": ["LOW", "MED", "HIGH"],
        "Close Quantity": [100, 100, 100],
        "Price": [100, 100, 100],
        "Exchange Rate": [1, 1, 1],
        # Theoretical = 10,000
        "Value in USD": [
            11200,  # Diff 1200. Pct = 1200/11200 = 10.7% -> Low (10-15%)
            12500,  # Diff 2500. Pct = 2500/12500 = 20% -> Medium (15-30%)
            15000,  # Diff 5000. Pct = 5000/15000 = 33.3% -> High (> 30%)
        ],
    }
    df = pd.DataFrame(data)
    validator = CalculationValidator(df, pd.DataFrame())
    errors = validator.validate()

    low = next(e for e in errors if e.ticker == "LOW")
    med = next(e for e in errors if e.ticker == "MED")
    high = next(e for e in errors if e.ticker == "HIGH")

    assert low.severity == "Low"
    assert med.severity == "Medium"
    assert high.severity == "High"


def test_calculation_validator_detects_multiplier():
    data = {
        "Date": [datetime(2023, 1, 1)],
        "P_Ticker": ["FUT"],
        "Close Quantity": [10],
        "Price": [100.0],
        "Exchange Rate": [1.0],
        # Theoretical = 1000
        # Reported = 5000 (x5 multiplier)
        "Value in USD": [5000.0],
    }
    df = pd.DataFrame(data)
    validator = CalculationValidator(df, pd.DataFrame())
    errors = validator.validate()

    assert len(errors) == 1
    assert errors[0].ticker == "FUT"
    assert errors[0].severity == "Low"  # Downgraded because it's explained
    assert "missing multiplier: x5" in errors[0].description


def test_calculation_validator_detects_reciprocal_multiplier():
    data = {
        "Date": [datetime(2023, 1, 1)],
        "P_Ticker": ["FUT_SMALL"],
        "Close Quantity": [10],
        "Price": [100.0],
        "Exchange Rate": [1.0],
        # Theoretical = 1000
        # Reported = 250 (x0.25 or 1/4 multiplier)
        "Value in USD": [250.0],
    }
    df = pd.DataFrame(data)
    validator = CalculationValidator(df, pd.DataFrame())
    errors = validator.validate()

    assert len(errors) == 1
    assert errors[0].ticker == "FUT_SMALL"
    assert errors[0].severity == "Low"
    assert "missing multiplier: x0.25 or 1/4" in errors[0].description


def test_calculation_validator_ignores_rounding():
    data = {
        "Date": [datetime(2023, 1, 1)],
        "P_Ticker": ["AAPL"],
        "Close Quantity": [10],
        "Price": [150.1234],
        "Exchange Rate": [1.0],
        "Value in USD": [1501.23],  # Theoretical 1501.234. Diff 0.004. < $1.00
    }
    df = pd.DataFrame(data)
    validator = CalculationValidator(df, pd.DataFrame())
    errors = validator.validate()
    assert len(errors) == 0


def test_calculation_validator_ignores_missing_data():
    """
    Ensure that if Price, Quantity, or FX is missing (0), we do NOT flag an error.
    """
    data = {
        "Date": [datetime(2023, 1, 1)] * 3,
        "P_Ticker": ["MISS_PX", "MISS_QTY", "MISS_FX"],
        "Close Quantity": [100, 0, 100],
        "Price": [0, 100, 100],
        "Exchange Rate": [1.0, 1.0, 0],
        "Value in USD": [
            1000.0,
            1000.0,
            1000.0,
        ],  # Reported value exists, but inputs missing
    }
    df = pd.DataFrame(data)
    validator = CalculationValidator(df, pd.DataFrame())
    errors = validator.validate()

    # Should find NO errors because we skip rows where Theoretical Value is ~0
    assert len(errors) == 0


def test_calculation_validator_detects_sign_mismatch():
    """
    Ensure that if Reported and Calculated values have opposite signs, it is a High severity error.
    """
    data = {
        "Date": [datetime(2023, 1, 1)],
        "P_Ticker": ["SIGN_ERR"],
        "Close Quantity": [100],
        "Price": [10.0],
        "Exchange Rate": [1.0],
        # Theoretical = 1000 (Positive)
        # Reported = -1000 (Negative)
        "Value in USD": [-1000.0],
    }
    df = pd.DataFrame(data)
    validator = CalculationValidator(df, pd.DataFrame())
    errors = validator.validate()

    assert len(errors) == 1
    assert errors[0].ticker == "SIGN_ERR"
    assert errors[0].severity == "High"
    assert "Sign Mismatch" in errors[0].description


def test_calculation_validator_systematic_multiplier():
    """
    Ensure that if a ticker consistently has the same multiplier error, it is detected as systematic.
    """
    # Create 5 days of data for the same ticker, all off by x10
    dates = [datetime(2023, 1, i + 1) for i in range(5)]
    data = {
        "Date": dates,
        "P_Ticker": ["SYS_ERR"] * 5,
        "Close Quantity": [100] * 5,
        "Price": [10.0] * 5,
        "Exchange Rate": [1.0] * 5,
        # Theoretical = 1000
        # Reported = 10,000 (x10)
        "Value in USD": [10000.0] * 5,
    }
    df = pd.DataFrame(data)
    validator = CalculationValidator(df, pd.DataFrame())
    errors = validator.validate()

    assert len(errors) == 5
    # Check the first one
    err = errors[0]
    assert err.ticker == "SYS_ERR"
    # Should be downgraded to Low because it's systematic/explained
    assert err.severity == "Low"
    assert (
        "Systematic Multiplier" in err.description
        or "missing multiplier" in err.description
    )
