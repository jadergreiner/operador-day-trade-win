@echo off
REM =========================================================
REM  Agente WDO/WINFUT Macro Score — Loop Continuo
REM
REM  Executa a cada 5 minutos automaticamente.
REM  Ctrl+C para interromper.
REM =========================================================

title Agente WDO/WINFUT Loop (5 min)

cd /d "%~dp0"

echo.
echo ========================================
echo   AGENTE WDO/WINFUT — LOOP CONTINUO
echo   Intervalo: 5 minutos
echo   Ctrl+C para parar
echo ========================================
echo.

REM Ativa virtual env se existir
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

python scripts\run_agente_wdo_winfut.py --loop --interval 5 --config "docs\model_agente\wdo_winfut\config_wdo_winfut.json"

pause
