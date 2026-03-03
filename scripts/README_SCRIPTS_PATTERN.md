# 📚 Padrão de Organização de Scripts do Projeto

**Versão:** 1.0.0
**Data:** 02 de Março de 2026
**Escopo:** Todos os scripts do projeto (Python, Batch, PowerShell)

---

## 🎯 Objetivo

Padronizar a organização, nomenclatura e documentação de scripts para:
- ✅ Facilitar a localização e manutenção
- ✅ Clarificar responsabilidades de cada script
- ✅ Documentar uso e dependências
- ✅ Organizar outputs de forma consistente

---

## 📁 Estrutura de Pastas Recomendada

```
scripts/
│
├── README_SCRIPTS_PATTERN.md          ← Este arquivo
├── version_manifest.json              ← Versionamento centralizado
│
├── execution/                         ← Scripts de execução/menu
│   ├── rodar_task_phase6.bat         ← Menu Phase 6 (v1.0.0)
│   ├── INICIAR_RL_SCHEDULER.ps1       ← Launcher RL Training
│   ├── INICIAR_RL_SCHEDULER.bat       ← Compatibilidade Batch
│   └── SETUP_RL_QUICK.bat             ← Setup automático
│
├── core/                              ← Scripts principais do sistema
│   ├── agente_micro_tendencia_winfut.py         (4453 LOC)
│   ├── launch_agent_with_ml_v1_2_3.py          (launcher)
│   ├── backtest_detector.py                     (backtest)
│   └── rl_training_loop_v3.py                   (RL core)
│
├── ml/                                ← Scripts específicos de ML
│   ├── rl_training_scheduler.py       (370 LOC - scheduling)
│   ├── rl_training_integration.py     (280 LOC - integração)
│   ├── rl_health_monitor.py           (130 LOC - monitoramento)
│   └── ... (outros scripts ML)
│
├── monitoring/                        ← Scripts de monitoramento
│   ├── monitor_simple_macro_score.py  (simulador macro)
│   ├── start_journals_full_display.py (journaling)
│   ├── sync_mt5_trades_to_db.py      (sincronização)
│   └── ... (outros monitors)
│
├── utilities/                         ← Utilitários diversos
│   ├── diagnostic/
│   │   ├── diagnostico_simples.py
│   │   ├── diagnostico_trading_db.py
│   │   └── DIAGNOSTICO_INSTALACAO.bat
│   │
│   ├── debug/
│   │   ├── debug_matching.py
│   │   ├── check_episode_ids.py
│   │   (outros debug scripts)
│   │
│   └── maintenance/
│       ├── cleanup_dados_automatico.py
│       └── (outros maintenance scripts)
│
└── README_SCRIPTS_PATTERN.md (este arquivo)
```

---

## 🏷️ Convenções de Nomenclatura

### Scripts Batch (.bat)

**Padrão geral:**
```
[TIPO]_[FUNCIONALIDADE].bat
```

**Exemplos:**
- `RODAR_TASK_PHASE6.bat` - Menu de tasks
- `INICIAR_RL_SCHEDULER.bat` - Launcher
- `SETUP_RL_QUICK.bat` - Setup automático
- `DIAGNOSTICO_INSTALACAO.bat` - Diagnóstico

**Regras:**
- ✅ Usar MAIÚSCULAS (por ser arquivo executável do Windows)
- ✅ Usar underscores para separação
- ✅ Se for launcher: `INICIAR_[NOME].bat`
- ✅ Se for setup: `SETUP_[NOME].bat`
- ✅ Se for diagnóstico: `DIAGNOSTICO_[DESCRICAO].bat`
- ✅ Manter em pasta específica (`execution/`, `utilities/diagnostic/`)

### Scripts PowerShell (.ps1)

**Padrão geral:** Mesmo das .bat
```
[TIPO]_[FUNCIONALIDADE].ps1
```

**Exemplos:**
- `INICIAR_RL_SCHEDULER.ps1` (menu interativo)
- `SETUP_AMBIENTE.ps1` (setup de ambiente)

**Regras:**
- ✅ Usar PascalCase para partes de funcionalidade
- ✅ Preferir para operações mais complexas
- ✅ Usar quando precisar de operações elevadas

### Scripts Python (.py)

**Padrão geral:**
```
[tipo]_[funcionalidade]_[versao].py
```

