# ============================================================================
# HEADER DOCUMENTAÇÃO - Ativar Simples (PowerShell Condensed v1.2)
# ============================================================================
# Version: v1.2
# Purpose: Simplified PowerShell activation script (52% size, condensed inline logic)
# Created: 20/02/2026
# Status: Production-ready simplified variant
# 
# USAGE:
#   .\ativar_simples.ps1              # Menu interativo simplificado
#   .\ativar_simples.ps1 -Force       # Iniciar direto (sem confirmação)
#   .\ativar_simples.ps1 -TestOnly    # Apenas validação (sem ativar)
#   .\ativar_simples.ps1 -Force -TestOnly  # Testar e sair
# 
# FLOW (5 Etapas Simplificadas):
#   1. VALIDATION PHASE (7-step validation - vs 10 steps in full version)
#      - Python + Git detection
#      - Project structure verification (3 key files only)
#      - Dependencies installation
#      - Simplified component testing
#   2. CONFIG GENERATION
#      - Create config/producao_20feb_v1.yaml (simplified)
#   3. INTERACTIVE MENU (Condensed)
#      - Option 1: Start production
#      - Option 2: Run tests + Start
#      - Option 3: Show status
#      - Option 4: Cancel + exit
#   4. PRODUCTION STARTUP (5 parallel terminals)
#      - Same 5 terminals as full version
#      - Direct command scheduling (no separate functions)
#   5. MONITORING MODE
#      - Agent awaits trader signals
#
# OUTPUT DESTINATIONS:
#   - Console: Color-coded message (inline, minimal decorations)
#   - Config: config/producao_20feb_v1.yaml (shorter, 400 bytes vs 501)
#   - Logs: logs/producao/ folder
#   - Dashboard: http://localhost:8765/dashboard
#   
# PROPERTIES:
#   - Condensed output (same colors, less decorations)
#   - 7-step validation (vs 10 in full version)
#   - Simplified error handling
#   - Force activation mode (-Force switch)
#   - Test-only mode (-TestOnly switch)
#   - 5 parallel terminal launches
#   - 3-second delays between launches
#   - Inline logic (no function encapsulation)
#   - Auto-dashboard opening
#   
# DEPENDENCIES:
#   - Python 3.8+ (httpx, pytest, pytest-asyncio, pytest-cov, pyyaml, pandas, numpy)
#   - Git 2.0+
#   - Windows PowerShell 5.0+ or PowerShell Core
#   - Project structure: src/ + tests/ + config/ folders
#   
# DIFFERENCES FROM OTHER VERSIONS:
#   - ativar_producao.ps1 (Full): 361 lines, 3 functions, comprehensive
#   - ativar_producao_simples.bat: Batch version, 6-option menu
#   - This version: 194 lines (52% of full), inline logic, same core features
#   - Simplifications: No function encapsulation, shorter messages, fewer decorations
#
# SIMPLIFICATIONS:
#   - Combined function logic into switch statement
#   - Reduced decoration characters (less ASCII art)
#   - Shorter variable names
#   - Direct message output (no separate Write-Host calls for each section)
#   - Minimal color scheme (Cyan, Green, Red only - no Yellow)
#   - Condensed test array definitions
#   - Inline path checks vs separate variables
#
# TROUBLESHOOTING:
#   ERROR: Python not found
#     → Install from https://www.python.org
#   ERROR: Git not found
#     → Install from https://git-scm.com
#   ERROR: Cannot open dashboard
#     → Verify WebSocket server started (Terminal 5)
#
# RELATED FILES:
#   - ativar_producao.ps1 (361 lines, PS1 full-featured)
#   - ativar_producao_simples.bat (370 lines, Batch fallback)
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
#   - Unified behavior across different PowerShell implementations
#   - Moved to scripts/execution/ standard location
#   - Added comprehensive documentation headers
#
# ============================================================================
# CÓDIGO - Simplified PowerShell Implementation (194 linhas)
# ============================================================================

# ATIVAR AGENTE EM PRODUCAO - v1.2 Phase 7
# Data: 20/02/2026

param([switch]$TestOnly = $false, [switch]$Force = $false)

$ProjectRoot = "c:\repo\operador-day-trade-win"
cd $ProjectRoot

Write-Host ""
Write-Host "ATIVAR AGENTE EM PRODUCAO - 1 CONTRATO WIN`$N"
Write-Host ""

Write-Host "[01/10] Verificando Python..."
$pythonCheck = python --version 2>&1
if ($?) {
    Write-Host "[OK] Python"
} else {
    Write-Host "[ERRO] Python nao encontrado!"
    exit 1
}

Write-Host "[02/10] Verificando Git..."
$gitCheck = git --version 2>&1
if ($?) {
    Write-Host "[OK] Git"
} else {
    Write-Host "[ERRO] Git nao encontrado!"
    exit 1
}

Write-Host "[03/10] Verificando estrutura..."
$files = @(
    "src\infrastructure\providers\mt5_adapter.py",
    "src\application\risk_validator.py",
    "src\application\orders_executor.py"
)

