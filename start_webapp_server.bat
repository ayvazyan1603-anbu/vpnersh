@echo off
chcp 65001 > nul
title WebApp Local Server (http://localhost:8080)
echo ===================================================
echo   Запуск локального сервера WebApp на порту 8080
echo ===================================================
start "" "http://localhost:8080/webapp/index.html"
python -m http.server 8080
pause
