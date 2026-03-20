@echo off
title RL 5000 - OPERADOR RL v5000 [PRODUCAO ESTRITA] - EA ID: 234500
setlocal enabledelayedexpansion

REM ============================================================
REM  LAUNCHER: RL 5000 - MODO PRODUCAO ESTRITA
REM  Versao: 4.0 - GO LIVE COMPLIANCE
REM  Data: 19/03/2026
REM ============================================================

cd /d "%~dp0"
if not exist "outputs" mkdir outputs >nul 2>&1

echo.
echo   ============================================================
echo   OPERADOR RL v5000 - PRODUCAO ESTRITA
echo   ============================================================
echo.

call :bootstrap_checks
if errorlevel 1 exit /b 1

echo.
echo   ============================================================
echo   CONTRATO OPERACIONAL RL 5000
echo   ============================================================
echo   [OK] Wrapper canonico com supervisao e heartbeat
echo   [OK] SL/TP dinamicos com RR minimo 1.5:1
echo   [OK] Maximo 6 trades por sessao
echo   [OK] Maximo 1 posicao simultanea
echo   [OK] Confirmacao multi-vela (2 candles)
echo   [OK] Novas entradas so ate 17:25 BRT
echo   [OK] Monitoramento/protecao ate 17:55 BRT
echo   [OK] Cooldown base 5 min e pos-SL 30 min
echo   ============================================================
echo.
echo   Alvo: R$140.00 / Stop Loss: -R$250.00
echo.
echo   ============================================================
echo.

:MENU
echo.
echo   [1] AVALIAR MODELO (Simulacao)
echo   [2] OPERAR MERCADO REAL (PRODUCAO ESTRITA)
echo   [3] VALIDAR GO LIVE (BL-01 + BL-07 + BL-08)
echo   [4] Sair
echo.

set /p CHOICE="Escolha (1-4): "

if "%CHOICE%"=="1" (
    echo.
    echo   Iniciando avaliacao do modelo...
    python scripts\treinar_novo_agente_rl.py --dados-reais --apenas-avaliar
    if errorlevel 1 echo. & echo   [ERRO] Avaliacao falhou. & pause
    goto :MENU
)

if "%CHOICE%"=="2" (
    echo.
    call :get_confirmation
    if errorlevel 1 (
        echo.
        echo   [CANCELADO] Operacao real cancelada pelo operador.
        echo.
        goto :MENU
    )

    call :real_preflight
    if errorlevel 1 (
        echo.
        echo   [ERRO] Pre-flight reprovado. Operacao nao iniciada.
        echo.
        pause
        goto :MENU
    )

    echo.
    echo   [START] OPERACAO REAL COM WRAPPER CANONICO
    echo   Objetivo: Lucro R$ 140,00 ou Prejuizo -R$ 250,00
    echo   Modo SL/TP: DINAMICO
    echo   Artefato GO LIVE: outputs\release_gates\go_live_decision.json
    echo.
    python scripts\agente_com_supervision.py --sl-tp-mode dinamico
    echo.
    echo   [INFO] Operacao encerrada.
    pause
    goto :MENU
)

if "%CHOICE%"=="3" (
    echo.
    echo   [GATE] Executando BL-01, BL-07 e BL-08...
    python scripts\validate_go_live_gates.py
    if errorlevel 1 (
        echo.
        echo   [GATE] Reprovado - corrigir pendencias antes de operar.
    ) else (
        echo.
        echo   [GATE] Aprovado - ambiente pronto para GO LIVE.
    )
    echo.
    pause
    goto :MENU
)

if "%CHOICE%"=="4" (
    echo.
    echo   Encerrando...
    exit /b 0
)

echo.
echo   [ERRO] Opcao invalida. Digite 1, 2, 3 ou 4.
echo.
goto :MENU

:bootstrap_checks
echo   [CHECK] Validando prerequisitos basicos...

python --version >nul 2>&1
if errorlevel 1 (
    echo   [FATAL] Python nao encontrado no PATH.
    pause
    exit /b 1
)
echo   [OK] Python detectado

if exist "data\models\novo_agente_rl\modelo_final\q_network.pkl" (
    echo   [OK] Modelo localizado em: data\models\novo_agente_rl\modelo_final\
) else if exist "..\operador-day-trade-win\data\models\novo_agente_rl\modelo_final\q_network.pkl" (
    echo   [OK] Modelo localizado em: ..\operador-day-trade-win\data\models\novo_agente_rl\modelo_final\
) else (
    echo   [FATAL] Arquivo q_network.pkl nao localizado.
    pause
    exit /b 1
)

if not exist "scripts\agente_com_supervision.py" (
    echo   [FATAL] Wrapper canonico ausente: scripts\agente_com_supervision.py
    pause
    exit /b 1
)

if not exist "scripts\validate_go_live_gates.py" (
    echo   [FATAL] Script de gate ausente: scripts\validate_go_live_gates.py
    pause
    exit /b 1
)

exit /b 0

:get_confirmation
echo.
echo   *** AVISO CRITICO ***
echo   ORDENS REAIS serao executadas no MetaTrader 5.
echo   O launcher usa o wrapper canonico com supervisao completa.
echo   Risco de perda financeira permanece.
echo.

:confirm_loop
set /p CONFIRM="Tem certeza? (S/N): "
if /i "!CONFIRM!"=="S" exit /b 0
if /i "!CONFIRM!"=="N" exit /b 1
echo   Responda S ou N.
goto :confirm_loop

:real_preflight
echo.
echo   [PRE-FLIGHT] Validando ambiente para auto-trade...

if not exist "data\db\trading.db" (
    echo   [ERRO] SQLite principal ausente: data\db\trading.db
    exit /b 1
)
echo   [OK] SQLite principal encontrado

if not exist "scripts\system_health_monitor.py" (
    echo   [ERRO] Script de health check ausente.
    exit /b 1
)

if not exist "scripts\sync_mt5_trades_to_db.py" (
    echo   [ERRO] Script de sincronizacao MT5 ausente.
    exit /b 1
)

python -c "from config.settings import TradingConfig; from pathlib import Path; import sys; cfg=TradingConfig(); terminal=(cfg.mt5_terminal_path or '').strip(); print(f'[OK] MT5 server: {cfg.mt5_server}'); print(f'[OK] MT5 terminal: {terminal}'); sys.exit(0 if terminal and Path(terminal).exists() else 2)"
if errorlevel 1 (
    echo   [ERRO] Credenciais ou terminal MT5 invalidos. Verifique .env / ambiente.
    exit /b 1
)

echo   [PRE-FLIGHT] Executando health check...
python scripts\system_health_monitor.py
if errorlevel 1 (
    echo   [ERRO] Health check reprovado.
    exit /b 1
)
echo   [OK] Health check aprovado

echo   [SYNC] Sincronizando trades MT5 para SQLite...
python scripts\sync_mt5_trades_to_db.py --days-back 3
if errorlevel 1 (
    echo   [ERRO] Falha na sincronizacao MT5 -> SQLite.
    exit /b 1
)
echo   [OK] Sincronizacao concluida

if exist "outputs\release_gates\go_live_decision.json" (
    echo   [INFO] Ultima decisao GO LIVE: outputs\release_gates\go_live_decision.json
) else (
    echo   [INFO] Nenhum go_live_decision.json encontrado ainda.
)

exit /b 0
