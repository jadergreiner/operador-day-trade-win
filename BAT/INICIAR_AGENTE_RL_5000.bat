@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM  LAUNCHER: NOVO AGENTE RL (OPERACAO REAL 5000 EPISODIOS)
REM  Versao: 2.0 - Corrigida para compatibilidade total
REM ============================================================

cd /d "%~dp0\.."

echo.
echo   ============================================================
echo   * OPERADOR RL - MODELO 5000 EPISODIOS (v5000)
echo   ============================================================
echo.

echo   [CHECK] Verificando arquivo do modelo...
if not exist "data\models\novo_agente_rl\modelo_final\q_network.pkl" (
    echo   [FATAL] Arquivo q_network.pkl nao localizado.
    pause
    exit /b 1
)

echo.
echo   ============================================================
echo   VERSAO ATIVA: ANTI-OVERTRADING (BALANCED MODE)
echo   ============================================================
echo   - Operacao livre ate TARGET ou STOP LOSS
echo   - Cooldown 5 min entre trades
echo   - Confirmacao multi-vela
echo   - Filtro volatilidade minima (0.05 porcento)
echo   - Win rate target: 68 porcento
echo   ============================================================
echo.

:MENU
echo.
echo   [1] AVALIAR MODELO (Simulacao)
echo   [2] OPERAR MERCADO REAL (BALANCED) *** ATIVO ***
echo   [3] OPERAR MERCADO REAL (ORIGINAL - SEM PROTECAO)
echo   [4] Sair
echo.

set /p CHOICE="Escolha (1-4): "

if "%CHOICE%"=="1" (
    echo.
    echo   Iniciando avaliacao do modelo...
    python scripts/treinar_novo_agente_rl.py --dados-reais --apenas-avaliar
    if errorlevel 1 echo. & echo   [ERRO] Avaliacao falhou. & pause
    goto :MENU
)

if "%CHOICE%"=="2" (
    echo.
    echo   [START] OPERACAO REAL COM ANTI-OVERTRADING (BALANCED MODE)
    echo   Objetivo: Lucro R$ 140,00 ou Prejuizo -R$ 250,00
    echo.
    python scripts/operar_novo_agente_rl_real_antiovertrading.py
    echo.
    echo   [INFO] Operacao encerrada.
    pause
    goto :MENU
)

if "%CHOICE%"=="3" (
    echo.
    echo   [AVISO] Versao ORIGINAL (SEM protecao anti-overtrading)
    echo   Objetivo: Lucro R$ 140,00 ou Prejuizo -R$ 250,00
    echo.
    python scripts/operar_novo_agente_rl_real.py
    echo.
    echo   [INFO] Operacao encerrada.
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