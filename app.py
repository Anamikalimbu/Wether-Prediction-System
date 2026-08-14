Yes — from the screenshot, your Streamlit app is stuck while generating ML predictions for all cities.

The important part is:

Generating ML predictions for all cities (happens once per hour)...

This usually means your app is doing a large prediction loop during page loading, and Streamlit is waiting for it to finish before displaying the rest of the UI.

Most likely problem

If you have around 293 municipalities, your code may be doing something like:

for city in cities:
    weather = get_weather(city)
    prediction = model.predict(weather)

If this happens every time Streamlit reruns, the app can appear frozen for several minutes.

Fix 1 — Cache the prediction function

Use Streamlit caching:

@st.cache_data(ttl=3600)
def generate_all_predictions():
    predictions = []


    for city in cities:
        # get weather
        # prepare features
        # model prediction
        predictions.append(...)


    return predictions

Then:

with st.spinner("Generating ML predictions for all cities..."):
    predictions = generate_all_predictions()

ttl=3600 means Streamlit can reuse the result for 1 hour instead of regenerating everything on every rerun.

Fix 2 — Don't run prediction before displaying your UI

If your code currently looks like:

predictions = generate_all_predictions()


st.title("Weather Prediction System")

change it to:

st.title("Weather Prediction System")


st.info("Loading ML predictions...")


predictions = generate_all_predictions()

Better still, put prediction generation behind a button:

st.title("Weather Prediction System")


if st.button("Generate Predictions"):
    with st.spinner("Generating predictions for all cities..."):
        predictions = generate_all_predictions()


    st.success("Predictions generated successfully!")
Fix 3 — Add progress so you know it isn't frozen

For 293 cities:

progress = st.progress(0)
status = st.empty()


predictions = []


for i, city in enumerate(cities):
    status.write(f"Processing {city} ({i + 1}/{len(cities)})...")


    # Your prediction code here


    predictions.append(result)


    progress.progress((i + 1) / len(cities))


status.success("All predictions completed!")

This will show:

Processing Kathmandu (1/293)
Processing Pokhara (2/293)
Processing Lalitpur (3/293)
...

instead of making the browser look stuck.

⚠️ Also check your weather API

If you're calling a weather API 293 times, that is probably the biggest reason.

For example:

for city in cities:
    response = requests.get(weather_api_url)

can take a long time, especially if requests are slow or one request hangs.

Add a timeout:

response = requests.get(
    weather_api_url,
    params=params,
    timeout=10
)

And handle failures:

try:
    response = requests.get(
        weather_api_url,
        params=params,
        timeout=10
    )
    response.raise_for_status()


except requests.RequestException as e:
    st.warning(f"Could not get weather for {city}: {e}")
    continue
⭐ Best structure for your project

Since you're generating predictions for all Nepal municipalities, I'd recommend this architecture:

Streamlit starts
       ↓
Load ML model
       ↓
Load 293 municipalities
       ↓
Check cached predictions
       ↓
 ┌───────────────┐
 │ Cache exists? │
 └───────┬───────┘
         │
    Yes  │  No
     ↓   │   ↓
Use      │ Generate
cache    │ predictions
     ↓   │   ↓
     └───┴───→ Display dashboard

And use:

@st.cache_resource
def load_model():
    return joblib.load("model.pkl")




@st.cache_data(ttl=3600)
def generate_predictions(cities):
    # generate predictions
    return predictions

This is particularly important because Streamlit reruns your Python script whenever the user interacts with widgets.

If it has been stuck for a long time

If the browser has been showing that message for 5–10+ minutes, don't keep waiting. There is probably a slow API call, infinite loop, model issue, or expensive computation.

Send me your app.py / Streamlit code (especially the part containing Generating ML predictions for all cities) and I can point out the exact line causing the problem and rewrite it so the dashboard loads quickly.

Pasted code.py
Python

I checked your uploaded Python file. The important discovery is that this file is your Flask backend, not the Streamlit code shown in your screenshot. Your backend loads the ML models once and provides endpoints such as /api/current, /api/forecast/24-hours, and /api/forecast/5-days.

🔴 Why your Streamlit page is getting stuck

Your backend's /api/current endpoint does this for every city request:

City
 ↓
resolve_city()
 ↓
predict_row()
 ↓
scaler.transform()
 ↓
6 separate ML model predictions
 ↓
JSON response

