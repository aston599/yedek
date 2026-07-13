@echo off
chcp 65001 >nul
title Bulmaca777 — Ubuntu .env aktar
cd /d "%~dp0"

set "SERVER=root@164.90.163.55"
set "REMOTE=/opt/bulmaca777"

echo.
echo  .env dosyasi sunucuya gonderiliyor...
echo  (SSH sifreniz sorulacak)
echo.

if not exist ".env" (
  echo HATA: .env bulunamadi.
  pause
  exit /b 1
)

scp ".env" "%SERVER%:%REMOTE%/.env"
if errorlevel 1 (
  echo.
  echo HATA: scp basarisiz. Sunucuda klasor var mi?
  echo   ssh %SERVER% "mkdir -p %REMOTE%"
  pause
  exit /b 1
)

echo.
echo  Servis yeniden baslatiliyor...
ssh %SERVER% "chown www-data:www-data %REMOTE%/.env 2>nul; systemctl restart bulmaca777; sleep 1; curl -s http://127.0.0.1:3847/api/health; echo.; systemctl is-active bulmaca777"
echo.
echo  Tamam. Tarayici: https://bulmaca777.com/admin/
pause
