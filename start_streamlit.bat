@echo off
:: Weather Prediction - Streamlit App Launcher
:: Run this as Administrator to also open the firewall port

echo ====================================
echo  Weather Prediction - Streamlit App
echo ====================================

:: Open firewall port 8501 (silently, will succeed if admin)
netsh advfirewall firewall add rule name="Weather App Streamlit 8501" dir=in action=allow protocol=TCP localport=8501 >nul 2>&1

:: Get local IP address
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set IP=%%a
    goto :found_ip
)
:found_ip
set IP=%IP: =%

echo.
echo  Starting Streamlit server...
echo  Access from THIS device:   http://localhost:8501
echo  Access from OTHER devices: http://%IP%:8501
echo.
echo  Make sure both devices are on the same Wi-Fi/network!
echo  Press Ctrl+C to stop the server.
echo ====================================
echo.

cd /d "%~dp0"

:: Activate venv if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: Run Streamlit bound to 0.0.0.0 so it's reachable from other devices
streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501 --server.enableCORS false --server.enableXsrfProtection false

pause
