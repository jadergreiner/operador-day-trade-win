# 7️⃣ PLANO DE EXECUÇÃO - 7 PASSOS SEQUENCIAIS

**Data:** 06/03/2026  
**Status:** Estrutura para execução imediata  
**Responsável:** GitHub Copilot + Time Técnico

---

## PASSO 1: Revisar P0-URGENT-1 com Stakeholders (45 min)

### O Que Apresentar:

**Problema (2 min):**
```
Contexto:
  - Modelo aprendeu que inatividade é melhor que trades ruins
  - Últimos 3 dias: 0 trades, R$ 735-1.005 custos operacionais
  - Confidence caindo: 0.50 → 0.48 → 0.46
  
Impacto:
  - Loop de não-decisão = "melhor não fazer nada"
  - Custo fixo de operação sem receita
  - Modelo estagnado desde 03/03
```

**Solução (3 min):**
```
Penalidade Progressiva por Inatividade:
  121 minutos   → -3.1% confiança (R$ 87 custo)
  200 minutos   → -5.0% confiança (R$ 144 custo)
  390 minutos   → -5.0% confiança (R$ 280 custo)
  
Reset: Imediato ao ENTRAR em trade
Objetivo: Forçar modelo a tentar novamente
```

**Evidência (5 min):**
```
✅ 10 testes criados - todos PASSANDO
✅ 5/5 acceptance criteria atendidos
✅ Code syntax validado (py_compile OK)
✅ 150 LOC integradas ao agente principal
✅ Logs implementados para auditoria

Arquivo Evidência: scripts/test_inactivity_penalty.py
```

**Timeline (5 min):**
```
Hoje (06/03):   Deploy staging
Amanhã (07/03):  Ativar em produção
Dias 07-09:      Monitorar 3 dias
Esperado:        Trades 0 → 2-3 na semana
```

**Riscos & Mitigação (10 min):**
```
Risco 1: Penalidade muito agressiva
  → Mitigação: Ajustar constantes se necessário, rollback pronto

Risco 2: Confidence continua caindo
  → Mitigação: Revisar threshold (pode estar muito alto), P0-URGENT-2 backup

Risco 3: Agent crash
  → Mitigação: Backup completo trading.db, rollback automático

Risco 4: Penalidade ativa em momento errado
  → Mitigação: Logs detalhados para auditoria, pode desativar via config
```

**Q&A (15 min):**
```
Perguntas Esperadas:
1. "E se não funcionar?" → P0-URGENT-2 em backup
2. "Quanto tempo para ver resultado?" → 3 dias mínimo
3. "Pode afetar trades atuais?" → Não, apenas força decisões
4. "Como faço rollback?" → 1 minuto com backup
```

### Checklist Pré-Reunião:
- [ ] Ler IMPLEMENTACAO_P0_URGENT_1.md
- [ ] Rodar testes 1x: `python scripts/test_inactivity_penalty.py`
- [ ] Preparar graphs de confidence trend (histórico)
- [ ] Ter rollback plan escrito
- [ ] Contactar stakeholders 2h antes

### Participantes Necessários:
- [ ] ML Expert (validar lógica)
- [ ] Head Finanças (aprovar R$ 280 base)
- [ ] CTO (integração OK)
- [ ] Operador (teste no staging)

### Saída Esperada:
✅ **Aprovação de 3/4 personas** para proceder com deploy

---

## PASSO 2: Deploy para Staging (30 min)

### Pré-Requisitos:
- [ ] P0-URGENT-1 aprovado por stakeholders
- [ ] Backup de trading.db criado
- [ ] Testes passando

### Procedimento:

```bash
# Terminal - Passo 2.1: Backup do banco atual
cd c:\repo\operador-day-trade-win
dir data\db\trading.db

# Copiar para backup
copy data\db\trading.db data\db\trading.db.backup_06mar

# Verificar que foi criado
dir data\db\trading.db*
# Esperado: trading.db + trading.db.backup_06mar
```