predict_row() runs six model predictions for one city.

If your Streamlit frontend is doing:

293 cities
 ×
6 ML predictions
 =
1758 model predictions

then the message:

Generating ML predictions for all cities (happens once per hour)...

makes sense.

There is another important clue: your Flask file does not contain an endpoint that generates predictions for all 293 cities at once. It only has /api/current for an individual city.

So your Streamlit frontend is very likely requesting the cities one by one.

✅ Best fix

Instead of making 293 API calls, add a new Flask endpoint:

/api/predictions/all

It should send all 293 cities to the ML models as one batch.

Your current predict_row() creates a DataFrame and calls the scaler/models separately for every city.

We can change that to:

293 cities
     ↓
one DataFrame
     ↓
one scaler.transform()
     ↓
batch ML prediction
     ↓
one JSON response

That should make a huge difference.

Also cache the result

Since your UI says it only needs to happen once per hour, the architecture should be:

Streamlit
   ↓
Check cached predictions
   ↓
 ┌───────────────┐
 │ Cache exists? │
 └───────┬───────┘
         │
     YES │ NO
      ↓  │  ↓
Return   │ Flask batch
cache    │ prediction
         ↓
       Cache
         ↓
     Dashboard
One more thing I noticed

Your backend already creates a very useful lookup containing the latest row for each city:

latest_by_city = (
    df.groupby('City', as_index=False)
      .last()
      .set_index('City')
)

So you do not need to reload the CSV for every city.

That's good.

What I need next

The actual text "Generating ML predictions for all cities (happens once per hour)..." is coming from your Streamlit frontend, because it isn't present in this Flask file.

Upload your Streamlit .py file — probably something like app.py, streamlit_app.py, dashboard.py, etc.

Then I can 
modify the actual code so that:

⚡ 293 cities load much faster
🧠 ML predictions are batch-generated
💾 predictions are cached for 1 hour
🔄 Streamlit doesn't regenerate everything on every interaction
📊 your dashboard appears immediately
❌ no more infinite-looking loading screen

I can also create a simple architecture diagram showing Streamlit → Flask → ML Models → 293 Cities → Cache if you'd like to use it in your project presentation.

update whole

Done. I updated the whole Flask backend and verified that the new file passes Python syntax validation.

Main improvements
⚡ Added batch prediction for all 293 cities
💾 Added 1-hour prediction cache
🚫 Prevents running the ML models repeatedly for every page refresh
📊 Uses one scaler.transform() for all cities instead of city-by-city processing
🧠 Runs each ML model in batch
🔄 Added ?refresh=true to force a new prediction
❤️ Added /api/health
🔗 Added multiple all-city prediction route aliases
🛠️ Improved Flask threading for deployment

The existing individual-city endpoint remains available, so your current frontend functionality isn't removed.

Download the updated backend

Download app_updated.py

Important

Your screenshot's loading message is coming from the Streamlit/frontend side, while the file you uploaded is Flask. The new backend provides:

GET /api/predictions/all

Your frontend should request this once, instead of doing 293 individual prediction requests.

The response will contain:

293 cities
    ↓
1 API request
    ↓
Batch ML prediction
    ↓
Cached for 1 hour
    ↓
Dashboard

So the next file I would update is your Streamlit/frontend .py file, because that's where the "Generating ML predictions for all cities..." loading process is actually happening. 

app_updated.py
Code

Library
/
app_updated.py
from flask import Flask, request, jsonify, render_template
import pandas as pd
import numpy as np
import joblib
import os
import json
import datetime
import random
import time
import threading

app = Flask(__name__)

# ─── Prediction cache ─────────────────────────────────────────────────────────
# The dashboard can request all-city predictions repeatedly.  Keep the result
# in memory for one hour so the ML models are not run 293 times on every load.
ALL_PREDICTIONS_CACHE_TTL = int(os.environ.get('PREDICTIONS_CACHE_TTL', '3600'))
_all_predictions_cache = {'timestamp': 0.0, 'data': None}
_all_predictions_lock = threading.Lock()

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE_DIR, 'models')
DATA_PATH = os.path.join(BASE_DIR, 'data', 'nepal_293_cities_weather_2020_2025.csv')