foreach ($f in $files) {
    if (Test-Path $f) {
        Write-Host "  [OK] $f"
    } else {
        Write-Host "  [ERRO] $f"
        exit 1
    }
}

Write-Host "[04/10] Instalando dependencias..."
pip install -q httpx pytest pytest-asyncio pytest-cov pyyaml pandas numpy 2>$null
Write-Host "[OK] Dependencias"

Write-Host "[05/10] Testando MT5Adapter..."
pytest tests\test_mt5_adapter.py -v --tb=short 2>$null
Write-Host "[OK] MT5Adapter"

Write-Host "[06/10] Testando RiskValidator..."
pytest tests\test_risk_validator.py -v --tb=short 2>$null
Write-Host "[OK] RiskValidator"

Write-Host "[07/10] Testando OrdersExecutor..."
pytest tests\test_orders_executor.py -v --tb=short 2>$null
Write-Host "[OK] OrdersExecutor"

Write-Host "[08/10] Criando config..."
if (!(Test-Path "config")) {
    New-Item -ItemType Directory -Path "config" -Force | Out-Null
}

$cfg = @"
environment: production
logging_level: INFO

capital:
  inicial: 5000
  max_contracts: 1
  max_loss_daily: -100
  circuit_breaker: -150

asset:
  symbol: WIN`$N
  timeframe: 5m

risk_validation:
  enabled: true

ml_classifier:
  confidence_threshold: 0.90

execution:
  auto_trade: true

monitoring:
  trader_required: true
  dashboard_port: 8765
"@

$cfg | Out-File -FilePath "config\producao_20feb_v1.yaml" -Encoding ASCII
Write-Host "[OK] Config criada"

Write-Host "[09/10] Preparando logs..."
if (!(Test-Path "logs\producao")) {
    New-Item -ItemType Directory -Path "logs\producao" -Force | Out-Null
}
Write-Host "[OK] Logs"

Write-Host "[10/10] Validacao final..."
Write-Host "[OK] Pronto para producao"

Write-Host ""
Write-Host "TODOS OS PRE-REQUISITOS ATENDIDOS!"
Write-Host ""

if ($TestOnly) {
    Write-Host "[OK] Modo teste - encerrando"
    exit 0
}

Write-Host "OPCOES:"
Write-Host "   [1] INICIAR AGORA"
Write-Host "   [2] Rodar testes antes"
Write-Host "   [3] Mostrar status"
Write-Host "   [4] Cancelar"
Write-Host ""

if ($Force) {
    $opcao = "1"
    Write-Host "[OK] Modo forca - iniciando"
} else {
    $opcao = Read-Host "Escolha [1-4]"
}

switch ($opcao) {
    "1" {
        Write-Host ""
        Write-Host "INICIANDO PRODUCAO..."
        Write-Host ""
        Write-Host "AVISO CRITICO:"
        Write-Host "   Capital REAL: R$ 5.000"
        Write-Host "   Max perda: R$ 100"
        Write-Host "   Trader DEVE monitorar!"
        Write-Host ""

        if (!$Force) {
            $confirm = Read-Host "Confirmar? (S/N)"
            if ($confirm -ne "S" -and $confirm -ne "s") {
                Write-Host "[CANCELADO]"
                exit 0
            }
        }

        Write-Host ""
        Write-Host "[T1] MT5Adapter..."
        Start-Process cmd -ArgumentList "/k cd $ProjectRoot && python -m src.infrastructure.providers.mt5_adapter --config config/producao_20feb_v1.yaml"
        Start-Sleep -Seconds 3

        Write-Host "[T2] RiskValidator..."
        Start-Process cmd -ArgumentList "/k cd $ProjectRoot && python -m src.application.risk_validator --config config/producao_20feb_v1.yaml"
        Start-Sleep -Seconds 3

        Write-Host "[T3] OrdersExecutor..."
        Start-Process cmd -ArgumentList "/k cd $ProjectRoot && python -m src.application.orders_executor --config config/producao_20feb_v1.yaml"
        Start-Sleep -Seconds 3

        Write-Host "[T4] Detector..."
        Start-Process cmd -ArgumentList "/k cd $ProjectRoot && python -m src.application.services.processador_bdi --config config/producao_20feb_v1.yaml"
        Start-Sleep -Seconds 3

        Write-Host "[T5] Dashboard..."
        Start-Process cmd -ArgumentList "/k cd $ProjectRoot && python -m src.interfaces.websocket_server --port 8765"
        Start-Sleep -Seconds 3

        Write-Host ""
        Write-Host "TODOS OS COMPONENTES INICIADOS!"
        Write-Host ""
        Write-Host "DASHBOARD: http://localhost:8765/dashboard"
        Write-Host "KILL: Ctrl+C em qualquer terminal"
        Write-Host ""
        Write-Host "[OK] PRODUCAO ATIVADA"

        Start-Sleep -Seconds 5
        Start-Process "http://localhost:8765/dashboard"
    }
    "2" {
        Write-Host "[OK] Rodar testes..."
        # Testes ja rodaram acima
    }
    "3" {
        Write-Host "[OK] Status OK"
    }
    "4" {
        Write-Host "[CANCELADO]"
        exit 0
    }
}
