@echo off
REM ============================================================================
REM RL TRAINING SCHEDULER LAUNCHER - Windows
REM Inicia o scheduler de treinamento RL em background
REM ============================================================================

setlocal enabledelayedexpansion

echo.
echo ============================================================================
echo   RL TRAINING SCHEDULER LAUNCHER
echo ============================================================================
echo.

REM Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python não encontrado!
    echo    Instale Python 3.11+ antes de continuar
    pause
    exit /b 1
)

REM Verificar APScheduler
python -c "import apscheduler" >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ APScheduler não instalado!
    echo.
    echo Instalando dependências...
    pip install apscheduler
    if %errorlevel% neq 0 (
        echo ❌ Erro ao instalar APScheduler
        pause
        exit /b 1
    )
)

REM Criar logs dir
if not exist "logs" mkdir logs

echo ✅ Dependências verificadas
echo.

REM Menu
:menu
echo OPÇÕES:
echo.
echo   1) Iniciar scheduler (background)
echo   2) Executar uma vez (teste)
echo   3) Verificar saúde do modelo
echo   4) Ver jobs agendados
echo   5) Sair
echo.
set /p choice="Escolha uma opção [1-5]: "

if "%choice%"=="1" goto start_scheduler
if "%choice%"=="2" goto run_once
if "%choice%"=="3" goto check_health
if "%choice%"=="4" goto list_jobs
if "%choice%"=="5" goto exit
goto menu

:start_scheduler
echo.
echo 🚀 Iniciando scheduler em background...
echo    (Este console pode ser fechado)
echo.

REM Iniciar em background usando VBS
call :create_vbs_launcher "scripts\rl_training_scheduler.py"

timeout /t 2 /nobreak
goto menu

:run_once
echo.
echo 🔄 Executando treinamento uma vez...
echo.
python -c "from scripts.rl_training_scheduler import RLTrainingScheduler; s = RLTrainingScheduler(); s.run_once()"
if %errorlevel% equ 0 (
    echo.
    echo ✅ Treinamento completado!
) else (
    echo.
    echo ❌ Erro ao treinar
)
pause
goto menu

:check_health
echo.
echo 📊 Verificando saúde do modelo...
echo.
python scripts/rl_health_monitor.py
pause
goto menu

:list_jobs
echo.
echo 📋 Jobs Agendados:
echo.
python -c "from scripts.rl_training_scheduler import RLTrainingScheduler; s = RLTrainingScheduler(); s.show_jobs()"
pause
goto menu

:exit
echo.
echo 👋 Encerrando...
exit /b 0

:create_vbs_launcher
setlocal enabledelayedexpansion
set "py_script=%~1"

REM Criar VBS temporizador
(
    echo Set objWS = WScript.CreateObject("WScript.Shell"^)
    echo strPath = objWS.CurrentDirectory
    echo objWS.Run "python " ^& strPath ^& "\%py_script%", 0, False
) > start_scheduler_bg.vbs

cscript.exe //nologo start_scheduler_bg.vbs
del start_scheduler_bg.vbs
endlocal
exit /b 0
