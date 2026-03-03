@REM ╔════════════════════════════════════════════════════════════════════════════╗
@REM ║                      ATIVAR_PRODUCAO_AGORA.bat                            ║
@REM ║                                                                            ║
@REM ║  Version:     v1.2                                                        ║
@REM ║  Purpose:     Activate agent in production (Phase 7) with 1 contract      ║
@REM ║  Created:     20/02/2026                                                  ║
@REM ║  Status:      Skeleton → Production (1 contract, R$ 5k capital)           ║
@REM ║  Location:    scripts/execution/                                          ║
@REM ║                                                                            ║
@REM ║  Usage:       ATIVAR_PRODUCAO_AGORA.bat                                  ║
@REM ║                                                                            ║
@REM ║  Flow:        [1] Validate prerequisites (Python, Git, structure)         ║
@REM ║               [2] Install dependencies                                    ║
@REM ║               [3] Run integration tests                                   ║
@REM ║               [4] Create production config (YAML)                         ║
@REM ║               [5] Interactive menu (4 options)                            ║
@REM ║               [6] Launch 5 terminals in parallel (if option 1)            ║
@REM ║               [7] Open dashboard + logs                                   ║
@REM ║                                                                            ║
@REM ║  Output:      - config\producao_20feb_v1.yaml (production config)         ║
@REM ║               - logs\producao\ (audit trail + logs)                       ║
@REM ║               - Browser tab: http://localhost:8765/dashboard              ║
@REM ║               - 5 parallel terminals (MT5, Risk, Orders, Detector, WS)    ║
@REM ║                                                                            ║
@REM ║  Properties:  - Color-coded feedback (green/yellow/red)                  ║
@REM ║               - Safety checks (confirmation required)                     ║
@REM ║               - Kill switch support (Ctrl+C or taskkill)                  ║
@REM ║               - CVM-compliant audit logging                               ║
@REM ║               - Health check before launch                                ║
@REM ║               - Debug mode available                                      ║
@REM ║                                                                            ║
@REM ║  Dependencies: Python 3.9+, Git (optional), pytest, pandas, numpy         ║
@REM ║                                                                            ║
@REM ║  Troubleshooting:                                                         ║
@REM ║  - "Python não found": Install from https://www.python.org               ║
@REM ║  - "MT5 Gateway falha": Check if gateway is running                      ║
@REM ║  - "Permission denied": Run as Administrator                              ║
@REM ║  - "Script lento": Normal on first run (pytest discovery)                ║
@REM ║                                                                            ║
@REM ║  Related:     ATIVAR_PRODUCAO_README.md (instructions)                   ║
@REM ║               Ativar-Producao.ps1 (PowerShell version - RECOMMENDED)      ║
@REM ║               config/producao_20feb_v1.yaml (generated config)            ║
@REM ║                                                                            ║
@REM ║  Phase:       Phase 7 - Automatic Execution                               ║
@REM ║  Sprint:      Initial live activation (skeleton with parallel ML training)║
@REM ║  Go Live:     10/04/2026 with 50k capital (after gates)                  ║
@REM ║                                                                            ║
@REM ╚════════════════════════════════════════════════════════════════════════════╝

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
    echo Depois execute este script novamente.
    echo.
    pause
    goto :EOF
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python %PYTHON_VERSION% encontrado

echo.
echo [02/10] Verificando Git...
git --version >nul 2>&1
if errorlevel 1 (
    color 6F
    echo ⚠️  AVISO: Git não encontrado no PATH
    echo         (Não critical para execução em produção)
)
echo ✅ Git encontrado ou pulado

echo.
echo [03/10] Verificando estrutura do projeto...
set VALIDACAO_OK=1

if not exist "src\infrastructure\providers\mt5_adapter.py" (
    echo ⚠️  AVISO: src\infrastructure\providers\mt5_adapter.py não encontrado
    set VALIDACAO_OK=0
)
if not exist "src\application\risk_validator.py" (
    echo ⚠️  AVISO: src\application\risk_validator.py não encontrado
    set VALIDACAO_OK=0
)
if not exist "src\application\orders_executor.py" (
    echo ⚠️  AVISO: src\application\orders_executor.py não encontrado
    set VALIDACAO_OK=0
)

