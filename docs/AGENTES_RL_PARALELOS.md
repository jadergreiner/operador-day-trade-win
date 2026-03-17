# Agentes Paralelos - Arquitetura Independente

## Visão Geral

O projeto suporta **4 agentes operando em paralelo
com posições completamente independentes**:

| # | Agente | Launcher | Magic |
|---|--------|----------|-------|
| 1 | RL 5000 (Supervisionado) | `INICIAR_AGENTE_RL_5000.bat` | 234500 |
| 2 | RL Direto (Autônomo) | `INICIAR_AGENTE_RL_DIRETO.bat` | 234600 |
| 3 | Micro Tendência (ML) | `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` | 234700 |
| 4 | Diários (Auditoria) | `INICIAR_DIARIOS.bat` | 234800 |

Cada agente:

- ✅ Tem seu próprio **Magic Number (EA ID)** no MT5
- ✅ Mantém **logs separados** em `outputs/`
- ✅ Opera com **estado isolado** (zero interferência)
- ✅ Pode rodar **em paralelo** (simultaneamente)
- ✅ Gerencia suas próprias **posições e trades**
- ✅ Filtra posições por `magic` (nativo MT5)

---

## Isolamento por Magic Number (EA ID) — ADR-012

> **Decisão**: 17/03/2026 — Supercede isolamento
> por Session ID (ADR-011). Ver `docs/ADRS.md`.

O campo `magic` do MT5 é persistido pela corretora
na posição. Sobrevive a restarts, desconexões e
crash do agente. Cada agente envia ordens com magic
exclusivo e filtra posições por esse valor.

```text
Ordem enviada → MT5 grava magic na posição
Agente reinicia → consulta posições com pos.magic
→ só vê as suas
```

### Pontos de implementação (por agente)

1. **Constante global**: `MAGIC_NUMBER = 234XXX`
2. **Order de entrada**: `Order(..., magic_number=MAGIC_NUMBER)`
3. **Order de saída**: `Order(..., magic_number=MAGIC_NUMBER)`
4. **Filtro de posições**: `if pos.magic != MAGIC_NUMBER: continue`

---

## Arquitetura de Isolamento

### RL 5000 (Supervisionado) — Magic 234500

```text
Script: scripts/operar_novo_agente_rl_real_antiovertrading.py
Magic Number: 234500
Símbolo: WIN$N

Isolamento:
  - monitorar_posicoes() filtra por magic
  - processar_protecao_lucros() filtra por magic
  - proteger_lucro_trade() filtra por magic
  - modificar_sl_ordem() usa MAGIC_NUMBER
  - fechar_parcial_posicao() usa MAGIC_NUMBER
  - MotorDecisaoIsolado: rastreia posicoes por agent_id
    (substitui tickets_proprios: set[int] removido)
  - Persistencia: outputs/posicoes_ativas_agente_*.json

Logs:
  - outputs/agente_supervision.log
  - outputs/agente_debug.log
```

### RL Direto (Autônomo) — Magic 234600

```text
Script: scripts/agente_rl_direto_independente.py
Magic Number: 234600
Símbolo: WIN$N

Isolamento:
  - verificar_posicao_no_mt5() filtra por magic
  - PosicaoIsoladaManager: valida ownership por session_id
  - MotorDecisaoIsolado: rastreia posicoes e P&L
    (substitui AgentePosicaoStatus inline removido)
  - Persistencia: outputs/posicoes_ativas_agente_direto_*.json
  - Verifica posição a cada ciclo via MT5 por ticket

Logs:
  - outputs/agente_direto_[TIMESTAMP].log
```

### Micro Tendência (ML) — Magic 234700

```text
Script: scripts/agente_micro_tendencia_winfut.py
Launcher: scripts/launch_agent_with_ml_v1_2_3.py
Magic Number: 234700
Símbolo: WIN$N

Isolamento:
  - execute_entry() passa magic na Order
  - _close_position() passa magic na Order
  - monitor_hedge_orphans() filtra por magic
  - manage_positions() usa self.open_trades (interno)

Logs:
  - Terminal interativo (dashboard)
```

### Diários (Auditoria) — Magic 234800 (reservado)

```text
Script: scripts/start_journals_full_display.py
Magic Number: 234800 (reservado, não envia ordens)
Símbolo: WIN$N (leitura)

Função:
  - Trading Journal (narrativa macro/micro, 5 min)
  - AI Reflection (auto-avaliação, 10 min)
  - RL Performance Diary (rewards, 15 min)
```

---

## Comparação Detalhada

