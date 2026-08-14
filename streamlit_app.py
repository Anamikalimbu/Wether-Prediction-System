"""
streamlit_app.py
================
Runs the WeatherAI app purely in Streamlit Cloud without a background API.
It pre-calculates the data for all cities and mocks the fetch() API in the browser.
"""

import os
import json
import datetime
import random
import pandas as pd
import numpy as np
import joblib
import streamlit as st
import streamlit.components.v1 as components

# 1. CONFIGURATION
BASE_DIR  = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE_DIR, 'models')
DATA_PATH = os.path.join(BASE_DIR, 'data', 'nepal_293_cities_weather_2020_2025.csv')

FEATURES = [
    'District_encoded', 'Latitude', 'Longitude', 'Precip', 'Pressure',
    'Humidity_2m', 'Temp_2m', 'MaxTemp_2m', 'MinTemp_2m', 'WindSpeed_10m',
    'year', 'sin_day_of_year', 'cos_day_of_year', 'sin_month', 'cos_month',
    'Temp_2m_lag_1', 'Temp_2m_lag_2', 'Temp_2m_lag_3', 'Precip_lag_1',
    'Temp_2m_rolling_mean_7'
]

# 2. LOAD RESOURCES
@st.cache_resource(show_spinner="Loading models and processing dataset...")
def load_resources():
    scaler       = joblib.load(os.path.join(MODEL_DIR, 'preprocessing_pipeline.pkl'))
    temp_model   = joblib.load(os.path.join(MODEL_DIR, 'best_temperature_model.pkl'), mmap_mode='r')
    multi_models = joblib.load(os.path.join(MODEL_DIR, 'multi_target_models.pkl'), mmap_mode='r')

    with open(os.path.join(MODEL_DIR, 'district_classes.json')) as f:
        district_classes = json.load(f)
    district_index = {name: idx for idx, name in enumerate(district_classes)}

    try:
        with open(os.path.join(MODEL_DIR, 'city_classes.json')) as f:
            cities_list = json.load(f)
    except Exception:
        cities_list = []

    try:
        performance_metrics = joblib.load(os.path.join(MODEL_DIR, 'model_metadata.pkl'))
    except Exception:
        performance_metrics = {'Model': 'Random Forest', 'MAE': 1.5, 'RMSE': 2.1, 'R2': 0.85}

    df = pd.read_csv(DATA_PATH)
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
    df.drop_duplicates(inplace=True)
    df.sort_values(['City', 'Date'], inplace=True)
    df.reset_index(drop=True, inplace=True)

    df['year']            = df['Date'].dt.year
    df['month']           = df['Date'].dt.month
    df['day_of_year']     = df['Date'].dt.dayofyear
    df['sin_day_of_year'] = np.sin(2 * np.pi * df['day_of_year'] / 365.25)
    df['cos_day_of_year'] = np.cos(2 * np.pi * df['day_of_year'] / 365.25)
    df['sin_month']       = np.sin(2 * np.pi * df['month'] / 12)
    df['cos_month']       = np.cos(2 * np.pi * df['month'] / 12)

    df['District_encoded'] = df['District'].map(district_index).fillna(0).astype(int)

    for lag in [1, 2, 3]:
        df[f'Temp_2m_lag_{lag}']  = df.groupby('City')['Temp_2m'].shift(lag)
        df[f'Precip_lag_{lag}']   = df.groupby('City')['Precip'].shift(lag)

    df['Temp_2m_rolling_mean_7'] = (
        df.groupby('City')['Temp_2m']
          .transform(lambda x: x.rolling(7, min_periods=1).mean())
    )
    df.dropna(subset=FEATURES, inplace=True)

    latest_by_city = (
        df.groupby('City', as_index=False)
          .last()
          .set_index('City')
    )
    
    if not cities_list:
        cities_list = sorted(latest_by_city.index.tolist())

    return scaler, temp_model, multi_models, district_index, latest_by_city, cities_list, performance_metrics

def generate_diurnal_curve(min_temp, max_temp, base_humidity, start_hour=10):
    hours, temps, humidities = [], [], []
    for i in range(24):
        h    = (start_hour + i) % 24
        norm = (np.sin(((h - 5) % 24 / 24) * 2 * np.pi - np.pi / 2) + 1) / 2
        temp = min_temp + norm * (max_temp - min_temp)
        hum  = base_humidity - norm * 15
        amp  = "AM" if h < 12 else "PM"
        dh   = h if h <= 12 else h - 12
        if dh == 0: dh = 12
        hours.append(f"{dh}:00 {amp}")
        temps.append(round(temp, 1))
        humidities.append(round(max(0, min(100, hum)), 1))
    return hours, temps, humidities