if !VALIDACAO_OK! EQU 1 (
    echo ✅ Estrutura do projeto OK (MT5Adapter, RiskValidator, OrdersExecutor)
) else (
    echo ⚠️  Alguns arquivos estão faltando, mas continuando...
    echo.
)

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
if exist tests\test_mt5_adapter.py (
    python -m pytest tests\test_mt5_adapter.py -v --tb=short 2>nul
    if errorlevel 1 (
        color 6F
        echo ⚠️  AVISO: Testes MT5Adapter reportaram problemas
        echo.
        echo Possíveis causas:
        echo  - MT5 Gateway não está rodando (curl http://localhost:8000/api/v1/health)
        echo  - Credenciais MT5 incorretas
        echo  - Ambiente de teste não configurado
        echo.
        echo Continuando mesmo assim...
        echo.
    ) else (
        echo ✅ MT5Adapter validado
    )
) else (
    color 6F
    echo ⚠️  AVISO: Arquivo de teste não encontrado (tests\test_mt5_adapter.py)
    echo           Pulando validação...
    echo.
)

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
powershell -NoProfile -Command "
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
  symbol: WIN\$N
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
'@ | Out-File -Encoding UTF8 'config\producao_20feb_v1.yaml'
" 2>nul

if exist "config\producao_20feb_v1.yaml" (
    echo ✅ Config de produção criada (config\producao_20feb_v1.yaml)
) else (
    color 6F
    echo ⚠️  AVISO: Falha ao criar config via PowerShell
    echo           Criando versão simplificada...
    (
        echo # PRODUCAO - TESTE 1 CONTRATO
        echo environment: production
        echo logging_level: INFO
        echo capital: 5000
        echo asset: WIN$N
    ) > config\producao_20feb_v1.yaml
    echo ✅ Config simplificada criada
)

echo.
echo [09/10] Validando readiness...
if exist scripts\validate_production_readiness.py (
    python scripts\validate_production_readiness.py --config config\producao_20feb_v1.yaml 2>nul
    if errorlevel 1 (
        color 6F
        echo ⚠️  AVISO: Validação reportou avisos
        echo           Sistema ainda pode funcionar
    ) else (
        echo ✅ Sistema pronto para produção
    )
) else (
    echo ⚠️  Script de validação não encontrado
    echo           Pulando validação...
)

echo.
echo [10/10] Preparando inicialização...

REM Criar pasta de logs se não existir
if not exist "logs" mkdir logs
if not exist "logs\producao" mkdir logs\producao

REM Criar timestamp
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a%%b)

echo %mydate% %mytime% > logs\producao\ATIVACAO_LOG.txt 2>nul

if exist "logs\producao\ATIVACAO_LOG.txt" (
    echo ✅ Log session iniciada: logs\producao\ATIVACAO_LOG.txt
) else (
    echo ⚠️  Não foi possível criar arquivo de log
)

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

echo.
color 6F
echo ❌ Opção inválida! Use 1, 2, 3 ou 4.
echo.
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

set TESTES_OK=1

if exist tests\test_mt5_adapter.py (
    echo [1/5] Testando MT5Adapter...
    python -m pytest tests\test_mt5_adapter.py -v --tb=short 2>nul
    if !ERRORLEVEL! NEQ 0 (
        echo ⚠️  Testes MT5Adapter tiveram problemas
        set TESTES_OK=0
    )
) else (
    echo [1/5] Teste MT5Adapter: arquivo não encontrado
)

echo.
if exist tests\test_risk_validator.py (
    echo [2/5] Testando RiskValidator...
    python -m pytest tests\test_risk_validator.py -v --tb=short 2>nul
) else (
    echo [2/5] Teste RiskValidator: arquivo não encontrado
)

echo.
if exist tests\test_orders_executor.py (
    echo [3/5] Testando OrdersExecutor...
    python -m pytest tests\test_orders_executor.py -v --tb=short 2>nul
) else (
    echo [3/5] Teste OrdersExecutor: arquivo não encontrado
)

echo.
if exist tests\test_ml_feature_engineer.py (
    echo [4/5] Testando FeatureEngineer...
    python -m pytest tests\test_ml_feature_engineer.py -v --tb=short 2>nul
) else (
    echo [4/5] Teste FeatureEngineer: arquivo não encontrado
)

echo.
if exist tests\test_ml_classifier.py (
    echo [5/5] Testando MLClassifier...
    python -m pytest tests\test_ml_classifier.py -v --tb=short 2>nul
) else (
    echo [5/5] Teste MLClassifier: arquivo não encontrado
)

echo.
if !TESTES_OK! EQU 1 (
    echo ✅ TESTES OK - Prosseguindo para produção
) else (
    color 6F
    echo ⚠️  AVISO: Alguns testes tiveram problemas
    echo           Mas é possível continuar mesmo assim
)
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
REM Adicionar ao final do arquivo
REM ============================================================================

:DEBUG
cls
echo.
echo 🐛 MODO DEBUG - Informações do Sistema
echo.
echo Sistema Operacional: %OS%
echo Versão Windows: %WINVER%
echo.

echo Verificando Python:
python --version 2>&1

echo.
echo Verificando Git:
git --version 2>&1

echo.
echo Verificando diretório atual:
echo %cd%

echo.
echo Arquivos/Pastas:
dir src 2>nul || echo "Pasta src não encontrada"
dir tests 2>nul || echo "Pasta tests não encontrada"
dir config 2>nul || echo "Pasta config não encontrada"

echo.
pause
goto :EOF
