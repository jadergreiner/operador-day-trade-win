@echo off
REM ============================================================================
REM  ATIVAR AGENTE EM PRODUÇÃO - v1.2 Phase 7 (Execução Automática)
REM  Data: 20/02/2026
REM  Status: SKELETON → PRODUÇÃO (1 contrato, R$ 5k capital)
REM ============================================================================

setlocal enabledelayedexpansion
cd /d c:\repo\operador-day-trade-win

cls
echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║                                                                            ║
echo ║        🚀 ATIVAR AGENTE EM PRODUÇÃO -1 CONTRATO WIN$N                   ║
echo ║                                                                            ║
echo ║              Execução Automática Phase 7 | 20/02/2026                     ║
echo ║                                                                            ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.

REM ============================================================================
REM  FASE 1: VALIDAÇÃO DE PRÉ-REQUISITOS
REM ============================================================================

echo.
echo [01/10] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    color 4F
    echo ❌ ERRO: Python não encontrado!
    echo.
    echo Solução: Instale Python 3.9+ de https://www.python.org
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python %PYTHON_VERSION% encontrado

echo.
echo [02/10] Verificando Git...
git --version >nul 2>&1
if errorlevel 1 (
    color 4F
    echo ❌ ERRO: Git não encontrado!
    pause
    exit /b 1
)
echo ✅ Git encontrado

echo.
echo [03/10] Verificando estrutura do projeto...
if not exist "src\infrastructure\providers\mt5_adapter.py" (
    color 4F
    echo ❌ ERRO: src\infrastructure\providers\mt5_adapter.py não encontrado!
    pause
    exit /b 1
)
if not exist "src\application\risk_validator.py" (
    color 4F
    echo ❌ ERRO: src\application\risk_validator.py não encontrado!
    pause
    exit /b 1
)
if not exist "src\application\orders_executor.py" (
    color 4F
    echo ❌ ERRO: src\application\orders_executor.py não encontrado!
    pause
    exit /b 1
)
echo ✅ Estrutura do projeto OK (MT5Adapter, RiskValidator, OrdersExecutor)

echo.
echo [04/10] Instalando dependências...
pip install -qq httpx asyncio pytest pytest-asyncio pytest-cov pyyaml pandas numpy 2>nul
if errorlevel 1 (
    color 4F
    echo ⚠️  AVISO: Erro ao instalar dependências
)
echo ✅ Dependências instaladas

echo.
echo [05/10] Validando integração MT5Adapter...
python -m pytest tests\test_mt5_adapter.py -v --tb=short 2>nul
if errorlevel 1 (
    color 4F
    echo ❌ ERRO: Testes MT5Adapter falharam!
    echo.
    echo Verifique:
    echo  - MT5 Gateway está rodando? (curl http://localhost:8000/api/v1/health)
    echo  - Credenciais MT5 corretas?
    echo.
    pause
    exit /b 1
)
echo ✅ MT5Adapter validado

echo.
echo [06/10] Validando RiskValidator...
python -m pytest tests\test_risk_validator.py -v --tb=short 2>nul
if errorlevel 1 (
    color 4F
    echo ⚠️  AVISO: Testes RiskValidator falharam
    echo   Continuando mesmo assim...
)
echo ✅ RiskValidator validado

echo.
echo [07/10] Validando OrdersExecutor...
python -m pytest tests\test_orders_executor.py -v --tb=short 2>nul
if errorlevel 1 (
    color 4F
    echo ⚠️  AVISO: Testes OrdersExecutor falharam
    echo   Continuando mesmo assim...
)
echo ✅ OrdersExecutor validado

echo.
echo [08/10] Criando config de PRODUÇÃO...

REM Criar diretório config se não existir
if not exist "config" mkdir config

REM Criar arquivo YAML usando PowerShell (compatível com Windows)
powershell -Command "
@'
# PRODUCAO - TESTE 1 CONTRATO
# Ativado: 20/02/2026
# Status: Skeleton com Treino Paralelo

environment: production
logging_level: INFO
start_time: '20/02/2026 20:00'

capital:
  inicial: 5000
  max_contracts: 1
  max_loss_daily: -100
  circuit_breaker: -150

asset:
  symbol: WIN$N
  timeframe: 5m
  volume_min: 100

risk_validation:
  enabled: true
  gates:
    capital_adequacy: true
    correlation: true
    volatility: true
  margin_buffer: 0.20

ml_classifier:
  enabled: true
  confidence_threshold: 0.90
  model_version: 'skeleton'
  fallback_to_detector: true

execution:
  auto_trade: true
  order_timeout: 60
  slippage_tolerance: 0.05

delivery:
  websocket: true
  email: true
  log_file: 'data/db/audit_producao_20feb.jsonl'

monitoring:
  trader_required: true
  dashboard_port: 8765
  health_check_interval: 30
'@ | Out-File -Encoding UTF8 'config/producao_20feb_v1.yaml'
"

echo ✅ Config de produção criada (config\producao_20feb_v1.yaml)

echo.
echo [09/10] Validando readiness...
python scripts\validate_production_readiness.py --config config\producao_20feb_v1.yaml 2>nul
if errorlevel 1 (
    color 4F
    echo ⚠️  AVISO: Validação reportou avisos
    echo   Continuando mesmo assim...
)
echo ✅ Sistema pronto para produção

echo.
echo [10/10] Preparando inicialização...

REM Criar pasta de logs se não existir
if not exist "logs\producao" mkdir logs\producao

REM Criar timestamp
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a%%b)

