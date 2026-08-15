import json
import os

notebook_content = {
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Nepal Weather Prediction - ML Pipeline\n",
    "\n",
    "This notebook demonstrates the end-to-end Machine Learning pipeline for the Nepal Weather Prediction project. It covers Data Inspection, Data Cleaning, Exploratory Data Analysis (EDA), Feature Engineering, Model Training, and Evaluation."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "import pandas as pd\n",
    "import numpy as np\n",
    "import plotly.express as px\n",
    "import matplotlib.pyplot as plt\n",
    "import seaborn as sns\n",
    "from sklearn.model_selection import TimeSeriesSplit\n",
    "from sklearn.linear_model import LinearRegression\n",
    "from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor\n",
    "from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score\n",
    "\n",
    "# Set seaborn style for plots\n",
    "sns.set_theme(style=\"darkgrid\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 1. Data Inspection & Cleaning"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Load Dataset\n",
    "df = pd.read_csv('../data/nepal_293_cities_weather_2020_2025.csv')\n",
    "\n",
    "# Parse Dates\n",
    "df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y', errors='coerce')\n",
    "df = df.dropna(subset=['Date'])\n",
    "\n",
    "print(\"Dataset Shape:\", df.shape)\n",
    "df.head()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Map Districts to Provinces\n",
    "DISTRICT_TO_PROVINCE = {\n",
    "    \"Bhojpur\": \"Koshi\", \"Dhankuta\": \"Koshi\", \"Ilam\": \"Koshi\", \"Jhapa\": \"Koshi\", \"Khotang\": \"Koshi\", \"Morang\": \"Koshi\", \"Okhaldhunga\": \"Koshi\", \"Panchthar\": \"Koshi\", \"Sankhuwasabha\": \"Koshi\", \"Solukhumbu\": \"Koshi\", \"Sunsari\": \"Koshi\", \"Taplejung\": \"Koshi\", \"Terhathum\": \"Koshi\", \"Udayapur\": \"Koshi\",\n",
    "    \"Bara\": \"Madhesh\", \"Dhanusha\": \"Madhesh\", \"Mahottari\": \"Madhesh\", \"Parsa\": \"Madhesh\", \"Rautahat\": \"Madhesh\", \"Saptari\": \"Madhesh\", \"Sarlahi\": \"Madhesh\", \"Siraha\": \"Madhesh\",\n",
    "    \"Bhaktapur\": \"Bagmati\", \"Chitwan\": \"Bagmati\", \"Dhading\": \"Bagmati\", \"Dolakha\": \"Bagmati\", \"Kathmandu\": \"Bagmati\", \"Kavrepalanchok\": \"Bagmati\", \"Lalitpur\": \"Bagmati\", \"Makwanpur\": \"Bagmati\", \"Nuwakot\": \"Bagmati\", \"Ramechhap\": \"Bagmati\", \"Rasuwa\": \"Bagmati\", \"Sindhuli\": \"Bagmati\", \"Sindhupalchok\": \"Bagmati\",\n",
    "    \"Baglung\": \"Gandaki\", \"Gorkha\": \"Gandaki\", \"Kaski\": \"Gandaki\", \"Lamjung\": \"Gandaki\", \"Manang\": \"Gandaki\", \"Mustang\": \"Gandaki\", \"Myagdi\": \"Gandaki\", \"Nawalpur\": \"Gandaki\", \"Parbat\": \"Gandaki\", \"Syangja\": \"Gandaki\", \"Tanahun\": \"Gandaki\",\n",
    "    \"Arghakhanchi\": \"Lumbini\", \"Banke\": \"Lumbini\", \"Bardiya\": \"Lumbini\", \"Dang\": \"Lumbini\", \"Gulmi\": \"Lumbini\", \"Kapilvastu\": \"Lumbini\", \"Parasi\": \"Lumbini\", \"Palpa\": \"Lumbini\", \"Pyuthan\": \"Lumbini\", \"Rolpa\": \"Lumbini\", \"Rupandehi\": \"Lumbini\", \"East Rukum\": \"Lumbini\",\n",
    "    \"Dailekh\": \"Karnali\", \"Dolpa\": \"Karnali\", \"Humla\": \"Karnali\", \"Jajarkot\": \"Karnali\", \"Jumla\": \"Karnali\", \"Kalikot\": \"Karnali\", \"Mugu\": \"Karnali\", \"Salyan\": \"Karnali\", \"Surkhet\": \"Karnali\", \"West Rukum\": \"Karnali\",\n",
    "    \"Achham\": \"Sudurpashchim\", \"Baitadi\": \"Sudurpashchim\", \"Bajhang\": \"Sudurpashchim\", \"Bajura\": \"Sudurpashchim\", \"Dadeldhura\": \"Sudurpashchim\", \"Darchula\": \"Sudurpashchim\", \"Doti\": \"Sudurpashchim\", \"Kailali\": \"Sudurpashchim\", \"Kanchanpur\": \"Sudurpashchim\"\n",
    "}\n",
    "df['Province'] = df['District'].map(DISTRICT_TO_PROVINCE).fillna('Unknown')\n",
    "df = df.sort_values(by=['City', 'Date']).reset_index(drop=True)\n",
    "print(\"Missing Values:\\n\", df.isnull().sum())"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 2. Exploratory Data Analysis (EDA)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Temperature distribution across Provinces\n",
    "plt.figure(figsize=(10, 6))\n",
    "sns.boxplot(x='Province', y='Temp_2m', data=df)\n",
    "plt.title('Temperature Distribution by Province')\n",
    "plt.xticks(rotation=45)\n",
    "plt.show()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 3. Feature Engineering"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "def feature_engineering(df):\n",
    "    df = df.copy()\n",
    "    # Temporal\n",
    "    df['Year'] = df['Date'].dt.year\n",
    "    df['Month'] = df['Date'].dt.month\n",
    "    df['DayOfYear'] = df['Date'].dt.dayofyear\n",
    "    \n",
    "    df['Month_sin'] = np.sin(2 * np.pi * df['Month']/12)\n",
    "    df['Month_cos'] = np.cos(2 * np.pi * df['Month']/12)\n",
    "    df['DayOfYear_sin'] = np.sin(2 * np.pi * df['DayOfYear']/365.25)\n",
    "    df['DayOfYear_cos'] = np.cos(2 * np.pi * df['DayOfYear']/365.25)\n",
    "    \n",
    "    # Lags & Rolling Means\n",
    "    grouped = df.groupby('City')\n",
    "    df['Temp_2m_lag1'] = grouped['Temp_2m'].shift(1)\n",
    "    df['Precip_lag1'] = grouped['Precip'].shift(1)\n",
    "    df['RH_2m_lag1'] = grouped['RH_2m'].shift(1)\n",
    "    \n",
    "    df['Temp_2m_roll3'] = grouped['Temp_2m'].rolling(window=3, min_periods=1).mean().reset_index(level=0, drop=True)\n",
    "    df['Temp_2m_roll7'] = grouped['Temp_2m'].rolling(window=7, min_periods=1).mean().reset_index(level=0, drop=True)\n",
    "    df['Precip_roll3'] = grouped['Precip'].rolling(window=3, min_periods=1).mean().reset_index(level=0, drop=True)\n",
    "    df['RH_2m_roll3'] = grouped['RH_2m'].rolling(window=3, min_periods=1).mean().reset_index(level=0, drop=True)\n",
    "    \n",
    "    # Targets\n",
    "    df['Precip_tomorrow'] = grouped['Precip'].shift(-1)\n",
    "    df['RH_2m_tomorrow'] = grouped['RH_2m'].shift(-1)\n",
    "    return df\n",
    "\n",
    "df_engineered = feature_engineering(df)\n",
    "df_engineered.head()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 4. Modeling & Evaluation"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "features = [\n",
    "    'Latitude', 'Longitude', 'Temp_2m', 'Precip', 'RH_2m', 'Pressure', \n",
    "    'Month_sin', 'Month_cos', 'DayOfYear_sin', 'DayOfYear_cos',\n",
    "    'Temp_2m_lag1', 'Precip_lag1', 'RH_2m_lag1',\n",
    "    'Temp_2m_roll3', 'Temp_2m_roll7', 'Precip_roll3', 'RH_2m_roll3'\n",
    "]\n",
    "targets = ['Temp_2m_tomorrow', 'Precip_tomorrow', 'RH_2m_tomorrow']\n",
    "\n",
    "df_clean = df_engineered.dropna(subset=features + targets).copy()\n",
    "\n",
    "# Chronological Split\n",
    "train_df = df_clean[df_clean['Year'] < 2024]\n",
    "test_df = df_clean[df_clean['Year'] >= 2024]\n",
    "\n",
    "X_train, y_train = train_df[features], train_df['Temp_2m_tomorrow']\n",
    "X_test, y_test = test_df[features], test_df['Temp_2m_tomorrow']\n",
    "\n",
    "print(\"Train size:\", X_train.shape)\n",
    "print(\"Test size:\", X_test.shape)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Train Models for Temperature Prediction\n",
    "models = {\n",
    "    \"Linear Regression\": LinearRegression(),\n",
    "    \"Random Forest\": RandomForestRegressor(n_estimators=10, max_depth=5, random_state=42, n_jobs=-1),\n",
    "    \"HistGradientBoosting\": HistGradientBoostingRegressor(random_state=42)\n",
    "}\n",
    "\n",
    "for name, model in models.items():\n",
    "    model.fit(X_train, y_train)\n",
    "    preds = model.predict(X_test)\n",
    "    r2 = r2_score(y_test, preds)\n",
    "    rmse = np.sqrt(mean_squared_error(y_test, preds))\n",
    "    print(f\"{name} - RMSE: {rmse:.4f}, R2: {r2:.4f}\")"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.10.0"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}

with open("notebooks/Weather_Prediction_EDA_Modeling.ipynb", "w") as f:
    json.dump(notebook_content, f, indent=1)
print("Notebook created successfully.")
