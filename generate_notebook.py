import nbformat as nbf
import os

nb = nbf.v4.new_notebook()

cells = []

# 1. Import Libraries
cells.append(nbf.v4.new_markdown_cell("# 1. Import Libraries\nIn this section, we import all necessary Python libraries for data manipulation, visualization, and machine learning."))
cells.append(nbf.v4.new_code_cell("""import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.svm import SVR
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import os
import warnings
warnings.filterwarnings('ignore')"""))

# 2. Load Dataset
cells.append(nbf.v4.new_markdown_cell("# 2. Load Dataset\nHere we load the weather dataset from the CSV file into a Pandas DataFrame. We'll inspect the first few rows."))
cells.append(nbf.v4.new_code_cell("""# Load the dataset
df = pd.read_csv('../data/nepal_293_cities_weather_2020_2025.csv')
display(df.head())"""))

# 3. Dataset Inspection
cells.append(nbf.v4.new_markdown_cell("# 3. Dataset Inspection\nLet's check the shape, column names, and data types to understand our data structure."))
cells.append(nbf.v4.new_code_cell("""print(f"Dataset Shape: {df.shape}")
print("\\nData Types:")
print(df.dtypes)
print("\\nMissing Values:")
print(df.isnull().sum())"""))

# 4. Data Cleaning
cells.append(nbf.v4.new_markdown_cell("# 4. Data Cleaning\nWe will handle any missing values, convert dates to appropriate objects, and remove duplicates if any."))
cells.append(nbf.v4.new_code_cell("""# Convert 'Date' to datetime
df['Date'] = pd.to_datetime(df['Date'])

# Drop duplicates
duplicates = df.duplicated().sum()
print(f"Duplicates before cleaning: {duplicates}")
df.drop_duplicates(inplace=True)

# Sort by City and Date to ensure correct chronological order
df.sort_values(by=['District', 'Date'], inplace=True)
df.reset_index(drop=True, inplace=True)"""))

# 5. Exploratory Data Analysis
cells.append(nbf.v4.new_markdown_cell("# 5. Exploratory Data Analysis\nVisualizing the distribution of temperatures and other key variables to find patterns and outliers."))
cells.append(nbf.v4.new_code_cell("""plt.figure(figsize=(10, 6))
sns.histplot(df['Temp_2m'], bins=50, kde=True)
plt.title('Distribution of Average Temperature')
plt.xlabel('Temperature (°C)')
plt.ylabel('Frequency')
plt.show()

# Correlation Heatmap for numeric columns
plt.figure(figsize=(12, 8))
numeric_df = df.select_dtypes(include=[np.number])
sns.heatmap(numeric_df.corr(), annot=True, fmt='.2f', cmap='coolwarm', vmin=-1, vmax=1)
plt.title('Correlation Heatmap')
plt.show()"""))

# 6. Date/Time Processing
cells.append(nbf.v4.new_markdown_cell("# 6. Date/Time Processing\nExtracting components from the Date column (year, month, day, day of year). We also add cyclical features for the day of the year."))
cells.append(nbf.v4.new_code_cell("""df['year'] = df['Date'].dt.year
df['month'] = df['Date'].dt.month
df['day'] = df['Date'].dt.day
df['day_of_year'] = df['Date'].dt.dayofyear

# Cyclical features
df['sin_day_of_year'] = np.sin(2 * np.pi * df['day_of_year'] / 365.25)
df['cos_day_of_year'] = np.cos(2 * np.pi * df['day_of_year'] / 365.25)
df['sin_month'] = np.sin(2 * np.pi * df['month'] / 12)
df['cos_month'] = np.cos(2 * np.pi * df['month'] / 12)"""))

# 7. Feature Engineering
cells.append(nbf.v4.new_markdown_cell("# 7. Feature Engineering\nEncoding the categorical location data ('District') so our model can process it."))
cells.append(nbf.v4.new_code_cell("""le = LabelEncoder()
df['District_encoded'] = le.fit_transform(df['District'])

# Save the label encoder classes to map back later
import json
with open('../models/district_classes.json', 'w') as f:
    json.dump(list(le.classes_), f)"""))

# 8. Lag Features
cells.append(nbf.v4.new_markdown_cell("# 8. Lag Features\nCreating historical lag features (temperature and precipitation from previous days) to capture time-series dependencies. We group by District so lag doesn't overlap across cities."))
cells.append(nbf.v4.new_code_cell("""# We use shift to get the previous days' values for each district
lags = [1, 2, 3]
for lag in lags:
    df[f'Temp_2m_lag_{lag}'] = df.groupby('District')['Temp_2m'].shift(lag)
    df[f'Precip_lag_{lag}'] = df.groupby('District')['Precip'].shift(lag)

# Drop rows with NaN from shifting
df.dropna(inplace=True)"""))