# Feature list must match train_models.py exactly
FEATURES = [
    'District_encoded', 'Latitude', 'Longitude', 'Precip', 'Pressure',
    'Humidity_2m', 'Temp_2m', 'MaxTemp_2m', 'MinTemp_2m', 'WindSpeed_10m',
    'year', 'sin_day_of_year', 'cos_day_of_year', 'sin_month', 'cos_month',
    'Temp_2m_lag_1', 'Temp_2m_lag_2', 'Temp_2m_lag_3', 'Precip_lag_1',
    'Temp_2m_rolling_mean_7'
]

# ─── Load models ──────────────────────────────────────────────────────────────
print("Loading models …")
scaler       = joblib.load(os.path.join(MODEL_DIR, 'preprocessing_pipeline.pkl'))
temp_model   = joblib.load(os.path.join(MODEL_DIR, 'best_temperature_model.pkl'))
multi_models = joblib.load(os.path.join(MODEL_DIR, 'multi_target_models.pkl'))

with open(os.path.join(MODEL_DIR, 'district_classes.json')) as f:
    district_classes = json.load(f)           # list, ordered as LabelEncoder saw them
district_index = {name: idx for idx, name in enumerate(district_classes)}

# ─── Load & pre-process dataset once ─────────────────────────────────────────
print("Loading CSV (may take a moment) …")
df = pd.read_csv(DATA_PATH)
df['Date'] = pd.to_datetime(df['Date'])
df.drop_duplicates(inplace=True)
df.sort_values(['City', 'Date'], inplace=True)
df.reset_index(drop=True, inplace=True)

# Time features
df['year']            = df['Date'].dt.year
df['month']           = df['Date'].dt.month
df['day_of_year']     = df['Date'].dt.dayofyear
df['sin_day_of_year'] = np.sin(2 * np.pi * df['day_of_year'] / 365.25)
df['cos_day_of_year'] = np.cos(2 * np.pi * df['day_of_year'] / 365.25)
df['sin_month']       = np.sin(2 * np.pi * df['month'] / 12)
df['cos_month']       = np.cos(2 * np.pi * df['month'] / 12)

# District encoding (same as training)
df['District_encoded'] = df['District'].map(district_index).fillna(0).astype(int)

# Lag features — grouped by City (not District) to respect per-city ordering
for lag in [1, 2, 3]:
    df[f'Temp_2m_lag_{lag}']  = df.groupby('City')['Temp_2m'].shift(lag)
    df[f'Precip_lag_{lag}']   = df.groupby('City')['Precip'].shift(lag)

# Rolling mean
df['Temp_2m_rolling_mean_7'] = (
    df.groupby('City')['Temp_2m']
      .transform(lambda x: x.rolling(7, min_periods=1).mean())
)

df.dropna(subset=FEATURES, inplace=True)

# Build per-city lookup of the most recent row
latest_by_city = (
    df.groupby('City', as_index=False)
      .last()
      .set_index('City')
)
print(f"Ready. {len(latest_by_city)} cities available.")
print(
    f"All-city prediction cache: {ALL_PREDICTIONS_CACHE_TTL} seconds "
    f"({ALL_PREDICTIONS_CACHE_TTL / 3600:.1f} hours)."
)


# ─── Helpers ──────────────────────────────────────────────────────────────────
def resolve_city(name: str):
    """Return the row Series for name, or the closest match, or global last."""
    if name in latest_by_city.index:
        return latest_by_city.loc[name]
    low = name.lower()
    for k in latest_by_city.index:
        if low in k.lower():
            return latest_by_city.loc[k]
    return latest_by_city.iloc[-1]


def predict_row(row) -> dict:
    """Run all models on one feature row, return a dict of predictions."""
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
        # keep raw lags for recursive forecast
        '_lag_temps':  [row['Temp_2m_lag_1'], row['Temp_2m_lag_2'], row['Temp_2m_lag_3']],
        '_lag_precip': [row['Precip_lag_1'],  row['Precip_lag_1'],  row['Precip_lag_1']],
        '_prev_temp':  float(row['Temp_2m']),
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

        amp = "AM" if h < 12 else "PM"
        dh  = h if h <= 12 else h - 12
        if dh == 0: dh = 12
        hours.append(f"{dh}:00 {amp}")
        temps.append(round(temp, 1))
        humidities.append(round(max(0, min(100, hum)), 1))
    return hours, temps, humidities



