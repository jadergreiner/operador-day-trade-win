# operador-day-trade-win

Sistema de trading automatizado para Mini Índice (WIN$N) com 4 agentes executores e múltiplos componentes de análise, ML e RL.

## 🚀 Quick Start

### Dependências Principais

Este projeto requer Python 3.11+ e as seguintes dependências críticas:

```bash
pip install pydantic>=2.0 pyyaml>=6.0
```

**Nota operacional:**
- Antes de atualizar agentes em produção, certifique-se de ter `pydantic` e `pyyaml` instalados no ambiente virtual
- Falha de import causa erro de boot; o código tem fallback mas funcionalidades de config governance ficarão limitadas

### Executáveis Principais

| Launcher | Propósito | Magic Number |
|----------|-----------|--------------|
| `INICIAR_DIARIOS.bat` | Journaling + contexto macro + retraining | 234800 |
| `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` | Sinais intraday (~29/dia) com ML | 234700 |
| `INICIAR_AGENTE_RL_5000.bat` | Execução RL em produção estrita | 234500 |
| `INICIAR_AGENTE_RL_DIRETO.bat` | Execução RL isolada paralela | 234600 |
| `INICIAR_MONITOR_QUANTICO.bat` | Dashboard web + API tendência | N/A |

## ⚙️ Profit Protection - Configuração de Perfis

**Implementado:** 04/04/2026 (ADR-018)
**Arquivo de config:** `config/profit_protection.yaml`

### O que é

Sistema de proteção de lucros com thresholds externalizados para permitir calibração A/B sem redeploy de código.

### Perfis Disponíveis (v1.0.0)

**baseline** (padrão histórico):
```yaml
profit_target_pct: 2.0      # Fecha 100% ao atingir +2%
stop_loss_pct: 1.0          # Fecha 100% ao perder -1%
partial_close_pct: 0.75     # Fecha 75% da posição ao atingir profit_target
break_even_offset_pct: 0.10 # Move SL para breakeven após +0.10%
reversao_threshold_pct: 0.75 # Detecta reversão se cair 75% do lucro
cooldown_seconds: 5         # Aguarda 5s após proteção antes de nova ação
```

**conservador** (proteção antecipada):
```yaml
profit_target_pct: 1.5      # Fecha mais cedo
stop_loss_pct: 1.0
partial_close_pct: 0.85     # Fecha mais (85%)
break_even_offset_pct: 0.08 # Breakeven mais rápido
reversao_threshold_pct: 0.60 # Mais sensível a reversão
cooldown_seconds: 5
```

**agressivo** (deixa lucro correr):
```yaml
profit_target_pct: 3.0      # Target mais alto
stop_loss_pct: 1.0
partial_close_pct: 0.50     # Mantém mais (50%)
break_even_offset_pct: 0.15 # Breakeven mais tardio
reversao_threshold_pct: 0.90 # Menos sensível
cooldown_seconds: 10        # Mais calmo
```

### Como Usar

**1. Alterar perfil padrão (produção):**

Edite `config/profit_protection.yaml`:
```yaml
profile_ativo: "conservador"  # baseline | conservador | agressivo
shadow_mode: false            # true = apenas log, false = executa
```

**2. Testar perfil em um agente específico:**

```yaml
agent_overrides:
  agente_direto_20260405_090000:
    profile: "agressivo"  # Apenas este agente usa agressivo
```

**3. Mudança temporária via ENV var (staging):**

```bash
SET PROFIT_PROTECTION_PROFILE=conservador
.\INICIAR_AGENTE_RL_DIRETO.bat
```

### Precedência de Configuração

A resolução de perfil segue a ordem (do mais específico ao mais geral):

1. **agent_overrides[agent_id]** → Override cirúrgico no YAML
2. **PROFIT_PROTECTION_PROFILE** → Variável de ambiente
3. **profile_ativo** → Padrão do YAML
4. **baseline builtin** → Fallback hardcoded (se YAML ausente)

### Shadow Mode (Validação Sem Risco)

Antes de ativar um novo perfil em produção, valide sem risco de capital:

```yaml
profile_ativo: "agressivo"
shadow_mode: true  # Apenas loga ações sugeridas, NÃO executa
```

Monitore os logs para ver quais ações o perfil agressivo TERIA executado:
```bash
tail -f outputs/agente_direto_*.log | grep -i "SHADOW MODE"
```

### Calibração A/B

Compare perfis sobre trades históricos do SQLite:

```bash
python scripts/calibrar_profit_protection.py
```

**Guards de rollback automático:**
- Se degradação win rate > 2 pontos percentuais → rollback para baseline
- Se aumento drawdown > 15% → rollback para baseline

**Saída:**
- `outputs/profit_protection/baseline_vs_candidato_<timestamp>.json`
- `outputs/profit_protection/baseline_vs_candidato_<timestamp>.md`

### Impacto Operacional

**Launcher afetado:** `INICIAR_AGENTE_RL_DIRETO.bat` (impacto DIRETO)

**Ações pós-mudança:**
1. Reiniciar launcher: `.\INICIAR_AGENTE_RL_DIRETO.bat`
2. Validar boot correto:
   ```bash
   grep -i "ProfitProtectionConfig.*carregada" outputs/agente_direto_*.log
   # Expected: version=1.0.0, profile_ativo=<perfil>, shadow_mode=false
   ```
3. Monitorar por 2 horas:
   ```bash
   tail -f outputs/agente_direto_*.log | grep -i "profit_protection\|protecao"
   ```

**Rollback (se necessário):**
```bash
# 1. Parar launcher (Ctrl+C)
# 2. Restaurar config anterior
cp config/profit_protection.yaml.backup config/profit_protection.yaml
# 3. Reiniciar launcher
.\INICIAR_AGENTE_RL_DIRETO.bat
```

### Referências

- **ADR-018:** `docs/ADRS.md#adr-018` (Decisão arquitetural completa)
- **Regra de negócio:** `docs/REGRAS_DE_NEGOCIO.md` → R-CONFIG-001
- **Arquitetura:** `docs/ARQUITETURA_ALVO.md` → Infrastructure Layer
- **Loader:** `src/infrastructure/config/profit_protection_config.py`
- **Calibration service:** `src/application/services/profit_protection_calibration_service.py`

---

## 📚 Documentação Completa

Resumo rápido do repositório e nota de dependências relevantes.

Este repositório implementa um sistema de trading automatizado com 4
launchers principais e vários agentes (RL, Micro Tendência, Diários,
Monitor). Para carregar configurações canônicas (ex.: `profit_protection.yaml`)
utilizamos `pydantic` para validação/typing e `pyyaml` para parsing de YAML.

Dependências importantes (adicionadas por `Profit Protection v2`):

- `pydantic` — validação e modelos tipados para `ProfitProtectionProfile`.
- `pyyaml` — carregamento do arquivo `profit_protection.yaml`.

Nota operacional:

- Antes de atualizar agentes em produção, atualize o ambiente virtual
  (`.venv`) ou `pyproject.toml`/`requirements.txt` para incluir essas libs.
- Falha de import destas libs causa erro de arranque; o código tem fallback
  que evita crash, mas o comportamento esperado (profiles/telemetria) ficará
  restrito até a instalação.

Veja `docs/REGRAS_DE_NEGOCIO.md` e `docs/BACKLOG.md` para instruções de
operação e cards de backlog relacionados.
