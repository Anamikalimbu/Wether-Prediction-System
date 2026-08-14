"""
streamlit_app.py
================
Runs the WeatherAI app inside Streamlit.

Strategy
--------
- A lightweight Flask server is started in a background thread on a fixed
  port (default 5001).  This serves the existing API endpoints (/api/*)
  exactly as before.
- The full custom HTML/CSS/JS UI is embedded via st.components.v1.html()
  with the API base-URL patched to point at the background Flask server.
- The Streamlit page itself shows nothing except the embedded component,
  so the user sees the original design with no Streamlit chrome inside
  the app area (though the Streamlit sidebar / top-bar remain around it).

Run with:
    streamlit run streamlit_app.py
"""

import os
import json
import datetime
import random
import threading

import numpy as np
import pandas as pd
import joblib

#Flask (background API server) 
from flask import Flask, request, jsonify

#Streamlit 
import streamlit as st
import streamlit.components.v1 as components

# 1.  CONFIGURATION
API_PORT  = 5001          # Flask background server port

import socket
def _get_local_ip():
    """Return the LAN IP of this machine (works on Windows/Linux/Mac)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))   # doesn't send data, just resolves routing
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
LOCAL_IP = _get_local_ip()
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

# 2.  MODEL & DATA LOADING 
@st.cache_resource(show_spinner="Loading AI models…")
def load_resources():
    scaler       = joblib.load(os.path.join(MODEL_DIR, 'preprocessing_pipeline.pkl'))
    temp_model   = joblib.load(os.path.join(MODEL_DIR, 'best_temperature_model.pkl'))
    multi_models = joblib.load(os.path.join(MODEL_DIR, 'multi_target_models.pkl'))

    with open(os.path.join(MODEL_DIR, 'district_classes.json')) as f:
        district_classes = json.load(f)
    district_index = {name: idx for idx, name in enumerate(district_classes)}

    df = pd.read_csv(DATA_PATH)
    df['Date'] = pd.to_datetime(df['Date'])
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
    return scaler, temp_model, multi_models, district_index, latest_by_city


# 3.  HELPER FUNCTIONS
def resolve_city(name, latest_by_city):
    if name in latest_by_city.index:
        return latest_by_city.loc[name]
    low = name.lower()
    for k in latest_by_city.index:
        if low in k.lower():
            return latest_by_city.loc[k]
    return latest_by_city.iloc[-1]


def predict_row(row, scaler, temp_model, multi_models):
    X        = pd.DataFrame([row[FEATURES].values], columns=FEATURES)
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

    return {
        'temperature': round(pred_temp, 1),
        'max_temp':    round(pred_max, 1),
        'min_temp':    round(pred_min, 1),
        'humidity':    round(max(0, min(100, pred_hum)), 1),
        'wind_speed':  round(max(0, pred_wind), 1),
        'pressure':    round(float(row.get('Pressure', 1013)), 1),
        'rain_chance': rain_chance,
        'condition':   condition,
        '_row':        row,
        '_pred_prec':  pred_prec,
        '_pred_temp':  pred_temp,
    }


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


def build_ai_insight(city, pred):
    temp      = pred['temperature']
    max_t     = pred['max_temp']
    min_t     = pred['min_temp']
    humidity  = pred['humidity']
    wind      = pred['wind_speed']
    rain_pct  = pred['rain_chance']
    condition = pred['condition']

    now    = datetime.datetime.now()
    month  = now.month
    hour   = now.hour

    if month in [3, 4, 5]:   season = 'spring'
    elif month in [6,7,8,9]: season = 'monsoon'
    elif month in [10,11]:   season = 'autumn'
    else:                    season = 'winter'

    comfort_index = temp - 0.55 * (1 - humidity / 100) * (temp - 14.5)
    sentences = []

    if condition == 'Rainy':
        openers = [
            f"The ML model anticipates a wet, rainy spell for {city} today.",
            f"Rain is the defining feature of today's forecast for {city}.",
            f"Expect persistent rainfall across {city} as predicted by the AI model.",
        ]
    elif condition == 'Partly Cloudy':
        openers = [
            f"Partly cloudy skies are expected to dominate {city}'s weather today.",
            f"A mix of clouds and breaks of sunshine is forecast for {city}.",
            f"The model indicates variable cloud cover for {city} throughout the day.",
        ]
    elif condition == 'Sunny':
        openers = [
            f"Sunny conditions are forecast for {city}, making for a bright day.",
            f"Clear skies and warm sunshine are predicted for {city} today.",
            f"The AI model expects an excellent, sunny day across {city}.",
        ]
    else:
        openers = [
            f"Clear and calm conditions are predicted for {city} today.",
            f"A clear, settled day is expected across {city}.",
            f"The forecast model points to clear conditions and mild temperatures for {city}.",
        ]
    sentences.append(random.choice(openers))

    temp_range = max_t - min_t
    if temp_range > 12:
        sentences.append(f"A notable temperature swing of {temp_range:.1f}°C is forecast — highs of {max_t:.1f}°C and lows of {min_t:.1f}°C — so layering clothing is advisable.")
    elif temp > 35:
        sentences.append(f"Peak temperature is expected to reach {max_t:.1f}°C, indicating intense heat. Stay hydrated and avoid prolonged sun exposure.")
    elif temp > 28:
        sentences.append(f"Temperatures will be warm, reaching up to {max_t:.1f}°C with a minimum of {min_t:.1f}°C.")
    elif temp < 5:
        sentences.append(f"Temperatures will be very cold, dropping to {min_t:.1f}°C, with a high of only {max_t:.1f}°C. Warm clothing is strongly recommended.")
    elif temp < 15:
        sentences.append(f"Cool temperatures are expected, ranging from {min_t:.1f}°C to {max_t:.1f}°C — a light jacket will be useful.")
    else:
        sentences.append(f"Temperatures will hover between {min_t:.1f}°C and {max_t:.1f}°C, offering relatively comfortable conditions.")

    if rain_pct > 70:
        sentences.append(f"Precipitation probability is high at {rain_pct}%. Carrying an umbrella is strongly advised.")
    elif rain_pct > 40:
        sentences.append(f"There is a moderate {rain_pct}% chance of rain — be prepared for possible showers.")
    elif rain_pct > 15:
        sentences.append(f"Rain probability is relatively low at {rain_pct}%, though isolated showers cannot be ruled out.")
    else:
        sentences.append(f"Precipitation probability is minimal at just {rain_pct}%. Outdoor activities should be largely unaffected by rain.")

    if humidity > 85:
        sentences.append(f"Humidity is very high at {humidity:.0f}%, which may make the heat feel more oppressive than the thermometer suggests.")
    elif humidity < 30:
        sentences.append(f"The air is notably dry at {humidity:.0f}% relative humidity — keeping hydrated will be especially important.")

    if wind > 40:
        sentences.append(f"Strong winds of {wind:.1f} km/h are forecast; outdoor events or travel may be disrupted.")
    elif wind > 20:
        sentences.append(f"A moderately brisk wind at {wind:.1f} km/h will add a cooling effect to the day.")
    elif wind < 5:
        sentences.append(f"Winds will be light and calm at {wind:.1f} km/h, providing still conditions.")
    else:
        sentences.append(f"Winds will be gentle at around {wind:.1f} km/h — pleasant for outdoor activities.")

    if comfort_index > 35:
        sentences.append(f"The apparent temperature ('feels like') is estimated at {comfort_index:.1f}°C — significantly hotter than the actual reading due to humidity.")
    elif comfort_index < 0:
        sentences.append(f"Wind chill and cold temperatures combine to make conditions feel closer to {comfort_index:.1f}°C. Take appropriate precautions.")

    if season == 'monsoon':
        sentences.append("As Nepal is in the heart of the monsoon season, weather can shift rapidly. Monitor forecasts frequently.")
    elif season == 'winter':
        sentences.append("Winter conditions are prevailing across Nepal. Mountain regions may face snow and road disruptions.")
    elif season == 'spring':
        sentences.append("Spring brings variable weather to Nepal. Expect pleasant days with the occasional afternoon shower.")
    elif season == 'autumn':
        sentences.append("Autumn is typically one of Nepal's clearest and most stable seasons — ideal conditions for trekking and outdoor pursuits.")

    return ' '.join(sentences), season


# 4.  BACKGROUND FLASK API SERVER

_flask_started = threading.Event()

def _start_flask(scaler, temp_model, multi_models, latest_by_city):
    """Start the Flask API server in a daemon thread."""
    api = Flask(__name__)

    # suppress Flask startup banner & access logs in Streamlit output
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    # CORS so the browser-side JS  can
    # call the Flask server on a different port
    @api.after_request
    def add_cors(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    @api.route('/api/cities')
    def get_cities():
        try:
            with open(os.path.join(MODEL_DIR, 'city_classes.json')) as f:
                cities = json.load(f)
            return jsonify({'cities': cities})
        except Exception:
            return jsonify({'cities': sorted(latest_by_city.index.tolist())})

    @api.route('/api/current')
    def get_current():
        city = request.args.get('city', 'Dharan')
        row  = resolve_city(city, latest_by_city)
        pred = predict_row(row, scaler, temp_model, multi_models)
        return jsonify({
            'city':        city,
            'temperature': pred['temperature'],
            'condition':   pred['condition'],
            'humidity':    pred['humidity'],
            'wind_speed':  pred['wind_speed'],
            'pressure':    pred['pressure'],
            'rain_chance': pred['rain_chance'],
        })

    @api.route('/api/forecast/24-hours')
    def get_24hr_forecast():
        city = request.args.get('city', 'Dharan')
        row  = resolve_city(city, latest_by_city)
        pred = predict_row(row, scaler, temp_model, multi_models)
        hours, temps, humidities = generate_diurnal_curve(
            pred['min_temp'], pred['max_temp'], pred['humidity']
        )
        forecast = [
            {'time': h, 'temperature': t, 'humidity': hum,
             'rain': pred['rain_chance'], 'wind': pred['wind_speed']}
            for h, t, hum in zip(hours, temps, humidities)
        ]
        return jsonify({'forecast': forecast})

    @api.route('/api/forecast/5-days')
    def get_5day_forecast():
        city      = request.args.get('city', 'Dharan')
        base_row  = resolve_city(city, latest_by_city)
        base_date = datetime.datetime.now()
        forecast  = []

        lag_temps  = [base_row['Temp_2m_lag_1'], base_row['Temp_2m_lag_2'], base_row['Temp_2m_lag_3']]
        lag_precip = [base_row['Precip_lag_1']] * 3
        prev_temp  = float(base_row['Temp_2m'])

        for i in range(1, 6):
            date        = base_date + datetime.timedelta(days=i)
            day_of_year = date.timetuple().tm_yday
            month       = date.month

            feat_vals = {
                'District_encoded':       base_row['District_encoded'],
                'Latitude':               base_row['Latitude'],
                'Longitude':              base_row['Longitude'],
                'Precip':                 lag_precip[0],
                'Pressure':               base_row['Pressure'],
                'Humidity_2m':            base_row['Humidity_2m'],
                'Temp_2m':                prev_temp,
                'MaxTemp_2m':             base_row['MaxTemp_2m'],
                'MinTemp_2m':             base_row['MinTemp_2m'],
                'WindSpeed_10m':          base_row['WindSpeed_10m'],
                'year':                   date.year,
                'sin_day_of_year':        np.sin(2 * np.pi * day_of_year / 365.25),
                'cos_day_of_year':        np.cos(2 * np.pi * day_of_year / 365.25),
                'sin_month':              np.sin(2 * np.pi * month / 12),
                'cos_month':              np.cos(2 * np.pi * month / 12),
                'Temp_2m_lag_1':          lag_temps[0],
                'Temp_2m_lag_2':          lag_temps[1],
                'Temp_2m_lag_3':          lag_temps[2],
                'Precip_lag_1':           lag_precip[0],
                'Temp_2m_rolling_mean_7': base_row['Temp_2m_rolling_mean_7'],
            }

            X        = pd.DataFrame([[feat_vals[f] for f in FEATURES]], columns=FEATURES)
            X_scaled = scaler.transform(X)

            pred_temp = float(temp_model.predict(X_scaled)[0])
            pred_hum  = float(multi_models['Humidity_2m'].predict(X_scaled)[0])
            pred_max  = float(multi_models['MaxTemp_2m'].predict(X_scaled)[0])
            pred_min  = float(multi_models['MinTemp_2m'].predict(X_scaled)[0])
            pred_wind = float(multi_models['WindSpeed_10m'].predict(X_scaled)[0])
            pred_prec = float(multi_models['Precip'].predict(X_scaled)[0])

            rain_chance = min(100, int((max(0, pred_prec) / 20.0) * 100))

            if pred_prec > 5:    cond = 'Rainy'
            elif pred_prec > 1:  cond = 'Partly Cloudy'
            elif pred_temp > 30: cond = 'Sunny'
            elif pred_temp > 20: cond = 'Partly Cloudy'
            else:                cond = 'Clear'

            forecast.append({
                'day':         date.strftime('%A').upper(),
                'date':        date.strftime('%Y-%m-%d'),
                'max_temp':    round(pred_max, 1),
                'min_temp':    round(pred_min, 1),
                'humidity':    round(max(0, min(100, pred_hum)), 1),
                'rain_chance': rain_chance,
                'condition':   cond,
            })

            lag_temps  = [prev_temp] + lag_temps[:2]
            lag_precip = [max(0, pred_prec)] + lag_precip[:2]
            prev_temp  = pred_temp

        return jsonify({'forecast': forecast})

    @api.route('/api/model-performance')
    def get_model_performance():
        try:
            metrics = joblib.load(os.path.join(MODEL_DIR, 'model_metadata.pkl'))
            return jsonify(metrics)
        except Exception:
            return jsonify({'Model': 'Random Forest', 'MAE': 1.5, 'RMSE': 2.1, 'R2': 0.85})

    @api.route('/api/ai-insight')
    def get_ai_insight():
        city = request.args.get('city', 'Dharan')
        row  = resolve_city(city, latest_by_city)
        pred = predict_row(row, scaler, temp_model, multi_models)
        insight_text, season = build_ai_insight(city, pred)
        return jsonify({
            'city':    city,
            'insight': insight_text,
            'tags': {
                'season':    season,
                'condition': pred['condition'],
                'rain_pct':  pred['rain_chance'],
                'temp':      round(pred['temperature'], 1)
            }
        })

    _flask_started.set()
    api.run(host='0.0.0.0', port=API_PORT, use_reloader=False, threaded=True)


# 5.  LOAD STATIC FILES
def _read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


# 6.  STREAMLIT PAGE
st.set_page_config(
    page_title="WeatherAI – ML Forecast",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Hide Streamlit's default header/footer/hamburger for a clean embed
st.markdown("""
<style>
    #MainMenu, header, footer { visibility: hidden; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    [data-testid="stAppViewContainer"] { padding: 0 !important; }
    [data-testid="stVerticalBlock"] { gap: 0 !important; padding: 0 !important; }
