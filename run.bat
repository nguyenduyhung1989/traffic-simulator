@echo off
chcp 65001 >nul
title Traffic Simulator - Web UI
cd /d %~dp0

if not exist logs mkdir logs

echo ============================================
echo   TRAFFIC SIMULATOR - WEB UI
echo   http://localhost:7878
echo ============================================
echo.
echo Dang khoi dong server... Mo trinh duyet len nhe sep!
echo Bam Ctrl+C de dung.
echo.

start "" http://localhost:7878
python app.py

pause
