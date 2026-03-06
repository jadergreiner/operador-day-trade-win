@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM  LAUNCHER: NOVO AGENTE RL (OPERACAO REAL 5000 EPISODIOS)
REM  Data: 06/03/2026 - v1.0.8 - ULTRA SAFE
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

:MENU
echo.
echo   [1] AVALIAR MODELO (Simulacao)
echo   [2] OPERAR MERCADO REAL (WINJ26)
echo   [3] Sair
echo.

set /p CHOICE="Escolha: "

if "%CHOICE%"=="1" (
    python scripts/treinar_novo_agente_rl.py --dados-reais --apenas-avaliar
    pause
    goto :MENU
)

if "%CHOICE%"=="2" (
    echo.
    echo   OPERACAO REAL ATIVADA. ALVO: R$ 140,00.
    python scripts/operar_novo_agente_rl_real.py
    pause
    goto :MENU
)

if "%CHOICE%"=="3" exit /b 0

echo Opcao invalida.
goto :MENU