```bash
# Terminal - Passo 2.2: Validar código
python -m py_compile scripts/agente_micro_tendencia_winfut.py
# Esperado: Sem erro = sintaxe OK

python -m py_compile scripts/test_inactivity_penalty.py
# Esperado: Sem erro
```

```bash
# Terminal - Passo 2.3: Rodar testes em staging
python scripts/test_inactivity_penalty.py

# Esperado:
# TEST 1: ✓ PASS
# TEST 2: ✓ PASS
# ...
# TEST 10: ✓ PASS
# TODOS OS TESTES PASSARAM!
```

```bash
# Terminal - Passo 2.4: Iniciar agent em staging (modo teste)
# IMPORTANTE: Comente líneas de MT5 real (use simulator)
# Arquivo config: config/settings.py → MT5_SIMULATOR_MODE = True

python scripts/agente_micro_tendencia_winfut.py

# Monitorar por 5-10 minutos:
# ✅ Esperado: Logs começam aparecer
# ✅ Esperado: IntraDayLearner initialized
# ✅ Esperado: Nenhum erro crítico
# ❌ NÃO esperado: Exceptions ou crashing
```

### Checklist Pós-Deploy:
- [ ] Backup criado (data/db/trading.db.backup_06mar)
- [ ] Sintaxe validada (py_compile OK)
- [ ] Testes 10/10 passando
- [ ] Agent iniciado sem erros
- [ ] Logs gerados (check outputs/trading_*.log)
- [ ] Penalty sendo calculado (ver logs)

### Saída Esperada:
✅ **Agent rodando em staging sem crashes, P0-URGENT-1 ativo**

---

## PASSO 3: Notificar Equipe P1-LEARNING (20 min)

### Email Padrão:

```
Título: [P1-LEARNING] Kick-off Preparado - Aguardando Validação P0-URGENT-1

Olá ML Expert + Data Analyst,

P1-LEARNING (Framework Causal de 7 Passos) está planejado para iniciar 
assim que P0-URGENT-1 seja validado em produção (3-5 dias).

PREPARAÇÃO NECESSÁRIA (hoje/amanhã):

[ ] 1. Infrastructure Setup (2h)
    ├─ Criar tabela: causal_learning_episodes
    ├─ Referência: docs/features/causal-learning/ROADMAP_P1_LEARNING.md
    └─ Owner: Data Engineer

[ ] 2. Classes Skeleton (3h)
    ├─ Criar: src/application/services/causal_learning_engine.py
    ├─ Criar: scripts/test_causal_learning.py
    └─ Owner: ML Expert

[ ] 3. Review Docs (1h)
    ├─ ROADMAP_P1_LEARNING.md
    └─ Owner: Tech Lead

DATA DE KICK-OFF: Confirmada quando P0-URGENT-1 estabilizar (< 5 dias)

REUNIÃO AGENDADA: [Reservar data quando P0 validado]
LOCAL: [Video call]
DURAÇÃO: 60 min
AGENDA:
  14:00-14:10: Context + Objetivos
  14:10-14:25: Architecture Deep-dive
  14:25-14:45: Sprint Planning
  14:45-15:00: Q&A + Start Coding

MATERIAIS:
- Roadmap: docs/features/causal-learning/ROADMAP_P1_LEARNING.md
- Architecture: docs/ADR-010-CAUSAL_FEEDBACK_LOOP.md
- Framework Reference: outputs/FRAMEWORK_APRENDIZADO_CONTINUO_GUIA_PRATICO.md

PRÉ-REQUISITOS PARA PARTICIPAR:
[ ] Ler ROADMAP_P1_LEARNING.md (30 min)
[ ] Entender 7-step causal loop (15 min)
[ ] Database schema review (15 min)
[ ] Confirmar disponibilidade 2-3 semanas

PRÓXIMA AÇÃO:
Confirme recebimento e disponibilidade até [próxima data].

Obrigado,
GitHub Copilot + Tech Lead
```

