@echo off
title DIARIOS - OPERADOR CONTEXTUAL [DIARIOS AUTOMATICOS] - EA ID: 234800
REM Inicia o operador contextual dos Diarios + canais de journaling
REM Duplo clique neste arquivo para iniciar

echo ================================================================================
echo OPERADOR QUANTICO - DIARIOS AUTOMATICOS + FEATURES INTRADAY
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

REM =========================================================================
REM P50-B: Daily Confidence Retraining (baseado em WIN RATE real pregao anterior)
REM =========================================================================
echo [09:33] Iniciando P50-B Daily Confidence Retraining...
python scripts\daily_confidence_retraining.py
echo [09:34] P50-B OK - Confidence retrainado
echo.

echo Iniciando sistema com narrativa completa...
echo.

python scripts\start_journals_full_display.py

REM =========================================================================
REM P50-C: Generate Opportunity Summary (fim do dia anterior)
REM =========================================================================
echo.
echo [17:30] Gerando sumário de oportunidades do dia anterior (P50-C)...
python scripts\generate_opportunity_summary.py
echo [17:31] P50-C OK - Sumário gerado (verificar outputs\)

echo.
echo ================================================================================
echo [INFO] P0-2 Status: verificar em data\backtest\p0_2_status.json
echo [INFO] P0-2 Logs: verificar em data\logs\p0_2_execution*.log
echo ================================================================================

pause
