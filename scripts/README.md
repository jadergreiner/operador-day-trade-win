# Scripts - Guia de Padrão e Localização

**Versão:** 1.1
**Data:** 16/03/2026
**Responsável:** Product Owner / GitHub Copilot

---

## 📋 Visão Geral

Este diretório centraliza todos os scripts Python do projeto, seguindo um padrão
consistente de nomenclatura e propósito. Todos os scripts Python devem estar aqui,
**NUNCA na raiz do projeto**.

---

## 📂 Estrutura e Convenção de Nomenclatura

```
scripts/
├── spec_*.py          # Especificações técnicas (design docs executáveis)
├── run_*.py           # Scripts de execução/main (aplicação de lógica)
├── launch_*.py        # Scripts de inicialização (batch/PowerShell wrappers)
├── check_*.py         # Scripts de verificação/diagnóstico
├── cleanup_*.py       # Scripts de limpeza (dados, cache, etc)
├── verify_*.py        # Scripts de validação (testes, checks)
├── analyze_*.py       # Scripts de análise (dados, logs, performance)
├── debug_*.py         # Scripts de debug (troubleshooting)
├── export_*.py        # Scripts de exportação (dados, reports)
├── import_*.py        # Scripts de importação (dados)
├── test_*.py          # Testes (se não em pasta tests/)
└── utility_*.py       # Utilitários gerais
```

---

## 🎯 Quando Usar Cada Tipo

### `spec_*.py` - Especificações Técnicas
**Propósito:** Documentar especificações técnicas executáveis
**Exemplo:** `spec_eng003_mt5_api.py`
**Uso:**
```bash
python scripts/spec_eng003_mt5_api.py  # Imprime spec
```
**Características:**
- Contém especificações em docstrings
- Serve como referência executável
- Não contém lógica de negócio
- Usually printed or referenced

**Quando usar:**
- Especificações de API
- Definições de schema/estrutura
- Planos técnicos na forma de código

---

### `run_*.py` - Execução Principal
**Propósito:** Scripts que executam lógica principal
**Exemplo:** `run_automated_trading.py`
**Uso:**
```bash
python scripts/run_automated_trading.py  # Inicia trading
```
**Características:**
- Contém lógica principal/negócio
- Entry points da aplicação
- Pode aceitar argumentos CLI
- Should be idempotent

**Quando usar:**
- Scripts que iniciam serviços
- Scripts que processam dados
- Scripts que executam workflows

---

### `launch_*.py` - Inicialização
**Propósito:** Wrappers para inicializar com configuração
**Exemplo:** `launch_agent_with_ml.py`
**Uso:**
```bash
python scripts/launch_agent_with_ml.py --mode auto --port 8000
```
**Características:**
- Configura ambiente antes de executar
- CLI argument parsing
- Setup/teardown logic
- Pode chamar outros scripts

**Quando usar:**
- Configuração antes de execução
- Multi-step initialization
- Mode switching (dev/prod)

---

### `check_*.py` - Verificação/Diagnóstico
**Propósito:** Validar estado do sistema/dados
**Example:** `check_order_creator.py`
**Uso:**
```bash
python scripts/check_order_creator.py  # Verifica origem ordens
```
**Características:**
- Diagnóstico sem modificação
- Return exit codes (0=OK, 1=FAIL)
- Safety checks antes de operações
- Gera relatórios

**Quando usar:**
- Diagnóstico de ambiente
- Validação de dados
- Health checks
- Pre-flight checks

---

### `cleanup_*.py` - Limpeza
**Propósito:** Limpeza de dados, cache, arquivos temp
**Example:** `cleanup_dados_automatico.py`
**Uso:**
```bash
python scripts/cleanup_dados_automatico.py  # Limpa BD
```
**Características:**
- Backup antes de deletar
- User confirmation required
- Logging de operações
- Rollback capability

**Quando usar:**
- Limpeza automática de BD
- Remoção de temp files
- Cache invalidation

---

### `verify_*.py` - Validação
**Propósito:** Validar integridade/conformidade
**Example:** `verify_fix_s2_5.py`
**Uso:**
```bash
python scripts/verify_fix_s2_5.py  # Valida fix
```
**Características:**
- Assert statements
- Test execution
- Return boolean/exit code
- Non-destructive

**Quando usar:**
- Validação pós-deploy
- Teste de conformidade
- Verificação de integridade