### Distribuição:
- [ ] ML Expert (lead técnico)
- [ ] Data Engineer (DB setup)
- [ ] QA (testes)
- [ ] Tech Lead (documentação)

### Saída Esperada:
✅ **Equipe notificada, confirmações recebidas, calendar bloqueado**

---

## PASSO 4: Monitorar P0-URGENT-1 (Contínuo - 3-5 dias)

### Daily Standup (09:00 BRT):

**Template para cada dia:**

```
📊 DAILY STANDUP - DATA [DD/MM]
=====================================

SISTEMA: P0-URGENT-1 (Inactivity Penalty)
STATUS: [🟢 OK / 🟡 AVISO / 🔴 CRÍTICO]

MÉTRICA 1: TRADES/DIA
  Target:  2-3 trades
  Atual:   ? trades
  Trend:   [📈 subindo / → estável / 📉 caindo]
  
MÉTRICA 2: CONFIDENCE
  Target:  Para de cair, começa subir
  Atual:   [0.XX]
  Trend:   [📈 subindo / → estável / 📉 caindo]
  
MÉTRICA 3: INACTIVITY PENALTY
  Esperado: Presente nos logs
  Atual:    [✅ Vendo penalty / ❌ Sem penalty]
  Exemplos: [INACTIVITY_PENALTY(LEVE|MÉDIA|CRÍTICA): ...]
  
MÉTRICA 4: ERROS
  Target:  Zero
  Atual:   [0 / quantidade]
  Crítico: [Liste qualquer exception]

---

ANÁLISE:
[Descreva o que está funcionando ou não]

PRÓXIMAS AÇÕES:
1. [...]
2. [...]

BLOCKERS:
[ ] Nenhum / [ ] [Descrever]

---
Próximo Standup: [data]
```

### Verificação Diária (5 min):

```bash
# 1. Verificar que agent está rodando
Get-Process python -ErrorAction SilentlyContinue
# Esperado: agente_micro_tendencia_winfut.py em execução

# 2. Verificar logs de hoje
Get-Content outputs/trading_*.log -Tail 20
# Procurar por: INACTIVITY_PENALTY, evaluate_opportunity, ENTER

# 3. Verificar erros críticos
Select-String "ERROR|Exception|Traceback" outputs/trading_*.log
# Esperado: Nenhum match
```

### Critérios de Sucesso por Dia:
```
Dia 1-2 (07-08/03):
  ✅ Agent rodando sem crashes
  ✅ Penalties sendo aplicadas
  ✅ Trades podem começar (ou não, normal)
  
Dia 3-4 (09-10/03):
  ✅ 2-3 trades realizados (esperado)
  ✅ Confidence estável ou subindo
  ✅ Penalidades ajudando decisões
  
Dia 5+ (11/03+):
  ✅ Padrão estabelecido
  ✅ Pronto para P1-LEARNING
```

### Saída Esperada:
✅ **P0-URGENT-1 validado após 3-5 dias, métricas OK**

---

## PASSO 5: Preparar P1-LEARNING (Paralelo a monitoramento)

### Infrastructure Setup (2h - Data Engineer)

