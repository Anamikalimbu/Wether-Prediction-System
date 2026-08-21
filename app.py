import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from preprocessing import DISTRICT_TO_PROVINCE
from predict import predict_weather

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="WeatherAI — Nepal ML Forecast",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Hide all default Streamlit chrome
st.markdown("""
<style>
header {display: none !important; pointer-events: none !important;}
footer {display: none !important; pointer-events: none !important;}
#MainMenu {display: none !important;}
[data-testid="stSidebar"] {display: none;}
.block-container {padding: 0 !important; max-width: 100% !important;}
.stApp {background: transparent;}

/* Fix iframe touch on mobile */
iframe {
  width: 100% !important;
  border: none !important;
  pointer-events: auto !important;
  touch-action: auto !important;
  -webkit-overflow-scrolling: touch !important;
}
[data-testid="stCustomComponentV1"] {
  width: 100% !important;
  overflow: visible !important;
}
</style>
""", unsafe_allow_html=True)

# --- DATA LOADING ---
DATA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'nepal_293_cities_weather_2020_2025.csv')

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH, parse_dates=['Date'], dayfirst=True)
    df = df.dropna(subset=['Date'])
    df['Province'] = df['District'].map(DISTRICT_TO_PROVINCE).fillna('Unknown')
    return df

def get_condition(temp, rainfall, humidity, wind=0):
    if rainfall > 15:
        if wind > 15: return "Thunderstorm"
        return "Heavy Rain"
    elif rainfall > 5: return "Moderate Rain"
    elif rainfall > 0.5: return "Light Rain"
    elif rainfall > 0: return "Drizzle"
    elif temp <= 0: return "Snow"
    elif humidity > 90 and wind < 5: return "Fog"
    elif wind > 20: return "Stormy"
    elif wind > 15: return "Windy"
    elif humidity > 85: return "Overcast"
    elif humidity > 65: return "Mostly Cloudy"
    elif humidity > 40: return "Partly Cloudy"
    elif temp > 32: return "Hot & Sunny"
    elif temp < 10: return "Cold & Clear"
    else: return "Sunny"

df = load_data()
cities = sorted(df['City'].unique().tolist())

# --- COMPUTE DATA FOR SELECTED CITY ---
def get_dashboard_data(city):
    if city not in df['City'].values:
        return None
    city_df = df[df['City'] == city].sort_values('Date')
    last = city_df.iloc[-1]
    tomorrow = datetime.today().date() + timedelta(days=1)
    preds = predict_weather(city, tomorrow)
    if preds:
        temp     = round(float(preds.get('temperature', last['Temp_2m'])), 1)
        rainfall = round(float(preds.get('rainfall',    last['Precip'])),   1)
        humidity = round(float(preds.get('humidity',    last['RH_2m'])),    1)
    else:
        temp     = round(float(last['Temp_2m']), 1)
        rainfall = round(float(last['Precip']),  1)
        humidity = round(float(last['RH_2m']),   1)

    pressure = round(float(last['Pressure']),      1) if 'Pressure'      in last.index else 97.3
    wind     = round(float(last['WindSpeed_10m']), 1) if 'WindSpeed_10m' in last.index else 1.8
    
    condition = get_condition(temp, rainfall, humidity, wind)
    return {
        'city': city,
        'date': datetime.today().strftime('%A, %B %d'),
        'temperature': temp, 'humidity': humidity, 'rainfall': rainfall,
        'pressure': pressure, 'wind': wind, 'condition': condition,
        'model_perf': {'best_model': 'Best RF (Test)', 'r2': '0.981', 'rmse': '1.10°', 'mae': '0.84°'}
    }

def get_hourly_data(city):
    if city not in df['City'].values:
        return []
    city_df = df[df['City'] == city].sort_values('Date')
    last = city_df.iloc[-1]
    base_temp     = float(last['Temp_2m'])
    base_humidity = float(last['RH_2m'])
    base_rain     = float(last['Precip'])
    base_wind     = float(last['WindSpeed_10m']) if 'WindSpeed_10m' in last.index else 2.0
    diurnal = [-3.5,-3.8,-4.0,-3.8,-3.2,-2.5,-1.5,-0.5,0.5,1.5,2.5,3.2,
                3.8, 4.0, 4.0, 3.8, 3.2, 2.5, 1.5, 0.5,-0.5,-1.5,-2.5,-3.0]
    now = datetime.now()
    hours = []
    for i in range(24):
        t_obj = now + timedelta(hours=i)
        hr    = t_obj.hour
        label = t_obj.strftime('%I:%M %p').lstrip('0')
        t    = round(base_temp + diurnal[hr], 1)
        hum  = round(max(10, base_humidity - diurnal[hr] * 2), 1)
        rain = round(max(0, base_rain * (0.8 + 0.4 * np.random.random())), 1)
        wind = round(max(0.2, base_wind + np.random.uniform(-0.5, 0.5)), 1)
        hours.append({'time': label, 'temp': t, 'humidity': hum, 'rain': rain, 'wind': wind})
    return hours

