@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM  LAUNCHER: NOVO AGENTE RL (OPERACAO REAL 5000 EPISODIOS)
REM  Data: 06/03/2026 - v1.0.9 - COM SUPORTE A ARGUMENTOS
REM ============================================================

REM Garante que o script esta rodando na raiz do projeto
cd /d "%~dp0\.."

echo.
echo   ============================================================
echo   * OPERADOR RL - MODELO 5000 EPISODIOS (v5000)
echo   ============================================================
echo.

REM 1. Validacao de Saude do Ambiente
echo   [CHECK] Verificando arquivo do modelo...

if not exist "data\models\novo_agente_rl\modelo_final\q_network.pkl" (
    if not exist "q_network.pkl" (
        echo   [FATAL] Arquivo q_network.pkl nao localizado.
        echo.
        pause
        exit /b 1
    )
)

echo.
echo   ============================================================
echo   VERSAO ATIVA: ANTI-OVERTRADING (BALANCED MODE)
echo   ============================================================
echo   - Max 5 trades/dia
echo   - Cooldown 5 min entre trades
echo   - Confirmacao multi-vela
echo   - Filtro volatilidade minima
echo   - Win rate target: 68 percent
echo   ============================================================
echo.

REM Se houver argumento na linha de comando, usar direto
if not "%1"=="" (
    set CHOICE=%1
    goto :PROCESS
)

REM Caso contrario, mostrar menu
:MENU
echo.
echo   [1] AVALIAR MODELO (Simulacao)
echo   [2] OPERAR MERCADO REAL (BALANCED) *** ATIVO ***
echo   [3] OPERAR MERCADO REAL (ORIGINAL - SEM PROTECAO)
echo   [4] Sair
echo.

set /p CHOICE="Escolha: "

:PROCESS

if "%CHOICE%"=="1" (
    echo.
    echo   Avaliando modelo em simulacao...
    python scripts/treinar_novo_agente_rl.py --dados-reais --apenas-avaliar
    pause
    goto :MENU
)

if "%CHOICE%"=="2" (
    echo.
    echo   OPERACAO REAL COM ANTI-OVERTRADING (BALANCED).
    echo   Inicializando operador...
    python scripts/operar_novo_agente_rl_real_antiovertrading.py
    pause
    goto :MENU
)

if "%CHOICE%"=="3" (
    echo.
    echo   *** AVISO: Versao ORIGINAL (SEM protecao anti-overtrading) ***
    echo.
    echo   OPERACAO REAL ATIVADA. ALVO: R$ 140,00.
    python scripts/operar_novo_agente_rl_real.py
    pause
    goto :MENU
)

if "%CHOICE%"=="4" exit /b 0

echo.
echo   Opcao invalida. Tente novamente.
echo.
goto :MENU
