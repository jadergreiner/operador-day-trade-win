@echo off
chcp 1252 > nul
setlocal enabledelayedexpansion

REM ============================================================================
REM INICIAR AGENTE MICRO TENDENCIA AUTO TRADE (Background)
REM ============================================================================
REM Versao: 06/03/2026
REM P0-URGENT-1: Inactivity Penalty System INTEGRADO
REM
REM Executa agent em background com logging automatico
REM ============================================================================

echo.
echo ==============================================================================
echo  AGENTE MICRO TENDENCIA AUTO TRADE - Day Trade B3
echo ==============================================================================
echo.
echo  Status:    INICIANDO EM BACKGROUND
echo  Modo:      AUTO TRADE (P0-URGENT-1 inactivity penalty)
echo  Ciclo:     2 minutos
echo  Horario:   09:00-17:55 BRT
echo  Simbolo:   WIN$N
echo.

set PYTHON_EXE=C:\Users\Usuario\AppData\Local\Programs\Python\Python311\python.exe

if not exist "%PYTHON_EXE%" (
    echo ERRO: Python nao encontrado
    echo Corrija o caminho em PYTHON_EXE
    pause
    exit /b 1
)

cd /d "%~dp0.."

REM Gerar timestamp para log
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a%%b)

set LOGFILE=outputs\agent_auto_trade_!mydate!_!mytime!.log
set ENV_ENCODING=PYTHONIOENCODING=utf-8

REM Iniciar em background usando PowerShell
powershell -Command "$env:PYTHONIOENCODING='utf-8'; $process = Start-Process python -ArgumentList 'scripts/agente_micro_tendencia_winfut.py' -RedirectStandardOutput '%LOGFILE%' -PassThru -NoNewWindow; Write-Host 'Agent iniciado (PID: ' $process.Id ')'; Write-Host 'Logs: %LOGFILE%'"

echo.
echo ==============================================================================
echo  CONFIRMACAO
echo ==============================================================================
echo.
echo  Status:   Agent em execucao
echo  Log:      %LOGFILE%
echo.
echo  Para monitorar em tempo real (PowerShell):
echo    Get-Content %LOGFILE% -Wait
echo.
echo  Para parar:
echo    Get-Process python ^| Stop-Process -Force
echo.
echo ==============================================================================
echo.

timeout /t 3 /nobreak
exit /b 0