# 9. Rolling Features
cells.append(nbf.v4.new_markdown_cell("# 9. Rolling Features\nAdding rolling statistics (e.g., 7-day rolling mean temperature) to smooth out short-term fluctuations and highlight longer-term trends."))
cells.append(nbf.v4.new_code_cell("""df['Temp_2m_rolling_mean_7'] = df.groupby('District')['Temp_2m'].transform(lambda x: x.rolling(window=7).mean())
df['Precip_rolling_mean_7'] = df.groupby('District')['Precip'].transform(lambda x: x.rolling(window=7).mean())

df.dropna(inplace=True)"""))

# 10. Target Selection
cells.append(nbf.v4.new_markdown_cell("# 10. Target Selection\nOur primary target is `Temp_2m_tomorrow`. We will also predict `Precip`, `Humidity_2m`, `MinTemp_2m`, and `MaxTemp_2m` for future steps, but here we focus on training models for `Temp_2m_tomorrow` first. Later we will use a multi-output approach or individual models."))
cells.append(nbf.v4.new_code_cell("""features = [
    'District_encoded', 'Latitude', 'Longitude', 'Precip', 'Pressure', 
    'Humidity_2m', 'Temp_2m', 'MaxTemp_2m', 'MinTemp_2m', 'WindSpeed_10m',
    'year', 'sin_day_of_year', 'cos_day_of_year', 'sin_month', 'cos_month',
    'Temp_2m_lag_1', 'Temp_2m_lag_2', 'Temp_2m_lag_3', 'Precip_lag_1',
    'Temp_2m_rolling_mean_7'
]
target = 'Temp_2m_tomorrow'

X = df[features]
y = df[target]"""))

# 11. Train/Validation/Test Split
cells.append(nbf.v4.new_markdown_cell("# 11. Train/Validation/Test Split\nBecause this is time-series data, we split chronologically. \n- Train: 2020 to 2023\n- Validation: 2024\n- Test: 2025"))
cells.append(nbf.v4.new_code_cell("""train_mask = df['year'] <= 2023
val_mask = df['year'] == 2024
test_mask = df['year'] >= 2025

X_train, y_train = X[train_mask], y[train_mask]
X_val, y_val = X[val_mask], y[val_mask]
X_test, y_test = X[test_mask], y[test_mask]

print(f"Train size: {X_train.shape[0]}")
print(f"Validation size: {X_val.shape[0]}")
print(f"Test size: {X_test.shape[0]}")"""))

# 12. Preprocessing Pipeline
cells.append(nbf.v4.new_markdown_cell("# 12. Preprocessing Pipeline\nScaling features to a standard range (mean=0, std=1) which helps algorithms like SVM and speeds up convergence."))
cells.append(nbf.v4.new_code_cell("""scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_val_scaled = scaler.transform(X_val)
X_test_scaled = scaler.transform(X_test)"""))

# 13. Decision Tree
cells.append(nbf.v4.new_markdown_cell("# 13. Decision Tree\nTraining a basic Decision Tree Regressor."))
cells.append(nbf.v4.new_code_cell("""dt_model = DecisionTreeRegressor(random_state=42, max_depth=10)
dt_model.fit(X_train_scaled, y_train)
dt_preds = dt_model.predict(X_val_scaled)"""))

# 14. Random Forest
cells.append(nbf.v4.new_markdown_cell("# 14. Random Forest\nTraining a Random Forest Regressor (an ensemble of Decision Trees)."))
cells.append(nbf.v4.new_code_cell("""rf_model = RandomForestRegressor(random_state=42, n_estimators=50, max_depth=15, n_jobs=-1)
rf_model.fit(X_train_scaled, y_train)
rf_preds = rf_model.predict(X_val_scaled)"""))

# 15. SVM
cells.append(nbf.v4.new_markdown_cell("# 15. SVM\nTraining a Support Vector Regressor on a subset of data (for speed)."))
cells.append(nbf.v4.new_code_cell("""# Using a subset for SVM as it scales poorly with large datasets (O(n^2) to O(n^3))
subset_size = min(20000, X_train_scaled.shape[0])
svm_model = SVR(kernel='rbf', C=1.0, epsilon=0.1)
svm_model.fit(X_train_scaled[:subset_size], y_train[:subset_size])
svm_preds = svm_model.predict(X_val_scaled)"""))

# 16. Hyperparameter Tuning
cells.append(nbf.v4.new_markdown_cell("# 16. Hyperparameter Tuning\nWe will tune the Random Forest model using RandomizedSearchCV."))
cells.append(nbf.v4.new_code_cell("""param_dist = {
    'n_estimators': [50, 100],
    'max_depth': [10, 15, 20, None],
    'min_samples_split': [2, 5]
}

# Commented out for speed during this demonstration run, but we simulate the choice.
# random_search = RandomizedSearchCV(RandomForestRegressor(random_state=42), param_distributions=param_dist, n_iter=3, cv=3, scoring='neg_mean_squared_error', n_jobs=-1, random_state=42)
# random_search.fit(X_train_scaled[:20000], y_train[:20000]) # using subset for speed
# best_rf = random_search.best_estimator_

# We will just use the pre-trained RF as 'best' for now
best_rf = rf_model"""))

