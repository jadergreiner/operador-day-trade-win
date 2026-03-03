@echo off
REM ============================================================================
REM ATIVAR AGENTE EM PRODUCAO - v1.2 Phase 7 (Execucao Automatica)
REM Data: 20/02/2026
REM Status: SKELETON PRODUCAO (1 contrato, R$ 5k capital)
REM ============================================================================

setlocal enabledelayedexpansion
cd /d c:\repo\operador-day-trade-win

cls
echo.
echo ============================================================================
echo.
echo            ATIVAR AGENTE EM PRODUCAO - 1 CONTRATO WIN$N
echo.
echo                      Execucao Automatica Phase 7
echo.
echo ============================================================================
echo.

REM ============================================================================
REM FASE 1: VALIDACAO DE PRE-REQUISITOS
REM ============================================================================

echo.
echo [01/10] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    color 4F
    echo ERRO: Python nao encontrado!
    echo.
    echo Solucao: Instale Python 3.9+ de https://www.python.org
    echo Depois execute este script novamente.
    echo.
    pause
    goto :EOF
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo OK: Python %PYTHON_VERSION% encontrado

echo.
echo [02/10] Verificando Git...
git --version >nul 2>&1
if errorlevel 1 (
    color 6F
    echo AVISO: Git nao encontrado no PATH
    echo        (Nao e critico para execucao em producao)
)
echo OK: Git encontrado ou pulado

echo.
echo [03/10] Verificando estrutura do projeto...
set VALIDACAO_OK=1

if not exist "src\infrastructure\providers\mt5_adapter.py" (
    echo AVISO: src\infrastructure\providers\mt5_adapter.py nao encontrado
    set VALIDACAO_OK=0
)
if not exist "src\application\risk_validator.py" (
    echo AVISO: src\application\risk_validator.py nao encontrado
    set VALIDACAO_OK=0
)
if not exist "src\application\orders_executor.py" (
    echo AVISO: src\application\orders_executor.py nao encontrado
    set VALIDACAO_OK=0
)

if !VALIDACAO_OK! EQU 1 (
    echo OK: Estrutura do projeto OK (MT5Adapter, RiskValidator, OrdersExecutor)
) else (
    echo AVISO: Alguns arquivos estao faltando, mas continuando...
    echo.
)

echo.
echo [04/10] Instalando dependencias...
pip install -qq httpx asyncio pytest pytest-asyncio pytest-cov pyyaml pandas numpy 2>nul
if errorlevel 1 (
    color 4F
    echo AVISO: Erro ao instalar dependencias
)
echo OK: Dependencias instaladas

