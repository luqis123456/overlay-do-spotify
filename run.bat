@echo off
title Spotify Gaming Overlay
cd /d "%~dp0"
echo Starting Spotify Gaming Overlay...
py main.py %*
if %ERRORLEVEL% neq 0 (
    echo.
    echo If Python is not in PATH, try: python main.py
    pause
)

