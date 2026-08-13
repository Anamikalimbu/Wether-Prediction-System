// DOM Elements & State
const state = {
    currentCity: 'Dharan', // default city
    cities: [],
    theme: localStorage.getItem('theme') || 'dark',
    unit: localStorage.getItem('unit') || 'C',
    animations: localStorage.getItem('animations') !== 'false',
    forecast24: [] // cache for chart swapping
};

// Elements
const citySelector = document.getElementById('city-selector');
const cityList = document.getElementById('city-list');
const themeToggle = document.getElementById('theme-toggle');
let trendChartInstance = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    applyTheme(state.theme);
    applyUnit(state.unit);
    applyAnimations(state.animations);
    
    // Setup Sidebar Nav
    document.querySelectorAll('.menu-item[data-target]').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            switchPage(e.currentTarget.dataset.target);
            // close mobile sidebar if open
            const sidebar = document.querySelector('.sidebar');
            if(sidebar.classList.contains('open')) {
                sidebar.classList.remove('open');
            }
        });
    });

    // Theme Toggle Header Button
    themeToggle.addEventListener('click', () => {
        setTheme(state.theme === 'dark' ? 'light' : 'dark');
    });

    // Search Box Listener
    citySelector.addEventListener('change', (e) => {
        const val = e.target.value;
        if (state.cities.includes(val)) {
            state.currentCity = val;
            fetchDataForCurrentCity();
            e.target.blur();
        }
    });

    // Allow pressing Enter in the search box to trigger search
    citySelector.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            searchCity();
            e.target.blur();
        }
    });
    
    citySelector.addEventListener('focus', (e) => {
        e.target.select();
    });

    initApp();
});

// Sidebar & Modals
function switchPage(targetId) {
    document.querySelectorAll('.menu-item[data-target]').forEach(el => el.classList.remove('active'));
    document.querySelector(`.menu-item[data-target="${targetId}"]`).classList.add('active');
    
    document.querySelectorAll('.page-section').forEach(el => el.classList.remove('active', 'hidden'));
    document.querySelectorAll('.page-section').forEach(el => {
        if(el.id !== targetId) el.classList.add('hidden');
    });
}

function toggleSidebar() {
    document.querySelector('.sidebar').classList.toggle('open');
}

function toggleModal(modalId) {
    const modal = document.getElementById(modalId);
    if(modal.classList.contains('hidden')) {
        modal.classList.remove('hidden');
    } else {
        modal.classList.add('hidden');
    }
}

// Settings
function setTheme(theme) {
    state.theme = theme;
    localStorage.setItem('theme', theme);
    applyTheme(theme);
}
function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    document.querySelectorAll('.setting-group .btn-toggle').forEach(btn => {
        if (btn.textContent.toLowerCase() === theme) btn.classList.add('active');
        else if (btn.textContent.toLowerCase() === (theme === 'dark' ? 'light' : 'dark')) btn.classList.remove('active');
    });
    // redraw chart for colors
    if(trendChartInstance) {
        trendChartInstance.update();
    }
}

function setUnit(unit) {
    state.unit = unit;
    localStorage.setItem('unit', unit);
    applyUnit(unit);
    // Ideally, re-fetch or re-calculate data. For now just update UI toggle.
    fetchDataForCurrentCity(); // Reload to apply unit (assuming API doesn't handle, we'd handle locally, but for simplicity reload)
}
function applyUnit(unit) {
    document.getElementById('unit-c').classList.toggle('active', unit === 'C');
    document.getElementById('unit-f').classList.toggle('active', unit === 'F');
}

function setAnimation(anim) {
    state.animations = anim;
    localStorage.setItem('animations', anim);
    applyAnimations(anim);
}
function applyAnimations(anim) {
    document.getElementById('anim-on').classList.toggle('active', anim);
    document.getElementById('anim-off').classList.toggle('active', !anim);
    if(!anim) {
        document.body.style.setProperty('--transition', 'none');
    } else {
        document.body.style.setProperty('--transition', 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)');
    }
}

