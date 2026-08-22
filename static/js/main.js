// MOBILE SIDEBAR 
function toggleSidebar() {
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  const isOpen  = sidebar.classList.contains('open');
  if (isOpen) {
    closeSidebar();
  } else {
    sidebar.classList.add('open');
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden'; // prevent background scroll
  }
}

function closeSidebar() {
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  sidebar.classList.remove('open');
  overlay.classList.remove('open');
  document.body.style.overflow = '';
}

let currentCity = 'Dharan Sub';
let currentTrendData = null;
let chartInstance = null;
let currentTab = 'temp';

//  THEME 
function applyTheme(theme) {
  document.body.classList.toggle('light', theme === 'light');
  localStorage.setItem('wa-theme', theme);
  const toggle = document.getElementById('theme-toggle');
  if (toggle) toggle.checked = (theme === 'light');
  // Update moon/sun icon in topbar
  const themeBtn = document.getElementById('theme-btn');
  if (themeBtn) themeBtn.textContent = theme === 'light' ? '☀️' : '🌙';
  // Re-render chart with correct colors
  if (currentTrendData) renderChart(currentTrendData, currentTab);
}

function toggleTheme() {
  const isLight = document.body.classList.contains('light');
  applyTheme(isLight ? 'dark' : 'light');
}

//  NAVIGATION 
document.addEventListener('DOMContentLoaded', () => {
  // Restore theme
  const savedTheme = localStorage.getItem('wa-theme') || 'dark';
  applyTheme(savedTheme);

  // Nav routing
  const navItems = document.querySelectorAll('.nav-item[data-page]');
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const p = item.dataset.page;
      if (p === 'about')    { openModal('about-modal');    return; }
      if (p === 'settings') { openModal('settings-modal'); return; }
      showPage(p);
    });
  });

  // Theme toggle in topbar
  document.getElementById('theme-btn').addEventListener('click', toggleTheme);

  // Theme toggle in settings modal
  const themeToggle = document.getElementById('theme-toggle');
  if (themeToggle) {
    themeToggle.addEventListener('change', () => {
      applyTheme(themeToggle.checked ? 'light' : 'dark');
    });
  }

  // Chart tab buttons
  document.querySelectorAll('.chart-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.chart-tab').forEach(b => b.classList.remove('active'));
      const metric = btn.dataset.metric;
      document.querySelectorAll(`.chart-tab[data-metric="${metric}"]`).forEach(b => b.classList.add('active'));
      
      currentTab = metric;
      if (currentTrendData) {
        renderChart(currentTrendData, currentTab);
      }
    });
  });

  // Search
  document.getElementById('search-btn').addEventListener('click', doSearch);
  document.getElementById('city-input').addEventListener('keydown', e => {
    if (e.key === 'Enter') doSearch();
  });

  // Default page + initial load
  showPage('dashboard');
  fetchAll('Dharan Sub');
});

function showPage(pageId) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item[data-page]').forEach(n => n.classList.remove('active'));

  const target = document.getElementById('page-' + pageId);
  const nav    = document.querySelector(`.nav-item[data-page="${pageId}"]`);
  if (target) target.classList.add('active');
  if (nav)    nav.classList.add('active');
  
  // Re-render charts to fix Chart.js invisibility issue when container is display:none
  if (currentTrendData && pageId === 'dashboard') {
      setTimeout(() => {
          renderChart(currentTrendData, currentTab);
      }, 50);
  }
}

function doSearch() {
  const city = document.getElementById('city-input').value.trim();
  if (city) { currentCity = city; fetchAll(city); }
}

//  FETCH ALL DATA 
function fetchAll(city) {
  fetchDashboard(city);
  fetchHourly(city);
  fetchTrend(city);
}

//  DASHBOARD 
function fetchDashboard(city) {
  setLoadingHero();
  fetch('/api/dashboard?city=' + encodeURIComponent(city))
    .then(r => r.json())
    .then(data => {
      if (data.error) { showToast('⚠️ ' + data.error, 'error'); return; }
      renderDashboard(data);
    })
    .catch(() => showToast('Connection error', 'error'));
}

function setLoadingHero() {
  setInner('hero-temp', '—°');
  setInner('hero-cond', 'Loading...');
  setInner('hero-city', '—');
}

