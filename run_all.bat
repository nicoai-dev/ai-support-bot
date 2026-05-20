@echo off
title Nico Market Full Stack Launcher
echo ==========================================
echo       Starting Nico Market Full Stack...
echo ==========================================

:: Проверка наличия виртуального окружения
if not exist "venv" (
    echo [ERROR] Virtual environment 'venv' not found!
    echo Please create it and install requirements first.
    pause
    exit /b
)

:: Запуск единого Python скрипта автоматизации
.\venv\Scripts\python.exe run_all.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Process crashed with exit code %ERRORLEVEL%
    pause
)
