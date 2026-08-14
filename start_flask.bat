@echo off
:: Weather Prediction - Flask App Launcher
:: Run this as Administrator to also open the firewall port

echo ====================================
echo  Weather Prediction - Flask Server
echo ====================================

:: Open firewall port 5000 (silently, will succeed if admin)
netsh advfirewall firewall add rule name="Weather App Flask 5000" dir=in action=allow protocol=TCP localport=5000 >nul 2>&1

:: Get local IP address
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set IP=%%a
    goto :found_ip
)
:found_ip
set IP=%IP: =%

echo.
echo  Starting Flask server...
echo  Access from THIS device:   http://localhost:5000
echo  Access from OTHER devices: http://%IP%:5000
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

:: Run Flask with host 0.0.0.0 so it's reachable from other devices
python app.py

pause
