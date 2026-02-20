# 🤖 Guia de Auto-Trading Automático - WIN$N (WinJ26)

**Status:** ✅ ATIVO E MONITORANDO

## 1. Fluxo de Execução Automática

```
DETECTOR (T4)
   ↓ Monitora velas 5M
   ↓ Detecta spike de volatilidade
   ├─→ [ALERTAssistant] (com score)
   │
   ↓
RISK VALIDATOR (T2)
   ├─→ Gate 1: Capital disponível? (R$ 5k)
   ├─→ Gate 2: Correlação OK? (<70%)
   ├─→ Gate 3: Volatilidade dentro limites?
   │
   └─→ Todas as gates = PASS?
       ├─→ SIM: Próximo
       └─→ NÃO: REJEITA oportunidade
   │
   ↓
ORDERS EXECUTOR (T3)
   ├─→ Estado 1: ENQUEUED
   ├─→ Estado 2: VALIDATED
   ├─→ Estado 3: SENT → MT5
   ├─→ Estado 4: ACCEPTED
   ├─→ Estado 5: EXECUTED
   ├─→ Estado 6: FILLED
   ├─→ Estados 7-10: Monitoring/Close
   │
   ↓
MT5 BROKER (T1)
   └─→ ORDEM EXECUTADA NO WIN$N (WinJ26)
       └─→ Entrada automática
       └─→ SL + TP automáticos
       └─→ Stop Loss: -2% (R$ 100)
       └─→ Take Profit: +3% a +5%

   ↓
DASHBOARD (T5)
   └─→ TEMPO REAL
       ├─→ Ordem enviada?
       ├─→ Fill price?
       ├─→ P&L atual?
       └─→ Status execução?
```

## 2. Configuração Ativa

```yaml
AUTO-TRADING ATIVO:
  ✅ Capital: R$ 5.000
  ✅ Contrato: WIN$N (WinJ26)
  ✅ Lote: 1 contrato
  ✅ Timeframe: 5 minutos
  ✅ ML Threshold: 90% confiança
  ✅ Auto-Trade: ENABLED
```

## 3. Gatilhos de Execução

### ✅ Ordem será EXECUTADA quando:

1. **Detector identifica oportunidade**
   - Volatilidade > 2.0σ (desvio padrão)
   - Score ML ≥ 90%
   - Padrão detectado

2. **RiskValidator APROVA (3 gates)**
   - ✅ Gate 1: Capital disponível (R$ 5k > R$ 100)
   - ✅ Gate 2: Correlação OK (<70%)
   - ✅ Gate 3: Volatilidade < 3σ (não extrema)

3. **OrdersExecutor envia ao MT5**
   - Entrada: Entrada automática no mercado
   - SL: -100 pontos (Stop Loss de R$ 100)
   - TP: +150-250 pontos (alvo dinâmico)

### ❌ Ordem será REJEITADA quando:

- [ ] Capital insuficiente
- [ ] Correlação > 70% (risco sistêmico)
- [ ] Volatilidade extrema (>3.0σ)
- [ ] Trader não monitorando (se requirido)
- [ ] Drawdown diário > -2% (R$ 100)

## 4. Monitoramento em Tempo Real

### Dashboard Ativo: http://localhost:8765/dashboard

Monitora:
- 🟢 Status de conexão
- 📊 Total de alertas
- 🚨 Alertas em tempo real
- 💰 P&L por trade
- ⏱️ Latência de execução

## 5. Controle Manual (Trader)

### ⚠️ AVISO CRÍTICO:

Mesmo com auto-trade ATIVO, o trader DEVE monitorar:

1. **Dashboard aberto** (http://localhost:8765/dashboard)
2. **Verificar cada ordem** antes de execução
3. **Veto manual** disponível (pausar programa)
4. **Circuit breaker** ativo: -3% = HALT tudo

### Comandos de Controle:

- **Pausar trades**: `Ctrl+C` em T3 (OrdersExecutor)
- **Ver logs**: `logs/producao/`
- **Status**: `GET http://localhost:8765/metrics`
- **Kill tudo**: `Ctrl+C` em qualquer terminal

## 6. Logs e Auditoria

Todos os trades são registrados em:

```
logs/producao/
├─ detector_alertas.jsonl
├─ validador_risco.jsonl
├─ executor_ordens.jsonl
└─ audit_trail_completo.json (CVM-ready)
```

Cada registro contém:
- Timestamp exato
- Decisão (AUTORIZADO/REJEITADO)
- Motivo
- Parâmetros usados
- P&L resultado

## 7. Próximos Passos

### ✅ AGORA (20/02 20:45):
- [x] Auto-trade ATIVO
- [x] Detector monitorando
- [x] 5 terminais RUNNING
- [x] Dashboard LIVE

### 📊 HOJE/AMANHÃ (21/02):
- [ ] Trader inicia monitoramento 24h
- [ ] Aguardar primeira oportunidade
- [ ] Validar primeira execução
- [ ] Coletar dados de performance

### 📈 ESTA SEMANA (24-27/02):
- [ ] Coleta de dados para GATE 1
- [ ] Análise de win rate real
- [ ] Validação de latência P95

### 🚀 PROXIMA SEMANA (27/02-05/03):
- [ ] SPRINT 1 Kickoff
- [ ] ML training em paralelo
- [ ] Feature engineering
- [ ] GATE 1 Review (05/03)

---

## ⚡ Ação Rápida

```bash
# Ver logs em tempo real
tail -f logs/producao/detector_alertas.jsonl

# Ver status das 5 terminais
ps aux | grep python

# Ver dashboard
open http://localhost:8765/dashboard
```

---

**Status:** 🟢 PRODUCAO ATIVA
**Data:** 20/02/2026 20:45 UTC
**Capital em Risco:** R$ 5.000
**Contrato:** WIN$N (WinJ26)
**Auto-Trading:** ✅ HABILITADO