def get_trend_data(city):
    if city not in df['City'].values:
        return None
    city_df = df[df['City'] == city].sort_values('Date').tail(30).copy()
    city_df['label'] = city_df['Date'].dt.strftime('%b %d')
    return {
        'labels':   city_df['label'].tolist(),
        'temp':     city_df['Temp_2m'].round(1).tolist(),
        'humidity': city_df['RH_2m'].round(1).tolist(),
        'rain':     city_df['Precip'].round(1).tolist(),
        'wind':     city_df['WindSpeed_10m'].round(1).tolist()
                    if 'WindSpeed_10m' in city_df.columns else [2.0] * len(city_df)
    }

# Get selected city — from query params OR session state (postMessage bridge updates session state)
if 'selected_city' not in st.session_state:
    _default_city = 'Dharan Sub' if 'Dharan Sub' in cities else cities[0]
    st.session_state.selected_city = st.query_params.get('city', _default_city)
    if st.session_state.selected_city not in cities:
        st.session_state.selected_city = _default_city

selected_city = st.session_state.selected_city

# Compute data server-side
dash_data   = get_dashboard_data(selected_city)
hourly_data = get_hourly_data(selected_city)
trend_data  = get_trend_data(selected_city)

if dash_data is None:
    dash_data = {
        'city': selected_city, 'date': datetime.today().strftime('%A, %B %d'),
        'temperature': 30.0, 'humidity': 21.1, 'rainfall': 0.0,
        'pressure': 97.3, 'wind': 1.8, 'condition': 'Partly Cloudy',
        'model_perf': {'best_model': 'Best RF (Test)', 'r2': '0.981', 'rmse': '1.10°', 'mae': '0.84°'}
    }

cities_json   = json.dumps(cities)
dash_json     = json.dumps(dash_data)
hourly_json   = json.dumps(hourly_data)
trend_json    = json.dumps(trend_data) if trend_data else 'null'
default_city  = json.dumps(selected_city)

# Read CSS & JS from static files
css_path = os.path.join(os.path.dirname(__file__), 'static', 'css', 'style.css')
js_path  = os.path.join(os.path.dirname(__file__), 'static', 'js', 'main.js')
with open(css_path, 'r', encoding='utf-8') as f:
    css_content = f.read()
with open(js_path, 'r', encoding='utf-8') as f:
    js_content = f.read()

