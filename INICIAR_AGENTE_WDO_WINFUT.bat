@echo off
REM =========================================================
REM  Agente WDO/WINFUT Macro Score — Execucao Unica
REM
REM  Produz pontuacoes independentes para:
REM    - WDO  (Dolar Futuro / USDBRL)
REM    - WINFUT (Ibovespa Futuro)
REM =========================================================

title Agente WDO/WINFUT Macro Score

cd /d "%~dp0"

echo.
echo ========================================
echo   AGENTE WDO/WINFUT MACRO SCORE
echo   %date% %time%
echo ========================================
echo.

REM Ativa virtual env se existir
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

python scripts\run_agente_wdo_winfut.py --config "docs\model_agente\wdo_winfut\config_wdo_winfut.json"

echo.
echo Pressione qualquer tecla para fechar...
pause > nul