// Icon Helper
function getIconClass(condition) {
    if(!condition) return 'fa-cloud';
    const cond = condition.toLowerCase();
    if (cond.includes('sunny') || cond.includes('clear')) return 'fa-sun text-warning';
    if (cond.includes('cloud')) return 'fa-cloud-sun text-secondary';
    if (cond.includes('rain')) return 'fa-cloud-rain text-accent';
    if (cond.includes('storm')) return 'fa-cloud-bolt text-accent';
    if (cond.includes('snow')) return 'fa-snowflake text-accent';
    return 'fa-cloud';
}

function convertTemp(celsius) {
    if (state.unit === 'F') {
        return Math.round((celsius * 9/5) + 32);
    }
    return Math.round(celsius);
}

// Data Fetching
async function initApp() {
    showOverlay('<div class="skeleton-box" style="width:50px;height:50px;border-radius:50%;margin:0 auto 1rem;"></div><p>Initializing AI Weather System...</p>');
    try {
        const res = await fetch('/api/cities');
        const data = await res.json();
        
        state.cities = data.cities || ['Kathmandu'];
        cityList.innerHTML = '';
        state.cities.forEach(city => {
            const opt = document.createElement('option');
            opt.value = city;
            cityList.appendChild(opt);
        });
        
        // Default to Dharan; fall back to first city in list
        state.currentCity = state.cities.includes('Dharan') ? 'Dharan' : state.cities[0];
        citySelector.value = state.currentCity;
        
        await fetchDataForCurrentCity();
        hideOverlay();
    } catch(e) {
        console.error(e);
        showError('Unable to connect to WeatherAI Core. Please check your connection.');
    }
}

async function fetchDataForCurrentCity() {
    const city = state.currentCity;
    // Show skeletons
    document.querySelectorAll('.skeleton-text, .skeleton-box').forEach(el => el.style.opacity = '1');
    
    try {
        await Promise.all([
            fetchCurrent(city),
            fetch24Hour(city),
            fetch5Day(city),
            fetchPerformance(),
            fetchAIInsight(city)
        ]);
        
        // Remove skeletons by setting classes
        document.querySelectorAll('.skeleton-text, .skeleton-box').forEach(el => {
            el.classList.remove('skeleton-text', 'skeleton-box');
            el.style.opacity = '';
        });
    } catch(e) {
        console.error(e);
        showError('Failed to generate ML predictions for ' + city);
    }
}

async function fetchCurrent(city) {
    const res = await fetch(`/api/current?city=${encodeURIComponent(city)}`);
    const data = await res.json();
    
    document.getElementById('curr-city').textContent = data.city;
    const now = new Date();
    document.getElementById('curr-date').textContent = now.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
    
    document.getElementById('curr-temp').textContent = `${convertTemp(data.temperature)}°`;
    document.getElementById('curr-cond').textContent = data.condition;
    document.getElementById('curr-icon').className = `fa-solid ${getIconClass(data.condition)}`;
    
    document.getElementById('curr-hum').textContent = `${data.humidity}%`;
    document.getElementById('curr-wind').textContent = `${data.wind_speed} km/h`;
    document.getElementById('curr-pres').textContent = `${data.pressure} hPa`;
    document.getElementById('curr-rain').textContent = `${data.rain_chance}%`;
}

async function fetch24Hour(city) {
    const res = await fetch(`/api/forecast/24-hours?city=${encodeURIComponent(city)}`);
    const data = await res.json();
    state.forecast24 = data.forecast;
    
    const container = document.getElementById('hourly-container');
    container.innerHTML = '';
    
    data.forecast.forEach(f => {
        const div = document.createElement('div');
        div.className = 'hour-card';
        div.innerHTML = `
            <p class="text-secondary text-sm">${f.time}</p>
            <i class="fa-solid fa-cloud-sun"></i> <!-- Simulated generic icon -->
            <p class="temp">${convertTemp(f.temperature)}°</p>
            <p class="rain"><i class="fa-solid fa-droplet"></i> ${f.humidity}%</p>
        `;
        container.appendChild(div);
    });
    
    // Default chart is temperature
    switchChartMetric('temperature');
}

