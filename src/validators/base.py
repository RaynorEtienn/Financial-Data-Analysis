from abc import ABC, abstractmethod
import pandas as pd
from typing import List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ValidationError:
    date: datetime
    ticker: str
    error_type: str
    description: str
    severity: str = "Medium"


class BaseValidator(ABC):
    """
    Abstract base class for all validators.
    """

    def __init__(self, positions_df: pd.DataFrame, trades_df: pd.DataFrame):
        self.positions_df = positions_df
        self.trades_df = trades_df
        self.errors: List[ValidationError] = []

    @abstractmethod
    def validate(self) -> List[ValidationError]:
        """
        Performs the validation logic and returns a list of errors found.
        """
        pass

    def add_error(self, date, ticker, error_type, description, severity="Medium"):
        self.errors.append(
            ValidationError(
                date=date,
                ticker=ticker,
                error_type=error_type,
                description=description,
                severity=severity,
            )
        )