function renderDashboard(d) {
  setInner('hero-city',     d.city);
  setInner('hero-date',     d.date);
  setInner('hero-temp',     d.temperature + '°');
  setInner('hero-cond',     d.condition);
  setInner('hero-icon',     condIcon(d.condition));
  setInner('m-humidity',    d.humidity + '%');
  setInner('m-wind',        d.wind + ' km/h');
  setInner('m-pressure',    d.pressure + ' hPa');
  setInner('m-precip',      d.rainfall + '%');
  setInner('insight-temp-tag', '🌡️ ' + d.temperature + '°C');
  setInner('insight-rain-tag', '💧 ' + d.rainfall + '% rain');
  setInner('insight-body',  buildInsight(d));
  if (d.model_perf) renderPerf(d.model_perf);
}

//  HOURLY 24-HOUR 
function fetchHourly(city) {
  fetch('/api/hourly?city=' + encodeURIComponent(city))
    .then(r => r.json())
    .then(data => {
      if (data.error) return;
      renderHourly(data);
    });
}

function renderHourly(hours) {
  const makeCards = (containerId) => {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = hours.map(h => `
      <div class="hour-card">
        <div class="hour-time">${h.time}</div>
        <div class="hour-icon">${condIcon(h.rain > 2 ? 'Rainy' : h.rain > 0.5 ? 'Partly Cloudy' : 'Sunny')}</div>
        <div class="hour-temp">${h.temp}°</div>
        <div class="hour-rain">💧 ${h.rain}%</div>
      </div>`).join('');
  };
  makeCards('hourly-cards');
}

// TREND CHART 
function fetchTrend(city) {
  fetch('/api/trend?city=' + encodeURIComponent(city))
    .then(r => r.json())
    .then(data => {
      if (data.error) return;
      currentTrendData = data;
      renderChart(data, currentTab);
    });
}

const CHART_META = {
  temp:     { key: 'temp',     label: 'Temperature (°C)',   color: '#fbbf24', fill: 'rgba(251,191,36,0.10)' },
  humidity: { key: 'humidity', label: 'Humidity (%)',        color: '#38bdf8', fill: 'rgba(56,189,248,0.10)' },
  wind:     { key: 'wind',     label: 'Wind Speed (km/h)',   color: '#a78bfa', fill: 'rgba(167,139,250,0.10)' },
  rain:     { key: 'rain',     label: 'Precipitation (mm)',  color: '#34d399', fill: 'rgba(52,211,153,0.10)' },
};

function buildChartConfig(data, metric) {
  const m = CHART_META[metric] || CHART_META.temp;
  const isLight = document.body.classList.contains('light');
  const gridColor = isLight ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.04)';
  const tickColor = isLight ? '#475569' : '#64748b';

  return {
    type: 'line',
    data: {
      labels: data.labels,
      datasets: [{
        label: m.label,
        data: data[m.key],
        borderColor: m.color,
        backgroundColor: m.fill,
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: m.color,
        pointBorderColor: isLight ? '#ffffff' : '#0f172a',
        pointBorderWidth: 2,
        borderWidth: 2,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: isLight ? '#ffffff' : '#1e293b',
          titleColor: isLight ? '#0f172a' : '#f8fafc',
          bodyColor: isLight ? '#475569' : '#94a3b8',
          borderColor: isLight ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)',
          borderWidth: 1,
          padding: 10,
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: tickColor, maxTicksLimit: 8, font: { size: 11 } }
        },
        y: {
          grid: { color: gridColor },
          ticks: { color: tickColor, font: { size: 11 } }
        }
      }
    }
  };
}

function renderChart(data, metric) {
  const canvas = document.getElementById('trend-chart');
  if (!canvas) return;
  if (chartInstance) { chartInstance.destroy(); chartInstance = null; }
  chartInstance = new Chart(canvas, buildChartConfig(data, metric));
}



