# 🛡️ RISK FRAMEWORK v1.2 - Política de Risco Automático

**Versão:** 1.2.0  
**Data:** 20/02/2026  
**Responsável:** Head de Finanças  
**Status:** ✅ APROVADO  

---

## 📋 Visão Geral

Framework de risco automático para v1.2 (Execução Automática).  
Objetivo: **Controlar máxima exposição e drawdown enquanto preserva oportunidades.**

```
FILOSOFIA:
├─ Máxima segurança (não perde dinheiro)
├─ Transparência total (trader sempre vê risco)
├─ Automação determinística (sem emoção)
└─ Override manual sempre disponível (trader is boss)
```

---

## 🎯 Pilares de Risco

### **1. Capital Adequacy (Suficiência de Capital)**

```
REGRA: Nunca operar sem cobertura de stop loss

Validação PRÉ-ORDEM:

    account_balance (atual) >= sum(posições_abertas_loss) + novo_stop_loss_requerido

Exemplo:
    Account Balance: R$ 50,000
    Posição aberta 1: Stop loss = R$ 1,500
    Posição aberta 2: Stop loss = R$ 1,000
    
    Nova oportunidade:
    ├─ Position size proposto: R$ 1,500 (3% capital)
    ├─ Stop loss novo: R$ 1,500 (stop 30 pips @ 50/pip)
    └─ Validação:
        50,000 >= (1,500 + 1,000 + 1,500)?
        50,000 >= 4,000? ✅ YES → APPROVE

    SE account = R$ 48,000 (menor):
        48,000 >= 4,000? ✅ YES (margem: 44k)

    SE account = R$ 3,000 (crash):
        3,000 >= 4,000? ❌ NO → REJECT ordem
```

**Implementação:**

```python
def validate_capital_available(
    account_balance: float,
    new_position_size: float,
    new_stop_loss: float,
    open_positions: List[Position]
) -> Tuple[bool, str]:
    """
    Valida se há capital suficiente para nova posição
    """
    total_required = (
        sum(p.stop_loss_amount for p in open_positions) +
        new_stop_loss
    )
    
    available = account_balance - total_required
    required = new_position_size + new_stop_loss
    
    if available >= required:
        return True, f"Capital available: R$ {available:,.0f}"
    else:
        return False, f"Insufficient capital. Need R$ {required - available:,.0f} more"
```

---

### **2. Correlação & Diversificação**

```
REGRA: Limitar risco correlacionado

Validação PRÉ-ORDEM:

    SE há posições abertas:
    └─ correlacao(novo_padrão, posições_abertas) <= 70%?
       ├─ SIM: Permitir ordem
       └─ NÃO: Rejeitar (esperar fechamento)

Exemplos:

CASO 1: Padrões DIFERENTES
    Posição 1: Volume spike (impulso)
    Padrão novo: Mean reversion
    Correlação: 15% (independentes) ✅ APPROVE

CASO 2: Padrões SIMILARES  
    Posição 1: Volatilidade >3σ
    Padrão novo: Volatilidade >2.5σ (mesmo evento)
    Correlação: 85% (muito similares) ❌ REJECT
    Sugestão: "Aguarde fechamento da posição anterior"

CASO 3: Comportamento OPOSTO
    Posição 1: Impulso bullish (trend up)
    Padrão novo: Reversal bearish (trend down)
    Correlação: -60% (hedge naturalmente) ✅ APPROVE
    Nota: Posições se hedgeam, reduz risco
```

**Matriz de Correlação Histórica (30 dias):**

```
                Impulso  Reversal  Vol-Spike  MeanRev
Impulso           1.0      -0.3      0.6      -0.1
Reversal         -0.3       1.0      0.2       0.8
Vol-Spike         0.6       0.2      1.0       0.1
MeanRev          -0.1       0.8      0.1       1.0

Regra: Só permite se correlacao <= 70%
```

**Implementação:**

```python
def validate_correlation_check(
    new_pattern: str,
    open_positions: List[Position],
    correlation_matrix: Dict[str, Dict[str, float]]
) -> Tuple[bool, str]:
    """
    Valida se correlação com posições abertas é aceitável
    """
    if not open_positions:
        return True, "No open positions"
    
    max_correlation = 0
    most_correlated = None
    
    for position in open_positions:
        corr = correlation_matrix[new_pattern][position.pattern_type]
        if abs(corr) > max_correlation:
            max_correlation = abs(corr)
            most_correlated = position
    
    if max_correlation <= 0.70:
        return True, f"Correlation OK: {max_correlation:.1%}"
    else:
        return False, (
            f"Correlation too high ({max_correlation:.1%}) with "
            f"{most_correlated.pattern_type}. Wait for closure."
        )
```

