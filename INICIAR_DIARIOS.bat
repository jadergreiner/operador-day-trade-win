@echo off
REM Inicia os Diarios Automaticos do Operador Quantico
REM Duplo clique neste arquivo para iniciar

echo ================================================================================
echo OPERADOR QUANTICO - DIARIOS AUTOMATICOS
echo ================================================================================
echo.

cd /d "%~dp0"

REM ========================================================================
REM P0-2: Iniciar validacao de backtest em BACKGROUND (nao bloqueia)
REM ========================================================================
echo [09:32] Iniciando P0-2 Backtest Validation em background...
start /B python scripts\run_p0_2_backtest.py > data\logs\p0_2_execution.log 2>&1
echo [09:32] P0-2 iniciado (background - nao bloqueia operador)
echo.

echo Iniciando sistema com narrativa completa...
echo.

python scripts\start_journals_full_display.py

echo.
echo ================================================================================
echo [INFO] P0-2 Status: verificar em data\backtest\p0_2_status.json
echo [INFO] P0-2 Logs: verificar em data\logs\p0_2_execution*.log
echo ================================================================================

pause
