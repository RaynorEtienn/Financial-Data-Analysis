# ARR Investment Partners - Portfolio Error Detection

## Project Overview

This project is designed to analyze a hypothetical portfolio dataset to identify data integrity issues, inconsistencies, and calculation errors. It serves as a technical assessment for the Quantitative Developer role at ARR Investment Partners.

## Problem Statement

The input dataset contains daily portfolio positions and transaction details. The goal is to detect errors such as:

- Inconsistent prices (day-to-day jumps).
- Mismatches between holding quantity changes and trade information.
- Incorrect calculated ratios (weights, values).
- Discrepancies between trade prices and holding prices.
- Others?

## Architecture

The project follows a modular architecture to ensure scalability and maintainability:

1.  **Data Ingestion Layer**: Responsible for loading raw data (Excel/CSV) and standardizing it into a usable format (e.g., Pandas DataFrame).
2.  **Validation Engine**: A collection of specialized validators, each responsible for a specific type of error check.
    - <input type="checkbox" checked> `PriceValidator`: Checks for unrealistic price movements.
    - <input type="checkbox" checked> `ReconciliationValidator`: Reconciles positions with trades.
    - <input type="checkbox" checked> `CalculationValidator`: Verifies derived metrics (Market Value, Weights).
    - <input type="checkbox" checked> `ConsistencyValidator`: Checks cross-referencing data (Trade Price vs. Market Price).
    - <input type="checkbox" unchecked> `DataCompletenessValidator` (Planned): Checks for missing critical data points (Prices, FX rates) before other validators run.
3.  **Reporting Layer**: Aggregates findings from all validators and produces a structured report.
4.  **Presentation**: A Jupyter Notebook demonstrating the usage of the library and highlighting the findings.

## Project Structure

```
.
├── data/               # Input data and generated reports
├── notebooks/          # Jupyter notebooks for analysis and presentation
├── src/                # Source code
│   ├── __init__.py
│   ├── data_loader.py  # Data ingestion
│   ├── validators/     # Error detection logic
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── price.py
│   │   ├── quantity.py
│   │   └── ...
│   └── utils.py        # Helper functions
├── tests/              # Unit tests
├── requirements.txt    # Project dependencies
└── README.md           # Project documentation
```

## Setup

1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Place the input data file in the `data/` directory.

## Testing

To run the unit tests, execute the following command from the project root:

```bash
python -m pytest
```

## Usage

Run the analysis via the Jupyter Notebook in `notebooks/analysis.ipynb` or execute the main script (to be implemented).
