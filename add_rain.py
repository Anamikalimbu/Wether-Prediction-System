import pandas as pd
import numpy as np
import os

print("Loading dataset...")
data_path = os.path.join("data", "nepal_293_cities_weather_2020_2025.csv")
df = pd.read_csv(data_path)
dates = pd.to_datetime(df['Date'], format='%d/%m/%Y', errors='coerce')
months = dates.dt.month

np.random.seed(42)
# Base probability of rain: higher in monsoon (6, 7, 8, 9)
is_monsoon = months.isin([6, 7, 8, 9])
# Humidity factor
rh_factor = (df['RH_2m'] / 100.0) ** 2  # Higher humidity -> much higher chance

prob_rain = np.where(is_monsoon, 0.4 + 0.5 * rh_factor, 0.05 + 0.3 * rh_factor)
prob_rain = np.clip(prob_rain, 0, 1)

# Mask for days with rain
rain_mask = np.random.rand(len(df)) < prob_rain

# Generate rain amount (exponential distribution, more rain in monsoon)
rain_amount = np.zeros(len(df))
monsoon_amounts = np.random.exponential(scale=15.0, size=len(df))  # avg 15mm in monsoon
non_monsoon_amounts = np.random.exponential(scale=3.0, size=len(df))

rain_amount[is_monsoon] = monsoon_amounts[is_monsoon]
rain_amount[~is_monsoon] = non_monsoon_amounts[~is_monsoon]

# Apply mask and round
df['Precip'] = np.where(rain_mask, np.round(rain_amount, 1), 0.0)

print("Precipitation added. Statistics:")
print(df['Precip'].describe())
print(f"Days with rain: {(df['Precip'] > 0).sum()} out of {len(df)}")

print("Saving dataset...")
df.to_csv(data_path, index=False)
print("Done.")
