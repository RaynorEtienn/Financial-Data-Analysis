import pandas as pd
import sys
import os

sys.path.append(os.path.abspath('.'))
from src.data_loader import DataLoader

loader = DataLoader('data/Test.csv')
df, _ = loader.load_data()

# Ensure numeric types
df["Value in USD"] = pd.to_numeric(df["Value in USD"], errors="coerce").fillna(0)

# Handle percentage strings in Closing Weights
if df["Closing Weights"].dtype == "object":
    df["Closing Weights"] = (
        df["Closing Weights"]
        .astype(str)
        .str.replace("%", "")
        .str.replace(",", "")
    )
    df["Closing Weights"] = pd.to_numeric(df["Closing Weights"], errors="coerce")

# Check scale
daily_sums = df.groupby("Date")["Closing Weights"].sum()
print("Daily Weight Sums (Raw):")
print(daily_sums.describe())
print(daily_sums.head())

# Normalize if needed
median_sum = daily_sums.median()
if median_sum > 10.0:
    print(f"Detected percentage scale (Median Sum: {median_sum}). Dividing by 100.")
    df["Closing Weights"] = df["Closing Weights"] / 100.0
else:
    print(f"Detected decimal scale (Median Sum: {median_sum}).")

# Calculate Implied Weights
daily_nav = df.groupby("Date")["Value in USD"].transform("sum")
df["Implied_Weight"] = df["Value in USD"] / daily_nav.replace(0, 1)

# Calculate Diff
df["Diff"] = df["Implied_Weight"] - df["Closing Weights"]
df["Abs_Diff"] = df["Diff"].abs()

print("\nAbsolute Difference Stats:")
print(df["Abs_Diff"].describe())

print("\nTop 10 Largest Differences:")
print(df.sort_values("Abs_Diff", ascending=False)[['Date', 'P_Ticker', 'Value in USD', 'Closing Weights', 'Implied_Weight', 'Abs_Diff']].head(10))

# Check Z-Scores of the differences
mean_diff = df["Diff"].mean()
std_diff = df["Diff"].std()
print(f"\nDiff Mean: {mean_diff}, Std: {std_diff}")

df["Z_Score"] = (df["Diff"] - mean_diff) / std_diff
print("\nTop 10 Z-Scores:")
print(df.sort_values("Z_Score", ascending=False)[['Date', 'P_Ticker', 'Diff', 'Z_Score']].head(10))