async function fetch5Day(city) {
    const res = await fetch(`/api/forecast/5-days?city=${encodeURIComponent(city)}`);
    const data = await res.json();
    
    const container = document.getElementById('daily-container');
    container.innerHTML = '';
    
    data.forecast.forEach((f, idx) => {
        const div = document.createElement('div');
        div.className = `day-card glass-panel fade-in delay-${idx+1} ${idx === 0 ? 'today' : ''}`;
        div.innerHTML = `
            <h3 class="text-lg">${f.day}</h3>
            <p class="text-xs text-secondary mb-2">${f.date}</p>
            <i class="fa-solid ${getIconClass(f.condition)}"></i>
            <p class="text-sm mt-2">${f.condition}</p>
            <div class="day-temps mt-2">
                <span>${convertTemp(f.max_temp)}°</span>
                <span class="text-secondary">${convertTemp(f.min_temp)}°</span>
            </div>
            <div class="day-stats mt-4">
                <span><i class="fa-solid fa-droplet text-accent"></i> ${f.humidity}%</span>
                <span><i class="fa-solid fa-umbrella text-accent"></i> ${f.rain_chance}%</span>
            </div>
        `;
        container.appendChild(div);
    });
}

async function fetchPerformance() {
    const res = await fetch('/api/model-performance');
    const data = await res.json();
    
    document.getElementById('perf-name').textContent = data.Model || 'Random Forest';
    document.getElementById('perf-r2').textContent = data.R2 ? data.R2.toFixed(3) : '--';
    document.getElementById('perf-rmse').textContent = data.RMSE ? data.RMSE.toFixed(2) + '°' : '--';
    document.getElementById('perf-mae').textContent = data.MAE ? data.MAE.toFixed(2) + '°' : '--';
}

async function fetchAIInsight(city) {
    const insightEl = document.getElementById('ai-insight');
    const tagsEl    = document.getElementById('ai-insight-tags');

    // Loading state
    insightEl.innerHTML = '<span class="insight-loading"><span></span><span></span><span></span></span>';
    if (tagsEl) tagsEl.innerHTML = '';

    try {
        const res  = await fetch(`/api/ai-insight?city=${encodeURIComponent(city)}`);
        const data = await res.json();

        // Typewriter effect
        typewriterEffect(insightEl, data.insight, 18);

        // Render tags
        if (tagsEl && data.tags) {
            const tagIcons = {
                season:    { monsoon: '🌧️', summer: '☀️', spring: '🌸', autumn: '🍂', winter: '❄️' },
                condition: { Rainy: '🌧️', 'Partly Cloudy': '⛅', Sunny: '☀️', Clear: '🌤️' },
            };
            const seasonIcon    = tagIcons.season[data.tags.season]    || '🌍';
            const conditionIcon = tagIcons.condition[data.tags.condition] || '🌡️';
            tagsEl.innerHTML = `
                <span class="insight-tag">${seasonIcon} ${capitalize(data.tags.season)}</span>
                <span class="insight-tag">${conditionIcon} ${data.tags.condition}</span>
                <span class="insight-tag">🌡️ ${data.tags.temp}°C</span>
                <span class="insight-tag">🌧️ ${data.tags.rain_pct}% rain</span>
            `;
        }
    } catch (e) {
        console.error('AI Insight error:', e);
        insightEl.textContent = 'Unable to generate AI insight at this time.';
    }
}

function typewriterEffect(el, text, speed = 20) {
    el.innerHTML = '';
    el.classList.add('typewriter-active');
    let i = 0;
    const cursor = document.createElement('span');
    cursor.className = 'typewriter-cursor';
    cursor.textContent = '|';
    el.appendChild(cursor);

    const interval = setInterval(() => {
        if (i < text.length) {
            cursor.before(text.charAt(i));
            i++;
        } else {
            clearInterval(interval);
            cursor.remove();
            el.classList.remove('typewriter-active');
        }
    }, speed);
}

function capitalize(str) {
    return str ? str.charAt(0).toUpperCase() + str.slice(1) : str;
}

