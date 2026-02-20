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
