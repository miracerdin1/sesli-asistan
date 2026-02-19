@echo off
title Sesli Asistan
color 0B
cls
echo ==================================================
echo           SESLI ASISTAN BASLATILIYOR...
echo ==================================================
echo.
echo [BILGI] Uygulama dizinine gidiliyor...
cd /d "%~dp0"

echo [BILGI] Tarayici aciliyor...
start "" "http://127.0.0.1:5000"

echo [BILGI] Sunucu baslatiliyor (Cikmak icin bu pencereyi kapatin)...
echo.
python app.py
pause
