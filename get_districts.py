import pandas as pd
import json

df = pd.read_csv("data/nepal_293_cities_weather_2020_2025.csv")
districts = sorted(df["District"].dropna().unique().tolist())
with open("districts.json", "w") as f:
    json.dump(districts, f, indent=4)
