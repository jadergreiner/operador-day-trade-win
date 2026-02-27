# 📊 Inventário de Persistência de Dados - Operador Quantitativo WIN

**Data:** 27/02/2026
**Auditoria:** Reunião Virtual Sprint 1 - Blocker Analysis
**Status:** ✅ CONSOLIDADO E VALIDADO
**Responsável:** Data Engineer + Facilitador

---

## 🎯 Resumo Executivo

```
┌─────────────────────────────────────────────────┐
│ FONTE DE VERDADE: data/db/trading.db            │
│                                                 │
│ Contém: Trades, RLs, Logs, Métricas            │
│ Referências: 45+ scripts Python                │
│ Status: ✅ ATIVO E VALIDADO                    │
│ Crítica: 🔴 MÁXIMA - Não fragmentar!           │
└─────────────────────────────────────────────────┘
```

---

## 📁 Mapeamento Completo de Bancos

### ✅ BANCO PRIMÁRIO (Produção)

#### `data/db/trading.db` (SQLite)

**Referências Confirmadas (45+ scripts):**
- monitor_execution_live.py
- migrate_add_execution_method.py
- identify_manual_operation.py
- get_order_numbers.py
- fix_order_sync.py
- cleanup_dados_automatico.py
- check_rl_table.py
- check_rl_rewards_table.py
- check_interseção.py
- check_episode_ids.py
- check_order_creator.py
- analyze_order_origin.py
- analyze_critical_failure.py
- analyze_historical_patterns.py
- analise_rl_training.py
- analise_operacao_encerramento_26fev.py
- register_manual_closure.py
- recover_historical_sl_tp.py
- debug_matching.py
- **+ 25 mais...**

**Tabelas Principais:**
```
trades                    // Execuções MT5
rl_episodes              // Episódios de treinamento RL
rl_rewards               // Rewards RL
rl_training_metrics      // Métricas históricas RL
market_data             // Dados OHLCV
features                // Features engenheiradas (24)
predictions             // Previsões do modelo
decisions               // Decisões do sistema
manual_activities       // Intervenções trader
trading_journal_logs    // Logs de journal
rl_training_history     // Histórico de treinamento
```

**Configuração Oficial:**
```
config/settings.py:
  db_path: str = Field(default="data/db/trading.db", env='DB_PATH')

config/rl_scheduler_config.json:
  "path": "data/db/trading.db"

.env.example:
  DB_PATH=data/db/trading.db
```

**Status Sprint 1:**
- ✅ ATIVO
- ✅ VALIDADO
- ✅ 45+ referências
- ✅ Contém RLs + Trades

---

### ❌ DEPRECATED (Não Usar!)

#### `data/analytics.db` (SQLite)
- **Status:** ORPHANED
- **Motivo:** Nunca referenciado em código produção (Sprint 1)
- **Ação:** REMOVER ou investigar propósito
- **Risco:** Fragmentação de dados se mantido

#### `data/analytics_staging.db` (SQLite)
- **Status:** LEGACY (S2-6 deprecated)
- **Motivo:** Referenciado em `.env.staging` mas não em código ativo
- **Ação:** Deprecar formalmente em Phase 2
- **Risco:** Confusão com analytics.db

---

### ❓ INVESTIGAÇÃO NECESSÁRIA

#### `data/db/wdo_winfut.db` (SQLite)
- **Referências:** diario_overnight_20260211.md
- **Propósito:** Dados WDO/WINFUT históricos?
- **Status:** DESCONHECIDO
- **Ação:** Validar uso + documentar ou remover
- **Criticidade:** 🟡 MÉDIA

---

### 🔄 EM DESENVOLVIMENTO

#### `data/db/alertas_audit.db` (SQLite - Planejado)
- **Ref:** PROXIMOS_PASSOS_INTEGRACAO.md
- **Propósito:** Auditoria de alertas
- **Timeline:** Phase 2
- **Status:** 🔄 PLANEJADO

#### `data/simulator.db` (SQLite - Dev Only)
- **Uso:** Diagnóstico e testes locais
- **Scripts:** diagnostico_simples.py, diagnostico_rapido.py
- **Status:** ✅ DEV ONLY (não usar produção)

---

### 🌐 CLOUD (Phase 4+)

#### PostgreSQL Azure
- **Host:** operador-db-staging.postgres.database.azure.com
- **Database:** operador_db_staging
- **Timeline:** Phase 4 (10/04/2026+)
- **Status:** 🔄 PROVISIONING
- **Propósito:** Cloud production database

