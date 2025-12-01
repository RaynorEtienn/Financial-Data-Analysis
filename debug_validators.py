import pandas as pd
import sys
import os

sys.path.append(os.path.abspath('.'))
from src.data_loader import DataLoader

loader = DataLoader('data/Test.csv')
df, _ = loader.load_data()

print("--- Data Completeness Debug ---")
missing_qty = df[df['Close Quantity'].isna()]
print(f"Rows with missing Close Quantity: {len(missing_qty)}")
if not missing_qty.empty:
    print(missing_qty[['Date', 'P_Ticker', 'Traded Today', 'Value in USD']].head())
    print("Unique Tickers with missing Qty:", missing_qty['P_Ticker'].unique())

print("\n--- FX Consistency Debug ---")
# Check counts per currency per date
fx_counts = df.groupby(['Date', 'Currency']).size()
print("Distribution of assets per currency (Date, Currency): Count")
print(fx_counts[fx_counts > 1].head(10))
print(f"Max assets sharing a currency on one day: {fx_counts.max()}")

print("\n--- Weight Debug ---")
# Check if weights sum to 1
daily_weights = df.groupby('Date')['Closing Weights'].sum()
print("Daily Weight Sums (Head):")
print(daily_weights.head())
