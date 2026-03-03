@echo off
REM Inicia o Agente de Micro Tendencias WINFUT
REM Usa o Python 3.11 com MetaTrader5 instalado

echo ==============================================================================
echo AGENTE MICRO TENDENCIA WINFUT - Day Trade B3
echo ==============================================================================
echo.
echo Ciclo: 2 minutos
echo Horario: 09:00-17:55 (Brasilia)
echo Simbolo: WIN$N
echo.

set PYTHON_EXE=C:\Users\Usuario\AppData\Local\Programs\Python\Python311\python.exe

if not exist "%PYTHON_EXE%" (
    echo ERRO: Python nao encontrado em "%PYTHON_EXE%"
    echo Ajuste o caminho do Python neste arquivo.
    pause
    exit /b 1
)

cd /d "%~dp0"

"%PYTHON_EXE%" scripts\agente_micro_tendencia_winfut.py

pause
