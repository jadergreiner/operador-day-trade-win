@echo off
REM ============================================================================
REM ATIVAR PRODUCAO - VERSAO ULTRA SIMPLES (Nao fecha!)
REM ============================================================================

setlocal enabledelayedexpansion

cls
echo.
echo ============================================================================
echo ATIVAR PRODUCAO - AGENTE QUANTICO
echo ============================================================================
echo.
echo Testando ambiente...
echo.

REM Mudar para o diretorio do script
cd /d "%~dp0"
echo Diretorio atual: %cd%
echo.

REM Teste 1: Python
echo [1/5] Verificando Python...
python --version
if errorlevel 1 (
    echo ERRO: Python nao encontrado!
    echo.
    echo SOLUCAO:
    echo 1. Instale Python de https://www.python.org
    echo 2. Marque "Add Python to PATH"
    echo 3. Reinicie este script
    echo.
) else (
    echo OK: Python encontrado
)

echo.

REM Teste 2: Git (opcional)
echo [2/5] Verificando Git...
git --version
if errorlevel 1 (
    echo AVISO: Git nao encontrado (e opcional)
) else (
    echo OK: Git encontrado
)

echo.

REM Teste 3: Estrutura do projeto
echo [3/5] Verificando estrutura do projeto...
if exist "src" (
    echo OK: Pasta src/ existe
) else (
    echo ERRO: Pasta src/ nao encontrada!
)

if exist "tests" (
    echo OK: Pasta tests/ existe
) else (
    echo ERRO: Pasta tests/ nao encontrada!
)

echo.

REM Teste 4: Criar pastas necessarias
echo [4/5] Criando pastas necessarias...
if not exist "config" mkdir config
if not exist "logs" mkdir logs
if not exist "logs\producao" mkdir logs\producao
echo OK: Pastas criadas

echo.

REM Teste 5: Criar arquivo de configuracao
echo [5/5] Criando arquivo de configuracao...
(
    echo # CONFIGURACAO PRODUCAO
    echo environment: production
    echo capital: 5000
    echo asset: WIN
) > config\producao_config.yaml
echo OK: Configuracao criada em config\producao_config.yaml

echo.
echo ============================================================================
echo RESUMO
echo ============================================================================
echo.
echo Status: PRONTO PARA INICIAR
echo.
echo Para iniciar o agente manualmente, execute:
echo.
echo   python -m src.application.services.processador_bdi
echo.
echo Pressione qualquer tecla para ver opcoes...
pause >nul

cls

echo.
echo ============================================================================
echo OPCOES
echo ============================================================================
echo.
echo [1] Iniciar Detector BDI
echo [2] Iniciar Risk Validator
echo [3] Ver Status do Sistema
echo [4] Ver Arquivo de Configuracao
echo [5] Sair
echo.
set /p OPCAO="Escolha [1-5]: "

if "%OPCAO%"=="1" goto INICIAR_BDI
if "%OPCAO%"=="2" goto INICIAR_RISK
if "%OPCAO%"=="3" goto STATUS
if "%OPCAO%"=="4" goto CONFIG
if "%OPCAO%"=="5" goto SAIR

echo Opcao invalida!
pause
goto :eof

:INICIAR_BDI
cls
echo Iniciando Detector BDI...
echo.
python -m src.application.services.processador_bdi --config config\producao_config.yaml
pause
goto :eof

:INICIAR_RISK
cls
echo Iniciando Risk Validator...
echo.
python -m src.application.risk_validator --config config\producao_config.yaml
pause
goto :eof

:STATUS
cls
echo Status do Sistema:
echo.
echo Diretorio: %cd%
echo Python:
python --version
echo.
echo Estrutura:
dir src tests config 2>nul || echo (Alguns diretorios podem estar faltando)
echo.
pause
goto :eof

:CONFIG
cls
echo Arquivo de Configuracao:
echo.
type config\producao_config.yaml 2>nul || echo (Arquivo nao existe)
echo.
pause
goto :eof

:SAIR
echo.
echo Ate logo!
echo.
timeout /t 1 /nobreak >nul
goto :eof
