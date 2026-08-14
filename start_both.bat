@echo off
:: Weather Prediction - Launch BOTH Flask + Streamlit
:: Run this as Administrator to also open firewall ports

echo ====================================
echo  Weather Prediction - All Servers
echo ====================================

:: Open firewall ports (silently)
netsh advfirewall firewall add rule name="Weather App Flask 5000" dir=in action=allow protocol=TCP localport=5000 >nul 2>&1
netsh advfirewall firewall add rule name="Weather App Streamlit 8501" dir=in action=allow protocol=TCP localport=8501 >nul 2>&1
netsh advfirewall firewall add rule name="Weather App Flask API 5001" dir=in action=allow protocol=TCP localport=5001 >nul 2>&1

:: Get local IP address
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set IP=%%a
    goto :found_ip
)
:found_ip
set IP=%IP: =%

echo.
echo  Flask app (full UI):
echo    Local:   http://localhost:5000
echo    Network: http://%IP%:5000
echo.
echo  Streamlit app:
echo    Local:   http://localhost:8501
echo    Network: http://%IP%:8501
echo.
echo  Make sure both devices are on the same Wi-Fi/network!
echo ====================================
echo.

cd /d "%~dp0"

:: Activate venv if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: Start Flask in a new window
start "Flask - Weather App" cmd /k "cd /d %~dp0 && (if exist venv\Scripts\activate.bat call venv\Scripts\activate.bat) && python app.py"

:: Start Streamlit in a new window
start "Streamlit - Weather App" cmd /k "cd /d %~dp0 && (if exist venv\Scripts\activate.bat call venv\Scripts\activate.bat) && streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501 --server.enableCORS false --server.enableXsrfProtection false"

echo  Both servers launched in separate windows!
echo  Close those windows to stop the servers.
pause