**Exemplos:**
- `agente_micro_tendencia_winfut.py` (core agent)
- `rl_training_scheduler.py` (scheduler)
- `rl_health_monitor.py` (monitor)
- `check_episode_ids.py` (debug)
- `diagnostico_simples.py` (diagnostic)

**Regras:**
- ✅ Usar snake_case (padrão Python)
- ✅ Sem prefixo: Scripts principais
- ✅ `test_` ou `_test`: Testes (mas prefira pasta `tests/`, não `scripts/`)
- ✅ `check_`: Scripts de validação
- ✅ `debug_`: Scripts de debug
- ✅ `diagnostico_`: Scripts de diagnóstico
- ✅ `util_`: Utilitários genéricos
- ✅ Evitar caracteres especiais/acentos no nome

---

## 📝 Documentação Obrigatória

### Header Padrão (Python)

Cada script Python deve ter este header:

```python
"""
Operador Quantum - [Nome do Script]

Versão: 1.0.0
Data: 02 de Março de 2026
Propósito: [Descrição clara do que o script faz]

Uso:
    python scripts/[categoria]/[nome].py [argumentos opcionais]

Exemplo:
    python scripts/ml/rl_training_scheduler.py --mode watch
    python scripts/core/backtest_detector.py --config config.json

Entrada:
    - [Descrever entrada esperada]
    - Exemplo: Dataset em scripts/ml/data/

Saída:
    - [Descrever saída/output]
    - Exemplo: logs/rl_scheduler.log
    - Exemplo: outputs/[data]/backtest_results.json

Dependências (pip install):
    - APScheduler
    - SQLite (built-in)
    - scikit-learn

Dependências (internas):
    - src/application/services/rl_training_loop.py
    - src/infrastructure/database/ (SQLite)

Configuração:
    - Arquivo config: config/rl_scheduler_config.json
    - Variáveis ambiente: RL_WATCH_MODE, RL_SCHEDULER_TIME

Saída esperada:
    ✅ Sucesso: Script roda sem erros, logs salvos
    ❌ Erro: Verificar logs em logs/[script_name].log

Troubleshooting:
    - Erro de conexão BD: Verificar trading.db existe
    - Erro de import: python -m pip install -r requirements.txt
    - Erro de encoding: Certificar-se de UTF-8

Versionamento:
    - v1.0.0 (02/03/2026): Versão inicial

Localização no repositório:
    - scripts/[categoria]/[nome].py
"""
```

### Header Padrão (Batch)

```batch
REM ============================================================================
REM Operador Quantum - [Nome do Script]
REM ============================================================================
REM Arquivo: [nome].bat
REM Versao: 1.0.0
REM Data: 02 de Março de 2026
REM Proposito: [Descrição clara]
REM
REM Uso:
REM     rodar_task_phase6.bat
REM     (Menu interativo)
REM
REM Saida:
REM     - Executa tasks selecionadas
REM     - Resultados em backtest_results.json (se backtest)
REM
REM Dependencias:
REM     - Python 3.9+
REM     - PYTHONPATH configurado
REM     - Bibliotecas em requirements.txt
REM
REM Nota: Movido de raiz para scripts/execution/ em 02/03/2026
REM ============================================================================
```

---

## 📦 Outputs Padrão

### Estrutura de Pasta outputs/

Se um script gera arquivos output:

```
outputs/
├── [YYYY-MM-DD]/              ← Pasta por data de execução
│   ├── backtest_results.json  ← Resultados backtest
│   ├── performance_metrics.csv ← Métricas performance
│   └── summary_report.md      ← Relatório resumido
│
├── logs/                      ← Logs de todas execuções
│   ├── 2026-03-02.log
│   ├── 2026-03-01.log
│   └── current.log
│
├── README_OUTPUTS.md          ← README explicando formatos
│
└── .gitignore                 ← Ignorar outputs grandes
    (outputs/*.json)
    (outputs/*.csv)
```

### README_OUTPUTS.md (Obrigatório)

Documentar cada tipo de output:

```markdown
# Outputs do Sistema

## backtest_results.json
- **Origem:** scripts/core/backtest_detector.py
- **Formato:** JSON
- **Conteúdo:**
  - win_rate: Taxa de vitória (%)
  - capture: Taxa de captura (%)
  - false_positives: Taxa falsos positivos (%)
  - P&L: Lucro/prejuízo simulado

## performance_metrics.csv
- **Origem:** scripts/ml/performance_benchmarking.py
- **Colunas:** timestamp, latency_ms, memory_mb, cpu_percent
- **Frequência:** A cada execução

## summary_report.md
- **Formato:** Markdown
- **Conteúdo:** Resumo executivo de resultados
```