| Aspecto | RL 5000 | RL Direto | Micro Tend. |
|---------|---------|-----------|-------------|
| **Magic** | 234500 | 234600 | 234700 |
| **Script** | `operar_novo_*` | `agente_rl_direto_*` | `agente_micro_tend*` |
| **Modelo** | Q-Learning | Q-Learning | LightGBM+MacroScore |
| **Filtro pos.** | `monitorar_pos` | `verif_posicao_mt5` | `hedge_orphans` |
| **Isolamento** | `MotorDecisao` | `MotorDecisao`+`PosIsolada` | N/A |
| **AC5.8** | ✅ | ✅ | ✅ |
| **AC5.9/AC6** | ✅ | ✅ | ✅ |
| **SL/TP** | Dinâmicos | Dinâmicos | ATR calibrado |
| **Heartbeat** | ✅ (thread) | ❌ | ❌ |
| **Recuperação** | Automática | Manual | Manual |
| **Paralelo** | ✅ | ✅ | ✅ |

---

## Como Usar em Paralelo

### Cenário: Executar ambos os agentes simultaneamente

**Terminal 1:**

```bash
# Agente supervisionado
cmd /c "cd C:\repo\operador-day-trade-win && INICIAR_AGENTE_RL_5000.bat"
```

**Terminal 2:**

```bash
# Agente direto (simultâneos)
cmd /c "cd C:\repo\operador-day-trade-win && INICIAR_AGENTE_RL_DIRETO.bat"
```

**Resultado:**

- Dois agentes operando **SIMULTANEAMENTE**
- Cada um com seu próprio **session ID**
- Posições **COMPLETAMENTE ISOLADAS**
- Logs **SEPARADOS** para debugging
- **ZERO CONFLITO** entre operações

### Logs de Cada Agent

```text
outputs/
├── agente_supervision.log           ← Agente RL 5000 (supervisão)
├── agente_debug.log                 ← Agente RL 5000 (debug)
├── agente_direto_20260316_112359.log ← Agente Direto (específico)
└── agente_direto_debug_20260316_112359.log ← Agente Direto debug
```

---

## Isolamento de Estado

### Nível 1: MT5 (Magic Number)

Isolamento nativo do broker — campo `magic` na posição:

```python
# Ao enviar ordem
order = Order(..., magic_number=MAGIC_NUMBER)

# Ao consultar posições
for pos in mt5.get_positions(symbol):
    if pos.magic != MAGIC_NUMBER:
        continue  # ignora posição de outro agente
```

### Nível 2: Base de Dados

Todos usam o mesmo SQLite (`trading.db`),
isolamento via:

- **session_id** em queries
- **Índices sobre session_id** para performance
- **FK constraints** para integridade

### Nível 2b: Camada de Aplicação (Grupo 1)

Dois módulos em `src/application/` garantem
isolamento de decisões e posições entre agentes.
Desde 17/03/2026, ambos são **importados
diretamente** pelos scripts dos agentes (não
mais código inline duplicado).

**`motor_decisao_isolado.py`** — Motor de decisão
por `agent_id`. Cada agente grava decisões e
posições em arquivos JSON próprios
(`posicoes_ativas_{agent_id}.json`). Classe
`MotorDecisaoIsolado` com 10+ métodos.
- RL 5000: `motor_isolado` (substitui
  `tickets_proprios` set)
- RL Direto: `motor_decisao` (substitui lógica
  inline de `AgentePosicaoStatus`)

**`posicao_isolamento.py`** — Gerenciador de
posição isolada por `session_id` +
`agent_version`. Classe `PosicaoIsoladaManager`
valida ownership a cada leitura e impede acesso
cruzado entre agentes.
- RL Direto: `posicao_tracker` — substitui
  `AgentePosicaoStatus` (141 LOC removidos)

Ref: ADR-011/012, P0-NOVO (BACKLOG).

### Nível 2c: Feedback e Aprendizado (Grupo 2)

Cinco módulos em `src/application/` fecham o loop
de feedback entre execução e aprendizado.
Desde 17/03/2026, são **importados diretamente**
pelos scripts dos agentes (ADR-015).

**`ac5_8_position_monitor.py`** — Monitoramento
em tempo real de posições com SQLite (4 tabelas).
- Micro Tendência: registra/atualiza posições
- RL 5000: registra/atualiza posições
- RL Direto: registra abertura e fechamento

**`ac5_9_feedback_validator.py`** — Valida saúde
do ciclo trade→feedback→ML. Health check com
score e recomendações.
- Micro Tendência: a cada 10 ciclos
- Diários: no `run_rl_performance_diary()`
- RL Direto: a cada 10 ciclos
- RL 5000: a cada 10 ciclos