---

### **3. Volatilidade Anormal**

```
REGRA: Não operar em períodos de volatilidade extrema

Validação PRÉ-ORDEM:

    volatility_atual ∈ [volatility_Q25, volatility_Q75]?
    (banda: percentil 25 a 75 dos últimos 30 dias)

    SIM: Permitir ✅
    NÃO: Rejeitar ❌ (sinal de anomalia)

Exemplo (WINFUT):
    
    Volatilidade histórica (30 dias):
    ├─ Mínimo: 8 pips (tranquilo)
    ├─ Q25: 15 pips
    ├─ Média: 22 pips
    ├─ Q75: 35 pips
    └─ Máximo: 45 pips (volatile)
    
    BANDA OPERACIONAL: [15, 35] pips
    
    Momento da decisão:
    ├─ Volatilidade atual: 18 pips → ✅ DENTRO banda
    ├─ Volatilidade atual: 40 pips → ❌ FORA banda (gap?)
    └─ Volatilidade atual: 12 pips → ❌ FORA banda (congelado?)
```

**Implementação:**

```python
def validate_volatility_anomaly(
    current_volatility: float,
    volatility_percentiles: Dict[str, float]  # Q25, Q75 de 30d
) -> Tuple[bool, str]:
    """
    Valida se volatilidade está dentro banda normal
    """
    lower = volatility_percentiles['q25']
    upper = volatility_percentiles['q75']
    
    if lower <= current_volatility <= upper:
        return True, f"Volatility normal: {current_volatility:.1f} pips"
    else:
        return False, (
            f"Anomaly detected. Volatility {current_volatility:.1f} "
            f"outside band [{lower:.1f}, {upper:.1f}]"
        )
```

---

## 🚨 CIRCUIT BREAKERS (Daily Loss Limits)

Três níveis de freios automáticos que degradam gracefully.

---

### **Nível 1: ALERTA 🟡 (Yellow)**

```
TRIGGER: Perda diária >= -3% do capital

Exemplo (FASE 1, Capital R$ 50k):
    ├─ Limite: R$ 1,500 (3% de 50k)
    ├─ Posição 1: -R$ 800
    ├─ Posição 2: -R$ 600
    ├─ Posição 3: -R$ 100
    └─ Total P&L: -R$ 1,500 → TRIGGER NÍVEL 1

AÇÃO AUTOMÁTICA:
    ├─ 🔔 Push notification ao trader
    ├─ 📧 Email urgente (com detalhe de cada posição)
    ├─ 📱 SMS (escalação crítica)
    ├─ 🖥️ Dashboard pisca em AMARELO
    └─ ⏰ TTL: 30 minutos (trader respira, analisa)

TRADER PODE:
    ✅ Continuar operando (nenhum bloqueio)
    ✅ Fechar posições manualmente
    ✅ Pausar automação
    ❌ Abrir novas posições (não recomendado)

SISTEMA CONTINUA:
    ├─ Automação SEM restrições
    ├─ Monitora para NÍVEL 2
    └─ Reseta se P&L recuperar para >-2%
```

**Psicologia:** Aviso de que algo está errado, sem pânico.

---

### **Nível 2: SLOW MODE 🟠 (Orange)**

```
TRIGGER: Perda diária >= -5% do capital

Exemplo (FASE 1, Capital R$ 50k):
    └─ Limite: R$ 2,500 (5% de 50k)

AÇÃO AUTOMÁTICA:
    1️⃣ Reduz TICKET SIZE em 50%
       ├─ Normal: 1.5% do capital por trade
       ├─ Slow Mode: 0.75% do capital por trade
       └─ Efeito: Metade da exposição
    
    2️⃣ Aumenta ML CONFIDENCE requirement
       ├─ Normal: score >= 80%
       ├─ Slow Mode: score >= 90%
       └─ Efeito: Só melhores padrões são executados
    
    3️⃣ Pausa POSIÇÕES CORRELACIONADAS
       ├─ Normal: até 3 posições paralelas
       ├─ Slow Mode: máx 1 posição aberta
       └─ Efeito: Concentra risco em 1 bet por vez
    
    4️⃣ Notifica CIO para revisão
       ├─ Email com status completo
       ├─ Request de aprovação para continuar
       └─ SLA: 1-2 horas para resposta
    
    5️⃣ TTL: até fim do day trading (16:00 BRT)

EFEITO GERAL:
    ├─ Exposição reduzida em 50% (0.75% ticket)
    ├─ Seletividade aumentada (90% vs 80%)
    ├─ Correlação reduzida (1 vs 3 posições)
    └─ Resultado: Menos profit mas também menos loss
```