---

## 🔄 Versionamento de Scripts

### version_manifest.json (Obrigatório em scripts/)

```json
{
  "last_updated": "2026-03-02T23:45:00Z",
  "scripts": [
    {
      "name": "rodar_task_phase6.bat",
      "version": "1.0.0",
      "location": "scripts/execution/",
      "type": "menu",
      "purpose": "Menu para executar tasks Phase 6",
      "created": "2026-02-20",
      "moved_to_scripts": "2026-03-02",
      "dependencies": ["Python 3.9+", "pytest", "mypy"],
      "last_tested": "2026-03-02"
    },
    {
      "name": "rl_training_scheduler.py",
      "version": "1.0.0",
      "location": "scripts/ml/",
      "type": "scheduler",
      "purpose": "Executa treinamento RL diário e validação",
      "created": "2026-02-23",
      "dependencies": ["APScheduler", "scikit-learn", "SQLite3"],
      "last_tested": "2026-03-02"
    }
  ],
  "organization_standard": {
    "updated": "2026-03-02",
    "reference": "scripts/README_SCRIPTS_PATTERN.md"
  }
}
```

---

## ✅ Checklist de Criação de Script

Ao criar um novo script:

- [ ] **Nomeação:** Nome segue convenção (snake_case para Python, MAIUSCULA para Batch)
- [ ] **Localização:** Em pasta apropriada (execution/, core/, ml/, monitoring/, utilities/)
- [ ] **Header:** Documentação completa com versão, propósito, uso, entrada, saída
- [ ] **Type Hints:** 100% de type hints (Python)
- [ ] **Logging:** Usar módulo `logging` para logs estruturados
- [ ] **Testes:** Script testado manualmente antes de commit
- [ ] **Outputs:** Se gera arquivos, salvar em `outputs/[data]/`
- [ ] **Dependencies:** Listar todas as dependências no header
- [ ] **Error Handling:** Tratamento robusto de erros com try/except
- [ ] **Versionamento:** Atualizar `version_manifest.json`
- [ ] **Documentação:** Atualizar este arquivo se novo tipo de script
- [ ] **Git:** Commit com mensagem clara: `feat: novo script [categoria]/[nome]`

---

## 🚀 Exemplos de Uso

### Exemplo 1: Executar Script RL Training

```bash
# Terminal no projeto root
cd c:\repo\operador-day-trade-win

# Modo 1: Via menu (Batch)
scripts\execution\INICIAR_RL_SCHEDULER.bat

# Modo 2: Direto (Python)
python scripts/ml/rl_training_scheduler.py --mode watch

# Modo 3: Via PowerShell
& .\scripts\execution\INICIAR_RL_SCHEDULER.ps1
```

### Exemplo 2: Executar Menu Phase 6

```bash
# Batch
scripts\execution\rodar_task_phase6.bat

# Saída esperada: Menu interativo com 32 opções
```

### Exemplo 3: Verificar Versionamento

```bash
# Ver manifest
type scripts\version_manifest.json

# Atualizar manifest (após novo script)
# Editar manualmente ou via script automation
```

---

## 📋 Histórico de Mudanças

| Data | Ação | Script | Localização |
|------|------|--------|------------|
| 02/03/2026 | Movido de raiz | `rodar_task_phase6.bat` | scripts/execution/ |
| 02/03/2026 | Criado padrão | `README_SCRIPTS_PATTERN.md` | scripts/ |
| 02/03/2026 | Criado versionamento | `version_manifest.json` | scripts/ |
| 23/02/2026 | Criado | `rl_training_scheduler.py` | scripts/ml/ |

---

## 🔗 Referências

- **Backlog:** [docs/BACKLOG_UNIFICADO.md](../docs/BACKLOG_UNIFICADO.md)
- **Consolidação:** [outputs/CONSOLIDACAO_BACKLOG_02MAR2026.md](../outputs/CONSOLIDACAO_BACKLOG_02MAR2026.md)
- **Coding Standards:** [CODING_STANDARDS.md](../CODING_STANDARDS.md)

---

**Status:** ✅ Padrão implementado e documentado
**Data:** 02 de Março de 2026
**Responsável:** GitHub Copilot (Automação)
