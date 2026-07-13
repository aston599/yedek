@echo off
cd /d "%~dp0"

echo Betroy bot baslatiliyor...

for /f "tokens=2 delims==" %%a in ('wmic process where "CommandLine like '%%bot.main%%'" get ProcessId /value 2^>nul ^| find "="') do (
    taskkill /F /PID %%a >nul 2>&1
)

timeout /t 2 /nobreak >nul
echo Durdurmak icin Ctrl+C
.\.venv\Scripts\python.exe -m bot.main
