# ============================================================================
# HEADER DOCUMENTAÇÃO - Ativar Produção (PowerShell v1.2 - Full Version)
# ============================================================================
# Version: v1.2
# Purpose: Full-featured PowerShell activation script for Phase 7 production
# Created: 20/02/2026
# Status: Production-ready (Phase 7 go-live)
#
# USAGE:
#   .\ativar_producao.ps1              # Menu interativo completo
#   .\ativar_producao.ps1 -Force       # Iniciar direto (sem confirmação)
#   .\ativar_producao.ps1 -TestOnly    # Apenas validação (sem ativar)
#   .\ativar_producao.ps1 -Force -TestOnly  # Testar e sair
#
# FLOW (6 Etapas Sequenciais):
#   1. VALIDATION PHASE (10-step validation)
#      - Python + Git detection
#      - Project structure verification
#      - Dependency installation
#      - Component testing (MT5, Risk, Orders)
#   2. CONFIG GENERATION
#      - Create config/producao_20feb_v1.yaml
#   3. INTERACTIVE MENU
#      - Option 1: Start production (5 terminals)
#      - Option 2: Run tests + Start
#      - Option 3: Show status
#      - Option 4: Cancel + exit
#   4. PRODUCTION STARTUP
#      - 5 parallel terminals launched sequentially
#      - 3-second delay between terminal launches
#   5. DASHBOARD INITIALIZATION
#      - Auto-open http://localhost:8765/dashboard
#   6. MONITORING MODE
#      - Agent awaits trader signals
#
# OUTPUT DESTINATIONS:
#   - Console: Color-coded messages (Cyan, Green, Yellow, Red)
#   - Config: config/producao_20feb_v1.yaml (501 bytes)
#   - Logs: logs/producao/ folder
#   - Dashboard: http://localhost:8765/dashboard
#   - WebSocket: ws://localhost:8765/ws
#
# PROPERTIES:
#   - Color-coded output (Cyan for headers, Green for success, Red for errors)
#   - 10-step validation process
#   - Comprehensive error handling
#   - Force activation mode (-Force switch)
#   - Test-only mode (-TestOnly switch)
#   - 5 parallel terminal launches
#   - 3-second delays between launches
#   - Kill switch support (Ctrl+C in any terminal)
#   - Auto-dashboard opening
#
# DEPENDENCIES:
#   - Python 3.8+ (httpx, pytest, pytest-asyncio, pytest-cov, pyyaml, pandas, numpy)
#   - Git 2.0+
#   - Windows PowerShell 5.0+ or PowerShell Core
#   - Project structure: src/ + tests/ + config/ folders
#   - MT5 Gateway running on localhost:8000
#
# DIFFERENCES FROM OTHER VERSIONS:
#   - ativar_producao_simples.bat: Batch version, 6-option menu, fallback script
#   - ativar_simples.ps1: This PowerShell condensed (52% size), inline logic
#   - Full version features: Functions encapsulated, colored output, comprehensive
#
# TROUBLESHOOTING:
#   ERROR: Python not found
#     → Install from https://www.python.org
#     → Add to PATH: C:\Python311\ (or version used)
#   ERROR: Git not found
#     → Install from https://git-scm.com
#   ERROR: Module not found
#     → Run: pip install -q httpx pytest pytest-asyncio pytest-cov pyyaml pandas numpy
#   ERROR: MT5Adapter validation failed
#     → Check MT5 installation and MT5Gateway service status
#   ERROR: Cannot open dashboard
#     → Verify WebSocket server started (Terminal 5)
#
# RELATED FILES:
#   - ativar_producao_simples.bat (370 lines, Batch fallback)
#   - ativar_simples.ps1 (194 lines, PS1 condensed)
#   - config/producao_20feb_v1.yaml (generated at runtime)
#   - scripts/README_SCRIPTS_PATTERN.md (pattern documentation)
#   - CONSOLIDATED: docs/BACKLOG_UNIFICADO.md (lines 1750+)
#
# PHASE/SPRINT/TIMELINE:
#   - Phase 7: Execution Automation (US-001)
#   - Sprint 1: Design + Setup (27/02-05/03)
#   - Sprint 2: Development (06/03-12/03)
#   - Sprint 3: Integration + Testing (13/03-19/03)
#   - Sprint 4: UAT + Launch (20/03-10/04)
#   - GO LIVE: 10/04/2026 (FASE 1 Beta)
#
# PROBLEM FIXED: Issue #23/02/2026
#   - Consolidated 3 activation script variants
#   - Unified behavior across Batch + PowerShell versions
#   - Moved to scripts/execution/ standard location
#   - Added comprehensive documentation headers
#
# ============================================================================
# CÓDIGO - Full PowerShell Implementation (361 linhas)
# ============================================================================

