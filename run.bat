@echo off
chcp 65001 >nul
title Traffic Simulator - Web UI
cd /d %~dp0

echo ====================================================
echo   TRAFFIC SIMULATOR - AUTO ENVIRONMENT CHECK
echo ====================================================
echo.

REM 1. Kiem tra Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] May cua sep chua cai Python!
    echo Vui long tai va cai dat Python tai: https://www.python.org/
    echo LUU Y: Nho tich chon "Add Python to PATH" khi cai dat nhe.
    echo.
    pause
    exit /b
)
echo [OK] Da tim thay Python.

REM 2. Kiem tra thu vien Python
python -c "import flask, playwright" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Thieu thu vien Flask hoac Playwright. Dang tu dong cai dat...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Khong the cai dat thu vien. Vui long kiem tra ket noi mang!
        echo.
        pause
        exit /b
    )
)
echo [OK] Da cai dat day du cac thu vien Python.

REM 3. Kiem tra Playwright Chromium Browser
python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); p.chromium.launch(headless=True).close(); p.stop()" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Thieu trinh duyet Playwright. Dang tu dong tai Chromium...
    playwright install chromium
    if %errorlevel% neq 0 (
        echo [ERROR] Khong the tai xuong trinh duyet Playwright!
        echo.
        pause
        exit /b
    )
)
echo [OK] Trinh duyet Playwright da san sang.
echo.
echo ====================================================
echo   TRAFFIC SIMULATOR - WEB UI
echo   http://localhost:7878
echo ====================================================
echo.
echo Dang khoi dong server... Mo trinh duyet len nhe sep!
echo Bam Ctrl+C de dung.
echo.

if not exist logs mkdir logs

start "" http://localhost:7878
python app.py

pause
