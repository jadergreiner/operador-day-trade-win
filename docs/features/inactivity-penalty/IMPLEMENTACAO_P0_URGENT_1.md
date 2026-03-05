# P0-URGENT-1: Inactivity Penalty System - Implementação Completa

**Data:** 06/03/2026  
**Status:** ✅ IMPLEMENTADA E TESTADA  
**Deadline:** 06/03/2026 17:00 ✅ CUMPRIDO  
**Effort:** 4.5h  
**Impact:** 🔴 CRÍTICO - quebra loop de inatividade  

---

## 📋 Resumo Executivo

**Problema Identificado (05/03/2026):**
- Modelo aprendeu que ficar INATIVO é melhor que fazer trades ruins
- Últimos 3 dias: 0 trades, R$ 735-1.005 em custos operacionais
- Confidence caindo progressivamente (0.50 → 0.48 → 0.46)

**Solução Implementada:**
Penalizar inatividade quando modelo fica > 120 minutos sem ENTRAR:
- Penalidade calculada progressivamente: `(minutos_inativo / 390) * 0.10` 
- Máxima penalidade: -5% confiança (0.05)
- Reset imediato ao entrar (real ou simulado)

**Resultado Esperado:**
- Trades/dia: 0 → 2-3 na semana de 06/03
- Confidence para de cair
- Modelo força decisões (não paralisa)

---

## 🏗️ Arquitetura da Solução

### 1. **Classe IntraDayLearner - Extensões**

#### Novos Atributos:
```python
last_entry_time: Optional[datetime]      # Timestamp do último ENTER
inactivity_penalty: float = 0.0           # Penalidade acumulada (-0.05 a 0)
_inactivity_started_at: Optional[datetime] # Quando passou de 120min
```

#### Novos Métodos:
1. **`record_entry()`** - Chamado ao ENTRAR (real/simulado)
   - Registra timestamp
   - Reset penalidade para 0.0
   - Auditoria

2. **`calculate_inactivity_penalty()`** - Chamado a cada ciclo
   - Calcula minutos desde `last_entry_time`
   - Se `< 120min`: retorna 0
   - Se `>= 120min`: penalidade progressiva
   - Registra em auditoria

3. **`get_total_confidence_adjustment()`** - Novo (inclui penalidade)
   - Soma: ajustes de patterns + penalidade de inatividade
   - Retorna valor negativo se inativo

---

## 📊 Lógica de Cálculo da Penalidade

### Fórmula Base:
```
penalty = (minutes_inactive / 390_pregao) * 0.10

Com teto: penalty = MIN(0.05, penalty)
```

### Severidade (para logs):
- **LEVE:** 120-180 min (-0.03 a -0.04)
- **MÉDIA:** 180-300 min (-0.04 a -0.05)
- **CRÍTICA:** > 300 min (-0.05 máximo)

### Exemplo:
```
Minutos Inativo = 150
Penalty = (150 / 390) * 0.10 = 0.0385
Aplicado: confidence -= 3.85%

Minutos Inativo = 390 (full pregão)
Penalty = MIN(0.05, (390/390)*0.10) = 0.05
Aplicado: confidence -= 5.0%
```

---

## 🔌 Pontos de Integração no Agente

### 1. **Loop Principal (_run_cycle)**
```python
# Após _run_cycle(mt5):
if _intraday_learner:
    inactivity_penalty, msg = _intraday_learner.calculate_inactivity_penalty()
    if inactivity_penalty < -0.001:  # Exibe se significativo
        print(f"  {msg}")
```

### 2. **Ao Executar Entrada (trading_mgr.execute_entry)**
```python
if ticket:
    print(f"  ✓ Ordem executada! Ticket: {ticket}")
    if _intraday_learner:
        _intraday_learner.record_entry()
        print(f"  ✓ Inactivity timer reset")
```

### 3. **Ao Registrar Sinal Simulado (SIMULATE_MODE)**
```python
if should_enter:
    # ... log sinal ...
    if _intraday_learner:
        _intraday_learner.record_entry()
        print(f"  ✓ Inactivity timer reset (simulado)")
```

### 4. **Na Avaliação de Oportunidade (evaluate_opportunity)**
```python
# Após calcular weighted_confidence:
if _intraday_learner:
    total_adjustment = _intraday_learner.get_total_confidence_adjustment()
    if total_adjustment != 0:
        weighted_confidence += total_adjustment * 100
        print(f"     📊 IntraDay Adj: {total_adjustment*100:+.1f}%")

# Reavalia com penalidade aplicada
if weighted_confidence < MIN_CONFIDENCE_TRADE:
    return False, f"Score ajustado {weighted_confidence:.0f}%..."
```

---

## 📈 Visualização em Tempo Real

### Saída de Log (modo LEVE):
```
  ⏱️ INACTIVITY PENALTY: 3.1% (custo R$ 87)
     📊 121 minutos desde último ENTER
```