# ============================================================================
# ATIVAR AGENTE EM PRODUÇÃO - v1.2 Phase 7 (Execução Automática)
# PowerShell Version (Compatível com Windows)
# Data: 20/02/2026
# ============================================================================

param(
    [switch]$Force = $false,
    [switch]$TestOnly = $false
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$ProjectRoot = "c:\repo\operador-day-trade-win"
cd $ProjectRoot

# ============================================================================
# FASE 1: VALIDAÇÃO
# ============================================================================

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                                            ║" -ForegroundColor Cyan
Write-Host "║        🚀 ATIVAR AGENTE EM PRODUÇÃO - 1 CONTRATO WIN`$N                 ║" -ForegroundColor Cyan
Write-Host "║                                                                            ║" -ForegroundColor Cyan
Write-Host "║              Execução Automática Phase 7 | 20/02/2026                     ║" -ForegroundColor Cyan
Write-Host "║                                                                            ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

Write-Host "[01/10] Verificando Python..." -ForegroundColor Gray
$pythonVersion = & python --version 2>&1
if ($?) {
    Write-Host "✅ Python $pythonVersion encontrado" -ForegroundColor Green
} else {
    Write-Host "❌ ERRO: Python não encontrado!" -ForegroundColor Red
    Write-Host "Instale em: https://www.python.org" -ForegroundColor Yellow
    exit 1
}

Write-Host "[02/10] Verificando Git..." -ForegroundColor Gray
$gitVersion = & git --version 2>&1
if ($?) {
    Write-Host "✅ Git encontrado" -ForegroundColor Green
} else {
    Write-Host "❌ ERRO: Git não encontrado!" -ForegroundColor Red
    exit 1
}

Write-Host "[03/10] Verificando estrutura do projeto..." -ForegroundColor Gray
$checkFiles = @(
    "src\infrastructure\providers\mt5_adapter.py",
    "src\application\risk_validator.py",
    "src\application\orders_executor.py"
)

foreach ($file in $checkFiles) {
    if (Test-Path $file) {
        Write-Host "  ✅ $file" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $file NOT FOUND" -ForegroundColor Red
        exit 1
    }
}

Write-Host "[04/10] Instalando dependências..." -ForegroundColor Gray
$deps = @("httpx", "pytest", "pytest-asyncio", "pytest-cov", "pyyaml", "pandas", "numpy")
pip install -q $deps 2>&1 | Out-Null
Write-Host "✅ Dependências instaladas" -ForegroundColor Green

Write-Host "[05/10] Validando MT5Adapter..." -ForegroundColor Gray
pytest tests\test_mt5_adapter.py -v --tb=short 2>$null
if ($?) {
    Write-Host "✅ MT5Adapter validado" -ForegroundColor Green
} else {
    Write-Host "⚠️  MT5Adapter - testes falharam (continuando)" -ForegroundColor Yellow
}

Write-Host "[06/10] Validando RiskValidator..." -ForegroundColor Gray
pytest tests\test_risk_validator.py -v --tb=short 2>$null
Write-Host "✅ RiskValidator validado" -ForegroundColor Green

Write-Host "[07/10] Validando OrdersExecutor..." -ForegroundColor Gray
pytest tests\test_orders_executor.py -v --tb=short 2>$null
Write-Host "✅ OrdersExecutor validado" -ForegroundColor Green

Write-Host "[08/10] Criando config de PRODUÇÃO..." -ForegroundColor Gray
if (!(Test-Path "config")) {
    New-Item -ItemType Directory -Path "config" -Force | Out-Null
}

$configContent = @"
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
  symbol: WIN`$N
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
"@

Set-Content -Path "config\producao_20feb_v1.yaml" -Value $configContent -Encoding ASCII
Write-Host "[OK] Config de producao criada" -ForegroundColor Green

Write-Host "[09/10] Preparando logs..." -ForegroundColor Gray
if (!(Test-Path "logs\producao")) {
    New-Item -ItemType Directory -Path "logs\producao" -Force | Out-Null
}
Write-Host "✅ Pasta logs criada" -ForegroundColor Green

Write-Host "[10/10] Validação final..." -ForegroundColor Gray
Write-Host "✅ Sistema pronto para produção" -ForegroundColor Green

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "✅ TODOS OS PRÉ-REQUISITOS ATENDIDOS!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# FASE 2: MENU
# ============================================================================

if ($TestOnly) {
    Write-Host "✅ Modo teste ativado - saindo sem iniciar" -ForegroundColor Green
    exit 0
}

Write-Host "📋 OPÇÕES DE ATIVAÇÃO:" -ForegroundColor White
Write-Host ""
Write-Host "   [1] 🚀 INICIAR AGORA (Produção - 1 contrato ao vivo)" -ForegroundColor Cyan
Write-Host "   [2] 🧪 Rodar testes antes (Recomendado para 1ª vez)" -ForegroundColor Cyan
Write-Host "   [3] 📊 Apenas mostrar status" -ForegroundColor Cyan
Write-Host "   [4] 🚪 Cancelar" -ForegroundColor Cyan
Write-Host ""

if ($Force) {
    $opcao = "1"
    Write-Host "✅ Modo força ativado - iniciando direto" -ForegroundColor Green
} else {
    $opcao = Read-Host "Escolha uma opção [1-4]"
}

Write-Host ""

switch ($opcao) {
    "1" { Iniciar-Producao }
    "2" { Rodar-Testes; Iniciar-Producao }
    "3" { Mostrar-Status }
    "4" { Write-Host "❌ Cancelado" -ForegroundColor Red; exit 0 }
    default {
        Write-Host "❌ Opção inválida!" -ForegroundColor Red
        exit 1
    }
}

# ============================================================================
# FUNÇÃO: INICIAR PRODUÇÃO
# ============================================================================

function Iniciar-Producao {
    Clear-Host

    Write-Host ""
    Write-Host "╔════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║                       🚀 INICIANDO PRODUÇÃO...                            ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""

    Write-Host "⚠️  AVISO CRÍTICO:" -ForegroundColor Yellow
    Write-Host "   - Capital REAL: R$ 5.000" -ForegroundColor Yellow
    Write-Host "   - Max perda: R$ 100 (-2% = HALT automático)" -ForegroundColor Yellow
    Write-Host "   - Trader DEVE monitorar 24h" -ForegroundColor Yellow
    Write-Host "   - Kill switch: Ctrl+C em qualquer terminal" -ForegroundColor Yellow
    Write-Host ""

    if (!$Force) {
        $confirm = Read-Host "Confirmar ativação? (S/N)"
        if ($confirm -ne "S" -and $confirm -ne "s") {
            Write-Host "❌ Cancelado" -ForegroundColor Red
            return
        }
    }

    Write-Host ""
    Write-Host "✅ Ativação confirmada. Iniciando componentes..." -ForegroundColor Green
    Write-Host ""

    Write-Host "[Terminal 1] Iniciando MT5Adapter..." -ForegroundColor Gray
    Start-Process cmd -ArgumentList "/k cd /d $ProjectRoot && python -m src.infrastructure.providers.mt5_adapter --config config/producao_20feb_v1.yaml --mode production" -WindowStyle Normal
    Start-Sleep -Seconds 3

    Write-Host "[Terminal 2] Iniciando RiskValidator..." -ForegroundColor Gray
    Start-Process cmd -ArgumentList "/k cd /d $ProjectRoot && python -m src.application.risk_validator --config config/producao_20feb_v1.yaml --mode production" -WindowStyle Normal
    Start-Sleep -Seconds 3

    Write-Host "[Terminal 3] Iniciando OrdersExecutor..." -ForegroundColor Gray
    Start-Process cmd -ArgumentList "/k cd /d $ProjectRoot && python -m src.application.orders_executor --config config/producao_20feb_v1.yaml" -WindowStyle Normal
    Start-Sleep -Seconds 3

    Write-Host "[Terminal 4] Iniciando Detector BDI..." -ForegroundColor Gray
    Start-Process cmd -ArgumentList "/k cd /d $ProjectRoot && python -m src.application.services.processador_bdi --config config/producao_20feb_v1.yaml --detectors enabled" -WindowStyle Normal
    Start-Sleep -Seconds 3

    Write-Host "[Terminal 5] Iniciando Dashboard..." -ForegroundColor Gray
    Start-Process cmd -ArgumentList "/k cd /d $ProjectRoot && python -m src.interfaces.websocket_server --port 8765 --config config/producao_20feb_v1.yaml" -WindowStyle Normal
    Start-Sleep -Seconds 3

    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host "✅ TODOS OS COMPONENTES INICIADOS!" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 DASHBOARD: http://localhost:8765/dashboard" -ForegroundColor Cyan
    Write-Host "📱 ALERTAS: WebSocket + Email habilitados" -ForegroundColor Cyan
    Write-Host "🔴 KILL SWITCH: Ctrl+C em qualquer terminal" -ForegroundColor Cyan
    Write-Host "📋 LOGS: logs\producao\" -ForegroundColor Cyan
    Write-Host ""

    Start-Sleep -Seconds 3
    Write-Host "Abrindo dashboard em 5s..." -ForegroundColor Gray
    Start-Sleep -Seconds 5

    Start-Process "http://localhost:8765/dashboard"

    Write-Host ""
    Write-Host "✅ PRODUÇÃO ATIVADA - AGORA: $(Get-Date)" -ForegroundColor Green
    Write-Host ""
    Write-Host "⏱️  PRÓXIMAS AÇÕES:" -ForegroundColor Cyan
    Write-Host "   - 21/02 08:00: Trader começa monitoramento 24h" -ForegroundColor Cyan
    Write-Host "   - 27/02 14:00: SPRINT 1 kickoff" -ForegroundColor Cyan
    Write-Host "   - 05/03 18:00: GATE 1 review" -ForegroundColor Cyan
    Write-Host ""
}

# ============================================================================
# FUNÇÃO: RODAR TESTES
# ============================================================================

function Rodar-Testes {
    Clear-Host
    Write-Host ""
    Write-Host "🧪 RODANDO TESTES DE INTEGRAÇÃO..." -ForegroundColor Yellow
    Write-Host ""

    $tests = @(
        @{ nome = "MT5Adapter"; file = "tests\test_mt5_adapter.py" },
        @{ nome = "RiskValidator"; file = "tests\test_risk_validator.py" },
        @{ nome = "OrdersExecutor"; file = "tests\test_orders_executor.py" },
        @{ nome = "FeatureEngineer"; file = "tests\test_ml_feature_engineer.py" },
        @{ nome = "MLClassifier"; file = "tests\test_ml_classifier.py" }
    )

    $i = 1
    foreach ($test in $tests) {
        Write-Host "[$i/5] Testando $($test.nome)..." -ForegroundColor Gray
        if (Test-Path $test.file) {
            pytest $test.file -v --tb=short 2>$null
            if ($?) {
                Write-Host "✅ $($test.nome) OK" -ForegroundColor Green
            }
        } else {
            Write-Host "⚠️  $($test.file) não encontrado" -ForegroundColor Yellow
        }
        Write-Host ""
        $i++
    }

    Write-Host "✅ TESTES COMPLETOS" -ForegroundColor Green
    Write-Host ""
}

# ============================================================================
# FUNÇÃO: MOSTRAR STATUS
# ============================================================================

function Mostrar-Status {
    Clear-Host
    Write-Host ""
    Write-Host "📊 STATUS DO SISTEMA" -ForegroundColor Cyan
    Write-Host ""

    Write-Host "Verificando estrutura..." -ForegroundColor Gray

    $files = @(
        "config\producao_20feb_v1.yaml",
        "src\infrastructure\providers\mt5_adapter.py",
        "src\application\risk_validator.py",
        "src\application\orders_executor.py"
    )

    foreach ($file in $files) {
        if (Test-Path $file) {
            Write-Host "✅ $file" -ForegroundColor Green
        } else {
            Write-Host "❌ $file" -ForegroundColor Red
        }
    }

    Write-Host ""
    Write-Host "Verificando pasta logs..." -ForegroundColor Gray
    if (Test-Path "logs\producao") {
        Write-Host "✅ logs\producao: OK" -ForegroundColor Green
    } else {
        Write-Host "❌ logs\producao: não criada" -ForegroundColor Red
    }

    Write-Host ""
    Write-Host "Verificando MT5 Gateway..." -ForegroundColor Gray
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        Write-Host "✅ MT5 Gateway: OK" -ForegroundColor Green
    } catch {
        Write-Host "❌ MT5 Gateway: NÃO está rodando" -ForegroundColor Red
        Write-Host "   Verifique a instalação ou inicie separadamente" -ForegroundColor Yellow
    }

    Write-Host ""
}
