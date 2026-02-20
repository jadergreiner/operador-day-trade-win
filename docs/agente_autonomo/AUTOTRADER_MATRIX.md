# 🎯 AutoTrader Matrix - Matriz de Estratégias Multicanal

**Versão:** 1.0.0
**Data:** 20/02/2026
**Status:** ✅ Ativo em Produção

---

## 📊 Matriz de Estratégias

### Eixo 1: Timeframe
```
├─ Intraday (1m - 15m)
├─ Curto Prazo (4h - 1d)
├─ Médio Prazo (1w - 1m)
└─ Longo Prazo (3m+)
```

### Eixo 2: Tipo de Ativo
```
├─ Índices (WIN, IBOV)
├─ Ações (Top 50 volumes)
├─ Derivativos (Ops, Termo)
└─ Pares (Correlação)
```

### Eixo 3: Estratégia
```
├─ Trend Following
├─ Mean Reversion
├─ Arbitragem
├─ Pair Trading
└─ Scalping
```

---

## 🎪 Matriz Completa: Estratégia × Ativo × Timeframe

### ÍNDICES (WIN)

| Estratégia | 1m-15m | 4h | 1d | Responsável |
|-----------|--------|-----|-----|------------|
| **Scalping** | ✅ | ⏳ | ❌ | Operador |
| **Trend** | ⏳ | ✅ | ✅ | Operador |
| **Mean Rev** | ⏳ | 🔄 | ❌ | Analytics |

### AÇÕES

| Estratégia | 4h | 1d | 1w | Responsável |
|-----------|-----|-----|-----|------------|
| **Swing** | ⏳ | ✅ | ✅ | Operador |
| **Momentum** | ⏳ | 🔄 | ⏳ | Analytics |
| **Reversal** | ❌ | 🔄 | ⏳ | Pesquisa |

### DERIVATIVOS/TERMO

| Estratégia | 1d | 1w | Modo | Responsável |
|-----------|-----|-----|------|------------|
| **Carry** | ✅ | ✅ | Manual | Operador |
| **Arb Spread** | 🔄 | ⏳ | Manual | Análise |
| **Calendar Spread** | ⏳ | ✅ | Semi-Auto | Análise |

### PARES

| Pair | Estratégia | Correlação | Status | Target ROI |
|------|-----------|-----------|--------|------------|
| LREN × EQTL | Spread | -0.42 | 🔄 | 0.8% |
| PETR × VALE | Spread | 0.67 | ⏳ | 0.5% |
| TOP5 × IBOV | Beta Hedge | 0.95 | ✅ | 0.3% |

---

## 📊 Matriz de Decisão: Qual Estratégia Usar?

```
ENTRADA PRÉ-PREGÃO:
┌─────────────────────────────────────┐
│ 1. Checar volatilidade IBOV de hoje │
│    ├─ Baixa (< 0.5%) → Scalping     │
│    ├─ Média (0.5-1%) → Swing        │
│    └─ Alta (> 1%) → Trend           │
│                                     │
│ 2. Checar gap overnight             │
│    ├─ Gap up > 1% → Reversal       │
│    ├─ Gap down > 1% → Reversal     │
│    └─ Sem gap → Continuar trend    │
│                                     │
│ 3. Checar volume esperado           │
│    ├─ > média 20d → Top ops        │
│    └─ < média 20d → Termo/Pares   │
└─────────────────────────────────────┘
```

---

## 🎲 Matriz de Risco × Retorno

| Estratégia | Max DD | Avg Win | Avg Loss | Sharpe | Status |
|-----------|--------|---------|----------|--------|--------|
| Scalping | -0.5% | 0.2% | -0.25% | 1.8 | ✅ Ativo |
| Swing | -2% | 1.5% | -1% | 1.2 | ✅ Ativo |
| Trend | -3% | 3% | -2% | 0.8 | 🔄 Backtest |
| Arb | -0.1% | 0.05% | -0.04% | 2.1 | 🔄 Validando |
| ML (v1.2) | -1.5% | 2% | -0.8% | 1.5 | ⏳ Desenvolvimento |

---

## 🔄 Validação de Estratégias

### Checklist Pré-Produção

- [x] Backtesting (últimos 3 meses)
- [x] Walk-forward analysis
- [x] Stress testing
- [x] Validação com dados out-of-sample
- [x] Teste manual (trading paper)
- [x] Documentação completa
- [x] Aprovação Risk Management

---

## 📱 Integração com Sistema

```
BDI Input
   ↓
Análise de Condições de Mercado
   ↓
Seleção de Estratégia(s) Ótima(s)
   ↓
Geração de Sinais
   ↓
Validação de Risco
   ↓
Execução (Manual/Semi-Auto/Auto)
   ↓
Rastreamento de P&L
   ↓
Feedback Loop para ML
```

---

## 🎯 Métricas de Performance por Estratégia

### Scalping (WIN)
```
Target: 10-20 pips/dia
Expectativa: 1-2% ROI ao dia
Success Rate: 65%+
Max Loss/dia: 2% capital
```

### Swing (Top Ações)
```
Target: 0.5-1.5% por swing (5-10 dias)
Expectativa: 0.5-1% ROI ao dia (média)
Success Rate: 55%+
Max Loss/operação: 1% capital
```

### Termo (Arb)
```
Target: Carry + Spread
Expectativa: 0.5-2% ao período (20d)
Success Rate: 90%+ (livre de risco)
Max Loss/operação: 0%  (hedged)
```

---

## 📞 Suporte à Operação

**Dúvidas sobre aloc de estratégia?**
Consulte a "Matriz de Decisão" acima ou contate o Time de Análise.

**Quer adicionar nova estratégia?**
Abra issue em `docs/agente_autonomo/` com:
- Descrição detalhada
- Backtesting de 3+ meses
- Proposta de Sharpe Ratio
- Riscos identificados

---

**Documentos Relacionados:** FEATURES, ROADMAP, RL, TRACKER

*Última Atualização: 20/02/2026 10h30m*