**`ac6_7_drift_detector.py`** — Detecta
degradação de modelo via Z-score contra baseline.
- Micro Tendência: a cada 10 ciclos
- RL Direto: a cada 10 ciclos
- RL 5000: a cada 10 ciclos

**`ac6_8_online_learning.py`** — Treino
incremental com rollback automático.
- Micro Tendência: ativado quando drift detectado
- RL Direto: ativado quando drift detectado
- RL 5000: ativado quando drift detectado

**`ac6_9_baseline_comparator.py`** — Compara
métricas atuais vs baseline histórico.
- Micro Tendência: a cada 10 ciclos
- RL Direto: a cada 10 ciclos
- RL 5000: a cada 10 ciclos

Ref: ADR-015, P1 (BACKLOG), AC5.8-AC6.9.

### Nível 3: Memória

- Cada agente tem sua própria instância de:
  - `AgenteQLearning` (modelo em memória)
  - `ProfitProtectionEngine` (estado de proteção)
  - `RLRepository` (conexão DB)
  - `MotorDecisaoIsolado` (decisões + posições)
  - `PosicaoIsoladaManager` (ownership JSON)

---

## Sincronização de Modelo

Embora os agentes tenham **estado isolado**, compartilham:
- **Mesmo modelo RL**: `data/models/novo_agente_rl/modelo_final/q_network.pkl`
- **Mesmas features**: 15-dimensional state input

Cada agente:
1. Carrega o **mesmo modelo** na iniciação
2. Executa **inferência independente** (nenhum treino em live)
3. Passa por **SL/TP dinâmicos independentes**
4. Registra **resultados em session separate**

---

## Desenvolvimento: Próximas Melhorias

### Prioridade Alta

- [ ] Sincronização de modelo entre agentes (se um muda, outro nota)
- [ ] Dashboard unificado mostrando ambos os agentes
- [ ] Alertas coordenados (se um perde, o outro reduz agressividade)

### Prioridade Média

- [ ] Sharing de features (A aprende com trade de B)
- [ ] Rebalanceamento dinâmico de capital entre agentes
- [ ] Veto mútuo em certos cenários de risco

### Prioridade Baixa

- [ ] Comunicação RPC entre agentes
- [ ] Distributed training com dados de ambos
- [ ] Consenso na tomada de decisão

---

## Troubleshooting

### Ambos os agentes travados?

```bash
# Verificar logs
tail -f outputs/agente_supervision.log
tail -f outputs/agente_direto_*.log

# Procurar por [ERROR] ou [FATAL]
grep ERROR outputs/agente*.log
```

### Agente direto não inicia?

```bash
# Verificar se arquivo existe
if exist scripts\agente_rl_direto_independente.py (echo OK) else (echo MISSING)

# Testar import manual
python -c "import sys; sys.path.insert(0, '.'); \
  from scripts.agente_rl_direto_independente import *; print('OK')"
```

### Posições ficando misturadas?

```sql
-- Verificar isolamento por session
SELECT session_id, COUNT(*)
FROM trades
GROUP BY session_id;
```

### Agente vê posição de outro agente?

Verificar se magic number está correto:

```python
import MetaTrader5 as mt5
mt5.initialize()
for pos in mt5.positions_get(symbol="WIN$N"):
    print(f"ticket={pos.ticket} magic={pos.magic}")
# Esperado: cada agente com magic diferente
# 234500=RL5000, 234600=Direto, 234700=MicroTend
```

### Agente tentou modificar SL de outro?

Sintoma: `retcode=10013` no log. Causa: magic
number não bate. Solução: garantir que todas as
chamadas `mt5.order_send()` raw usam
`MAGIC_NUMBER` do agente correto.

---

## Referência Rápida

| Comando | Magic | Efeito |
|---------|-------|--------|
| `INICIAR_AGENTE_RL_5000.bat` | 234500 | RL supervisionado |
| `INICIAR_AGENTE_RL_DIRETO.bat` | 234600 | RL autônomo |
| `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` | 234700 | ML sinais |
| `INICIAR_DIARIOS.bat` | 234800 | Auditoria |
| Ctrl+C | — | Para o agente atual |

---

## Histórico

| Data | Decisão |
|------|--------|
| 16/03 | Session ID + arquivo JSON isolado (ADR-011) |
| 17/03 | Magic Number EA ID por agente (ADR-012) |
| 17/03 | Detecção SL/TP por ticket no agente direto |
| 17/03 | Filtro magic no monitor_hedge_orphans |

**Status:** ✅ Produção — isolamento por Magic Number
