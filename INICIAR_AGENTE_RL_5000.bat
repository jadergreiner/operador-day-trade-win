@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM  LAUNCHER: NOVO AGENTE RL (OPERACAO REAL 5000 EPISODIOS)
REM  Versao: 3.0 - SL/TP DINAMICOS + PROGRESSO REAL-TIME
REM  Data: 06/03/2026
REM ============================================================

cd /d "%~dp0\.."

echo.
echo   ============================================================
echo   OPERADOR RL v5000 - SL/TP DINAMICOS
echo   ============================================================
echo.

echo   [CHECK] Verificando arquivo do modelo...
REM Verificar em ambos os locais possiveis
if exist "data\models\novo_agente_rl\modelo_final\q_network.pkl" (
    echo   [OK] Arquivo encontrado em: data\models\novo_agente_rl\modelo_final\
) else if exist "..\operador-day-trade-win\data\models\novo_agente_rl\modelo_final\q_network.pkl" (
    echo   [OK] Arquivo encontrado em: ..\operador-day-trade-win\data\models\novo_agente_rl\modelo_final\
) else (
    echo   [FATAL] Arquivo q_network.pkl nao localizado em:
    echo     - data\models\novo_agente_rl\modelo_final\
    echo     - ..\operador-day-trade-win\data\models\novo_agente_rl\modelo_final\
    pause
    exit /b 1
)

echo.
echo   ============================================================
echo   NOVA VERSAO: ANTI-OVERTRADING + SL/TP DINAMICOS
echo   ============================================================
echo   [OK] Anti-overtrading (7 filtros de protecao)
echo   [OK] SL/TP dinamicos (analisa ultimos topos/fundos)
echo   [OK] Risk/Reward validado (1.5:1 minimo)
echo   [OK] Rastreamento de progresso em tempo real
echo   [OK] BALANCED MODE (ilimitado ate TARGET ou STOP LOSS)
echo   [OK] Cooldown 5 min entre trades
echo   [OK] Confirmacao multi-vela (2 candles)
echo   [OK] Filtro volatilidade minima (0.05 porcento)
echo   [OK] Win rate esperado: 65-68 porcento
echo   ============================================================
echo.
echo   Alvo: R$140.00 / Stop Loss: -R$250.00
echo.
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