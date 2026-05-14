@echo off
title AI Support Bot Launcher
echo ==========================================
echo       Starting AI Support Bot...
echo ==========================================

:: Проверка наличия виртуального окружения
if not exist "venv" (
    echo [ERROR] Virtual environment 'venv' not found!
    echo Please create it and install requirements first.
    pause
    exit /b
)

:: Запуск бота через интерпретатор из venv
echo [INFO] Activating environment and launching main.py...
.\venv\Scripts\python.exe main.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Bot crashed with exit code %ERRORLEVEL%
    pause
)