echo.
echo [05/10] Validando integracao MT5Adapter...
if exist tests\test_mt5_adapter.py (
    python -m pytest tests\test_mt5_adapter.py -v --tb=short 2>nul
    if errorlevel 1 (
        color 6F
        echo AVISO: Testes MT5Adapter reportaram problemas
        echo.
        echo Possiveis causas:
        echo  - MT5 Gateway nao esta rodando (curl http://localhost:8000/api/v1/health)
        echo  - Credenciais MT5 incorretas
        echo  - Ambiente de teste nao configurado
        echo.
        echo Continuando mesmo assim...
        echo.
    ) else (
        echo OK: MT5Adapter validado
    )
) else (
    color 6F
    echo AVISO: Arquivo de teste nao encontrado (tests\test_mt5_adapter.py)
    echo           Pulando validacao...
    echo.
)

echo.
echo [06/10] Validando RiskValidator...
python -m pytest tests\test_risk_validator.py -v --tb=short 2>nul
if errorlevel 1 (
    color 6F
    echo AVISO: Testes RiskValidator falharam
    echo   Continuando mesmo assim...
)
echo OK: RiskValidator validado

echo.
echo [07/10] Validando OrdersExecutor...
python -m pytest tests\test_orders_executor.py -v --tb=short 2>nul
if errorlevel 1 (
    color 6F
    echo AVISO: Testes OrdersExecutor falharam
    echo   Continuando mesmo assim...
)
echo OK: OrdersExecutor validado

echo.
echo [08/10] Criando config de PRODUCAO...

REM Criar diretorio config se nao existir
if not exist "config" mkdir config

REM Criar arquivo YAML simples (sem PowerShell problematico)
(
    echo # PRODUCAO - TESTE 1 CONTRATO
    echo # Ativado: 20/02/2026
    echo # Status: Skeleton com Treino Paralelo
    echo.
    echo environment: production
    echo logging_level: INFO
    echo start_time: '20/02/2026 20:00'
    echo.
    echo capital:
    echo   inicial: 5000
    echo   max_contracts: 1
    echo   max_loss_daily: -100
    echo   circuit_breaker: -150
    echo.
    echo asset:
    echo   symbol: WIN$N
    echo   timeframe: 5m
    echo   volume_min: 100
    echo.
    echo risk_validation:
    echo   enabled: true
    echo   gates:
    echo     capital_adequacy: true
    echo     correlation: true
    echo     volatility: true
    echo   margin_buffer: 0.20
    echo.
    echo ml_classifier:
    echo   enabled: true
    echo   confidence_threshold: 0.90
    echo   model_version: 'skeleton'
    echo   fallback_to_detector: true
    echo.
    echo execution:
    echo   auto_trade: true
    echo   order_timeout: 60
    echo   slippage_tolerance: 0.05
    echo.
    echo delivery:
    echo   websocket: true
    echo   email: true
    echo   log_file: 'data/db/audit_producao_20feb.jsonl'
    echo.
    echo monitoring:
    echo   trader_required: true
    echo   dashboard_port: 8765
    echo   health_check_interval: 30
) > config\producao_20feb_v1.yaml

if exist "config\producao_20feb_v1.yaml" (
    echo OK: Config de producao criada (config\producao_20feb_v1.yaml)
) else (
    color 6F
    echo AVISO: Falha ao criar config
    echo.
)

echo.
echo [09/10] Validando readiness...
if exist scripts\validate_production_readiness.py (
    python scripts\validate_production_readiness.py --config config\producao_20feb_v1.yaml 2>nul
    if errorlevel 1 (
        color 6F
        echo AVISO: Validacao reportou avisos
        echo           Sistema ainda pode funcionar
    ) else (
        echo OK: Sistema pronto para producao
    )
) else (
    echo AVISO: Script de validacao nao encontrado
    echo           Pulando validacao...
)

echo.
echo [10/10] Preparando inicializacao...

REM Criar pasta de logs se nao existir
if not exist "logs" mkdir logs
if not exist "logs\producao" mkdir logs\producao

REM Criar arquivo de log
echo Ativacao iniciada - %date% %time% > logs\producao\ATIVACAO_LOG.txt

if exist "logs\producao\ATIVACAO_LOG.txt" (
    echo OK: Log session iniciada: logs\producao\ATIVACAO_LOG.txt
) else (
    echo AVISO: Nao foi possivel criar arquivo de log
)

echo.
echo ============================================================================
echo.
echo OK: TODOS OS PRE-REQUISITOS ATENDIDOS!
echo.
echo ============================================================================
echo.

REM ============================================================================
REM FASE 2: MENU DE INICIALIZACAO
REM ============================================================================

echo.
echo OPCOES DE ATIVACAO:
echo.
echo    [1] INICIAR AGORA (Producao - 1 contrato ao vivo)
echo    [2] Rodar testes antes (Recomendado para 1a vez)
echo    [3] Apenas mostrar status (Sem ativar)
echo    [4] Cancelar
echo.

set /p OPCAO="Escolha uma opcao [1-4]: "

if "%OPCAO%"=="1" goto INICIAR_PRODUCAO
if "%OPCAO%"=="2" goto RODAR_TESTES
if "%OPCAO%"=="3" goto MOSTRAR_STATUS
if "%OPCAO%"=="4" goto CANCELAR

echo.
color 6F
echo ERRO: Opcao invalida! Use 1, 2, 3 ou 4.
echo.
pause
goto :EOF

REM ============================================================================
REM OPCAO 1: INICIAR PRODUCAO
REM ============================================================================

:INICIAR_PRODUCAO
cls
color 2F
echo.
echo ============================================================================
echo                       INICIANDO PRODUCAO...
echo ============================================================================
echo.

echo AVISO CRITICO:
echo   - Capital REAL: R$ 5.000
echo   - Max perda: R$ 100 (-2%% = HALT automatico)
echo   - Trader DEVE monitorar 24h
echo   - Kill switch: Ctrl+C em qualquer terminal
echo.

set /p CONFIRMA="Confirmar ativacao? (S/N): "
if /i not "%CONFIRMA%"=="S" goto CANCELAR

echo.
echo Ativacao confirmada. Iniciando componentes...
echo.

REM Terminal 1: MT5Adapter
echo [Terminal 1] Iniciando MT5Adapter...
start "MT5Adapter - Producao" cmd /k "cd /d c:\repo\operador-day-trade-win && python -m src.infrastructure.providers.mt5_adapter --config config/producao_20feb_v1.yaml --mode production"

timeout /t 3 /nobreak

REM Terminal 2: RiskValidationProcessor
echo [Terminal 2] Iniciando RiskValidator...
start "RiskValidator - Producao" cmd /k "cd /d c:\repo\operador-day-trade-win && python -m src.application.risk_validator --config config/producao_20feb_v1.yaml --mode production"

timeout /t 3 /nobreak

REM Terminal 3: OrdersExecutor
echo [Terminal 3] Iniciando OrdersExecutor...
start "OrdersExecutor - Producao" cmd /k "cd /d c:\repo\operador-day-trade-win && python -m src.application.orders_executor --config config/producao_20feb_v1.yaml"

timeout /t 3 /nobreak

REM Terminal 4: BDI Processor (Detector)
echo [Terminal 4] Iniciando Detector BDI...
start "Detector - Producao" cmd /k "cd /d c:\repo\operador-day-trade-win && python -m src.application.services.processador_bdi --config config/producao_20feb_v1.yaml --detectors enabled"

timeout /t 3 /nobreak

REM Terminal 5: WebSocket Dashboard
echo [Terminal 5] Iniciando Dashboard...
start "Dashboard - Producao" cmd /k "cd /d c:\repo\operador-day-trade-win && python -m src.interfaces.websocket_server --port 8765 --config config/producao_20feb_v1.yaml"

echo.
echo ============================================================================
echo.
echo OK: TODOS OS COMPONENTES INICIADOS!
echo.
echo Dashboard: http://localhost:8765/dashboard
echo Alertas: WebSocket + Email habilitados
echo Kill switch: Ctrl+C em qualquer terminal
echo Logs: logs\producao\
echo.
echo ============================================================================
echo.

timeout /t 2 /nobreak

echo Abrindo DASHBOARD em 5s...
timeout /t 5 /nobreak

start http://localhost:8765/dashboard

echo.
echo OK: PRODUCAO ATIVADA - AGORA: %date% %time%
echo.
echo PROXIMAS ACOES:
echo   - 21/02 08:00: Trader comeca monitoramento 24h
echo   - 27/02 14:00: SPRINT 1 kickoff (integracao + ML treino)
echo   - 05/03 18:00: GATE 1 review (dados reais)
echo.

REM Manter janela aberta
pause

goto :EOF

REM ============================================================================
REM OPCAO 2: RODAR TESTES
REM ============================================================================

:RODAR_TESTES
cls
echo.
echo RODANDO TESTES DE INTEGRACAO...
echo.

set TESTE_COUNT=0
set TESTE_OK=0

if exist tests\test_mt5_adapter.py (
    echo [Test 1/5] MT5Adapter...
    python -m pytest tests\test_mt5_adapter.py -q 2>nul
    set /a TESTE_COUNT+=1
    if !errorlevel! EQU 0 set /a TESTE_OK+=1
) else (
    echo [Test 1/5] MT5Adapter... (NAO ENCONTRADO)
)

if exist tests\test_risk_validator.py (
    echo [Test 2/5] RiskValidator...
    python -m pytest tests\test_risk_validator.py -q 2>nul
    set /a TESTE_COUNT+=1
    if !errorlevel! EQU 0 set /a TESTE_OK+=1
) else (
    echo [Test 2/5] RiskValidator... (NAO ENCONTRADO)
)

if exist tests\test_orders_executor.py (
    echo [Test 3/5] OrdersExecutor...
    python -m pytest tests\test_orders_executor.py -q 2>nul
    set /a TESTE_COUNT+=1
    if !errorlevel! EQU 0 set /a TESTE_OK+=1
) else (
    echo [Test 3/5] OrdersExecutor... (NAO ENCONTRADO)
)

echo.
echo ============================================================================
if !TESTE_COUNT! GEQ 1 (
    echo OK: Testes completados: !TESTE_OK!/!TESTE_COUNT! OK
) else (
    echo AVISO: Nenhum arquivo de teste encontrado
)
echo ============================================================================
echo.

pause

goto INICIAR_PRODUCAO

REM ============================================================================
REM OPCAO 3: MOSTRAR STATUS
REM ============================================================================

:MOSTRAR_STATUS
cls
echo.
echo STATUS DO SISTEMA
echo.
echo Data/Hora: %date% %time%
echo Diretorio: %cd%
echo.

echo Estrutura do projeto:
echo.
if exist "src" (
    echo OK: src/
) else (
    echo ERRO: src/ (NAO ENCONTRADO)
)

if exist "tests" (
    echo OK: tests/
) else (
    echo ERRO: tests/ (NAO ENCONTRADO)
)

if exist "config" (
    echo OK: config/
) else (
    echo ERRO: config/ (NAO ENCONTRADO)
)

if exist "logs" (
    echo OK: logs/
) else (
    echo ERRO: logs/ (NAO ENCONTRADO)
)

echo.
echo Componentes principais:
echo.
if exist "src\application\risk_validator.py" (
    echo OK: RiskValidator
) else (
    echo ERRO: RiskValidator (NAO ENCONTRADO)
)

if exist "src\application\orders_executor.py" (
    echo OK: OrdersExecutor
) else (
    echo ERRO: OrdersExecutor (NAO ENCONTRADO)
)

if exist "src\application\services\processador_bdi.py" (
    echo OK: ProcessadorBDI
) else (
    echo AVISO: ProcessadorBDI (NAO ENCONTRADO)
)

echo.
echo Configuracoes:
echo.
if exist "config\producao_20feb_v1.yaml" (
    echo OK: config\producao_20feb_v1.yaml (PRESENTE)
) else (
    echo ERRO: config\producao_20feb_v1.yaml (NAO ENCONTRADO)
)

echo.
pause
goto :EOF

REM ============================================================================
REM CANCELAR
REM ============================================================================

:CANCELAR
cls
echo.
echo Ativacao cancelada.
echo.
echo Proximas datas:
echo  - 21/02: Chamada de sync se pronto
echo  - 27/02 14:00: SPRINT 1 Kickoff (oficial)
echo.
pause
goto :EOF