---

### `analyze_*.py` - Análise
**Propósito:** Análise de dados/logs/performance
**Example:** `analyze_historical_patterns.py`
**Uso:**
```bash
python scripts/analyze_historical_patterns.py  # Analisa padrões
```
**Características:**
- Data processing
- Gera relatórios/visualizações
- Read-only operations
- Detail level configurável

**Quando usar:**
- Análise de dados
- Audit trail review
- Performance analysis
- Post-mortem analysis

---

### `debug_*.py` - Debug
**Propósito:** Troubleshooting e diagnóstico aprofundado
**Example:** `debug_matching.py`
**Uso:**
```bash
python scripts/debug_matching.py --verbose  # Debug com logs
```
**Características:**
- Verbose logging
- Step-by-step execution
- Breakpoints/pause points
- Detailed output

**Quando usar:**
- Troubleshooting issues
- Root cause analysis
- Detailed diagnostics

---

## 📋 Script Consolidados (02/03/2026)

| Nome | Tipo | Origem | Propósito |
|------|------|--------|----------|
| `spec_eng003_mt5_api.py` | spec | SPRINT2_TASK_ENG003_MT5_API.py | Especificação API MT5 |
| `spec_ml003_feature_analysis.py` | spec | SPRINT2_TASK_ML003_FEATURE_ANALYSIS.py | Especificação análise features |
| `spec_ml004_extended_backtest.py` | spec | SPRINT2_TASK_ML004_EXTENDED_BACKTEST.py | Especificação backtest 252 dias |
| `run_sprint2_dashboard.py` | run | SPRINT2_KICKOFF_DASHBOARD.py | Dashboard Sprint 2 |

---

## ✅ Checklist Para Novos Scripts

Ao criar um novo script, validar:

- [ ] Local: Arquivo em `scripts/` (nunca raiz)
- [ ] Nome: Segue padrão `{tipo}_{descricao}.py`
- [ ] Shebang: `#!/usr/bin/env python3`
- [ ] Encoding: `# -*- coding: utf-8 -*-`
- [ ] Docstring: Descrição em português
- [ ] Type hints: Decoradores de tipo (quando aplicável)
- [ ] Error handling: Try/except com logging
- [ ] Logging: import logging + configuração
- [ ] Exit codes: Retorno 0=sucesso, 1=erro
- [ ] Idempotente: Pode ser executado múltiplas vezes
- [ ] Documentado: Help text ou README section

### Template Mínimo

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Descrição breve do script em português.

Exemplos:
    python scripts/meu_script.py [opções]

Returns:
    0: Sucesso
    1: Erro
