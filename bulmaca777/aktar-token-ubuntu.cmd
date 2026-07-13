@echo off
chcp 65001 >nul
title Bulmaca777 — GitHub token ile Ubuntu kurulum
cd /d "%~dp0"
set "SERVER=root@164.90.163.55"

echo.
echo  GitHub Personal Access Token (repo okuma yetkisi)
echo  Olustur: https://github.com/settings/tokens
echo.
set /p GITHUB_TOKEN="Token (yapistir): "

if "%GITHUB_TOKEN%"=="" (
  echo HATA: Token bos.
  pause
  exit /b 1
)

echo.
echo  Sunucuda kurulum basliyor (SSH sifresi de sorulabilir)...
ssh %SERVER% "export GITHUB_TOKEN=%GITHUB_TOKEN%; bash -s" < scripts\kur-github-token.sh

echo.
pause
