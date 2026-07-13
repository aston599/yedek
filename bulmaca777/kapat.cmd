@echo off
setlocal EnableExtensions
chcp 65001 >nul

cd /d "%~dp0"
set "PORT=3847"
if exist ".env" for /f "usebackq tokens=1,* delims==" %%a in (`findstr /B /I "PORT=" ".env" 2^>nul`) do set "PORT=%%b"
set "PORT=%PORT: =%"

echo Port %PORT% ve proje pencereleri kapatiliyor...

for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":%PORT% " ^| findstr "LISTENING"') do taskkill /PID %%p /F >nul 2>&1

taskkill /FI "WINDOWTITLE eq YouTube Bulmacalari*" /F >nul 2>&1

echo Bitti. Cursor terminal sekmelerini elle kapatabilirsiniz.
timeout /t 3 >nul
endlocal
