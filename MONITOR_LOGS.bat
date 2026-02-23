@echo off
REM =====================================================
REM  MONITOR DE LOGS - Operador Day Trade WIN
REM  Foco nos logs detalhados do sistema
REM =====================================================

setlocal enabledelayedexpansion
chcp 65001 >nul

title Monitor de Logs - Operador Day Trade WIN
color 0F

cls
echo.
echo =====================================================
echo   MONITOR DE LOGS - OPERADOR DAY TRADE WIN
echo =====================================================
echo.
echo Conectando ao stream de logs...
echo.

REM Verifica se arquivo de log existe
if not exist "logs\deployment_stage1.log" (
    echo [AVISO] Arquivo de log nao encontrado ainda.
    echo Aguardando criacao...
    timeout /t 3
)

REM Monitora logs em tempo real
powershell -Command "Get-Content 'logs\deployment_stage1.log' -Tail 100 -Wait | ForEach-Object { $('[' + (Get-Date -Format 'HH:mm:ss') + '] ' + $_) }"

pause