# ─── Batch prediction helpers ──────────────────────────────────────────────────
def _condition_from_prediction(pred_temp, pred_prec):
    """Return the same weather condition labels used by predict_row()."""
    if pred_prec > 5:
        return 'Rainy'
    elif pred_prec > 1:
        return 'Partly Cloudy'
    elif pred_temp > 30:
        return 'Sunny'
    elif pred_temp > 20:
        return 'Partly Cloudy'
    return 'Clear'


def generate_all_predictions(force_refresh=False):
    """
    Generate predictions for every available city in one batch.

    This is much faster than calling predict_row() separately for every city:
    - one DataFrame for all cities
    - one scaler.transform()
    - one predict() call per target model
    - one cached result for one hour
    """
    now = time.time()

    with _all_predictions_lock:
        cached = _all_predictions_cache['data']
        cached_at = _all_predictions_cache['timestamp']

        if (
            not force_refresh
            and cached is not None
            and (now - cached_at) < ALL_PREDICTIONS_CACHE_TTL
        ):
            return cached, True

        # latest_by_city is already prepared during application startup.
        cities_df = latest_by_city.reset_index()

        # Keep only the model features and ensure the same column order
        # used during training.
        X = cities_df[FEATURES].copy()
        X_scaled = scaler.transform(X)

        # Batch predictions: each model receives all cities at once.
        pred_temp = np.asarray(temp_model.predict(X_scaled), dtype=float)
        pred_hum = np.asarray(
            multi_models['Humidity_2m'].predict(X_scaled), dtype=float
        )
        pred_max = np.asarray(
            multi_models['MaxTemp_2m'].predict(X_scaled), dtype=float
        )
        pred_min = np.asarray(
            multi_models['MinTemp_2m'].predict(X_scaled), dtype=float
        )
        pred_wind = np.asarray(
            multi_models['WindSpeed_10m'].predict(X_scaled), dtype=float
        )
        pred_prec = np.asarray(
            multi_models['Precip'].predict(X_scaled), dtype=float
        )

        results = []

        for i, city in enumerate(cities_df['City']):
            temperature = float(pred_temp[i])
            precipitation = float(pred_prec[i])
            humidity = max(0, min(100, float(pred_hum[i])))
            wind_speed = max(0, float(pred_wind[i]))

            rain_chance = min(
                100, int((max(0, precipitation) / 20.0) * 100)
            )

            results.append({
                'city': str(city),
                'temperature': round(temperature, 1),
                'max_temp': round(float(pred_max[i]), 1),
                'min_temp': round(float(pred_min[i]), 1),
                'humidity': round(humidity, 1),
                'wind_speed': round(wind_speed, 1),
                'pressure': round(
                    float(cities_df.iloc[i].get('Pressure', 1013)), 1
                ),
                'rain_chance': rain_chance,
                'condition': _condition_from_prediction(
                    temperature, precipitation
                )
            })

        # Sort alphabetically for a stable API response.
        results.sort(key=lambda item: item['city'].lower())

        _all_predictions_cache['data'] = results
        _all_predictions_cache['timestamp'] = time.time()

        return results, False


# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/cities')
def get_cities():
    try:
        with open(os.path.join(MODEL_DIR, 'city_classes.json')) as f:
            cities = json.load(f)
        return jsonify({'cities': cities})
    except Exception:
        return jsonify({'cities': sorted(latest_by_city.index.tolist())})



@app.route('/api/predictions/all')
def get_all_predictions():
    """
    Return predictions for all available cities.

    Cached for one hour by default. Use ?refresh=true to force regeneration.
    """
    refresh = request.args.get('refresh', 'false').lower() == 'true'

    try:
        predictions, from_cache = generate_all_predictions(
            force_refresh=refresh
        )

        return jsonify({
            'success': True,
            'count': len(predictions),
            'cached': from_cache,
            'cache_ttl_seconds': ALL_PREDICTIONS_CACHE_TTL,
            'generated_at': datetime.datetime.now().isoformat(),
            'predictions': predictions
        })

    except Exception as e:
        app.logger.exception("Failed to generate all-city predictions")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Backward-friendly aliases for frontends that use a different route name.
@app.route('/api/all-predictions')
def get_all_predictions_alias():
    return get_all_predictions()


@app.route('/api/cities/predictions')
def get_city_predictions_alias():
    return get_all_predictions()


