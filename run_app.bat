@echo off
cd /d "%~dp0"
title Lanzador Portafolio Zen

echo =========================================
echo       INICIANDO PORTAFOLIO ZEN
echo =========================================
echo.

echo [1/3] Iniciando el servidor Backend (Base de datos)...
start "Backend Portafolio Zen" cmd /c "start_backend.bat"

echo [2/3] Iniciando el servidor Web (Angular)...
start "Frontend Portafolio Zen" cmd /c "start_frontend.bat"

echo [3/3] Abriendo el navegador web...
echo Esperando unos segundos para que Angular termine de compilar...
timeout /t 7 /nobreak > nul

start http://localhost:4200
exit
