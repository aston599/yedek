@echo off
chcp 65001 >nul
title Bulmaca777 — canliya yukle (Ubuntu)
cd /d "%~dp0"

set "SERVER=root@164.90.163.55"
set "REMOTE=/opt/bulmaca777"

echo.
echo  ========================================
echo   Bulmaca777 - canli sunucuya aktarim
echo   %SERVER%  -^>  %REMOTE%
echo  ========================================
echo.
echo  Gonderilecek: server, public, website, scripts, package.json
echo  (node_modules ve oda veritabani haric)
echo.
echo  SSH sifresi sorulacak (DigitalOcean root).
echo.

ssh %SERVER% "mkdir -p %REMOTE%/data/rooms %REMOTE%/data/team-race"
if errorlevel 1 goto err

scp -r server public website scripts package.json package-lock.json .env.example %SERVER%:%REMOTE%/
if errorlevel 1 goto err

if exist "data\team-race" (
  echo  data\team-race aktariliyor...
  scp -r data\team-race %SERVER%:%REMOTE%/data/
  if errorlevel 1 goto err
)

if exist ".env" (
  echo  .env aktariliyor...
  scp ".env" "%SERVER%:%REMOTE%/.env"
  if errorlevel 1 goto err
) else (
  echo  UYARI: Yerel .env yok — sunucudaki .env korunur veya .env.production.example kullanin.
)

scp scripts\deploy-ubuntu-nogit.sh %SERVER%:/tmp/deploy-bulmaca.sh
if errorlevel 1 goto err

echo.
echo  Sunucuda npm install + servis yeniden baslatiliyor...
ssh %SERVER% "sed -i 's/\r$//' /tmp/deploy-bulmaca.sh 2>/dev/null; bash /tmp/deploy-bulmaca.sh"
if errorlevel 1 goto err

echo.
echo  Canli .env + dogrulama...
ssh %SERVER% "sed -i 's/\r$//' %REMOTE%/scripts/patch-production-env.sh %REMOTE%/scripts/post-deploy-check.sh 2>/dev/null; bash %REMOTE%/scripts/patch-production-env.sh; systemctl restart bulmaca777; sleep 2; bash %REMOTE%/scripts/post-deploy-check.sh"
if errorlevel 1 goto err

echo.
echo  ========================================
echo   Tamam
echo   Admin:  https://bulmaca777.com/admin/
echo   OBS:    https://bulmaca777.com/celebrity-overlay?room=ODA_ID
echo   Lab:    https://bulmaca777.com/play/celebrity-quiz-lab.html?room=ODA_ID
echo  ========================================
echo.
pause
exit /b 0

:err
echo.
echo  HATA — SSH/scp basarisiz veya sunucu erisilemiyor.
echo  Kontrol: ping 164.90.163.55, DO konsol, ssh %SERVER%
echo.
pause
exit /b 1
