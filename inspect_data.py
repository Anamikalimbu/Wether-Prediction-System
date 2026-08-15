import pandas as pd
import json

df = pd.read_csv("data/nepal_293_cities_weather_2020_2025.csv")
info = {
    "num_rows": len(df),
    "num_cols": len(df.columns),
    "columns": list(df.columns),
    "dtypes": df.dtypes.astype(str).to_dict(),
    "missing_values": df.isnull().sum().to_dict(),
    "duplicates": int(df.duplicated().sum()),
}

if "Municipality" in df.columns:
    info["unique_municipalities"] = df["Municipality"].nunique()
if "District" in df.columns:
    info["unique_districts"] = df["District"].nunique()
if "Province" in df.columns:
    info["unique_provinces"] = df["Province"].nunique()
if "Date" in df.columns:
    info["date_range"] = [df["Date"].min(), df["Date"].max()]

with open("dataset_info.json", "w") as f:
    json.dump(info, f, indent=4)
print("Data inspection complete. Info saved to dataset_info.json")