@app.route('/api/current')
def get_current():
    city = request.args.get('city', 'Dharan')
    row  = resolve_city(city)
    pred = predict_row(row)
    return jsonify({
        'city':        city,
        'temperature': pred['temperature'],
        'condition':   pred['condition'],
        'humidity':    pred['humidity'],
        'wind_speed':  pred['wind_speed'],
        'pressure':    pred['pressure'],
        'rain_chance': pred['rain_chance'],
    })


@app.route('/api/forecast/24-hours')
def get_24hr_forecast():
    city = request.args.get('city', 'Dharan')
    row  = resolve_city(city)
    pred = predict_row(row)

    hours, temps, humidities = generate_diurnal_curve(
        pred['min_temp'], pred['max_temp'], pred['humidity']
    )
    forecast = [
        {'time': h, 'temperature': t, 'humidity': hum,
         'rain': pred['rain_chance'], 'wind': pred['wind_speed']}
        for h, t, hum in zip(hours, temps, humidities)
    ]
    return jsonify({'forecast': forecast})


@app.route('/api/forecast/5-days')
def get_5day_forecast():
    city      = request.args.get('city', 'Dharan')
    base_row  = resolve_city(city)
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

        X        = pd.DataFrame([[feat_vals[f] for f in FEATURES]], columns=FEATURES)
        X_scaled = scaler.transform(X)

        pred_temp = float(temp_model.predict(X_scaled)[0])
        pred_hum  = float(multi_models['Humidity_2m'].predict(X_scaled)[0])
        pred_max  = float(multi_models['MaxTemp_2m'].predict(X_scaled)[0])
        pred_min  = float(multi_models['MinTemp_2m'].predict(X_scaled)[0])
        pred_wind = float(multi_models['WindSpeed_10m'].predict(X_scaled)[0])
        pred_prec = float(multi_models['Precip'].predict(X_scaled)[0])

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

        forecast.append({
            'day':        date.strftime('%A').upper(),
            'date':       date.strftime('%Y-%m-%d'),
            'max_temp':   round(pred_max, 1),
            'min_temp':   round(pred_min, 1),
            'humidity':   round(max(0, min(100, pred_hum)), 1),
            'rain_chance': rain_chance,
            'condition':  condition,
        })

        # Roll lags forward
        lag_temps  = [prev_temp] + lag_temps[:2]
        lag_precip = [max(0, pred_prec)] + lag_precip[:2]
        prev_temp  = pred_temp

    return jsonify({'forecast': forecast})



@app.route('/api/health')
def health():
    """Simple health/status endpoint for the frontend and deployment checks."""
    cache_age = None
    if _all_predictions_cache['timestamp']:
        cache_age = round(time.time() - _all_predictions_cache['timestamp'], 1)

    return jsonify({
        'status': 'ok',
        'cities_available': int(len(latest_by_city)),
        'models_loaded': True,
        'prediction_cache': {
            'ready': _all_predictions_cache['data'] is not None,
            'age_seconds': cache_age,
            'ttl_seconds': ALL_PREDICTIONS_CACHE_TTL
        }
    })


@app.route('/api/model-performance')
def get_model_performance():
    try:
        metrics = joblib.load(os.path.join(MODEL_DIR, 'model_metadata.pkl'))
        return jsonify(metrics)
    except Exception:
        return jsonify({'Model': 'Random Forest', 'MAE': 1.5, 'RMSE': 2.1, 'R2': 0.85})


