@echo off
title DIARIOS - OPERADOR CONTEXTUAL [DIARIOS AUTOMATICOS] - EA ID: 234800
REM Inicia o operador contextual dos Diarios + canais de journaling
REM Duplo clique neste arquivo para iniciar

echo ================================================================================
echo OPERADOR QUANTICO - DIARIOS AUTOMATICOS + FEATURES INTRADAY
echo ================================================================================
echo.

cd /d "%~dp0"

set "DIARIOS_DB_PATH=%CD%\data\db\trading_diarios.db"
set "DB_PATH=%DIARIOS_DB_PATH%"
set "TRADING_DB_PATH=%DIARIOS_DB_PATH%"

REM =========================================================================
REM P50-CHECK: Verificar operacoes pendentes do pregao anterior
REM =========================================================================
echo [STARTUP] Verificando pendencias do pregao anterior...
python scripts\check_pending_sync.py --db "%DIARIOS_DB_PATH%" --quiet
echo [STARTUP] Verificacao de pendencias concluida
echo.

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

echo [09:34] Gate diario de confidence (bootstrap)...
python -c "from pathlib import Path; import json; p=Path('config/confidence_override_today.json'); gate=0.60; gate=float(json.loads(p.read_text(encoding='utf-8')).get('confidence_current', gate)) if p.exists() else gate; gate=max(0.35, min(0.60, gate)); print(f'[09:34] Gate diario de confidence: {gate:.0%}')"
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

REM =========================================================================
REM P50-SYNC: Espelhar trades do agente_direto para trading_diarios.db
REM Garante que o P50-B do dia seguinte encontre os trades de hoje.
REM =========================================================================
echo.
echo [17:32] Espelhando trades do agente_direto para trading_diarios.db...
set "RL_DIRETO_DB=%CD%\data\db\trading_rl_direto.db"
python scripts\espelhar_trades_para_diarios.py --src "%RL_DIRETO_DB%" --dst "%DIARIOS_DB_PATH%"
if errorlevel 1 (
    echo [17:33] [WARN] P50-SYNC falhou
) else (
    echo [17:33] P50-SYNC OK
)

echo.
echo ================================================================================
echo [INFO] P0-2 Status: verificar em data\backtest\p0_2_status.json
echo [INFO] P0-2 Logs: verificar em data\logs\p0_2_execution*.log
echo [INFO] P50-SYNC: trades do agente_direto espelhados para trading_diarios.db
echo ================================================================================

pause