```bash
# Passo 5.1: Criar tabela causal_learning_episodes
# Arquivo: data/db/migrations/001_create_causal_episodes.sql

CREATE TABLE IF NOT EXISTS causal_learning_episodes (
    episode_id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Etapa 1: Signal Detection
    signal_timestamp TIMESTAMP,
    technical_factors JSON,  -- RSI, MACD, Bollinger, etc
    market_conditions JSON, -- Volatility, Trend, Volume
    parameters JSON,         -- Threshold, period, etc
    
    -- Etapa 2: Decision
    decision TEXT,           -- ENTER, HOLD, EXIT
    confidence REAL,        -- 0.0-1.0
    reasoning_factors JSON,  -- Why this decision
    
    -- Etapa 3: Monitoring
    monitoring_evolution JSON, -- Timestamp series
    parameter_drift REAL,
    market_regime_changes JSON,
    
    -- Etapa 4: Closure
    outcome TEXT,           -- WIN, LOSS, TIMEOUT
    exit_reason TEXT,
    final_conditions JSON,
    
    -- Etapa 5: L1 Analysis
    decision_correctness BOOLEAN,  -- DID IT WORK?
    
    -- Etapa 6: L2 Causal Analysis
    context_start JSON,     -- Market state at SIGNAL time
    context_end JSON,       -- Market state at CLOSE time
    context_changed BOOLEAN, -- Same conditions?
    
    -- Etapa 7: Learning Rule
    causal_rule JSON,       -- Extracted rule
    rule_confidence REAL,   -- How confident (0.0-1.0)
    
    CREATED_AT_INDEX (created_at),
    OUTCOME_INDEX (outcome)
);

-- Criar índices para query eficiente
CREATE INDEX IF NOT EXISTS idx_episode_outcome 
  ON causal_learning_episodes(outcome);
CREATE INDEX IF NOT EXISTS idx_episode_timestamp 
  ON causal_learning_episodes(signal_timestamp);
```

```bash
# Passo 5.2: Rodar migration
cd c:\repo\operador-day-trade-win

# Verificar sqlite3
sqlite3 data/db/trading.db ".tables"
# Esperado: causal_learning_episodes presente

# Validar schema
sqlite3 data/db/trading.db ".schema causal_learning_episodes"
```

### Classes Skeleton (3h - ML Expert)

```python
# Arquivo: src/application/services/causal_learning_engine.py
# ~200 LOC skeleton

from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import json

class CausalLearningEngine:
    """7-step causal loop para aprendizado estruturado."""
    
    def __init__(self, db_path: str = "data/db/trading.db"):
        self.db_path = db_path
        self.current_episode = None
    
    # Etapa 1: Signal Detection
    def record_signal_detection(
        self,
        technical_factors: Dict[str, float],
        market_conditions: Dict[str, Any],
        parameters: Dict[str, float]
    ) -> int:
        """Registra detecção de sinal inicial."""
        # TODO: Insert em tabela, retornar episode_id
        pass
    
    # Etapa 2: Decision
    def record_decision(
        self,
        episode_id: int,
        decision: str,  # ENTER, HOLD, EXIT
        confidence: float,
        reasoning_factors: Dict[str, Any]
    ) -> None:
        """Registra decisão e raciocínio."""
        # TODO: Update episode com decision data
        pass
    
    # Etapa 3: Monitoring
    def record_monitoring(
        self,
        episode_id: int,
        monitoring_evolution: list,
        parameter_drift: float,
        market_regime_changes: Dict
    ) -> None:
        """Registra evolução durante execução."""
        # TODO: Update episode com monitoring
        pass
    
    # Etapa 4: Closure
    def record_closure(
        self,
        episode_id: int,
        outcome: str,  # WIN, LOSS, TIMEOUT
        exit_reason: str,
        final_conditions: Dict
    ) -> None:
        """Registra encerramento da oportunidade."""
        # TODO: Update episode com closure
        pass
    
    # Etapa 5: L1 Analysis
    def analyze_decision_correctness(self, episode_id: int) -> Tuple[bool, str]:
        """Análise nível 1: A decisão foi correta?"""
        # TODO: Ler outcome vs decision, retornar (bool, reason)
        pass
    
    # Etapa 6: L2 Causal Analysis
    def analyze_causation(
        self,
        episode_id: int,
        context_start: Dict,
        context_end: Dict
    ) -> Tuple[bool, str]:
        """Análise nível 2: Mesma causação?"""
        # TODO: Comparar contextos, retornar (bool, differences)
        pass
    
    # Etapa 7: Learning Rule Generation
    def generate_causal_rule(self, episode_id: int) -> Optional[Dict]:
        """Gera regra causal a partir do episódio."""
        # TODO: Extract signal + decision + outcome + context
        # TODO: Create rule: "If [context] and [signal] then [decision]"
        # TODO: Retornar regra JSON
        pass
    
    def get_episode_summary(self, episode_id: int) -> Dict:
        """Retorna sumário completo de um episódio."""
        # TODO: Query tabela, retornar tudo
        pass

# Exemplo de uso:
# engine = CausalLearningEngine()
# ep_id = engine.record_signal_detection(...)
# engine.record_decision(ep_id, "ENTER", 0.75, {...})
# ... (etapas 3-5)
# rule = engine.generate_causal_rule(ep_id)
```