// Chart Logic
function switchChartMetric(metricType) {
    // Update active button
    document.querySelectorAll('.chart-controls .btn-sm').forEach(btn => {
        if(btn.textContent.toLowerCase().includes(metricType.substring(0,3))) btn.classList.add('active');
        else btn.classList.remove('active');
    });

    const labels = state.forecast24.map(f => f.time);
    let data = [];
    let labelName = '';
    let color = '';
    let bg = '';

    if (metricType === 'temperature') {
        data = state.forecast24.map(f => convertTemp(f.temperature));
        labelName = `Temperature (°${state.unit})`;
        color = '#f59e0b';
        bg = 'rgba(245, 158, 11, 0.1)';
    } else if (metricType === 'humidity') {
        data = state.forecast24.map(f => f.humidity);
        labelName = 'Humidity (%)';
        color = '#38bdf8';
        bg = 'rgba(56, 189, 248, 0.1)';
    } else if (metricType === 'wind') {
        data = state.forecast24.map(f => f.wind);
        labelName = 'Wind Speed (km/h)';
        color = '#a78bfa';
        bg = 'rgba(167, 139, 250, 0.1)';
    } else if (metricType === 'rain') {
        data = state.forecast24.map(f => f.rain);
        labelName = 'Rain Probability (%)';
        color = '#60a5fa';
        bg = 'rgba(96, 165, 250, 0.1)';
    }

    renderChart(labels, data, labelName, color, bg);
}

function renderChart(labels, data, labelName, borderColor, bgColor) {
    const ctx = document.getElementById('trendChart').getContext('2d');
    
    if (trendChartInstance) {
        trendChartInstance.destroy();
    }
    
    const isDark = state.theme === 'dark';
    const gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)';
    const textColor = isDark ? '#94a3b8' : '#64748b';

    trendChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: labelName,
                data: data,
                borderColor: borderColor,
                backgroundColor: bgColor,
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: isDark ? '#0f172a' : '#ffffff',
                pointBorderColor: borderColor,
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: isDark ? 'rgba(15, 23, 42, 0.9)' : 'rgba(255, 255, 255, 0.9)',
                    titleColor: isDark ? '#fff' : '#000',
                    bodyColor: borderColor,
                    borderColor: gridColor,
                    borderWidth: 1,
                    padding: 10
                }
            },
            scales: {
                y: {
                    grid: { color: gridColor },
                    ticks: { color: textColor }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: textColor, maxTicksLimit: 8 }
                }
            }
        }
    });
}

// Status Overlay
function showOverlay(htmlContent) {
    const overlay = document.getElementById('status-overlay');
    const content = document.getElementById('status-content');
    content.innerHTML = htmlContent;
    overlay.classList.remove('hidden');
}

function hideOverlay() {
    const overlay = document.getElementById('status-overlay');
    overlay.classList.add('hidden');
}

function showError(msg) {
    showOverlay(`
        <i class="fa-solid fa-triangle-exclamation text-danger" style="font-size:3rem;margin-bottom:1rem;"></i>
        <h3 class="mb-2">Data Unavailable</h3>
        <p class="text-secondary mb-4">${msg}</p>
        <button class="btn-ghost" style="padding: 0.5rem 1rem; border: 1px solid var(--glass-border); border-radius: 4px; color: var(--text-primary); cursor: pointer;" onclick="initApp()">
            <i class="fa-solid fa-rotate-right"></i> Retry
        </button>
    `);
}

// Search button handler
function searchCity() {
    const val = citySelector.value.trim();
    if (!val) return;
    // Try exact match first
    if (state.cities.includes(val)) {
        state.currentCity = val;
        fetchDataForCurrentCity();
        return;
    }
    // Try case-insensitive match
    const match = state.cities.find(c => c.toLowerCase() === val.toLowerCase());
    if (match) {
        state.currentCity = match;
        citySelector.value = match;
        fetchDataForCurrentCity();
    } else {
        showError(`City "${val}" not found. Please select from the list.`);
    }
}
