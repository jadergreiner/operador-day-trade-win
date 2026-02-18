@echo off
REM Inicia os Diarios Automaticos do Operador Quantico
REM Duplo clique neste arquivo para iniciar

echo ================================================================================
echo OPERADOR QUANTICO - DIARIOS AUTOMATICOS
echo ================================================================================
echo.

cd /d "%~dp0"

echo Iniciando sistema com narrativa completa...
echo.

python scripts\start_journals_full_display.py

pause