### Teste Skeleton (3h - QA)

```python
# Arquivo: scripts/test_causal_learning.py
# ~150 LOC skeleton

import pytest
from datetime import datetime
from src.application.services.causal_learning_engine import CausalLearningEngine

@pytest.fixture
def engine():
    """Fixture para engine de teste."""
    yield CausalLearningEngine(":memory:")  # SQLite in-memory

def test_signal_detection_records(engine):
    """Teste 1: Signal detection registra dados."""
    signal_data = {
        "technical_factors": {"RSI": 75, "MACD": 0.5},
        "market_conditions": {"volatility": 0.02, "trend": "UP"},
        "parameters": {"threshold": 0.75, "period": 20}
    }
    
    episode_id = engine.record_signal_detection(**signal_data)
    
    assert episode_id > 0
    assert engine.current_episode is not None

def test_decision_records(engine):
    """Teste 2: Decision registra decisão."""
    ep_id = engine.record_signal_detection({}, {}, {})
    engine.record_decision(
        ep_id,
        decision="ENTER",
        confidence=0.75,
        reasoning_factors={"reason": "RSI > 70"}
    )
    
    episode = engine.get_episode_summary(ep_id)
    assert episode["decision"] == "ENTER"
    assert episode["confidence"] == 0.75

def test_closure_and_outcome(engine):
    """Teste 3: Closure registra resultado."""
    ep_id = engine.record_signal_detection({}, {}, {})
    engine.record_decision(ep_id, "ENTER", 0.75, {})
    engine.record_closure(
        ep_id,
        outcome="WIN",
        exit_reason="Hit TP",
        final_conditions={"price": 100.5}
    )
    
    episode = engine.get_episode_summary(ep_id)
    assert episode["outcome"] == "WIN"

def test_causal_rule_generation(engine):
    """Teste 4: Gera regra causal."""
    ep_id = engine.record_signal_detection({}, {}, {})
    # ... registrar todas as etapas
    
    rule = engine.generate_causal_rule(ep_id)
    assert rule is not None
    assert "signal" in rule
    assert "decision" in rule
    assert "context" in rule

def test_episode_persistence(engine):
    """Teste 5: Episódio persiste no DB."""
    ep_id = engine.record_signal_detection({}, {}, {})
    
    # Recarregar engine
    engine2 = CausalLearningEngine()  # Novo engine
    episode = engine2.get_episode_summary(ep_id)
    
    assert episode is not None
```

### Saída Esperada:
✅ **Infrastructure + classes skeleton + testes criados**

---

## PASSO 6: P1-LEARNING Kick-off (Quando P0 validado)

### Agenda de Reunião (60 min):

