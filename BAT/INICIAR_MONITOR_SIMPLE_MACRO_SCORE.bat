@echo off
REM Inicia o monitor do Macro Score Simplificado
REM Usa o Python 3.11 com MetaTrader5 instalado

echo ==============================================================================
echo OPERADOR QUANTICO - MONITOR MACRO SCORE SIMPLIFICADO
echo ==============================================================================
echo.

set PYTHON_EXE=C:\Users\Usuario\AppData\Local\Programs\Python\Python311\python.exe

if not exist "%PYTHON_EXE%" (
    echo ERRO: Python nao encontrado em "%PYTHON_EXE%"
    echo Ajuste o caminho do Python neste arquivo.
    pause
    exit /b 1
)

cd /d "%~dp0"

"%PYTHON_EXE%" scripts\monitor_simple_macro_score.py

pause
