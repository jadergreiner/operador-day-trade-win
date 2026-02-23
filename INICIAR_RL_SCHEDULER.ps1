# ============================================================================
# RL TRAINING SCHEDULER - PowerShell Launcher (Windows Modern)
# ============================================================================

Write-Host ""
Write-Host "============================================================================"
Write-Host "  🤖 RL TRAINING SCHEDULER - PowerShell"
Write-Host "============================================================================"
Write-Host ""

# Verificar Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python: $pythonVersion"
} catch {
    Write-Host "❌ Python não encontrado!"
    Read-Host "Pressione Enter para sair"
    exit 1
}

# Verificar APScheduler
try {
    python -c "import apscheduler" 2>&1 | Out-Null
    Write-Host "✅ APScheduler instalado"
} catch {
    Write-Host "⚠️ Instalando APScheduler..."
    pip install apscheduler | Out-Null
    Write-Host "✅ APScheduler instalado"
}

# Criar logs dir
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
    Write-Host "✅ Diretório 'logs' criado"
}

Write-Host ""

# Menu
$menuRunning = $true
while ($menuRunning) {
    Write-Host "OPÇÕES:"
    Write-Host ""
    Write-Host "  1) Iniciar scheduler (background)"
    Write-Host "  2) Executar uma vez (teste)"
    Write-Host "  3) Verificar saúde do modelo"
    Write-Host "  4) Ver jobs agendados"
    Write-Host "  5) Sair"
    Write-Host ""

    $choice = Read-Host "Escolha uma opção [1-5]"

    switch ($choice) {
        1 {
            Write-Host ""
            Write-Host "🚀 Iniciando scheduler em background..."
            Write-Host ""

            # Iniciar em background
            $job = Start-Job -ScriptBlock {
                cd $args[0]
                python scripts/rl_training_scheduler.py
            } -ArgumentList $PWD

            Write-Host "   Job ID: $($job.Id)"
            Write-Host "   Status: $($job.State)"
            Write-Host "   Logs: logs/rl_scheduler.log"
            Write-Host ""
            Write-Host "💡 Use 'Get-Job' para ver status ou 'Stop-Job -Id <id>' para parar"
            Write-Host ""
            Read-Host "Pressione Enter para continuar"
        }
        2 {
            Write-Host ""
            Write-Host "🔄 Executando treinamento uma vez..."
            Write-Host ""

            python -c "from scripts.rl_training_scheduler import RLTrainingScheduler; s = RLTrainingScheduler(); s.run_once()"

            Write-Host ""
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅ Treinamento completado!"
            } else {
                Write-Host "❌ Erro ao treinar"
            }
            Write-Host ""
            Read-Host "Pressione Enter para continuar"
        }
        3 {
            Write-Host ""
            Write-Host "📊 Verificando saúde do modelo..."
            Write-Host ""

            python scripts/rl_health_monitor.py

            Write-Host ""
            Read-Host "Pressione Enter para continuar"
        }
        4 {
            Write-Host ""
            Write-Host "📋 Jobs Agendados:"
            Write-Host ""

            python -c "from scripts.rl_training_scheduler import RLTrainingScheduler; s = RLTrainingScheduler(); s.show_jobs()"

            Write-Host ""
            Read-Host "Pressione Enter para continuar"
        }
        5 {
            $menuRunning = $false
        }
        default {
            Write-Host ""
            Write-Host "❌ Opção inválida"
            Write-Host ""
        }
    }
}

Write-Host ""
Write-Host "👋 Encerrando..."
Write-Host ""