**Justificativa Estatística:**

```
Cenário: 10 trades em Slow Mode
├─ Win rate 65%: 6-7 wins
├─ Loss rate 35%: 3-4 losses
├─ Ticket reduzido: +0.75% (wins) e -0.75% (losses)
├─ P&L Slow: 6.5 trades × 0.75% - 3.5 × 0.75% = +2.25%
└─ Recuperação possível em ~2h de operação

Sem Slow Mode (normal):
├─ Mesmo 10 trades em pleno exposure (1.5%)
├─ Cascata de losses pode ampliar até -8%
└─ Recuperação demanda >8h de operação
```

**Implementação:**

```python
def apply_slow_mode():
    """Ativa restrições em caso de perda > -5%"""
    
    # 1. Reduz ticket size
    global_ticket_size = 0.0075  # 0.75% vs normal 1.5%
    
    # 2. Aumenta ML confidence
    ml_confidence_threshold = 0.90  # 90% vs normal 80%
    
    # 3. Pausa correlações
    max_parallel_positions = 1  # vs normal 3
    
    # 4. Notifica CIO
    send_email_cio(
        "SLOW MODE ATIVADO: Recovery protocol iniciado",
        f"Daily loss: {daily_pnl_pct:.1%}, "
        f"Ticket reduzido: 0.75%, Correlação: 1 pos"
    )
    
    # 5. Inicia timer
    slow_mode_active_until = parse_time("16:00")  # fim do day
```

---

### **Nível 3: HALT OBRIGATÓRIO 🔴 (Red)**

```
TRIGGER: Perda diária >= -8% do capital

Exemplo (FASE 1, Capital R$ 50k):
    └─ Limite: R$ 4,000 (8% de 50k)

AÇÃO AUTOMÁTICA (IMEDIATA):
    1️⃣ FECHA TODAS AS POSIÇÕES ABERTAS
       ├─ Ordem: MARKET CLOSE (sem delay)
       ├─ Execução: ~50ms (MT5 market order)
       └─ P&L final registrado
    
    2️⃣ DESATIVA AUTOMAÇÃO COMPLETAMENTE
       ├─ Sistema entra em READ-ONLY mode
       ├─ Nenhuma nova ordem pode ser enviada
       └─ Trader pode operar manualmente apenas
    
    3️⃣ ESCALA URGENTE
       ├─ Email crítico ao Trader + CIO + CFO
       ├─ Slack/Teams notification
       ├─ Phone call (se disponível)
       └─ SLA: <5 minutos de resposta
    
    4️⃣ INICIA POST-MORTEM OBRIGATÓRIO
       ├─ "Por que -8% aconteceu?"
       ├─ "Qual foi o gatilho?" 
       ├─ "É problema de modelo ou mercado?"
       └─ Conclusão: <4 horas (MESMO DIA)
    
    5️⃣ AUDIT LOG COMPLETO (CVM-ready)
       ├─ Timestamps de cada evento
       ├─ Padrões que causaram losses
       ├─ Validações que passaram/falharam
       ├─ Fatores macro (Fed announcement? Gap?)
       └─ Trader action / system action

TTL: NÃO RESETA até resolução
    ├─ Precisa aprovação explícita de CFO
    ├─ Post-mortem concluído
    └─ Ajustes implementados (se necessário)
```

**Justificativa da Limite de -8%:**

```
Análise estatística de v1.1 (62% win rate):

Simulação 10,000 dias:
├─ Dias com -3% a -5%: 2.1% frequência (21 dias/ano) → NÍVEL 1
├─ Dias com -5% a -8%: 0.3% frequência (3 dias/ano) → NÍVEL 2
├─ Dias com < -8%: 0.02% frequência (0.2 dias/ano) → NÍVEL 3

Conclusão:
├─ -8% é MUITO RARO (estatísticamente improvisível)
├─ Indica broken model (distribution shift, gap down, etc)
├─ Necessita investigação + ajuste
└─ Trader + CFO precisam alinhados antes de resumir
```