//  5 DAY FORECAST 
function render5Day(data) {
  const days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
  const temp = parseFloat(data.temperature || 28);
  const rain = parseFloat(data.rainfall || 0);
  const hum  = parseFloat(data.humidity || 50);
  const cond = data.condition || 'Partly Cloudy';

  const makeGrid = (id) => {
    const el = document.getElementById(id);
    if (!el) return;
    let html = '';
    for (let i = 0; i < 5; i++) {
      const dt  = new Date(); dt.setDate(dt.getDate() + i + 1);
      const day = days[dt.getDay()].toUpperCase();
      const ds  = dt.toISOString().split('T')[0];
      const hi  = (temp + (Math.random() * 2 - 0.5)).toFixed(0);
      const lo  = (temp - 4 - Math.random() * 2).toFixed(0);
      const r   = (rain * (0.8 + Math.random() * 0.4)).toFixed(1);
      const h   = (hum  * (0.9 + Math.random() * 0.2)).toFixed(1);
      const cls = i === 0 ? 'day-card highlight' : 'day-card';
      html += `
        <div class="${cls}">
          <div class="day-name">${day}</div>
          <div class="day-date">${ds}</div>
          <div class="day-icon">${condIcon(cond)}</div>
          <div class="day-cond">${cond}</div>
          <div class="day-temps">${hi}° <span class="day-lo">${lo}°</span></div>
          <div class="day-divider">
            <div class="day-hum">💧 ${h}%</div>
            <div class="day-rain">☂️ ${r}%</div>
          </div>
        </div>`;
    }
    el.innerHTML = html;
  };
  makeGrid('five-day-grid');
}

// Patch fetchDashboard to also render 5 day
const _origFetch = fetchDashboard;
window.fetchDashboard = function(city) {
  setLoadingHero();
  fetch('/api/dashboard?city=' + encodeURIComponent(city))
    .then(r => r.json())
    .then(data => {
      if (data.error) { showToast('⚠️ ' + data.error, 'error'); return; }
      renderDashboard(data);
      render5Day(data);
    })
    .catch(() => showToast('Connection error', 'error'));
};

//  HELPERS 
function condIcon(cond) {
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
}

function buildInsight(d) {
  const hi = (parseFloat(d.temperature) + 3.8).toFixed(1);
  const lo = (parseFloat(d.temperature) - 4.2).toFixed(1);
  const wet = parseFloat(d.rainfall) > 5;
  return `A mix of clouds and breaks of sunshine is forecast for <strong>${d.city}</strong>. 
  Temperatures will be ${d.temperature > 30 ? 'warm' : 'mild'}, reaching up to <strong>${hi}°C</strong> with a minimum of <strong>${lo}°C</strong>. 
  Precipitation probability is at <strong>${d.rainfall}%</strong>. Outdoor activities should be 
  ${wet ? '<strong>impacted — carry an umbrella</strong>' : 'largely <strong>unaffected by rain</strong>'}. 
  The air is at <strong>${d.humidity}%</strong> relative humidity. 
  Winds at <strong>${d.wind} km/h</strong>. 
  As Nepal is in the heart of the monsoon season, weather can shift rapidly. Monitor forecasts frequently.`;
}

function setInner(id, val) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = val;
}

function renderPerf(perf) {
  setInner('perf-model', perf.best_model || 'Best RF (Test)');
  setInner('perf-r2',    perf.r2  || '0.981');
  setInner('perf-rmse',  perf.rmse || '1.10°');
  setInner('perf-mae',   perf.mae  || '0.84°');
}

//  MODALS  
function openModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.add('open');
  // Sync settings toggle with current theme
  if (id === 'settings-modal') {
    const toggle = document.getElementById('theme-toggle');
    if (toggle) toggle.checked = document.body.classList.contains('light');
  }
}

function closeModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.remove('open');
}

document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('open');
  }
});

//  TOAST NOTIFICATIONS 
function showToast(msg, type = 'info') {
  let toast = document.getElementById('wa-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'wa-toast';
    toast.style.cssText = `position:fixed;bottom:24px;right:24px;z-index:9999;padding:12px 20px;border-radius:12px;font-size:0.88rem;font-weight:500;transition:all 0.3s;font-family:Inter,sans-serif;`;
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.style.background = type === 'error' ? '#ef4444' : '#38bdf8';
  toast.style.color = 'white';
  toast.style.opacity = '1';
  setTimeout(() => { toast.style.opacity = '0'; }, 3000);
}
