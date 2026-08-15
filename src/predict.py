import os
import joblib
import pandas as pd
import numpy as np

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")
DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "nepal_293_cities_weather_2020_2025.csv")

# Load models once
models = {}
for target in ['Temp_2m_tomorrow', 'Precip_tomorrow', 'RH_2m_tomorrow']:
    model_path = os.path.join(MODEL_DIR, f"model_{target}.pkl")
    if os.path.exists(model_path):
        models[target] = joblib.load(model_path)

features_path = os.path.join(MODEL_DIR, "feature_columns.pkl")
if os.path.exists(features_path):
    feature_columns = joblib.load(features_path)
else:
    feature_columns = []

# To make a prediction for a future date, we technically need the lag features from the previous day.
# In a real system, we'd recursively predict up to the target date.
# For simplicity in this internship project, if they ask for a future date, we take the *latest* available data
# for that city, pretend it's the "day before", and predict. If it's a historical date, we just look up the actuals.

_cached_df = None

def get_latest_city_data(city_name):
    global _cached_df
    if _cached_df is None:
        _cached_df = pd.read_csv(DATA_PATH)
        
    df = _cached_df
    city_df = df[df['City'] == city_name].copy()
    
    if city_df.empty:
        return None
        
    city_df['Date'] = pd.to_datetime(city_df['Date'], format='%d/%m/%Y', errors='coerce')
    city_df = city_df.sort_values(by='Date')
    
    # Feature engineering for the last row
    from src.preprocessing import feature_engineering
    city_df = feature_engineering(city_df)
    
    # Get the last row which contains the latest historical lag features
    last_row = city_df.iloc[-1:]
    return last_row

def predict_weather(city_name, target_date):
    last_row = get_latest_city_data(city_name)
    if last_row is None:
        return None
    
    # Overwrite temporal features with the target date
    target_date_obj = pd.to_datetime(target_date)
    last_row['Month'] = target_date_obj.month
    last_row['DayOfYear'] = target_date_obj.dayofyear
    last_row['Month_sin'] = np.sin(2 * np.pi * target_date_obj.month / 12)
    last_row['Month_cos'] = np.cos(2 * np.pi * target_date_obj.month / 12)
    last_row['DayOfYear_sin'] = np.sin(2 * np.pi * target_date_obj.dayofyear / 365.25)
    last_row['DayOfYear_cos'] = np.cos(2 * np.pi * target_date_obj.dayofyear / 365.25)
    
    X = last_row[feature_columns]
    
    predictions = {}
    if 'Temp_2m_tomorrow' in models:
        predictions['temperature'] = models['Temp_2m_tomorrow'].predict(X)[0]
    if 'Precip_tomorrow' in models:
        predictions['rainfall'] = models['Precip_tomorrow'].predict(X)[0]
    if 'RH_2m_tomorrow' in models:
        predictions['humidity'] = models['RH_2m_tomorrow'].predict(X)[0]
        
    return predictions