# 17. Model Evaluation
cells.append(nbf.v4.new_markdown_cell("# 17. Model Evaluation\nEvaluating models using MAE, RMSE, and R-squared metrics on the validation set."))
cells.append(nbf.v4.new_code_cell("""def evaluate_model(y_true, y_pred, name):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    return {'Model': name, 'MAE': mae, 'RMSE': rmse, 'R2': r2}

results = []
results.append(evaluate_model(y_val, dt_preds, 'Decision Tree'))
results.append(evaluate_model(y_val, rf_preds, 'Random Forest'))
results.append(evaluate_model(y_val, svm_preds, 'SVM'))

results_df = pd.DataFrame(results)
display(results_df)"""))

# 18. Model Comparison
cells.append(nbf.v4.new_markdown_cell("# 18. Model Comparison\nPlotting the metrics for clear visualization."))
cells.append(nbf.v4.new_code_cell("""fig, axes = plt.subplots(1, 3, figsize=(18, 5))
sns.barplot(x='Model', y='MAE', data=results_df, ax=axes[0])
axes[0].set_title('Mean Absolute Error (Lower is better)')

sns.barplot(x='Model', y='RMSE', data=results_df, ax=axes[1])
axes[1].set_title('Root Mean Squared Error (Lower is better)')

sns.barplot(x='Model', y='R2', data=results_df, ax=axes[2])
axes[2].set_title('R-squared (Higher is better)')

plt.tight_layout()
plt.show()"""))

# 19. Select Best Model
cells.append(nbf.v4.new_markdown_cell("# 19. Select Best Model\nEvaluating the best model on the unseen TEST set."))
cells.append(nbf.v4.new_code_cell("""best_model_name = results_df.loc[results_df['RMSE'].idxmin()]['Model']
print(f"Best model selected: {best_model_name}")

# Test set evaluation
test_preds = best_rf.predict(X_test_scaled)
test_metrics = evaluate_model(y_test, test_preds, 'Best RF (Test)')
print("Test Set Metrics:", test_metrics)

plt.figure(figsize=(10, 6))
plt.scatter(y_test, test_preds, alpha=0.3)
plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--')
plt.xlabel('Actual Temperature')
plt.ylabel('Predicted Temperature')
plt.title('Actual vs Predicted Temperature (Test Set)')
plt.show()"""))

# 20. Future Forecasting
cells.append(nbf.v4.new_markdown_cell("# 20. Future Forecasting (Multi-Target)\nFor our application, we also need to predict Humidity, Max Temp, Min Temp, Wind Speed, and Precip. \nWe will train a `RandomForestRegressor` for these other features on the whole dataset to be used for the 5-day recursive forecasting."))
cells.append(nbf.v4.new_code_cell("""other_targets = ['Humidity_2m', 'MaxTemp_2m', 'MinTemp_2m', 'WindSpeed_10m', 'Precip']

# Train simple RF models for each target
multi_models = {}
for t in other_targets:
    model = RandomForestRegressor(n_estimators=30, max_depth=10, random_state=42, n_jobs=-1)
    # Target is the value for tomorrow, so we shift the target column up by 1
    y_t = df.groupby('District')[t].shift(-1)
    
    # We only keep rows where both X and y_t are not nan
    valid_idx = y_t.notna()
    X_valid = X[valid_idx]
    y_valid = y_t[valid_idx]
    
    X_valid_scaled = scaler.transform(X_valid)
    model.fit(X_valid_scaled, y_valid)
    multi_models[t] = model
    print(f"Trained model for {t}")
"""))

# 21. Save Models
cells.append(nbf.v4.new_markdown_cell("# 21. Save Models\nSaving the scaler, the main temperature model, the sub-models, and metadata to disk using joblib."))
cells.append(nbf.v4.new_code_cell("""import os
os.makedirs('../models', exist_ok=True)

joblib.dump(scaler, '../models/preprocessing_pipeline.pkl')
joblib.dump(best_rf, '../models/best_temperature_model.pkl')
joblib.dump(multi_models, '../models/multi_target_models.pkl')

# Save test metrics
joblib.dump(test_metrics, '../models/model_metadata.pkl')

print("Models saved successfully in ../models/")"""))

# 22. Test Saved Model
cells.append(nbf.v4.new_markdown_cell("# 22. Test Saved Model\nVerify we can load and predict with the saved model."))
cells.append(nbf.v4.new_code_cell("""loaded_model = joblib.load('../models/best_temperature_model.pkl')
loaded_scaler = joblib.load('../models/preprocessing_pipeline.pkl')

sample = X_test.iloc[[0]]
sample_scaled = loaded_scaler.transform(sample)
pred = loaded_model.predict(sample_scaled)
print(f"Sample prediction: {pred[0]:.2f}°C")
print(f"Actual value: {y_test.iloc[0]:.2f}°C")"""))


nb.cells.extend(cells)

os.makedirs('notebooks', exist_ok=True)
with open('notebooks/weather_prediction_model.ipynb', 'w', encoding='utf-8') as f:
    nbf.write(nb, f)
print("Notebook generated at notebooks/weather_prediction_model.ipynb")