```
00:00-10:00: CONTEXTO + OBJETIVOS
  ├─ Problema: Modelo aprende correlações, não causação
  ├─ Solução: 7-step causal loop
  │  └─ SIGNAL → DECISION → MONITORING → CLOSURE → L1 → L2 → RULE
  ├─ Benefício: Win rate +12% (60% → 72%)
  └─ Timeline: 2-3 semanas com time paralelo

10:00-25:00: ARCHITECTURE DEEP-DIVE
  ├─ 7 etapas detalhadas
  │  1. Signal Detection (contexto inicial)
  │  2. Decision + Reasoning (por que entrou)
  │  3. Signal Monitoring (evolução durante trade)
  │  4. Signal Closure (como saiu)
  │  5. L1 Analysis (foi decisão correta?)
  │  6. L2 Causal Analysis (contexto era mesmo?)
  │  7. Learning Rule (regra causal extraída)
  ├─ Database schema (causal_learning_episodes table)
  ├─ Classes Python (CausalLearningEngine)
  └─ Integração com agent principal

25:00-45:00: SPRINT PLANNING
  ├─ Semana 1: Etapas 1-5
  │  └─ Daily standup 15:00 BRT
  ├─ Semana 2: Etapas 6-7 + Rule Extraction
  │  └─ Daily standup 15:00 BRT
  ├─ Roles:
  │  ├─ ML Expert (Lead técnico)
  │  ├─ Data Engineer (DB + data pipelines)
  │  └─ QA (Testes + validação)
  └─ Checkpoints: Gate checks a cada 3-4 dias

45:00-60:00: Q&A + START CODING
  ├─ Perguntas de design
  ├─ Setup local environment
  ├─ First commit de skeleton
  └─ Próximas 24h: Etapa 1 começar
```

### Pré-Requisitos (todos leram):
- [ ] ROADMAP_P1_LEARNING.md (30 min)
- [ ] ADR-010-CAUSAL_FEEDBACK_LOOP.md (15 min)
- [ ] Database schema (15 min)
- [ ] Classes skeleton (review, 15 min)

### Saída Esperada:
✅ **Kick-off OK, todas as etapas 1-5 começadas, primeiro commit feito**

---

## PASSO 7: Extrair Regras Causais (Etapas 6-7)

### Etapa 6: Causal Analysis (Semana 2, Dias 1-2)

```python
def analyze_causation(episode_id: int) -> Dict:
    """Compare context START vs END para validar causação."""
    
    # Buscar episódio completo
    episode = get_from_db(episode_id)
    
    context_start = episode["context_start"]  # Market state no sinal
    context_end = episode["context_end"]      # Market state no close
    
    # Comparar cada fator
    differences = {}
    for key in context_start:
        if context_start[key] != context_end[key]:
            differences[key] = {
                "start": context_start[key],
                "end": context_end[key],
                "changed": True
            }
    
    # Classificar: Mesmas condições? (para causação funcionar)
    same_context = len(differences) < 3  # Se poucos diffs = contexto similar
    
    return {
        "episode_id": episode_id,
        "same_context": same_context,
        "differences": differences,
        "analysis": "Contexto similar = Regra é causal" if same_context else "Contexto mudou = Não causal"
    }
```

### Etapa 7: Rule Generation (Semana 2, Dias 2-3)

```python
def generate_causal_rule(episode_id: int) -> Dict:
    """Extrai regra causal estruturada."""
    
    episode = get_from_db(episode_id)
    
    # Validar que é episódio causal
    if not episode["causal_analysis"]["same_context"]:
        return None  # Não é causal
    
    # Extrair componentes
    signal = episode["technical_factors"]
    decision = episode["decision"]
    outcome = episode["outcome"]
    context = episode["context_start"]
    
    # Gerar regra em formato estruturado
    rule = {
        "type": "causal_rule",
        "version": "1.0",
        "extracted_from": episode_id,
        "signal_conditions": {
            "rsi": signal.get("RSI"),
            "macd": signal.get("MACD"),
            "bollinger": signal.get("Bollinger")
        },
        "context_conditions": {
            "volatility_range": [context["vol_min"], context["vol_max"]],
            "trend": context["trend"],
            "volume": context["volume"] > "normal"
        },
        "decision": decision,
        "outcome": outcome,
        "confidence": calculate_confidence(episode),
        "rule_text": f"IF ({signal conditions}) AND ({context conditions}) THEN {decision} → {outcome}",
        "applicability": "Use this rule only when context matches"
    }
    
    return rule
```

### Validação de Regras (Semana 2, Dia 3-4):

