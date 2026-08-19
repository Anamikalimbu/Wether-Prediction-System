import os
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import TimeSeriesSplit
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor, RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, accuracy_score
from preprocessing import load_and_clean_data, feature_engineering

DATA_PATH = "../data/nepal_293_cities_weather_2020_2025.csv"
MODEL_DIR = "../models"

def evaluate_model(y_true, y_pred, model_name, is_classification=False):
    print(f"--- {model_name} ---")
    if is_classification:
        acc = accuracy_score(y_true, y_pred)
        print(f"Accuracy: {acc:.4f}")
        return {"score": acc}
    else:
        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        r2 = r2_score(y_true, y_pred)
        print(f"MAE:  {mae:.4f}")
        print(f"RMSE: {rmse:.4f}")
        print(f"R2:   {r2:.4f}")
        return {"score": r2}

def main():
    print("Loading and preprocessing data...")
    df = load_and_clean_data(DATA_PATH)
    df = feature_engineering(df)
    
    # Drop rows with NaN targets or NaN features (due to lagging)
    # Target columns: Temp_2m_tomorrow, Precip_tomorrow, RH_2m_tomorrow
    features = [
        'Latitude', 'Longitude', 'Temp_2m', 'Precip', 'RH_2m', 'Pressure', 
        'Month_sin', 'Month_cos', 'DayOfYear_sin', 'DayOfYear_cos',
        'Temp_2m_lag1', 'Precip_lag1', 'RH_2m_lag1',
        'Temp_2m_roll3', 'Temp_2m_roll7', 'Precip_roll3', 'RH_2m_roll3'
    ]
    targets = ['Temp_2m_tomorrow', 'Precip_tomorrow', 'RH_2m_tomorrow', 'Condition_tomorrow']
    
    df_clean = df.dropna(subset=features + targets).copy()
    
    # Chronological Split (Train: < 2024, Test: >= 2024)
    train_df = df_clean[df_clean['Year'] < 2024]
    test_df = df_clean[df_clean['Year'] >= 2024]
    
    X_train = train_df[features]
    X_test = test_df[features]
    
    metrics = {}
    best_models = {}
    
    for target in targets:
        print(f"\nTraining models for {target}...")
        y_train = train_df[target]
        y_test = test_df[target]
        
        is_classification = (target == 'Condition_tomorrow')
        
        if is_classification:
            models = {
                "Logistic Regression": LogisticRegression(max_iter=1000),
                "Random Forest": RandomForestClassifier(n_estimators=30, max_depth=10, random_state=42, n_jobs=-1),
                "HistGradientBoosting": HistGradientBoostingClassifier(random_state=42)
            }
        else:
            models = {
                "Linear Regression": LinearRegression(),
                "Random Forest": RandomForestRegressor(n_estimators=30, max_depth=10, random_state=42, n_jobs=-1),
                "HistGradientBoosting": HistGradientBoostingRegressor(random_state=42)
            }
        
        best_score = -float('inf')
        best_model_name = None
        
        for name, model in models.items():
            model.fit(X_train, y_train)
            preds = model.predict(X_test)
            res = evaluate_model(y_test, preds, name, is_classification)
            
            # Simple baseline: previous day's value
            if target == 'Temp_2m_tomorrow':
                baseline_preds = X_test['Temp_2m']
            elif target == 'Precip_tomorrow':
                baseline_preds = X_test['Precip']
            elif target == 'RH_2m_tomorrow':
                baseline_preds = X_test['RH_2m']
            elif target == 'Condition_tomorrow':
                baseline_preds = test_df['Condition']
            
            if name == list(models.keys())[0]:
                 print("--- Baseline (Previous Day) ---")
                 evaluate_model(y_test, baseline_preds, "Baseline", is_classification)
            
            if res['score'] > best_score:
                best_score = res['score']
                best_model_name = name
                best_models[target] = model
                
        print(f"Best model for {target}: {best_model_name} (Score: {best_score:.4f})")
    
    # Save the best models and metadata
    os.makedirs(MODEL_DIR, exist_ok=True)
    for target, model in best_models.items():
        joblib.dump(model, os.path.join(MODEL_DIR, f"model_{target}.pkl"))
        
    joblib.dump(features, os.path.join(MODEL_DIR, "feature_columns.pkl"))
    print("\nModels and features saved successfully.")

if __name__ == "__main__":
    main()
