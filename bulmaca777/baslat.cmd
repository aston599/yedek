@echo off
setlocal EnableExtensions
title YouTube Bulmacalari - Baslat

cd /d "%~dp0"

if not exist ".env" (
  if exist ".env.example" (
    copy /Y ".env.example" ".env" >nul
    echo [env] .env olusturuldu — CHAT_MODE=youtube ^(InnerChat^)
  )
) else (
  findstr /I /B "CHAT_MODE=mock" ".env" >nul 2>&1 && (
    echo [env] UYARI: .env icinde CHAT_MODE=mock — InnerChat icin CHAT_MODE=youtube yapin ve yeniden baslatin.
  )
)

set "PORT=3847"
if exist ".env" (
  for /f "tokens=1,* delims==" %%a in ('findstr /B /I "PORT=" ".env" 2^>nul') do (
    set "PORT=%%b"
  )
)
set "PORT=%PORT: =%"
if "%PORT%"=="" set "PORT=3847"

echo.
echo  YouTube Bulmacalari
echo  ===================
echo.

echo [1/3] Port %PORT% uzerindeki eski sunucu kapatiliyor...
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":%PORT% " ^| findstr "LISTENING"') do (
  taskkill /PID %%p /F >nul 2>&1
)

echo.
echo [2/3] UI sablonlari yenileniyor...
node scripts/regenerate-ui.js
if errorlevel 1 (
  echo UYARI: scripts/regenerate-ui.js hata verdi. Sunucu yine de acilacak.
)

echo.
echo [3/3] Sunucu bu pencerede baslatiliyor...
set "CHAT_MODE=youtube"
if exist ".env" (
  for /f "usebackq tokens=1,* delims==" %%a in (`findstr /B /I "CHAT_MODE=" ".env" 2^>nul`) do set "CHAT_MODE=%%b"
)
set "CHAT_MODE=%CHAT_MODE: =%"
echo Sohbet modu: %CHAT_MODE% ^(youtube = InnerChat^)
echo Panel aciliyor: http://127.0.0.1:%PORT%/admin/
start "" "http://127.0.0.1:%PORT%/admin/"
echo.
echo Sunucu calisiyor. Durdurmak icin Ctrl+C.
echo.
node server/index.js
set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo Sunucu kapandi (kod: %EXIT_CODE%).
echo Pencere kapanmadan once mesaji okuyabilirsiniz.
pause
exit /b %EXIT_CODE%