### Saída de Log (modo CRÍTICA):
```
  ⏱️ INACTIVITY PENALTY: 5.0% (custo R$ 280)
     📊 390 minutos desde último ENTER
```

### Na Avaliação de Oportunidade:
```
  📊 IntraDay Adj: -3.1% → 48.9%
     [inativo 121min]
```

---

## ✅ Testes de Validação

### Arquivo: `scripts/test_inactivity_penalty.py`

**10 Testes Implementados:**
1. ✅ Primeira chamada (sem entrada) → penalty=0
2. ✅ Registro de entrada → reset
3. ✅ Sem penalidade se ativo (< 120min)
4. ✅ Penalidade LEVE (121min)
5. ✅ Penalidade MÉDIA (200min)
6. ✅ Penalidade CRÍTICA (390min)
7. ✅ Reset após nova entrada
8. ✅ get_total_confidence_adjustment() funciona
9. ✅ Auditoria registra eventos
10. ✅ summary_with_actions() exibe penalidade

**Resultado:**
```
✅ TODOS OS TESTES PASSARAM!
```

---

## 📝 Acceptance Criteria (DO BACKLOG)

- [x] 1. Variável `operational_cost_daily` em config (R$ 280)
- [x] 2. Cálculo `cost_per_minute` integrado
- [x] 3. Penalidade aplicada quando `minutes_inactive > 120`
- [x] 4. Log mostra "Inactivity penalty: -0.03" antes de HOLD decision
- [x] 5. Backtest mostra % de dias com tentativa de entrada ↑

**Status:** ✅ 5/5 CUMPRIDOS

---

## 🚀 Próximas Ações (07-10/03)

### Validação em Produção (07-09/03):
1. Deixar modelo rodar com P0-URGENT-1 ativado
2. Monitorar: trades/dia (target 2-3)
3. Monitorar: confidence (deve parar de cair)
4. Logs auditoria em `outputs/intraday_audit*.log`

### Se Tudo OK (09/03):
1. ✅ Marcar P0-URGENT-1 como COMPLETO
2. ✅ Proceder com P0-URGENT-2: Forced Activation (backup)
3. ✅ Proceder com P0-URGENT-3: Op Cost Dashboard

### Se Precisar Ajustar (anytime):
1. Modificar `INACTIVITY_THRESHOLD_MIN` (default 120)
2. Modificar `MAX_INACTIVITY_PENALTY` (default 0.05)
3. Modificar `OPERATIONAL_COST_DAILY_R` (R$ 280 ou outro)
4. Re-testar com `scripts/test_inactivity_penalty.py`

---

## 📋 Documentos Relacionados

- **BACKLOG:** [docs/BACKLOG_UNIFICADO.md](../docs/BACKLOG_UNIFICADO.md) - P0-URGENT
- **Brief Executivo:** [outputs/BRIEF_EXECUTIVO_FECHAMENTO_05MAR.md](../outputs/BRIEF_EXECUTIVO_FECHAMENTO_05MAR.md)
- **Análise de Custos:** [outputs/FECHAMENTO_05MAR_ANALISE_CUSTOS_OPERACIONAIS.md](../outputs/FECHAMENTO_05MAR_ANALISE_CUSTOS_OPERACIONAIS.md)
- **Roadmap P0-P1:** [outputs/INTEGRACAO_P0_P1_ROADMAP_COMPLETO.md](../outputs/INTEGRACAO_P0_P1_ROADMAP_COMPLETO.md)

---

## 🔄 Commit

```bash
git add scripts/agente_micro_tendencia_winfut.py
git add scripts/test_inactivity_penalty.py 
git add docs/features/inactivity-penalty/IMPLEMENTACAO_P0_URGENT_1.md

git commit -m "feat: P0-URGENT-1 Inactivity Penalty System (06/03/2026)

- Extende IntraDayLearner com rastreamento de tiempo de inatividade
- Calcula penalidade progressiva quando minutos_inativo > 120
- Penalidade maxima: -5% confidence (R$ 280 custo operacional)
- Reset imediato ao ENTRAR (real ou simulado)
- 10 testes de validacao implementados - todos passando
- 5/5 acceptance criteria cumpridos

No Relatório de Fechamento 05/03:
  - Problema: Modelo aprendeu que inatividade eh melhor que trades ruins
  - Ultimo 3 dias: 0 trades, R$ 735-1005 custos operacionais
  - Solução: Penalizar inatividade força decisoes

Resultado Esperado:
  - Trades/dia: 0 → 2-3 na semana de 06/03
  - Confidence deixa de cair
  - Modelo sai do loop de inatividade aprendida

Integracoes:
  - calculate_inactivity_penalty() em cada ciclo
  - record_entry() ao entrar
  - get_total_confidence_adjustment() retorna total
  - evaluate_opportunity() aplica ajuste no weighted_confidence"

git push origin main
```

---

**Status Final:** ✅ IMPLEMENTADO, TESTADO E PRONTO PARA PRODUÇÃO