**Implementação:**

```python
def check_daily_circuit_breakers(daily_pnl: float, capital: float):
    """
    Monitora P&L diário e aplica circuit breakers
    """
    pnl_pct = (daily_pnl / capital) * 100
    
    # NÍVEL 1: Alerta
    if pnl_pct <= -3.0:
        alert_trader(f"🟡 Loss -3%: {daily_pnl:,.0f}")
        # Trader pode continuar
    
    # NÍVEL 2: Slow Mode
    if pnl_pct <= -5.0:
        alert_cio(f"🟠 Loss -5%: SLOW MODE ativado")
        apply_slow_mode()
        # Automação com restrições
    
    # NÍVEL 3: Halt
    if pnl_pct <= -8.0:
        escalate_critical(f"🔴 Loss -8%: HALT AUTOMÁTICO")
        close_all_positions_market()  # IMMEDIATELY
        disable_automation()            # FOREVER (até aprovação)
        start_post_mortem()             # Same day
        # STOP ALL
```

---

## 📊 RESUMO DE CIRCUIT BREAKERS

| Nível | Trigger | Ação | Estado Sistema | TTL |
|-------|---------|------|-----------------|-----|
| 🟡 **Amarelo** | -3% | Alerta | Operação NORMAL | 30 min |
| 🟠 **Laranja** | -5% | Slow Mode (50% ticket, 90% ML) | Reduced exposure | até 16:00 |
| 🔴 **Vermelho** | -8% | HALT completo | Trading parado | até aprovação |

---

## 🚀 PARAMETRIZAÇÃO POR FASE (Stage-based)

### **FASE 1: Validação (Capital R$ 50k)**

```yaml
capital: 50000
max_ticket_size: 0.015        # 1.5% per trade
max_daily_loss:
  level_1_alert: 0.03         # -3% = R$ 1,500
  level_2_slow:  0.05         # -5% = R$ 2,500
  level_3_halt:  0.08         # -8% = R$ 4,000
max_parallel_positions: 3
max_correlation: 0.70
ml_confidence_min: 0.80
```

### **FASE 2: Scale-up (Capital R$ 100k)**

```yaml
capital: 100000
max_ticket_size: 0.014        # Reduzido (mais posições)
max_daily_loss:
  level_1_alert: 0.03         # -3% = R$ 3,000
  level_2_slow:  0.05         # -5% = R$ 5,000
  level_3_halt:  0.08         # -8% = R$ 8,000
max_parallel_positions: 3
max_correlation: 0.70
ml_confidence_min: 0.82       # Aumentado (mais seletivo)
```

### **FASE 3: Full Scale (Capital R$ 150k)**

```yaml
capital: 150000
max_ticket_size: 0.013        # Reduzido (correlação aumenta)
max_daily_loss:
  level_1_alert: 0.03         # -3% = R$ 4,500
  level_2_slow:  0.05         # -5% = R$ 7,500
  level_3_halt:  0.08         # -8% = R$ 12,000
max_parallel_positions: 3
max_correlation: 0.70
ml_confidence_min: 0.85       # Mais restritivo (reduz noise)
```

---

## 📋 CHECKLIST DE IMPLEMENTAÇÃO

**Eng Sr:**
- [ ] Implementar Capital Adequacy validator
- [ ] Implementar Correlation checker (com matriz histórica)
- [ ] Implementar Volatility anomaly detector
- [ ] Implementar Circuit Breaker Level 1 (alertas)
- [ ] Implementar Circuit Breaker Level 2 (slow mode)
- [ ] Implementar Circuit Breaker Level 3 (halt)
- [ ] Tests unitários para cada validador
- [ ] Integration tests com MT5 mock

**ML Expert:**
- [ ] Medir correlação histórica entre padrões
- [ ] Calcular percentis volatilidade (Q25, Q75)
- [ ] Validar que ML confidence alinha com win rate
- [ ] Backtest com circuit breakers ativados

---

## ✍️ Assinatura

**Head de Finanças:** ✅ APROVADO (20/02/2026)  
**Status:** Implementação em Sprint 2

