@echo off
cd /d "%~dp0"
title FGTS Digital - Automacao
echo Iniciando aplicacao...
"venv\Scripts\python.exe" "main.py"
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] A aplicacao encerrou com erro.
    pause
)
