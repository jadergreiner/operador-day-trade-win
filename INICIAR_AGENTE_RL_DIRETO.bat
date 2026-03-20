@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM  LAUNCHER: RL DIRETO - PADRAO CANONICO
REM  Versao: 4.0 - GOVERNANCA OPERACIONAL
REM  Data: 19/03/2026
REM ============================================================

for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a%%b)

title RL DIRETO - OPERADOR RL AUTONOMO [PRODUCAO ESTRITA] - EA ID: 234600 [%mydate%_%mytime%]

cd /d "%~dp0"
if not exist "outputs" mkdir outputs >nul 2>&1

echo.
echo   ============================================================
echo   OPERADOR RL DIRETO - PRODUCAO ESTRITA
echo   ============================================================
echo.

call :bootstrap_checks
if errorlevel 1 exit /b 1

echo.
echo   ============================================================
echo   CONTRATO OPERACIONAL RL DIRETO
echo   ============================================================
echo   [OK] Launcher canonico com bootstrap, confirmacao e pre-flight
echo   [OK] Estado isolado por magic 234600 + session_id unico
echo   [OK] Logs separados em outputs\agente_direto_*.log
echo   [OK] Runtime com contexto de abertura e isolamento formal
echo   [OK] Pode rodar em paralelo com INICIAR_AGENTE_RL_5000.bat
echo   ============================================================
echo.
echo   Alvo exibido pelo runtime: R$140.00 / Stop Loss exibido: -R$250.00
echo.
echo   Script real: scripts\agente_rl_direto_independente.py --mode dinamico
echo   Gate operacional: outputs\release_gates\go_live_decision.json
echo.
echo   ============================================================
echo.

:MENU
echo.
echo   [1] AVALIAR MODELO (Simulacao)
echo   [2] OPERAR MERCADO REAL (AGENTE DIRETO ISOLADO)
echo   [3] VALIDAR GO LIVE (BL-01 + BL-07 + BL-08)
echo   [4] Sair
echo.

set /p CHOICE="Escolha (1-4): "

if "%CHOICE%"=="1" (
    echo.
    if not exist "scripts\treinar_novo_agente_rl.py" (
        echo   [ERRO] Script de avaliacao ausente: scripts\treinar_novo_agente_rl.py
        echo.
        pause
        goto :MENU
    )
    echo   Iniciando avaliacao do modelo...
    python scripts\treinar_novo_agente_rl.py --dados-reais --apenas-avaliar
    if errorlevel 1 (
        echo.
        echo   [ERRO] Avaliacao falhou.
    ) else (
        echo.
        echo   [OK] Avaliacao concluida.
    )
    echo.
    pause
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
    echo   [START] OPERACAO REAL COM AGENTE DIRETO ISOLADO
    echo   Objetivo visual do runtime: Lucro R$ 140,00 ou Prejuizo -R$ 250,00
    echo   Modo SL/TP: DINAMICO
    echo   Logs esperados: outputs\agente_direto_*.log
    echo   Artefato GO LIVE: outputs\release_gates\go_live_decision.json
    echo.
    python scripts\agente_rl_direto_independente.py --mode dinamico
    if errorlevel 1 (
        echo.
        echo   [ERRO] AGENTE DIRETO ENCERROU COM ERRO
        echo   Verifique:
        echo   - outputs\agente_direto_*.log
        echo   - outputs\agente_direto_debug_*.log
        echo   - conexao MT5 e configuracao do terminal
    ) else (
        echo.
        echo   [OK] AGENTE DIRETO ENCERROU SEM ERRO DE LAUNCHER
        echo   Estado isolado e logs separados permaneceram ativos.
    )
    echo.
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

if not exist "scripts\agente_rl_direto_independente.py" (
    echo   [FATAL] Wrapper do agente direto ausente: scripts\agente_rl_direto_independente.py
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
echo   O launcher usa o agente direto com estado isolado e logs dedicados.
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
python scripts\sync_mt5_trades_to_db.py --days-back 3 >nul 2>&1
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
