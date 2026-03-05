@echo off
REM AGENDA_LIMPEZA_DIARIA.bat
REM Agenda limpeza automática de ordens antigas no Windows Task Scheduler
REM Uso: AGENDA_LIMPEZA_DIARIA.bat [start|stop|status]

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0.."
set "PYTHON_SCRIPT=%SCRIPT_DIR%\scripts\cleanup_old_orders_scheduler.py"
set "TASK_NAME=P1-CORE-Limpeza-Ordens-Diarias"
set "TASK_DESCRIPTION=Limpeza automatica de ordens com mais de 7 dias no banco trading.db"
set "SCHEDULE_TIME=23:00"

echo ======================================================
echo  AGENDA DE LIMPEZA DIARIA - Order Queue P1-CORE
echo ======================================================
echo.

REM Verificar argumentos
if "%1"=="" (
    echo Uso: AGENDA_LIMPEZA_DIARIA.bat [start^|stop^|status]
    echo.
    echo  start  - Agenda limpeza diaria as 23:00
    echo  stop   - Remove limpeza do agenda
    echo  status - Verifica status da limpeza
    echo.
    echo Exemplo:
    echo  AGENDA_LIMPEZA_DIARIA.bat start
    echo.
    exit /b 1
)

if /i "%1"=="start" goto :start_scheduler
if /i "%1"=="stop" goto :stop_scheduler
if /i "%1"=="status" goto :check_status

echo erro: parametro invalido '%1'
exit /b 1

:start_scheduler
echo [INFO] Agendando limpeza diaria as %SCHEDULE_TIME%...
echo.

REM Criar comando de execucao
set "CMD=python ""%PYTHON_SCRIPT%"" --days 7 --backup"

REM Agendar tarefa (requer admin)
schtasks /create /tn "%TASK_NAME%" /tr "%CMD%" /sc daily /st %SCHEDULE_TIME% /f

if %ERRORLEVEL% equ 0 (
    echo [SUCESSO] Limpeza agendada com sucesso!
    echo.
    echo Detalhes:
    echo  Task Name:    %TASK_NAME%
    echo  Horário:      %SCHEDULE_TIME% (23:00)
    echo  Script:       %PYTHON_SCRIPT%
    echo  Parametros:   --days 7 --backup
    echo  Backup:       Automaticamente em data\db\backups\
    echo.
    echo Proximas Acoes:
    echo  1. Limpeza comeca automaticamente as 23:00 todos os dias
    echo  2. Backup criado antes da delecao (SAFE)
    echo  3. Integridade do banco validada pos-limpeza
    echo  4. Logs da execucao em console
    echo.
) else (
    echo [ERRO] Falha ao agendar. Requer permissoes de Administrador!
    echo.
    echo Solucao: Execute o prompt command como Administrador
    echo.
    exit /b 1
)

goto :end

:stop_scheduler
echo [INFO] Removendo limpeza do agenda...
echo.

schtasks /delete /tn "%TASK_NAME%" /f

if %ERRORLEVEL% equ 0 (
    echo [SUCESSO] Limpeza removida do agenda
    echo.
) else (
    echo [AVISO] Limpeza nao estava agendada ou erro de acesso
    echo.
)

goto :end

:check_status
echo [INFO] Verificando status da limpeza agendada...
echo.

schtasks /query /tn "%TASK_NAME%" /v /fo list

if %ERRORLEVEL% equ 0 (
    echo.
    echo [INFO] Limpeza esta agendada e ativa
) else (
    echo [INFO] Limpeza NAO esta agendada
)

echo.
goto :end

:end
echo.
echo ======================================================
echo  FIM
echo ======================================================
echo.