"""

import logging

logger = logging.getLogger(__name__)


def main() -> int:
    """Função principal."""
    try:
        # Lógica aqui
        logger.info("Script executado com sucesso")
        return 0
    except Exception as e:
        logger.error(f"Erro: {e}")
        return 1


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    exit(main())
```

---

## 🔗 Integração com Projeto

### Chamadas de Scripts
Sempre usar path relativo ao workspace:
```python
import subprocess
result = subprocess.run([
    "python",
    "scripts/run_automated_trading.py",
    "--mode", "auto"
], cwd="/repo/operador-day-trade-win")
```

### Scripts Agendados (Windows)
```cmd
schtasks /create /tn "TaskName" /tr "python scripts/run_daily_cleanup.py" /sc daily /st 04:00
```

### Scripts Agendados (Linux)
```bash
# Add to crontab
0 4 * * * cd /repo/operador-day-trade-win && python scripts/run_daily_cleanup.py
```

---

## 🤖 Scripts de Agentes RL

### `operar_novo_agente_rl_real_antiovertrading.py`

**Propósito:** Agente RL principal com proteção contra overtrading

**Tipo:** run
**Uso:**
```bash
python scripts/operar_novo_agente_rl_real_antiovertrading.py

# Com wrapper de supervisão (recomendado)
python scripts/agente_com_supervision.py --sl-tp-mode dinamico
```

**Características:**
- Q-Learning com 3 ações (BUY, SELL, HOLD)
- Anti-overtrading (7 filtros de proteção)
- SL/TP dinâmicos (análise de topos/fundos)
- Profit Protection Engine (break-even stop automático)
- Session ID via environment variable

**Modelos:** `data/models/novo_agente_rl/modelo_final/`

---

### `agente_rl_direto_independente.py` (NOVO - 16/03/2026)

**Propósito:** Agente RL com posição ISOLADA e INDEPENDENTE do agente 5000

**Tipo:** run (direto, sem wrapper)
**Uso:**
```bash
python scripts/agente_rl_direto_independente.py --mode dinamico

# Via batch file (recomendado)
INICIAR_AGENTE_RL_DIRETO.bat
```

**Características:**
- Session ID único: `agente_direto_TIMESTAMP`
- Logs separados por instância
- Pode rodar em PARALELO com operar_novo_agente_rl_real_antiovertrading.py
- Estado totalmente isolado (posições, trades, histórico)
- Inicialização própria de componentes
- Mesmo modelo RL compartilhado

**Arguments:**
- `--mode dinamico|fixo`: Define modo de SL/TP (padrão: dinamico)

**Logs:**
- `outputs/agente_direto_[TIMESTAMP].log`
- `outputs/agente_direto_debug_[TIMESTAMP].log`

**Diferença vs agente 5000:**
| Aspecto | Agente 5000 | Agente Direto |
|---------|---|---|
| Wrapper | Com supervisão | Sem wrapper |
| Session ID | Via environment | Via geração de ID |
| Paralelo | ✅ Sim | ✅ Sim |
| Heartbeat | ✅ Sim | ❌ Não |
| Complexidade | Média | Simples |

---

### `agente_com_supervision.py`

**Propósito:** Wrapper de supervisão para `operar_novo_agente_rl_real_antiovertrading.py`

**Tipo:** launch
**Uso:**
```bash
python scripts/agente_com_supervision.py --sl-tp-mode [dinamico|fixo]
```

**Características:**
- Monitoramento contínuo (heartbeat)
- Tratamento centralizado de exceções
- Logging unificado
- Recuperação automática de falhas
- Redirection de stdout/stderr

**Logs:**
- `outputs/agente_supervision.log` (saída completa)
- `outputs/agente_debug.log` (logs DEBUG detalhados)

---

## 📚 Documentação de Scripts

Cada script deve incluir:

1. **Docstring principal** (português)
2. **Exemplos de uso** (CLI)
3. **Acceptance criteria** (se aplicável)
4. **Exit codes** (docums sucesso/erro)
5. **Logging** (estruturado)
6. **Error handling** (graceful)

### Exemplo Completo

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análise de padrões históricos de trading.

Este script carrega dados históricos de trading e gera análise
de padrões, estatísticas e insights para ML training.

Exemplos:
    # Análise padrão
    python scripts/analyze_historical_patterns.py

    # Com verbose output
    python scripts/analyze_historical_patterns.py --verbose

    # Apenas período específico
    python scripts/analyze_historical_patterns.py \\
        --start-date 2026-01-01 \\
        --end-date 2026-02-28

Output:
    - Gera arquivo: analysis_results.json
    - Gera arquivo: analysis_charts.png
    - Log level: INFO

Exit Codes:
    0: Análise concluída com sucesso
    1: Erro ao carregar dados
    2: Erro ao processar análise
    3: Erro ao salvar resultados

Author:
    GitHub Copilot / Product Owner

Date:
    02/03/2026
"""
```

---

## 🚀 Melhorias Futuras

- [ ] Criar `scripts/config/` para configurações compartilhadas
- [ ] Implementar `scripts/libs/` para funções utilitárias reutilizáveis
- [ ] Adicionar CI/CD hooks em `scripts/.hooks/`
- [ ] Documentar scripts em wiki/ReadtheDocs
- [ ] Criar auto-discovery de scripts availáveis

---

## 📞 Troubleshooting

### Script não encontrado
```
Error: ModuleNotFoundError
Solução: Usar path absoluto: /repo/operador-day-trade-win/scripts/
```

### Permissões insuficientes
```
Error: PermissionError
Solução: chmod +x scripts/script.py
```

### Imports falhando
```
Error: ImportError
Solução: Adicionar PYTHONPATH=/repo/operador-day-trade-win
```

---

## 📋 Padrão Adotado

**Data de Adoção:** 02/03/2026
**Fonte:** `docs/BACKLOG_UNIFICADO.md` - P8: Padrão de Localização
**Status:** ✅ OBRIGATÓRIO para todos Python scripts

---

**Última Atualização:** 02/03/2026
**Proprietário:** Product Owner / GitHub Copilot