---

## 🎯 Garantias de Integridade (SLA)

| Tipo de Dado | Banco | SLA | Validação | Crítica |
|---|---|---|---|---|
| Trades | trading.db | 100ms persistência | MT5 ↔ DB 1:1 | 🔴 CRÍTICA |
| RL Episodes | trading.db | 1s | episode_id validado | 🔴 CRÍTICA |
| RL Rewards | trading.db | 1s | linking c/ episodes | 🔴 CRÍTICA |
| Manual Interv | trading.db | 500ms | Audit trail | 🔴 CRÍTICA |
| Journal Logs | trading.db | 5s | Completude | 🟡 ALTA |
| Market Data | trading.db | 100ms | Sem gaps | 🟡 ALTA |
| Predictions | trading.db | 500ms | Sync c/ trades | 🟡 ALTA |

---

## 🔧 Quick Reference - Troubleshooting

### "Não encontro trade de hoje"
1. ✅ Verificar: `data/db/trading.db` (não `analytics.db`!)
2. Query: `SELECT * FROM trades WHERE date(timestamp) = date('now')`
3. Se vazio: Checar `sync_mt5_trades_to_db.py` execution logs

### "RLs não aparecem"
1. ✅ Verificar: `data/db/trading.db` tabela `rl_episodes`
2. Query: `SELECT COUNT(*) FROM rl_episodes`
3. Se 0: Executar `scripts/rl_training_loop_v3.py`

### "Qual banco devo consultar?"
**RESPOSTA:** `data/db/trading.db` (sempre!)
- Não consulte `analytics.db` (orphaned)
- Não consulte `analytics_staging.db` (legacy)

### "Scripts estão 100% corretos mas dados sumiram"
1. Verificação dupla: Checar `trading.db` vs `analytics.db`
2. Possível duplicação de lógica → Consolidar em 1 banco
3. Revisar: Há integração dupla rodando? (risk de fragmentação)

---

## 📋 Checklist de Sincronização (Daily)

- [ ] `data/db/trading.db` contém trades de hoje (MT5 sync)
- [ ] RLs foram treinados (check `rl_training_metrics` timestamp)
- [ ] Nenhum trade em `analytics.db` (deve estar vazio!)
- [ ] `wdo_winfut.db` sincronizados (se aplicável)
- [ ] Backup automático de `trading.db` executado (22:00 BRT)
- [ ] Logs de sincronização sem erros
- [ ] Alertas de banco cheio? (disk space check)

---

## 🚀 Migrações & Mudanças Futuras

### Phase 2 (Próximos 30 dias)
- [ ] Deprecar formalmente `analytics_staging.db`
- [ ] Investigar e documentar propósito de `wdo_winfut.db`
- [ ] Eliminar `analytics.db` (se comprovadamente orphaned)
- [ ] Implementar `alertas_audit.db` (se planejado)

### Phase 4 (10/04/2026+)
- [ ] Migração SQLite → PostgreSQL Azure
- [ ] Replicação em tempo real (dual-write durante transição)
- [ ] Validação de integridade pós-migração
- [ ] Deprecar SQLite (backup only)

---

## 📞 Escalações & Contatos

| Questão | Responsável | Contato |
|---|---|---|
| Estrutura de trades | Executor Técnico (#10) | executor@operador-day-trade-win.local |
| RL episodes/rewards | ML Expert (#4) | ml.expert@operador-day-trade-win.local |
| Sincronização dados | Data Engineer (#11) | data@operador-day-trade-win.local |
| Auditoria/Compliance | Compliance Officer (#15) | compliance@operador-day-trade-win.local |
| Arquitetura geral | Eng Sr (#3) | engsr@operador-day-trade-win.local |

---

## 📚 Documentos Relacionados

- [ARCHITECTURE.md](ARCHITECTURE.md) - Arquitetura técnica completa
- [PERSISTENCE_GUARANTEE_PROTOCOL.md](PERSISTENCE_GUARANTEE_PROTOCOL.md) - Protocolo de garantia
- [STATUS_ENTREGAS.md](STATUS_ENTREGAS.md) - Status de desenvolvimento
- [CHANGELOG.md](../CHANGELOG.md) - Histórico de mudanças

---

**Última Verificação:** 27/02/2026 15:00 BRT
**Validado por:** Facilitador Reunião Virtual
**Status:** ✅ CONSOLIDADO