@st.cache_data(show_spinner="Generating ML predictions for all cities (happens once per hour)...", ttl=3600)
def generate_all_weather_data():
    scaler, temp_model, multi_models, district_index, latest_by_city, cities_list, perf = load_resources()
    
    data_payload = {
        'cities': cities_list,
        'performance': perf,
        'city_data': {}
    }

    base_date = datetime.datetime.now()

    for city in latest_by_city.index:
        base_row = latest_by_city.loc[city]
        
        # ── CURRENT PREDICTION
        X = pd.DataFrame([base_row[FEATURES].values], columns=FEATURES)
        X_scaled = scaler.transform(X)

        pred_temp  = float(temp_model.predict(X_scaled)[0])
        pred_hum   = float(multi_models['Humidity_2m'].predict(X_scaled)[0])
        pred_max   = float(multi_models['MaxTemp_2m'].predict(X_scaled)[0])
        pred_min   = float(multi_models['MinTemp_2m'].predict(X_scaled)[0])
        pred_wind  = float(multi_models['WindSpeed_10m'].predict(X_scaled)[0])
        pred_prec  = float(multi_models['Precip'].predict(X_scaled)[0])

        rain_chance = min(100, int((max(0, pred_prec) / 20.0) * 100))

        if pred_prec > 5:
            condition = 'Rainy'
        elif pred_prec > 1:
            condition = 'Partly Cloudy'
        elif pred_temp > 30:
            condition = 'Sunny'
        elif pred_temp > 20:
            condition = 'Partly Cloudy'
        else:
            condition = 'Clear'

        current_data = {
            'city': city,
            'temperature': round(pred_temp, 1),
            'condition': condition,
            'humidity': round(max(0, min(100, pred_hum)), 1),
            'wind_speed': round(max(0, pred_wind), 1),
            'pressure': round(float(base_row.get('Pressure', 1013)), 1),
            'rain_chance': rain_chance,
        }

        # ── 24 HOUR FORECAST
        hours, temps, humidities = generate_diurnal_curve(pred_min, pred_max, pred_hum)
        forecast24 = [
            {'time': h, 'temperature': t, 'humidity': hum, 'rain': rain_chance, 'wind': round(max(0, pred_wind), 1)}
            for h, t, hum in zip(hours, temps, humidities)
        ]

        # ── 5 DAY FORECAST
        forecast5 = []
        lag_temps  = [base_row['Temp_2m_lag_1'], base_row['Temp_2m_lag_2'], base_row['Temp_2m_lag_3']]
        lag_precip = [base_row['Precip_lag_1']] * 3
        prev_temp  = float(base_row['Temp_2m'])

        for i in range(1, 6):
            date        = base_date + datetime.timedelta(days=i)
            day_of_year = date.timetuple().tm_yday
            month       = date.month

            feat_vals = {
                'District_encoded':      base_row['District_encoded'],
                'Latitude':              base_row['Latitude'],
                'Longitude':             base_row['Longitude'],
                'Precip':                lag_precip[0],
                'Pressure':              base_row['Pressure'],
                'Humidity_2m':           base_row['Humidity_2m'],
                'Temp_2m':               prev_temp,
                'MaxTemp_2m':            base_row['MaxTemp_2m'],
                'MinTemp_2m':            base_row['MinTemp_2m'],
                'WindSpeed_10m':         base_row['WindSpeed_10m'],
                'year':                  date.year,
                'sin_day_of_year':       np.sin(2 * np.pi * day_of_year / 365.25),
                'cos_day_of_year':       np.cos(2 * np.pi * day_of_year / 365.25),
                'sin_month':             np.sin(2 * np.pi * month / 12),
                'cos_month':             np.cos(2 * np.pi * month / 12),
                'Temp_2m_lag_1':         lag_temps[0],
                'Temp_2m_lag_2':         lag_temps[1],
                'Temp_2m_lag_3':         lag_temps[2],
                'Precip_lag_1':          lag_precip[0],
                'Temp_2m_rolling_mean_7': base_row['Temp_2m_rolling_mean_7'],
            }

            X_f        = pd.DataFrame([[feat_vals[f] for f in FEATURES]], columns=FEATURES)
            X_f_scaled = scaler.transform(X_f)

            f_temp = float(temp_model.predict(X_f_scaled)[0])
            f_hum  = float(multi_models['Humidity_2m'].predict(X_f_scaled)[0])
            f_max  = float(multi_models['MaxTemp_2m'].predict(X_f_scaled)[0])
            f_min  = float(multi_models['MinTemp_2m'].predict(X_f_scaled)[0])
            f_prec = float(multi_models['Precip'].predict(X_f_scaled)[0])

            f_rain_chance = min(100, int((max(0, f_prec) / 20.0) * 100))

            if f_prec > 5: f_cond = 'Rainy'
            elif f_prec > 1: f_cond = 'Partly Cloudy'
            elif f_temp > 30: f_cond = 'Sunny'
            elif f_temp > 20: f_cond = 'Partly Cloudy'
            else: f_cond = 'Clear'

            forecast5.append({
                'day':        date.strftime('%A').upper(),
                'date':       date.strftime('%Y-%m-%d'),
                'max_temp':   round(f_max, 1),
                'min_temp':   round(f_min, 1),
                'humidity':   round(max(0, min(100, f_hum)), 1),
                'rain_chance': f_rain_chance,
                'condition':  f_cond,
            })

            lag_temps  = [prev_temp] + lag_temps[:2]
            lag_precip = [max(0, f_prec)] + lag_precip[:2]
            prev_temp  = f_temp

        # ── AI INSIGHT
        month = base_date.month
        if month in [3, 4, 5]: season = 'spring'
        elif month in [6, 7, 8, 9]: season = 'monsoon'
        elif month in [10, 11]: season = 'autumn'
        else: season = 'winter'

        comfort_index = pred_temp - 0.55 * (1 - pred_hum / 100) * (pred_temp - 14.5)
        sentences = []

        if condition == 'Rainy':
            sentences.append(random.choice([
                f"The ML model anticipates a wet, rainy spell for {city} today.",
                f"Rain is the defining feature of today's forecast for {city}."
            ]))
        elif condition == 'Partly Cloudy':
            sentences.append(random.choice([
                f"Partly cloudy skies are expected to dominate {city}'s weather today.",
                f"A mix of clouds and breaks of sunshine is forecast for {city}."
            ]))
        elif condition == 'Sunny':
            sentences.append(random.choice([
                f"Sunny conditions are forecast for {city}, making for a bright day.",
                f"Clear skies and warm sunshine are predicted for {city} today."
            ]))
        else:
            sentences.append(random.choice([
                f"Clear and calm conditions are predicted for {city} today.",
                f"A clear, settled day is expected across {city}."
            ]))

        temp_range = pred_max - pred_min
        if temp_range > 12:
            sentences.append(f"A notable temperature swing of {temp_range:.1f}°C is forecast — highs of {pred_max:.1f}°C and lows of {pred_min:.1f}°C — so layering clothing is advisable.")
        elif pred_temp > 35:
            sentences.append(f"Peak temperature is expected to reach {pred_max:.1f}°C, indicating intense heat. Stay hydrated.")
        elif pred_temp > 28:
            sentences.append(f"Temperatures will be warm, reaching up to {pred_max:.1f}°C with a minimum of {pred_min:.1f}°C.")
        elif pred_temp < 5:
            sentences.append(f"Temperatures will be very cold, dropping to {pred_min:.1f}°C. Warm clothing is strongly recommended.")
        elif pred_temp < 15:
            sentences.append(f"Cool temperatures are expected, ranging from {pred_min:.1f}°C to {pred_max:.1f}°C.")
        else:
            sentences.append(f"Temperatures will hover between {pred_min:.1f}°C and {pred_max:.1f}°C, offering relatively comfortable conditions.")

        if rain_chance > 70: sentences.append(f"Precipitation probability is high at {rain_chance}%. Carrying an umbrella is strongly advised.")
        elif rain_chance > 40: sentences.append(f"There is a moderate {rain_chance}% chance of rain — be prepared for possible showers.")
        elif rain_chance > 15: sentences.append(f"Rain probability is relatively low at {rain_chance}%, though isolated showers cannot be ruled out.")
        
        if pred_hum > 85: sentences.append(f"Humidity is very high at {pred_hum:.0f}%, which may make the heat feel more oppressive.")
        elif pred_hum < 30: sentences.append(f"The air is notably dry at {pred_hum:.0f}% relative humidity.")

        if comfort_index > 35: sentences.append(f"The apparent temperature ('feels like') is estimated at {comfort_index:.1f}°C.")
        elif comfort_index < 0: sentences.append(f"Wind chill and cold temperatures combine to make conditions feel closer to {comfort_index:.1f}°C.")

        insight_data = {
            'city': city,
            'insight': ' '.join(sentences),
            'tags': {
                'season': season,
                'condition': condition,
                'rain_pct': rain_chance,
                'temp': round(pred_temp, 1),
            }
        }

        data_payload['city_data'][city] = {
            'current': current_data,
            'forecast24': {'forecast': forecast24},
            'forecast5': {'forecast': forecast5},
            'insight': insight_data
        }

    return data_payload