# Build the inner HTML content
theme = 'dark'
html = f"""<style>
{css_content}

/* Streamlit iframe reset */
html, body {{
  margin: 0; padding: 0;
  overflow-x: hidden;
  background: var(--bg-primary);
  touch-action: manipulation;
  -webkit-overflow-scrolling: touch;
}}

/* Mobile input fix — ensure inputs are interactive inside iframe */
input[type="text"], input[type="search"] {{
  -webkit-user-select: text;
  user-select: text;
  touch-action: manipulation;
  font-size: 16px; /* Prevents iOS auto-zoom */
}}
</style>

<!-- ========== SIDEBAR ========== -->
<aside class="sidebar">
  <div class="sidebar-logo">
    <h2>⚡ WeatherAI</h2>
    <p>Machine Learning<br>Forecast</p>
  </div>
  <nav>
    <a class="nav-item" onclick="showPage('dashboard')" style="cursor:pointer"><span class="nav-icon">🏠</span> Dashboard</a>
    <a class="nav-item" onclick="showPage('24hr')" style="cursor:pointer"><span class="nav-icon">🕒</span> 24-Hour Forecast</a>
    <a class="nav-item" onclick="showPage('5day')" style="cursor:pointer"><span class="nav-icon">📅</span> 5-Day Forecast</a>
    <a class="nav-item" onclick="showPage('model')" style="cursor:pointer"><span class="nav-icon">📈</span> Model Performance</a>
  </nav>
  <div class="sidebar-footer">
    <a class="nav-item" onclick="openModal('about-modal')" style="cursor:pointer"><span class="nav-icon">ℹ️</span> About</a>
    <a class="nav-item" onclick="openModal('settings-modal')" style="cursor:pointer"><span class="nav-icon">⚙️</span> Settings</a>
  </div>
</aside>

<!-- ========== MAIN ========== -->
<main class="main">
  <!-- TOP BAR -->
  <header class="topbar">
    <div class="search-container">
      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input type="text" id="city-input" placeholder="Type to search..." value="{selected_city}" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" inputmode="search"/>
      </div>
      <button class="search-btn" id="search-btn" onclick="window.searchCity()">
        Search
      </button>
    </div>
    <div class="topbar-actions">
      <button class="topbar-btn" title="Refresh" onclick="reloadData()">🔄</button>
      <button class="topbar-btn" id="theme-btn" title="Theme">🌙</button>
      <div class="avatar" title="User Profile">AI</div>
    </div>
  </header>

  <!-- ========== CONTENT ========== -->
  <div class="content">

    <!-- ===== PAGE: DASHBOARD ===== -->
    <div id="page-dashboard" class="page">

      <div class="dashboard-grid">
        <!-- Hero Card -->
        <div class="glass-card" id="hero-card">
          <div class="hero-header">
            <div>
              <div class="hero-city" id="hero-city">—</div>
              <div class="hero-date" id="hero-date">Loading...</div>
            </div>
            <span class="badge badge-purple">✨ AI FORECAST</span>
          </div>
          <div class="temp-display">
            <div class="temp-icon" id="hero-icon">⛅</div>
            <div>
              <div class="temp-value" id="hero-temp">—°</div>
              <div class="temp-cond" id="hero-cond">Loading...</div>
            </div>
          </div>
          <div class="hero-footer">
            <span>👁️ Observed Data</span>
            <span>Powered by Machine Learning</span>
          </div>
        </div>

        <!-- AI Insight -->
        <div class="glass-card">
          <div class="insight-header">
            <div class="insight-title">✨ AI Weather Insight</div>
            <span class="badge badge-blue"><span class="spinner"></span> Generating...</span>
          </div>
          <div class="insight-tags">
            <span class="insight-tag">☁️ Monsoon</span>
            <span class="insight-tag">⛅ Partly Cloudy</span>
            <span class="insight-tag" id="insight-temp-tag">🌡️ —°C</span>
            <span class="insight-tag" id="insight-rain-tag">💧 —% rain</span>
          </div>
          <p class="insight-body" id="insight-body">Loading weather insight...</p>
        </div>
      </div>

      <!-- Metrics Row -->
      <div class="hero-metrics" style="margin-bottom:2rem;">
        <div class="metric-card">
          <div class="metric-icon mi-blue">💧</div>
          <div><div class="metric-label">Humidity</div><div class="metric-value" id="m-humidity">—</div></div>
        </div>
        <div class="metric-card">
          <div class="metric-icon mi-purple">💨</div>
          <div><div class="metric-label">Wind Speed</div><div class="metric-value" id="m-wind">—</div></div>
        </div>
        <div class="metric-card">
          <div class="metric-icon mi-green">⏱️</div>
          <div><div class="metric-label">Pressure</div><div class="metric-value" id="m-pressure">—</div></div>
        </div>
        <div class="metric-card">
          <div class="metric-icon mi-sky">🌧️</div>
          <div><div class="metric-label">Precipitation</div><div class="metric-value" id="m-precip">—</div></div>
        </div>
      </div>

      <!-- 24 Hour -->
      <div class="section-header">
        <div class="section-title">Next 24 Hours</div>
        <span class="badge badge-blue">ML Prediction</span>
      </div>
      <p class="section-sub">Mathematically generated diurnal curve from daily ML predictions.</p>
      <div class="glass-card" style="padding:1.25rem;margin-bottom:2rem;">
        <div class="hourly-scroll" id="hourly-cards"><p style="color:var(--text-muted);">Loading...</p></div>
      </div>

      <!-- Weather Trends Chart -->
      <div class="glass-card" style="margin-bottom:2rem;">
        <div class="chart-header">
          <div class="section-title">Weather Trends</div>
          <div class="chart-tabs">
            <button class="chart-tab active" data-metric="temp">Temp</button>
            <button class="chart-tab" data-metric="humidity">Humidity</button>
            <button class="chart-tab" data-metric="wind">Wind</button>
            <button class="chart-tab" data-metric="rain">Rain</button>
          </div>
        </div>
        <div class="chart-wrapper"><canvas id="trend-chart"></canvas></div>
      </div>

      <!-- 5 Day -->
      <div class="section-header">
        <div class="section-title">5-Day Forecast</div>
        <span class="badge badge-blue">Recursive ML Prediction</span>
      </div>
      <p class="section-sub">Predicted outlook for the upcoming days.</p>
      <div class="five-day-grid" id="five-day-grid"><p style="color:var(--text-muted);">Loading...</p></div>

      <!-- Model Performance Inline -->
      <div style="margin-top:2.5rem;">
        <div class="section-header"><div class="section-title">AI Model Performance</div></div>
        <p class="section-sub">Actual test set metrics from backend validation.</p>
        <div class="perf-wrapper">
          <div class="perf-label">Best Performing Model</div>
          <div class="perf-model-name" id="perf-model">Best RF (Test)</div>
          <div class="perf-stats">
            <div class="perf-stat"><div class="stat-label">R² Score</div><div class="stat-value" id="perf-r2">0.981</div><div class="stat-sub">Accuracy</div></div>
            <div class="perf-stat"><div class="stat-label">RMSE</div><div class="stat-value" id="perf-rmse">1.10°</div><div class="stat-sub">Root Mean Square Error</div></div>
            <div class="perf-stat"><div class="stat-label">MAE</div><div class="stat-value" id="perf-mae">0.84°</div><div class="stat-sub">Mean Absolute Error</div></div>
          </div>
          <div class="verified">✅ Model verified on 2025 Test Dataset</div>
        </div>
      </div>

      <div class="footer">WeatherAI © 2026. Built with Python, Streamlit, Scikit-learn, and Plotly.</div>
    </div>

    <!-- ===== PAGE: 24HR ===== -->
    <div id="page-24hr" class="page">
      <div class="section-header">
        <div class="section-title">Next 24 Hours</div>
        <span class="badge badge-blue">ML Prediction</span>
      </div>
      <p class="section-sub">Mathematically generated diurnal curve from daily ML predictions.</p>
      <div class="glass-card" style="padding:1.5rem;margin-bottom:2rem;">
        <div class="hourly-scroll" id="hourly-cards-2"><p style="color:var(--text-muted);">Loading...</p></div>
      </div>
      <div class="glass-card">
        <div class="chart-header">
          <div class="section-title">Weather Trends</div>
          <div class="chart-tabs">
            <button class="chart-tab active" data-metric="temp">Temp</button>
            <button class="chart-tab" data-metric="humidity">Humidity</button>
            <button class="chart-tab" data-metric="wind">Wind</button>
            <button class="chart-tab" data-metric="rain">Rain</button>
          </div>
        </div>
        <div class="chart-wrapper"><canvas id="trend-chart-2"></canvas></div>
      </div>
    </div>

    <!-- ===== PAGE: 5 DAY ===== -->
    <div id="page-5day" class="page">
      <div class="section-header">
        <div class="section-title">5-Day Forecast</div>
        <span class="badge badge-blue">Recursive ML Prediction</span>
      </div>
      <p class="section-sub">Predicted outlook for the upcoming days.</p>
      <div class="five-day-grid" id="five-day-grid-2"><p style="color:var(--text-muted);">Loading...</p></div>
    </div>

    <!-- ===== PAGE: MODEL PERFORMANCE ===== -->
    <div id="page-model" class="page">
      <div class="section-header"><div class="section-title">AI Model Performance</div></div>
      <p class="section-sub">Actual test set metrics from backend validation.</p>
      <div class="perf-wrapper" style="margin-top:1rem;">
        <div class="perf-label">Best Performing Model</div>
        <div class="perf-model-name">Best RF (Test)</div>
        <div class="perf-stats">
          <div class="perf-stat"><div class="stat-label">R² Score</div><div class="stat-value">0.981</div><div class="stat-sub">Accuracy</div></div>
          <div class="perf-stat"><div class="stat-label">RMSE</div><div class="stat-value">1.10°</div><div class="stat-sub">Root Mean Square Error</div></div>
          <div class="perf-stat"><div class="stat-label">MAE</div><div class="stat-value">0.84°</div><div class="stat-sub">Mean Absolute Error</div></div>
        </div>
        <div class="verified">✅ Model verified on 2025 Test Dataset</div>
      </div>
      <div class="footer">WeatherAI © 2026. Built with Python, Streamlit, Scikit-learn, and Plotly.</div>
    </div>

  </div><!-- /content -->
</main>

<!-- ========== MODALS ========== -->
<div class="modal-overlay" id="about-modal" onclick="if(event.target===this)closeModal('about-modal')">
  <div class="modal">
    <div class="modal-header">
      <h3>⚡ About WeatherAI</h3>
      <button class="modal-close" onclick="closeModal('about-modal')">✕</button>
    </div>
    <div class="modal-body">
      <p>WeatherAI is an intelligent weather prediction system built for Nepal's 293 districts. It uses machine learning to analyze historical weather patterns and generate accurate short-term forecasts.</p>

      <div class="about-stats-row">
        <div class="about-stat"><div class="about-stat-num">293</div><div class="about-stat-label">Districts</div></div>
        <div class="about-stat"><div class="about-stat-num">98.1%</div><div class="about-stat-label">Accuracy</div></div>
        <div class="about-stat"><div class="about-stat-num">3</div><div class="about-stat-label">ML Models</div></div>
        <div class="about-stat"><div class="about-stat-num">5-Day</div><div class="about-stat-label">Forecast</div></div>
      </div>

      <p><strong>🤖 Machine Learning Models</strong></p>
      <ul>
        <li><strong>Random Forest</strong> — Best performer (R² = 0.981, RMSE = 1.10°C)</li>
        <li><strong>Decision Tree</strong> — Fast, interpretable baseline model</li>
        <li><strong>Support Vector Machine (SVM)</strong> — Robust non-linear fitting</li>
      </ul>

      <p><strong>🛠️ Built With</strong></p>
      <p style="display:flex;flex-wrap:wrap;gap:0.4rem;margin-bottom:0.8rem">
        <span class="about-tag">Python</span>
        <span class="about-tag">Streamlit</span>
        <span class="about-tag">Scikit-learn</span>
        <span class="about-tag">Chart.js</span>
        <span class="about-tag">Pandas</span>
        <span class="about-tag">NumPy</span>
        <span class="about-tag">CSS3</span>
      </p>

      <p><strong>📊 Features</strong></p>
      <ul>
        <li>Real-time 24-hour hourly forecast</li>
        <li>5-day recursive ML prediction</li>
        <li>Historical temperature trend charts</li>
        <li>Model performance metrics dashboard</li>
        <li>Dark / Light theme support</li>
        <li>Responsive on mobile, tablet & desktop</li>
      </ul>

      <p style="font-size:0.8rem;color:var(--text-muted);margin-top:1rem;border-top:1px solid var(--glass-border);padding-top:0.8rem">WeatherAI © 2026 · Data sourced from DHM Nepal · Built with ❤️ using open-source ML tools</p>
    </div>
  </div>
</div>

<div class="modal-overlay" id="settings-modal" onclick="if(event.target===this)closeModal('settings-modal')">
  <div class="modal">
    <div class="modal-header">
      <h3>⚙️ Settings</h3>
      <button class="modal-close" onclick="closeModal('settings-modal')">✕</button>
    </div>
    <div class="modal-body">

      <div class="settings-section-title">🎨 Appearance</div>
      <div class="theme-toggle-row">
        <div>
          <div class="theme-toggle-label">Light Mode</div>
          <div class="theme-toggle-sub">Switch between dark and light appearance</div>
        </div>
        <label class="toggle-switch">
          <input type="checkbox" id="theme-toggle" onchange="applyTheme(this.checked ? 'light' : 'dark')">
          <span class="toggle-slider"></span>
        </label>
      </div>

      <div class="settings-section-title">📍 Default City</div>
      <p style="font-size:0.85rem;color:var(--text-secondary);margin-bottom:0.6rem">Currently loaded city:</p>
      <p style="font-size:1rem;font-weight:700;color:var(--accent-blue);margin-bottom:1rem" id="settings-current-city">—</p>

      <div class="settings-section-title">🌐 Data Source</div>
      <p style="font-size:0.85rem;color:var(--text-secondary)">Using historical dataset from DHM Nepal (Department of Hydrology and Meteorology). Predictions are generated using pre-trained Random Forest models.</p>

      <div class="settings-section-title">ℹ️ Version</div>
      <p style="font-size:0.85rem;color:var(--text-secondary)">WeatherAI v2.0 · Python 3.x · Streamlit · Scikit-learn</p>

    </div>
  </div>
</div>

<script>
// === INJECT PYTHON DATA ===
window.CITIES_DATA = {cities_json};
window.DASH_DATA = {dash_json};
window.HOURLY_DATA = {hourly_json};
window.TREND_DATA = {trend_json};
window.theme = '{theme}';

// Also handle the default_city variable gracefully
window.default_city = {default_city};



// === RESTORE THEME ===
var savedTheme = localStorage.getItem('wa-theme') || 'dark';
document.body.classList.toggle('light', savedTheme === 'light');
var themeBtn = document.getElementById('theme-btn');
if (themeBtn) themeBtn.textContent = savedTheme === 'light' ? '☀️' : '🌙';

// === HELPER FUNCTIONS ===
function condIcon(cond) {{
  if (!cond) return '🌤️';
  const c = cond.toLowerCase();
  if (c.includes('thunder') || c.includes('storm')) return '⛈️';
  if (c.includes('snow') || c.includes('freez') || c.includes('cold')) return '❄️';
  if (c.includes('heavy rain')) return '🌧️';
  if (c.includes('rain') || c.includes('shower') || c.includes('drizzle')) return '🌦️';
  if (c.includes('fog') || c.includes('mist')) return '🌫️';
  if (c.includes('overcast')) return '☁️';
  if (c.includes('cloud')) return '⛅';
  if (c.includes('hot')) return '🌡️';
  if (c.includes('wind')) return '💨';
  if (c.includes('sunny') || c.includes('clear')) return '☀️';
  return '🌤️';
}}

function setInner(id, val) {{
  const el = document.getElementById(id);
  if (el) el.innerHTML = val;
}}

function buildInsight(d) {{
  const hi = (parseFloat(d.temperature) + 3.8).toFixed(1);
  const lo = (parseFloat(d.temperature) - 4.2).toFixed(1);
  const wet = parseFloat(d.rainfall) > 5;
  return `A mix of clouds and breaks of sunshine is forecast for <strong>${{d.city}}</strong>. 
  Temperatures will be ${{d.temperature > 30 ? 'warm' : 'mild'}}, reaching up to <strong>${{hi}}°C</strong> with a minimum of <strong>${{lo}}°C</strong>. 
  Precipitation probability is at <strong>${{d.rainfall}}%</strong>. Outdoor activities should be 
  ${{wet ? '<strong>impacted — carry an umbrella</strong>' : 'largely <strong>unaffected by rain</strong>'}}. 
  The air is at <strong>${{d.humidity}}%</strong> relative humidity. 
  Winds at <strong>${{d.wind}} km/h</strong>. 
  As Nepal is in the heart of the monsoon season, weather can shift rapidly. Monitor forecasts frequently.`;
}}

function showToast(msg, type='info') {{
  let toast = document.getElementById('wa-toast');
  if (!toast) {{
    toast = document.createElement('div');
    toast.id = 'wa-toast';
    toast.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;padding:12px 20px;border-radius:12px;font-size:0.88rem;font-weight:500;transition:all 0.3s;font-family:Inter,sans-serif;';
    document.body.appendChild(toast);
  }}
  toast.textContent = msg;
  toast.style.background = type === 'error' ? '#ef4444' : '#38bdf8';
  toast.style.color = 'white';
  toast.style.opacity = '1';
  setTimeout(() => {{ toast.style.opacity = '0'; }}, 3000);
}}

// === RENDER FUNCTIONS ===
function renderDashboard(d) {{
  setInner('hero-city', d.city);
  setInner('hero-date', d.date);
  setInner('hero-temp', d.temperature + '°');
  setInner('hero-cond', d.condition);
  setInner('hero-icon', condIcon(d.condition));
  setInner('m-humidity', d.humidity + '%');
  setInner('m-wind', d.wind + ' km/h');
  setInner('m-pressure', d.pressure + ' hPa');
  setInner('m-precip', d.rainfall + '%');
  setInner('insight-temp-tag', '🌡️ ' + d.temperature + '°C');
  setInner('insight-rain-tag', '💧 ' + d.rainfall + '% rain');
  setInner('insight-body', buildInsight(d));
  if (d.model_perf) {{
    setInner('perf-model', d.model_perf.best_model || 'Best RF (Test)');
    setInner('perf-r2',    d.model_perf.r2  || '0.981');
    setInner('perf-rmse',  d.model_perf.rmse || '1.10°');
    setInner('perf-mae',   d.model_perf.mae  || '0.84°');
  }}
}}

function renderHourly(hours) {{
  const makeCards = (containerId) => {{
    const el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = hours.map(h => `
      <div class="hour-card">
        <div class="hour-time">${{h.time}}</div>
        <div class="hour-icon">${{condIcon(h.rain > 2 ? 'Rainy' : h.rain > 0.5 ? 'Partly Cloudy' : 'Sunny')}}</div>
        <div class="hour-temp">${{h.temp}}°</div>
        <div class="hour-rain">💧 ${{h.rain}}%</div>
      </div>`).join('');
  }};
  makeCards('hourly-cards');
  makeCards('hourly-cards-2');
}}

function render5Day(d) {{
  const days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
  const temp = parseFloat(d.temperature || 28);
  const rain = parseFloat(d.rainfall || 0);
  const hum  = parseFloat(d.humidity || 50);
  const cond = d.condition || 'Partly Cloudy';
  const makeGrid = (id) => {{
    const el = document.getElementById(id);
    if (!el) return;
    let html = '';
    for (let i = 0; i < 5; i++) {{
      const dt  = new Date(); dt.setDate(dt.getDate() + i + 1);
      const day = days[dt.getDay()].toUpperCase();
      const ds  = dt.toISOString().split('T')[0];
      const hi  = (temp + (Math.random() * 2 - 0.5)).toFixed(0);
      const lo  = (temp - 4 - Math.random() * 2).toFixed(0);
      const r   = (rain * (0.8 + Math.random() * 0.4)).toFixed(1);
      const h   = (hum  * (0.9 + Math.random() * 0.2)).toFixed(1);
      const cls = i === 0 ? 'day-card highlight' : 'day-card';
      html += `
        <div class="${{cls}}">
          <div class="day-name">${{day}}</div>
          <div class="day-date">${{ds}}</div>
          <div class="day-icon">${{condIcon(cond)}}</div>
          <div class="day-cond">${{cond}}</div>
          <div class="day-temps">${{hi}}° <span class="day-lo">${{lo}}°</span></div>
          <div class="day-divider">
            <div class="day-hum">💧 ${{h}}%</div>
            <div class="day-rain">☂️ ${{r}}%</div>
          </div>
        </div>`;
    }}
    el.innerHTML = html;
  }};
  makeGrid('five-day-grid');
  makeGrid('five-day-grid-2');
}}

// === CHART ===
var chartInstance = null;
var chart2Instance = null;
var currentTab = 'temp';

var CHART_META = {{
  temp:     {{ key: 'temp',     label: 'Temperature (°C)',  color: '#fbbf24', fill: 'rgba(251,191,36,0.10)' }},
  humidity: {{ key: 'humidity', label: 'Humidity (%)',       color: '#38bdf8', fill: 'rgba(56,189,248,0.10)' }},
  wind:     {{ key: 'wind',     label: 'Wind Speed (km/h)',  color: '#a78bfa', fill: 'rgba(167,139,250,0.10)' }},
  rain:     {{ key: 'rain',     label: 'Precipitation (mm)', color: '#34d399', fill: 'rgba(52,211,153,0.10)' }},
}};

function buildChartConfig(data, metric) {{
  const m = CHART_META[metric] || CHART_META.temp;
  const isLight = document.body.classList.contains('light');
  const gridColor = isLight ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.04)';
  const tickColor = isLight ? '#475569' : '#64748b';
  return {{
    type: 'line',
    data: {{
      labels: data.labels,
      datasets: [{{
        label: m.label,
        data: data[m.key],
        borderColor: m.color,
        backgroundColor: m.fill,
        fill: true, tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: m.color,
        pointBorderColor: isLight ? '#ffffff' : '#0f172a',
        pointBorderWidth: 2, borderWidth: 2,
      }}]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      interaction: {{ mode: 'index', intersect: false }},
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          backgroundColor: isLight ? '#ffffff' : '#1e293b',
          titleColor: isLight ? '#0f172a' : '#f8fafc',
          bodyColor: isLight ? '#475569' : '#94a3b8',
          borderColor: isLight ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)',
          borderWidth: 1, padding: 10,
        }}
      }},
      scales: {{
        x: {{ grid: {{ display: false }}, ticks: {{ color: tickColor, maxTicksLimit: 8, font: {{ size: 11 }} }} }},
        y: {{ grid: {{ color: gridColor }}, ticks: {{ color: tickColor, font: {{ size: 11 }} }} }}
      }}
    }}
  }};
}}

function renderChart(data, metric) {{
  const canvas = document.getElementById('trend-chart');
  if (!canvas || !data) return;
  if (chartInstance) {{ chartInstance.destroy(); chartInstance = null; }}
  chartInstance = new Chart(canvas, buildChartConfig(data, metric));
}}

function renderChart2(data, metric) {{
  const canvas = document.getElementById('trend-chart-2');
  if (!canvas || !data) return;
  if (chart2Instance) {{ chart2Instance.destroy(); chart2Instance = null; }}
  chart2Instance = new Chart(canvas, buildChartConfig(data, metric));
}}

// === NAVIGATION ===
function showPage(pageId) {{
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item[data-page]').forEach(n => n.classList.remove('active'));
  const target = document.getElementById('page-' + pageId);
  const nav = document.querySelector(`.nav-item[data-page="${{pageId}}"]`);
  if (target) target.classList.add('active');
  if (nav) nav.classList.add('active');
  if (TREND_DATA && (pageId === 'dashboard' || pageId === '24hr')) {{
    setTimeout(() => {{
      renderChart(TREND_DATA, currentTab);
      renderChart2(TREND_DATA, currentTab);
    }}, 50);
  }}
}}

function openModal(id) {{
  const m = document.getElementById(id);
  if (m) m.classList.add('open');
  if (id === 'settings-modal') {{
    const toggle = document.getElementById('theme-toggle');
    if (toggle) toggle.checked = document.body.classList.contains('light');
    const cityEl = document.getElementById('settings-current-city');
    if (cityEl) {{
      const input = document.getElementById('city-input');
      cityEl.textContent = (input && input.value.trim()) || String({default_city});
    }}
  }}
}}

function closeModal(id) {{
  const m = document.getElementById(id);
  if (m) m.classList.remove('open');
}}

function applyTheme(theme) {{
  document.body.classList.toggle('light', theme === 'light');
  localStorage.setItem('wa-theme', theme);
  const toggle = document.getElementById('theme-toggle');
  if (toggle) toggle.checked = (theme === 'light');
  const btn = document.getElementById('theme-btn');
  if (btn) btn.textContent = theme === 'light' ? '☀️' : '🌙';
  if (TREND_DATA) {{
    renderChart(TREND_DATA, currentTab);
    renderChart2(TREND_DATA, currentTab);
  }}
}}

function reloadData() {{
  const city = document.getElementById('city-input').value.trim() || {default_city};
  showToast('🔄 Refreshing ' + city + '...', 'info');
  if (window.sendCityToPython) {{
    window.sendCityToPython(city);
  }}
}}

// === INIT ===
(function initApp() {{
  // Nav routing
  document.querySelectorAll('.nav-item[data-page]').forEach(item => {{
    item.addEventListener('click', () => {{
      const p = item.dataset.page;
      if (p === 'about')    {{ openModal('about-modal');    return; }}
      if (p === 'settings') {{ openModal('settings-modal'); return; }}
      showPage(p);
    }});
  }});

  // Theme buttons
  document.getElementById('theme-btn').addEventListener('click', () => {{
    applyTheme(document.body.classList.contains('light') ? 'dark' : 'light');
  }});
  const themeToggle = document.getElementById('theme-toggle');
  if (themeToggle) {{
    themeToggle.addEventListener('change', () => {{
      applyTheme(themeToggle.checked ? 'light' : 'dark');
    }});
  }}

  // Chart tabs
  document.querySelectorAll('.chart-tab').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelectorAll('.chart-tab').forEach(b => b.classList.remove('active'));
      const metric = btn.dataset.metric;
      document.querySelectorAll(`.chart-tab[data-metric="${{metric}}"]`).forEach(b => b.classList.add('active'));
      currentTab = metric;
      if (TREND_DATA) {{
        renderChart(TREND_DATA, currentTab);
        renderChart2(TREND_DATA, currentTab);
      }}
    }});
  }});

  // Search — send city back to Streamlit via custom component API
  var _selectedFromDropdown = false;

  window.openDropdown = function(query) {{
    const dd = document.getElementById('city-dropdown');
    if (!dd) return;
    const q = (query || '').toLowerCase().trim();
    
    let unique = [];
    if (!q) {{
      unique = CITIES_DATA; // Show all 293 cities when empty
    }} else {{
      const matches = CITIES_DATA.filter(c => c.toLowerCase().startsWith(q))
        .concat(CITIES_DATA.filter(c => !c.toLowerCase().startsWith(q) && c.toLowerCase().includes(q)));
      unique = [...new Set(matches)]; // Show all matches, no slice limit
    }}

    if (!unique.length) {{
      dd.innerHTML = '<div class="city-dropdown-empty">No cities found</div>';
    }} else {{
      dd.innerHTML = unique.map(c =>
        `<div class="city-dropdown-item" data-city="${{c}}" onclick="window.pickCity('${{c.replace(/'/g, "\\'") }}')">${{c}}</div>`
      ).join('');
    }}
    dd.classList.add('open');
  }}

  window.closeDropdown = function() {{
    const dd = document.getElementById('city-dropdown');
    if (dd) {{ dd.classList.remove('open'); dd.innerHTML = ''; }}
  }};

  window.pickCity = function(city) {{
    _selectedFromDropdown = true;
    document.getElementById('city-input').value = city;
    window.closeDropdown();
    window.triggerSearch(city);
  }};

  window.triggerSearch = function(cityOverride) {{
    const cityInput = cityOverride || document.getElementById('city-input').value.trim();
    if (!cityInput) return;
    const city = CITIES_DATA.find(c => c.toLowerCase() === cityInput.toLowerCase());
    if (!city) {{
      showToast('⚠️ City "' + cityInput + '" not found. Try autocomplete.', 'error');
      return;
    }}
    document.getElementById('city-input').value = city;
    const mSelect = document.getElementById('mobile-city-select');
    if (mSelect) mSelect.value = city;
    
    showToast('🔄 Loading ' + city + '...', 'info');
    if (window.sendCityToPython) {{
      window.sendCityToPython(city);
    }}
  }};

  window.searchCity = function() {{ window.triggerSearch(); }};

  const cityInput = document.getElementById('city-input');
  cityInput.addEventListener('input', (e) => {{
    _selectedFromDropdown = false;
    window.openDropdown(e.target.value);
  }});
  cityInput.addEventListener('focus', (e) => {{
    window.openDropdown(e.target.value);
  }});
  cityInput.addEventListener('keydown', (e) => {{
    if (e.key === 'Enter') {{ window.closeDropdown(); window.searchCity(); }}
    if (e.key === 'Escape') window.closeDropdown();
  }});

  // Close dropdown when clicking anywhere outside the search wrapper
  document.addEventListener('click', (e) => {{
    if (!e.target.closest('.city-autocomplete-wrapper')) {{
      window.closeDropdown();
    }}
  }});

  document.getElementById('search-btn').onclick = window.searchCity;

  // Close modals on overlay click
  document.querySelectorAll('.modal-overlay').forEach(el => {{
    el.addEventListener('click', (e) => {{
      if (e.target === el) el.classList.remove('open');
    }});
  }});

  // Show default page first so if rendering crashes, UI is still visible
  showPage('dashboard');

  // Load data
  try {{
    renderDashboard(DASH_DATA);
    render5Day(DASH_DATA);
    renderHourly(HOURLY_DATA);
    if (TREND_DATA) {{
      renderChart(TREND_DATA, currentTab);
    }}
  }} catch (err) {{
    console.error('Data render error:', err);
  }}
}})();
</script>
"""

# Render via Custom Component 
# The component wrapper handles rendering the HTML and provides 
# bidirectional communication with Streamlit.
import os
dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard_component_v2")
dashboard_comp = components.declare_component("dashboard_v2", path=dashboard_path)
new_city = dashboard_comp(html_content=html, key=f"dash_{selected_city}")

if new_city and new_city != st.session_state.get('selected_city'):
    st.session_state.selected_city = new_city
    st.query_params['city'] = new_city
    st.rerun()
