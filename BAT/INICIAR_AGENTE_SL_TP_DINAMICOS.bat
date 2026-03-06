@echo off
REM Launcher para Operador RL v5000 com SL/TP DINAMICOS
REM Data: 06/03/2026
REM Funcionalidades:
REM   - Anti-overtrading (7 filtros de protecao)
REM   - SL/TP dinamicos baseados em ultimos topos/fundos
REM   - Calculo automatico de Risk/Reward minimo (1.5:1)
REM   - Rastreamento de progresso em tempo real
REM   - BALANCED MODE (sem limites diarios artificiais)

setlocal enabledelayedexpansion

cd /d "%~dp0\.."

cls
echo.
echo =====================================================================
echo   OPERADOR RL v5000 - SL/TP DINAMICOS
echo =====================================================================
echo.
echo Funcionalidades Ativas:
echo   [OK] Anti-overtrading (7 filtros)
echo   [OK] SL/TP dinamicos (topos/fundos)
echo   [OK] Risk/Reward validado (1.5:1 minimo)
echo   [OK] Rastreamento de progresso
echo   [OK] BALANCED MODE (ilimitado)
echo.
echo Alvo: R$140.00
echo Stop Loss: -R$250.00
echo.
echo =====================================================================
echo.

REM Usar timeout de 5s, se nao conseguir conectar MT5 vai falhar rapidinho
python scripts/operar_novo_agente_rl_real_antiovertrading.py

if errorlevel 1 (
    echo.
    echo =====================================================================
    echo   ERRO: Operador encerrou com mensagem de erro.
    echo =====================================================================
    echo.
    echo Verifique:
    echo   1. MT5 esta aberto?
    echo   2. Terminal Clear Investimentos conectado?
    echo   3. Ha posicao aberta? Se sim, feche antes de iniciar novo trade.
    echo   4. Modelo esta treinado em data\models\novo_agente_rl\modelo_final?
    echo.
    pause
) else (
    echo.
    echo =====================================================================
    echo   Operador finalizou normalmente.
    echo =====================================================================
    echo.
    pause
)

endlocal