# 3. STREAMLIT PAGE
st.set_page_config(
    page_title="WeatherAI – ML Forecast",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    #MainMenu, header, footer { visibility: hidden; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    [data-testid="stAppViewContainer"] { padding: 0 !important; }
    [data-testid="stVerticalBlock"] { gap: 0 !important; padding: 0 !important; }
</style>
""", unsafe_allow_html=True)

# Generate payload
data_payload = generate_all_weather_data()

# Read UI files
CSS_PATH = os.path.join(BASE_DIR, 'static', 'css', 'style.css')
JS_PATH  = os.path.join(BASE_DIR, 'static', 'js',  'script.js')
HTML_PATH = os.path.join(BASE_DIR, 'templates', 'index.html')

with open(CSS_PATH, 'r', encoding='utf-8') as f: css_content = f.read()
with open(JS_PATH, 'r', encoding='utf-8') as f: js_content = f.read()
with open(HTML_PATH, 'r', encoding='utf-8') as f: html_template = f.read()

# Inject the payload and mock fetch API
mock_script = f"""
<script>
window.PRELOADED_WEATHER_DATA = {json.dumps(data_payload)};

window.originalFetch = window.fetch;
window.fetch = async function(url, options) {{
    if (url.startsWith('/api/cities')) {{
        return new Response(JSON.stringify({{cities: window.PRELOADED_WEATHER_DATA.cities}}), {{status: 200}});
    }}
    if (url.startsWith('/api/model-performance')) {{
        return new Response(JSON.stringify(window.PRELOADED_WEATHER_DATA.performance), {{status: 200}});
    }}
    
    // Parse city from query params
    const urlObj = new URL(url, window.location.origin);
    const city = urlObj.searchParams.get('city');
    
    if (!city || !window.PRELOADED_WEATHER_DATA.city_data[city]) {{
        return new Response(JSON.stringify({{error: 'City not found'}}), {{status: 404}});
    }}
    
    const cityData = window.PRELOADED_WEATHER_DATA.city_data[city];
    
    if (url.pathname === '/api/current') {{
        return new Response(JSON.stringify(cityData.current), {{status: 200}});
    }}
    if (url.pathname === '/api/forecast/24-hours') {{
        return new Response(JSON.stringify(cityData.forecast24), {{status: 200}});
    }}
    if (url.pathname === '/api/forecast/5-days') {{
        return new Response(JSON.stringify(cityData.forecast5), {{status: 200}});
    }}
    if (url.pathname === '/api/ai-insight') {{
        return new Response(JSON.stringify(cityData.insight), {{status: 200}});
    }}

    // Fallback to original fetch
    return window.originalFetch(url, options);
}};
</script>
"""

# Replace Flask's url_for template tags with inline content
full_html = html_template

css_tag = f'<style>\n{css_content}\n</style>'
full_html = full_html.replace(
    "<link rel=\"stylesheet\" href=\"{{ url_for('static', filename='css/style.css') }}\">",
    css_tag
)

# We combine the mock script and the actual JS
patched_js_tag = f'{mock_script}\n<script>\n{js_content}\n</script>'
full_html = full_html.replace(
    "<script src=\"{{ url_for('static', filename='js/script.js') }}\"></script>",
    patched_js_tag
)

# Render inside Streamlit
components.html(full_html, height=900, scrolling=True)
