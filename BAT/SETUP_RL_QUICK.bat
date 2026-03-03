@echo off
REM ============================================================================
REM RL TRAINING - QUICK START
REM Instalação rápida de dependências + inicialização
REM ============================================================================

setlocal enabledelayedexpansion

cls
echo.
echo ============================================================================
echo   RL TRAINING - QUICK START
echo ============================================================================
echo.

REM Verificar Python
echo  Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   ❌ Python não encontrado!
    echo   Instale Python 3.11+ de python.org
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo   ✅ %PYTHON_VERSION%
echo.

REM Criar logs dir
echo   Criando diretórios...
if not exist "logs" mkdir logs
if not exist "data" mkdir data
if not exist "data\db" mkdir data\db
echo   ✅ Diretórios prontos
echo.

REM Verificar/Instalar APScheduler
echo  Verificando dependências...
pip list | find /I "apscheduler" >nul 2>&1
if %errorlevel% neq 0 (
    echo   ⚙️ Instalando APScheduler...
    pip install apscheduler -q
    if %errorlevel% neq 0 (
        echo   ❌ Erro ao instalar
        pause
        exit /b 1
    )
)
echo   ✅ APScheduler OK
echo.

REM Teste rápido
echo  Executando teste rápido...
python -c "from scripts.rl_training_scheduler import RLTrainingScheduler; print('   ✅ Imports OK')" 2>&1
if %errorlevel% neq 0 (
    echo   ❌ Erro nos imports
    pause
    exit /b 1
)
echo.

echo ============================================================================
echo   ✅ TUDO PRONTO!
echo ============================================================================
echo.
echo PRÓXIMOS PASSOS:
echo.
echo   1) INICIAR SCHEDULER (recomendado)
echo      .\INICIAR_RL_SCHEDULER.ps1
echo.
echo   2) OU TESTE RÁPIDO
echo      python scripts/rl_training_loop_v3.py
echo.
echo   3) VERIFICAR SAÚDE
echo      python scripts/rl_health_monitor.py
echo.
echo DOCUMENTAÇÃO:
echo   docs/RL_TRAINING_SCHEDULER_README.md
echo.
echo ============================================================================
echo.
pause