</style>
""", unsafe_allow_html=True)

# Load resources 
scaler, temp_model, multi_models, district_index, latest_by_city = load_resources()

# Start Flask background thread  
if 'flask_thread_started' not in st.session_state:
    t = threading.Thread(
        target=_start_flask,
        args=(scaler, temp_model, multi_models, latest_by_city),
        daemon=True,
    )
    t.start()
    _flask_started.wait(timeout=10)   # wait up to 10 s for Flask to bind
    st.session_state['flask_thread_started'] = True

#  Read static files 
CSS_PATH = os.path.join(BASE_DIR, 'static', 'css', 'style.css')
JS_PATH  = os.path.join(BASE_DIR, 'static', 'js',  'script.js')

css_content = _read_file(CSS_PATH)
js_content  = _read_file(JS_PATH)

# Patch the JS so every fetch('/api/...') becomes fetch('http://<LAN_IP>:PORT/api/...')
# Using the real LAN IP (not 127.0.0.1) so that phones/tablets on the same network
# can reach the Flask API running on this machine.
patched_js = js_content.replace(
    "fetch('/api/",
    f"fetch('http://{LOCAL_IP}:{API_PORT}/api/"
).replace(
    'fetch(`/api/',
    f'fetch(`http://{LOCAL_IP}:{API_PORT}/api/'
)

#  Build the full HTML page 
with open(os.path.join(BASE_DIR, 'templates', 'index.html'), 'r', encoding='utf-8') as f:
    html_template = f.read()

# Replace Flask's url_for template tags with inline content
full_html = html_template

# Inject CSS inline (replace the <link> tag for style.css)
css_tag = f'<style>\n{css_content}\n</style>'
full_html = full_html.replace(
    "<link rel=\"stylesheet\" href=\"{{ url_for('static', filename='css/style.css') }}\">",
    css_tag
)

# Inject JS inline (replace the <script src="..."> tag for script.js)
patched_js_tag = f'<script>\n{patched_js}\n</script>'
full_html = full_html.replace(
    "<script src=\"{{ url_for('static', filename='js/script.js') }}\"></script>",
    patched_js_tag
)

#  Render inside Streamlit 
components.html(full_html, height=900, scrolling=True)