```python
def extract_causal_rules(min_episodes: int = 20) -> List[Dict]:
    """Extrai todas as regras causais válidas do histórico."""
    
    # Buscar todos os episódios com outcome = WIN
    episodes = query_db(f"SELECT * FROM causal_learning_episodes WHERE outcome='WIN'")
    
    causal_rules = []
    
    for episode in episodes:
        # Analisar causação
        causal_analysis = analyze_causation(episode["id"])
        
        if causal_analysis["same_context"]:
            # É causal - extrair regra
            rule = generate_causal_rule(episode["id"])
            causal_rules.append(rule)
    
    # Agregar regras similares
    aggregated_rules = aggregate_similar_rules(causal_rules)
    
    return aggregated_rules
```

### Saída Esperada:
✅ **5+ regras causais extraídas, validadas, prontas para usar no modelo**

---

## 📊 MATRIZ DE PROGRESSO (7 Passos)

| Passo | Descrição | Duração | Status | Blocker |
|-------|-----------|---------|--------|---------|
| 1 | Revisar com stakeholders | 45 min | ⏳ HOJE | Nenhum |
| 2 | Deploy staging | 30 min | ⏳ HOJE | Passo 1 OK |
| 3 | Notificar equipe P1 | 20 min | ⏳ HOJE | Nenhum |
| 4 | Monitorar P0 contínuo | 3-5 dias | ⏳ PRÓXIMO | Passo 2 OK |
| 5 | Preparar P1 (paralelo) | 5-6h | ⏳ PARALELO | Nenhum |
| 6 | P1 Kick-off | 60 min | ⏳ QUANDO P0 OK | Passo 4 OK |
| 7 | Extrair regras causais | 5-8h | ⏳ DEPOIS | Passo 6 OK |

---

## ✅ CHECKLIST FINAL (7 Passos)

### Passo 1:
- [ ] Apresentação para stakeholders agendada
- [ ] Slides/evidência preparados
- [ ] Perguntas fáceis resolvidas
- [ ] Aprovação de 3/4 personas obtida

### Passo 2:
- [ ] Backup criado (trading.db.backup_06mar)
- [ ] Testes 10/10 passando
- [ ] Agent rodando em staging
- [ ] Logs exibindo penalidades

### Passo 3:
- [ ] Email enviado para equipe P1-LEARNING
- [ ] Documentação anexada
- [ ] Confirmações recebidas da equipe
- [ ] Calendário bloqueado para semana de kick-off

### Passo 4:
- [ ] Daily standup criado/agendado (09:00 BRT)
- [ ] Métricas sendo rastreadas (trades, confidence, penalties)
- [ ] Logs sendo monitorados
- [ ] 3-5 dias de validação completados
- [ ] P0-URGENT-1 validado como sucesso

### Passo 5:
- [ ] Database schema criado (causal_learning_episodes)
- [ ] Classes Python skeleton pronto (CausalLearningEngine)
- [ ] Testes skeleton criados (test_causal_learning.py)
- [ ] Tudo commitado no Git

### Passo 6:
- [ ] Reunião agendada (60 min)
- [ ] Agenda definida
- [ ] Pré-requisitos enviados (todos leram)
- [ ] Kick-off realizado, primeiro sprint iniciado

### Passo 7:
- [ ] Etapas 1-5 capturando dados (20+ episódios)
- [ ] Etapa 6 validando causação
- [ ] Etapa 7 extraindo regras
- [ ] 5+ regras causais geradas
- [ ] Regras validadas e prontas para produção

---

## 🎯 KPIs DE SUCESSO (Final)

```
P0-URGENT-1:
  ✅ Trades/dia: 0 → 2-3
  ✅ Confidence: Para de cair
  ✅ Op costs: Começam reduzir
  
P1-LEARNING:
  ✅ Etapas: 7/7 implementadas
  ✅ Episódios: 20+ capturados
  ✅ Regras: 5+ extraídas
  ✅ Win rate: +12% vs correlacional (60% → 72%)
```

---

**Responsável:** GitHub Copilot + Time Técnico  
**Status:** 🟢 PRONTO PARA EXECUÇÃO  
**Próximo:** Iniciar Passo 1 HOJE
