import pandas as pd
import os
from typing import Tuple


class DataLoader:
    """
    Industrial-grade data loader for portfolio data.
    Handles CSV ingestion, type inference, and data cleaning.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        if not file_path.lower().endswith(".csv"):
            raise ValueError("Only CSV files are supported.")

    def load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Loads and processes the portfolio data.
        Returns:
            positions (pd.DataFrame): Daily positions.
            trades (pd.DataFrame): Extracted trades.
        """
        try:
            df = pd.read_csv(self.file_path, skipinitialspace=True)
            df = self._clean_columns(df)
            df = self._infer_types(df)
            trades = self._extract_trades(df)
            return df, trades
        except Exception as e:
            raise RuntimeError(f"Data loading failed: {str(e)}") from e

    def _clean_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        df.columns = df.columns.str.strip()
        return df

    def _infer_types(self, df: pd.DataFrame) -> pd.DataFrame:
        # Date parsing
        date_cols = [c for c in df.columns if "date" in c.lower()]
        for col in date_cols:
            df[col] = pd.to_datetime(df[col], errors="coerce")
            if col.lower() == "date":
                df.rename(columns={col: "Date"}, inplace=True)

        # Numeric parsing
        for col in df.columns:
            if df[col].dtype == "object":
                # heuristic: check if column contains digits
                if df[col].astype(str).str.contains(r"\d").any():
                    # Clean currency/percentage symbols
                    cleaned = df[col].astype(str).str.replace(r"[$,% ]", "", regex=True)
                    converted = pd.to_numeric(cleaned, errors="coerce")
                    # If conversion rate is high, accept it
                    if converted.notna().mean() > 0.8:
                        df[col] = converted
        return df

    def _extract_trades(self, df: pd.DataFrame) -> pd.DataFrame:
        if "Traded Today" not in df.columns:
            return pd.DataFrame()

        # Ensure numeric
        if not pd.api.types.is_numeric_dtype(df["Traded Today"]):
            df["Traded Today"] = pd.to_numeric(df["Traded Today"], errors="coerce")

        mask = df["Traded Today"].notna() & (df["Traded Today"] != 0)
        trades = df[mask].copy()

        # Keep relevant columns
        keep_cols = [
            "Date",
            "P_Ticker",
            "Traded Today",
            "Trade Price",
            "Trade Day Move",
            "Trade Weight",
            "Side",
            "Currency",
        ]
        existing = [c for c in keep_cols if c in df.columns]
        return trades[existing]


if __name__ == "__main__":
    loader = DataLoader("data/Test.csv")
    try:
        pos, trades = loader.load_data()
        print("Positions columns:", pos.columns)
        print("Trades columns:", trades.columns)
        print(pos.head())
        print(f"Loaded {len(pos)} positions and {len(trades)} trades.")
    except Exception as e:
        print(e)