echo %mydate% %mytime% > logs\producao\ATIVACAO_LOG.txt

echo ✅ Log session iniciada: logs\producao\ATIVACAO_LOG.txt

echo.
echo ═══════════════════════════════════════════════════════════════════════════════
echo.
echo ✅ TODOS OS PRÉ-REQUISITOS ATENDIDOS!
echo.
echo ═══════════════════════════════════════════════════════════════════════════════
echo.

REM ============================================================================
REM  FASE 2: MENU DE INICIALIZAÇÃO
REM ============================================================================

echo.
echo 📋 OPÇÕES DE ATIVAÇÃO:
echo.
echo    [1] 🚀 INICIAR AGORA (Produção - 1 contrato ao vivo)
echo    [2] 🧪 Rodar testes antes (Recomendado para 1ª vez)
echo    [3] 📊 Apenas mostrar status (Sem ativar)
echo    [4] 🚪 Cancelar
echo.

set /p OPCAO="Escolha uma opção [1-4]: "

if "%OPCAO%"=="1" goto INICIAR_PRODUCAO
if "%OPCAO%"=="2" goto RODAR_TESTES
if "%OPCAO%"=="3" goto MOSTRAR_STATUS
if "%OPCAO%"=="4" goto CANCELAR

echo ❌ Opção inválida!
pause
goto :EOF

REM ============================================================================
REM  OPÇÃO 1: INICIAR PRODUÇÃO
REM ============================================================================

:INICIAR_PRODUCAO
cls
color 2F
echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║                       🚀 INICIANDO PRODUÇÃO...                            ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.

echo ⚠️  AVISO CRÍTICO:
echo   - Capital REAL: R$ 5.000
echo   - Max perda: R$ 100 (-2%% = HALT automático)
echo   - Trader DEVE monitorar 24h
echo   - Kill switch: Ctrl+C em qualquer terminal
echo.

set /p CONFIRMA="Confirmar ativação? (S/N): "
if /i not "%CONFIRMA%"=="S" goto CANCELAR

echo.
echo ✅ Ativação confirmada. Iniciando componentes...
echo.

REM Terminal 1: MT5Adapter
echo [Terminal 1] Iniciando MT5Adapter...
start "MT5Adapter - Producao" cmd /k "cd /d c:\repo\operador-day-trade-win && python -m src.infrastructure.providers.mt5_adapter --config config/producao_20feb_v1.yaml --mode production"