@app.route('/api/ai-insight')
def get_ai_insight():
    city = request.args.get('city', 'Dharan')
    row  = resolve_city(city)
    pred = predict_row(row)

    temp       = pred['temperature']
    max_t      = pred['max_temp']
    min_t      = pred['min_temp']
    humidity   = pred['humidity']
    wind       = pred['wind_speed']
    rain_pct   = pred['rain_chance']
    condition  = pred['condition']

    now        = datetime.datetime.now()
    month      = now.month
    hour       = now.hour

    # ── Season context (Nepal seasons)
    if month in [3, 4, 5]:
        season = 'spring'
    elif month in [6, 7, 8, 9]:
        season = 'monsoon'
    elif month in [10, 11]:
        season = 'autumn'
    else:
        season = 'winter'

    # ── Comfort Index (Heat Index approximation)
    comfort_index = temp - 0.55 * (1 - humidity / 100) * (temp - 14.5)

    # ── Build sentences
    sentences = []

    # 1. Opening summary
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
    else:  # Clear
        openers = [
            f"Clear and calm conditions are predicted for {city} today.",
            f"A clear, settled day is expected across {city}.",
            f"The forecast model points to clear conditions and mild temperatures for {city}.",
        ]
    sentences.append(random.choice(openers))

    # 2. Temperature analysis
    temp_range = max_t - min_t
    if temp_range > 12:
        sentences.append(
            f"A notable temperature swing of {temp_range:.1f}°C is forecast — highs of {max_t:.1f}°C"
            f" and lows of {min_t:.1f}°C — so layering clothing is advisable."
        )
    elif temp > 35:
        sentences.append(
            f"Peak temperature is expected to reach {max_t:.1f}°C, indicating intense heat."
            f" Stay hydrated and avoid prolonged sun exposure."
        )
    elif temp > 28:
        sentences.append(
            f"Temperatures will be warm, reaching up to {max_t:.1f}°C with a minimum of {min_t:.1f}°C."
        )
    elif temp < 5:
        sentences.append(
            f"Temperatures will be very cold, dropping to {min_t:.1f}°C, with a high of only {max_t:.1f}°C."
            f" Warm clothing is strongly recommended."
        )
    elif temp < 15:
        sentences.append(
            f"Cool temperatures are expected, ranging from {min_t:.1f}°C to {max_t:.1f}°C — a light jacket will be useful."
        )
    else:
        sentences.append(
            f"Temperatures will hover between {min_t:.1f}°C and {max_t:.1f}°C, offering relatively comfortable conditions."
        )

    # 3. Rain & humidity analysis
    if rain_pct > 70:
        sentences.append(
            f"Precipitation probability is high at {rain_pct}%. Carrying an umbrella is strongly advised."
        )
    elif rain_pct > 40:
        sentences.append(
            f"There is a moderate {rain_pct}% chance of rain — be prepared for possible showers."
        )
    elif rain_pct > 15:
        sentences.append(
            f"Rain probability is relatively low at {rain_pct}%, though isolated showers cannot be ruled out."
        )
    else:
        sentences.append(
            f"Precipitation probability is minimal at just {rain_pct}%. Outdoor activities should be largely unaffected by rain."
        )

    # Humidity comment
    if humidity > 85:
        sentences.append(
            f"Humidity is very high at {humidity:.0f}%, which may make the heat feel more oppressive than the thermometer suggests."
        )
    elif humidity < 30:
        sentences.append(
            f"The air is notably dry at {humidity:.0f}% relative humidity — keeping hydrated will be especially important."
        )

    # 4. Wind analysis
    if wind > 40:
        sentences.append(
            f"Strong winds of {wind:.1f} km/h are forecast; outdoor events or travel may be disrupted."
        )
    elif wind > 20:
        sentences.append(
            f"A moderately brisk wind at {wind:.1f} km/h will add a cooling effect to the day."
        )
    elif wind < 5:
        sentences.append(
            f"Winds will be light and calm at {wind:.1f} km/h, providing still conditions."
        )
    else:
        sentences.append(
            f"Winds will be gentle at around {wind:.1f} km/h — pleasant for outdoor activities."
        )

    # 5. Comfort & seasonal note
    if comfort_index > 35:
        sentences.append(
            f"The apparent temperature ('feels like') is estimated at {comfort_index:.1f}°C — significantly hotter than the actual reading due to humidity."
        )
    elif comfort_index < 0:
        sentences.append(
            f"Wind chill and cold temperatures combine to make conditions feel closer to {comfort_index:.1f}°C. Take appropriate precautions."
        )

    if season == 'monsoon':
        sentences.append(
            "As Nepal is in the heart of the monsoon season, weather can shift rapidly. Monitor forecasts frequently."
        )
    elif season == 'winter':
        sentences.append(
            "Winter conditions are prevailing across Nepal. Mountain regions may face snow and road disruptions."
        )
    elif season == 'spring':
        sentences.append(
            "Spring brings variable weather to Nepal. Expect pleasant days with the occasional afternoon shower."
        )
    elif season == 'autumn':
        sentences.append(
            "Autumn is typically one of Nepal's clearest and most stable seasons — ideal conditions for trekking and outdoor pursuits."
        )

    insight_text = ' '.join(sentences)

    return jsonify({
        'city':    city,
        'insight': insight_text,
        'tags': {
            'season':    season,
            'condition': condition,
            'rain_pct':  rain_pct,
            'temp':      round(temp, 1),
        }
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug, threaded=True)
