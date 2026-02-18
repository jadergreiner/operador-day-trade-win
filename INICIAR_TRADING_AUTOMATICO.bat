@echo off
REM OPERADOR QUANTICO - TRADING AUTOMATIZADO
REM
REM AVISO IMPORTANTE:
REM Este sistema executa ordens REAIS no MetaTrader 5
REM Dinheiro REAL esta em risco
REM
REM Certifique-se de:
REM 1. Configurar corretamente o .env
REM 2. Testar primeiro em conta DEMO
REM 3. Monitorar constantemente
REM 4. Ter estrategia de saida clara
REM

echo ================================================================================
echo OPERADOR QUANTICO - TRADING AUTOMATIZADO
echo ================================================================================
echo.
echo                            *** AVISO CRITICO ***
echo.
echo Este sistema vai executar ordens REAIS no MetaTrader 5!
echo Dinheiro REAL esta em risco!
echo.
echo Configuracao atual:
echo   - 1 contrato por vez
echo   - Risco: 2%% por trade
echo   - Confianca minima: 75%%
echo   - Alinhamento minimo: 75%%
echo.
echo ================================================================================
echo.

set /p confirm="Tem certeza que deseja iniciar? (digite SIM para confirmar): "

if /i not "%confirm%"=="SIM" (
    echo.
    echo Operacao cancelada.
    echo.
    pause
    exit /b
)

echo.
echo Iniciando sistema...
echo.

cd /d "%~dp0"

python scripts\run_automated_trading.py

pause
