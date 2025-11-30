import pytest
import pandas as pd
import os
from src.data_loader import DataLoader


@pytest.fixture
def sample_csv(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    p = d / "test_portfolio.csv"
    content = """Date,P_Ticker,Price,Traded Today,Trade Price
2023-01-01,AAPL,$150.00,0,
2023-01-01,GOOG,"2,000.00",10,2005.00
2023-01-02,AAPL,155.00,-5,154.00
"""
    p.write_text(content)
    return str(p)


def test_load_data_success(sample_csv):
    loader = DataLoader(sample_csv)
    pos, trades = loader.load_data()

    assert len(pos) == 3
    assert len(trades) == 2
    assert "Date" in pos.columns
    assert pd.api.types.is_datetime64_any_dtype(pos["Date"])
    assert pd.api.types.is_numeric_dtype(pos["Price"])
    assert pos.iloc[1]["Price"] == 2000.0


def test_file_not_found():
    with pytest.raises(FileNotFoundError):
        DataLoader("non_existent.csv")


def test_invalid_extension(tmp_path):
    p = tmp_path / "test.txt"
    p.touch()
    with pytest.raises(ValueError):
        DataLoader(str(p))
