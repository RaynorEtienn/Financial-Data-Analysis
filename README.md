# ARR Investment Partners - Portfolio Error Detection

**Repository Link**: [https://github.com/RaynorEtienn/Financial-Data-Analysis](https://github.com/RaynorEtienn/Financial-Data-Analysis)

## Introduction for Reviewers

Welcome! This repository contains my solution for the Portfolio Error Detection task. I have taken on the role of a "detective" to uncover inconsistencies and errors in the provided portfolio dataset.

**Where to start:**

- **Main Analysis**: The primary entry point is **[`notebooks/analysis.ipynb`](notebooks/analysis.ipynb)**. This notebook demonstrates the execution of the validation engine, visualizes the identified errors (price spikes, reconciliation breaks, etc.), and provides a summary of the findings.
- **Architecture**: The solution is designed as a modular Python library located in `src/`. Each class of error is handled by a dedicated validator in `src/validators/`, ensuring the code is scalable and easily extensible for new types of checks.
- **Quality Assurance**: Comprehensive unit tests are provided in `tests/` to verify the logic of each validator.

---

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
    - <input type="checkbox" checked> `DataCompletenessValidator`: Checks for missing critical data points (Prices, FX rates).
    - <input type="checkbox" checked> `FXConsistencyValidator`: Checks for inconsistent exchange rates across assets.
    - <input type="checkbox" checked> `StaticDataValidator`: Checks for consistency in static data (Sector, Currency) over time.
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
