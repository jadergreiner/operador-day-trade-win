@echo off
cd /d "%~dp0\.."
echo Iniciando OPERADOR BALANCED...
echo.
python scripts/operar_novo_agente_rl_real_antiovertrading.py
pause
