from abc import ABC, abstractmethod
import pandas as pd
from typing import List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ValidationError:
    """
    Represents a single validation error found in the data.

    Attributes:
        date (datetime): The date when the error occurred.
        ticker (str): The ticker symbol associated with the error.
        error_type (str): A short category string for the error (e.g., "Price Spike").
        description (str): A human-readable description of the error.
        severity (str): The severity level of the error ("Low", "Medium", "High").
    """

    date: datetime
    ticker: str
    error_type: str
    description: str
    severity: str = "Medium"


class BaseValidator(ABC):
    """
    Abstract base class for all validators.

    This class defines the interface that all specific validators must implement.
    It provides a common structure for storing and reporting validation errors.
    """

    def __init__(self, positions_df: pd.DataFrame, trades_df: pd.DataFrame):
        """
        Initialize the validator with the dataset.

        Args:
            positions_df (pd.DataFrame): DataFrame containing position data (Date, Ticker, Price, etc.).
            trades_df (pd.DataFrame): DataFrame containing trade data.
        """
        self.positions_df = positions_df
        self.trades_df = trades_df
        self.errors: List[ValidationError] = []

    @abstractmethod
    def validate(self) -> List[ValidationError]:
        """
        Performs the validation logic and returns a list of errors found.

        Returns:
            List[ValidationError]: A list of ValidationError objects detailing the issues found.
        """
        pass

    def add_error(self, date, ticker, error_type, description, severity="Medium"):
        """
        Helper method to add an error to the internal list.

        Args:
            date (datetime): The date of the error.
            ticker (str): The ticker symbol.
            error_type (str): The category of the error.
            description (str): Detailed description.
            severity (str, optional): Severity level. Defaults to "Medium".
        """
        self.errors.append(
            ValidationError(
                date=date,
                ticker=ticker,
                error_type=error_type,
                description=description,
                severity=severity,
            )
        )
