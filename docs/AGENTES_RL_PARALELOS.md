# Agentes RL Paralelos - Arquitetura Independente

## Visão Geral

O projeto suporta **dois agentes RL operando em paralelo com posições completamente independentes**:

1. **INICIAR_AGENTE_RL_5000.bat** - Agente Supervisionado (síncrono)
2. **INICIAR_AGENTE_RL_DIRETO.bat** - Agente Direto (autônomo)

Cada agente:
- ✅ Tem seu próprio **Session ID** único
- ✅ Mantém **logs separados** em outputs/
- ✅ Opera com **estado isolado** (nenhuma interferência entre eles)
- ✅ Pode rodar **em paralelo** (simultaneamente)
- ✅ Gerencia suas próprias **posições e trades**
- ✅ Usa a mesma **RL model** (q_network.pkl)

---

## Arquitetura de Isolamento

### INICIAR_AGENTE_RL_5000.bat (Supervisionado)

```
Script Principal: scripts/operar_novo_agente_rl_real_antiovertrading.py
Wrapper (Supervisão): scripts/agente_com_supervision.py

Session ID: agente_supervisionado_TIMESTAMP (via environment var)
Logs:
  - outputs/agente_supervision.log
  - outputs/agente_debug.log

Recursos:
  - Monitoramento contínuo (heartbeat)
  - Tratamento de exceções centralizado
  - Logging unificado via supervisão
  - Recuperação automática de falhas

Modo: SL/TP DINAMICOS (opção --sl-tp-mode)
```

### INICIAR_AGENTE_RL_DIRETO.bat (Direto/Autônomo)

```
Script Principal: scripts/agente_rl_direto_independente.py

Session ID: agente_direto_TIMESTAMP (gerado no script)
Logs:
  - outputs/agente_direto_[TIMESTAMP].log
  - outputs/agente_direto_debug_[TIMESTAMP].log

Recursos:
  - Inicialização própria de componentes
  - Estado isolado com session ID único
  - Logging independente por instância
  - Recuperação básica de erros

Modo: SL/TP DINAMICOS (opção --mode dinamico|fixo)
```

---

## Comparação Detalhada

| Aspecto | AGENTE RL 5000 | AGENTE DIRETO |
|---------|---|---|
| **Script** | `operar_novo_agente_rl_real_antiovertrading.py` | `agente_rl_direto_independente.py` |
| **Wrapper** | Com supervisão (`agente_com_supervision.py`) | Direto (sem wrapper) |
| **Session ID** | `agente_supervisionado_TIMESTAMP` | `agente_direto_TIMESTAMP` |
| **Log Principal** | `agente_supervision.log` | `agente_direto_[TIMESTAMP].log` |
| **Log Debug** | `agente_debug.log` | `agente_direto_debug_[TIMESTAMP].log` |
| **Heartbeat** | ✅ Sim (thread monitor) | ❌ Não (script direto) |
| **Tratamento Exception** | Centralizado em wrapper | Em cada componente |
| **Paralelo** | ✅ Pode rodar com direto | ✅ Pode rodar com 5000 |
| **Isolamento Session** | Via environment variable | Via geração de ID no script |
| **Recuperação Falha** | Automática (monitor thread) | Manual (user restart) |
| **Complexidade** | Média (com supervisão) | Simples (direto) |
| **Performance** | Igual (mesmo modelo RL) | Igual (mesmo modelo RL) |

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

```
outputs/
├── agente_supervision.log           ← Agente RL 5000 (supervisão)
├── agente_debug.log                 ← Agente RL 5000 (debug)
├── agente_direto_20260316_112359.log ← Agente Direto (específico)
└── agente_direto_debug_20260316_112359.log ← Agente Direto debug
```

---

## Isolamento de Estado

### Base de Dados

Ambos usam o mesmo SQLite (trading.db), mas isolamento via:
- **session_id** em queries
- **Índices sobre session_id** para performance
- **FK constraints** para integridade

Tabelas relevantes:
```sql
-- Trades isolados por session
trades (session_id, ticket, symbol, direction, ...)
positions (session_id, ticket, symbol, open_price, ...)
execution_feedback (session_id, trade_id, outcome, ...)
```

### Memória

- Cada agente tem sua própria instância de:
  - `AgenteQLearning` (modelo em memória)
  - `ProfitProtectionEngine` (estado de proteção)
  - `RLRepository` (conexão DB)

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
python -c "import sys; sys.path.insert(0, '.'); from scripts.agente_rl_direto_independente import *; print('OK')"
```

### Posições ficando misturadas?
```sql
-- Verificar isolamento por session
SELECT session_id, COUNT(*) as positions FROM trades GROUP BY session_id;

-- Esperado: 2+ sessions com dados independentes
```

---

## Referência Rápida

| Comando | Efeito |
|---------|--------|
| `INICIAR_AGENTE_RL_5000.bat` | Inicia agente supervisionado |
| `INICIAR_AGENTE_RL_DIRETO.bat` | Inicia agente direto (novo terminal) |
| Ctrl+C | Para o agente atual |
| Abrir 2 terminais | Ambos rodam em paralelo |

---

## Commit & Histórico

- **Data:** 16/03/2026
- **Commit 1:** feat: Criar agente_rl_direto_independente.py com session isolada
- **Commit 2:** docs: Agentes RL paralelos - arquitetura independente
- **Status:** ✅ Pronto para uso paralelo