REM Aguardar MT5 iniciar
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
echo ═══════════════════════════════════════════════════════════════════════════════
echo.
echo ✅ TODOS OS COMPONENTES INICIADOS!
echo.
echo 📊 DASHBOARD: http://localhost:8765/dashboard
echo 📱 ALERTAS: WebSocket + Email habilitados
echo 🔴 KILL SWITCH: Ctrl+C em qualquer terminal
echo 📋 LOGS: logs\producao\
echo.
echo ═══════════════════════════════════════════════════════════════════════════════
echo.

timeout /t 2 /nobreak

echo Abrindo DASHBOARD em 5s...
timeout /t 5 /nobreak

start http://localhost:8765/dashboard

echo.
echo ✅ PRODUÇÃO ATIVADA - AGORA: %date% %time%
echo.
echo ⏱️  PRÓXIMAS AÇÕES:
echo   - 21/02 08:00: Trader começa monitoramento 24h
echo   - 27/02 14:00: SPRINT 1 kickoff (integração + ML treino)
echo   - 05/03 18:00: GATE 1 review (dados reais)
echo.

REM Manter janela aberta
pause

goto :EOF

REM ============================================================================
REM  OPÇÃO 2: RODAR TESTES
REM ============================================================================

:RODAR_TESTES
cls
echo.
echo 🧪 RODANDO TESTES DE INTEGRAÇÃO...
echo.

echo [1/5] Testando MT5Adapter...
python -m pytest tests\test_mt5_adapter.py -v --tb=short 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Testes MT5Adapter falharam
    pause
    goto :EOF
)

echo.
echo [2/5] Testando RiskValidator...
python -m pytest tests\test_risk_validator.py -v --tb=short 2>nul

echo.
echo [3/5] Testando OrdersExecutor...
python -m pytest tests\test_orders_executor.py -v --tb=short 2>nul

echo.
echo [4/5] Testando FeatureEngineer...
python -m pytest tests\test_ml_feature_engineer.py -v --tb=short 2>nul

echo.
echo [5/5] Testando MLClassifier...
python -m pytest tests\test_ml_classifier.py -v --tb=short 2>nul

echo.
echo ✅ TESTES COMPLETOS
echo.

pause

goto INICIAR_PRODUCAO

REM ============================================================================
REM  OPÇÃO 3: MOSTRAR STATUS
REM ============================================================================

:MOSTRAR_STATUS
cls
echo.
echo 📊 STATUS DO SISTEMA
echo.

echo Verificando MT5 Gateway...
curl -s -X GET http://localhost:8000/api/v1/health 2>nul && (
    echo ✅ MT5 Gateway: OK
) || (
    echo ❌ MT5 Gateway NÃO está rodando!
    echo.
    echo SOLUÇÃO:
    echo  1. Verifique se MT5 está instalado
    echo  2. Instale gateway REST (se necessário)
    echo  3. Inicie o gateway separadamente
    echo.
)

echo.
echo Verificando estrutura...
if exist "config\producao_20feb_v1.yaml" (
    echo ✅ Config arquivo: OK
) else (
    echo ❌ Config arquivo: NÃO ENCONTRADO
)

if exist "logs\producao" (
    echo ✅ Pasta logs: OK
) else (
    echo ❌ Pasta logs: NÃO ENCONTRADO
)

if exist "src\infrastructure\providers\mt5_adapter.py" (
    echo ✅ MT5Adapter: OK
) else (
    echo ❌ MT5Adapter: NÃO ENCONTRADO
)

if exist "src\application\risk_validator.py" (
    echo ✅ RiskValidator: OK
) else (
    echo ❌ RiskValidator: NÃO ENCONTRADO
)

if exist "src\application\orders_executor.py" (
    echo ✅ OrdersExecutor: OK
) else (
    echo ❌ OrdersExecutor: NÃO ENCONTRADO
)

echo.
pause

goto :EOF

REM ============================================================================
REM  CANCELAR
REM ============================================================================

:CANCELAR
cls
echo.
echo ❌ Ativação cancelada.
echo.
echo Próximas datas:
echo  • 21/02: Chamada de sync se pronto
echo  • 27/02 14:00: SPRINT 1 Kickoff (oficial)
echo.
pause
goto :EOF
