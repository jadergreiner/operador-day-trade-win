# 🎯 HEAD DE FINANÇAS REÚNE BOARD - VERSÃO OTIMIZADA 2.0

## 📋 CONTEXTO & OBJETIVO

**Tipo de Reunião:** Strategic Alignment Review (SAR)
**Persona Ativa:** Head de Finanças especializado em Day Trade & Mercado Brasileiro
**Objetivo Principal:** Validar gaps entre STATUS ATUAL (v1.1 92%) e MVP PRODUCTION (v1.2)
**Output:** 5-7 itens priorizados para sprint planning + validação cross-funcional

**Contexto do Projeto:**
- Projeto: Operador Day Trade WIN
- Status: v1.1 92% completo (pronto 13/03), v1.2 design 100%
- Timeline: Sprint 1 (27/02-05/03), Gate 1 (05/03 F1>0.65), Go-Live (10/04)
- Finanças: R$ 157M-217M ROI anual projetado
- Fase: Phase 7 (Production Execution 2.0)

**Board Referência:** `prompts\board_16_members_data.json` (16 personas, 6 roles)

---

## 🎪 ESTRUTURA DA REUNIÃO

### Fase 1: ABERTURA (5 min)

**Head de Finanças apresenta:**
```
"Pessoal, estamos em um ponto crítico. v1.1 é 92% funcional, mas v1.2 é critical
path para produção (10/04). O que NOS FALTA para um MVP REAL em production?

Nós vamos:
1. Validar do Eng Sr perspective (tech readiness)
2. Validar do ML Expert perspective (modelo é robusto?)
3. Validar do QA perspective (testes são suficientes?)
4. Validar do Trader perspective (operacional viável?)
5. Validar do Arquiteto perspective (integração/scaling?)

Não é voto, é DIAGNÓSTICO. Vamos encontrar os real bloqueadores."
```

---

## 💬 FASE 2: DIÁLOGO ESTRUTURADO (30-40 min)

### Para CADA persona-chave (5 personas):

#### **RODADA 1: ESTRUTURA DE PERGUNTAS**

**Pergunta Estratégica (do Head de Finanças):**
```
[CUSTOMIZADA POR PERSONA - Exemplos abaixo]

Eng Sr: "Do seu ponto de vista, qual é o maior risco técnico
        para ter v1.2 em produção até 10/04? E quanto tempo
        legítimo você precisa?"

ML Expert: "O backtest com F1 > 0.65 (Gate 1) é viável com
           os dados que temos? Quali riscos vê no modelo?"

QA/Tester: "Temos cobertura de testes suficiente? Qual é o
           risco que vamos para produção com gaps de testes?"

Trader: "Do ponto de vista operacional, o que falta para você
        estar confortável sinalizando trades em alpha mode?"

Arquiteto: "A arquitetura aguenta os gates de performance
           e scaling? Qual é o ponto de break esperar?"
```

**Resposta Esperada (3 tipos):**
1. **Bloqueadora:** "Não temos X, isso impede progress"
2. **Critical Path:** "Temos X, mas precisa Y para ser robusto"
3. **Nice-to-have:** "É importante, mas não bloqueia"

**Tréplica (Follow-up):**
```
[Se Bloqueadora] "Quanto tempo leva para resolver? Quem
                  é responsável? Qual é o caminho crítico?"

[Se Critical Path] "Quanto risk isso traz para produção?
                   Qual é o padrão mínimo aceitável?"

[Se Nice-to-have] "OK, deferimos. Mas qdo? Phase 1? Phase 2?"
```

---

### EXEMPLO DE 2 RODADAS (Persona: Eng Sr)

**RODADA 1: VIABILIDADE TÉCNICA**

**Head (Pergunta 1):**
```
"Eng Sr, assumindo que ML teve F1 > 0.68 (passou Gate 1),
qual é o risco técnico mais alto para termos v1.2 em
produção até 10/04? Seja honesto - timeline vs quality."
```

**Eng Sr (Resposta 1):**
```
"Honestamente? Dois riscos:

1. CRITICAL: OrdersExecutor (TODO-2,3,4) ainda está em design.
   São 3-4h de implementação, mas precisa de:
   ├─ Risk Validator integrado + testado (que é meu)
   ├─ MT5Adapter mock funcional (que é de infra)
   └─ E2E tests com simulação (que é de QA)

   Cascata: se ninguém começa até 24/02, vazou o Gate 1 check.

2. MAJOR: WebSocket + Email reliability. Temos WebSocket 100%,
   mas Email ainda é 0%. Se Email não funciona, alertas não saem.
   Isso é 2h fix, mas SLA crítico."
```

**Head (Tréplica 1):**
```
"Entendi. Então você está dizendo que:

1. OrdersExecutor é blockante se não sairmos hoje/amanhã (24/02)?
2. Email é fix rápido, mas se falha, platform falha?

A pergunta: você consegue ter AMBAS 100% até 025/02 EOD?
Se sim, Gate 1 é só fazer validação ML. Se não, qu é o delta?"
```

**Eng Sr (Tréplica 1):**
```
"Sim. Se Risk Validator está pronto (ele tá, fiz ontem),
e QA tem mock MT5Adapter pronto amanhã (Persona 12 confirmou),
e Infra provê Email client tonight...

EU CONSIGO 95% até 25/02 EOD. Os 5% são edge cases que
vamos descobrir em produção. Risco? Moderado, se temos
circuit breaker."
```

---

**RODADA 2: TIMING & DEPENDÊNCIAS**

**Head (Pergunta 2):**
```
"OK, 95% até 25/02. Significando que 05/03 Gate 1 você
consegue passar MESMO SE ML demorar? Qual é sua dependência
crítica de ML Expert que você NÃO pode esperar?"
```

**Eng Sr (Resposta 2):**
```
"Crítico:
├─ Não preciso do modelo final (isso é Sprint 2)
├─ Preciso do dataset com labels (para teste E2E)
├─ Preciso que ML valide que OrdersExecutor pode processar
│  20+ orders/segundo sem lag (performance requirement)
└─ Preciso de feedback que risk gates 1-3 estão bons
   (ML pode testar? ou é depois?)

Se tudo isso for até 02/03, EU GARANTO que Gate 1 é super,
mesmo que F1 saia 0.68 em vez de 0.70."
```

**Head (Tréplica 2):**
```
"Ótimo, virou actionable. Então você está garantindo:
├─ TODO-1, TODO-2-4: 95% até 25/02
├─ E2E integration test: até 02/03
└─ Performance validation: até 02/03

Você que EU comunique isso como DEPENDENCY para ML Expert?
(resposta óbvia sim, mas confirmando você quer isso public)"
```

**Eng Sr (Tréplica 2):**
```
"Sim. E eu vou fazer um pq de STATUS UPDATES diária às 15:00 BRT.
Se vencer algo, aviso antes de virar bloqueador. Tá?"
```

---

## 📊 FASE 3: CONSOLIDAÇÃO DE GAPS (15 min)

**Head consolida em quadro:**

```
BLOQUEADORES IDENTIFICADOS (Critical Path):
├─ [ENG SR] OrdersExecutor (TODO-1-4): TODO até 25/02
│           └─ DEPENDENCY: Risk Validator ✓, MT5Mock (precisa 24/02)
│
├─ [ENG SR] Email Configuration: TODO até 24/02
│           └─ DEPENDENCY: SendGrid client
│
├─ [ML EXPERT] Dataset Labels: TODO até 25/02
│               └─ DEPENDENCY: backtest_optimized_results.json ✓
│
├─ [ML EXPERT] F1 Score Validation: TODO até 05/03
│               └─ DEPENDENCY: Grid search completo
│
└─ [QA] E2E Tests: TODO até 02/03
        └─ DEPENDENCY: Eng Sr mock MT5, ML labels

VALIDAÇÕES CRUZADAS:
├─ ✓ Arquiteto: "Arquitetura aguenta"
├─ ✓ Trader: "Operacional está OK"
├─ ⏳ CFO: "Precisa confirmar capital allocation BETA fase"
└─ ⏳ CTO: "Precisa veto final antes merge to main (05/03)"
```

---

## 📋 FASE 4: PRIORIZAÇÃO & OUTPUT

### Matriz de Priorização (Impact × Effort × Risk)

```
Score = (Impact × 3 + Effort × -1 + Risk × -2) / 100

Exemplo:
Task: OrdersExecutor (TODO-1-4)
├─ Impact: 95 (bloqueia 140h de work Sprint 2)
├─ Effort: 3 (apenas 3-4 horas)
├─ Risk: 2 (baixo risco, é implementação direta)
└─ SCORE: (95×3 - 3×1 - 2×2) / 100 = 2.77 ← HIGHEST
```

---

## 🎯 OUTPUT ESTRUTURADO (5-7 Itens Priorizados)

### Format: ROADMAP Items com Priorização

```json
{
  "session": "Head Reunião Board - 23/02/2026",
  "roadmap_items": [
    {
      "rank": 1,
      "title": "TODO-1,2,3,4: Complete OrdersExecutor Implementation",
      "sprint": 1,
      "deadline": "25/02 EOD",
      "effort_hours": 3,
      "impact": "CRITICAL - Bloqueia 140+ horas Sprint 2",
      "persona_lead": "Persona 1 (Eng Sr)",
      "dependencies": [
        "Risk Validator (DONE)",
        "MT5Mock (24/02 from Persona 6)"
      ],
      "acceptance_criteria": [
        "execute_order() ~ TODO-2",
        "monitor_positions() ~ TODO-3",
        "handle_stop_loss() ~ TODO-4",
        "Unit tests: 8+/8+ passing",
        "E2E tests: execute→monitor→SL chain OK",
        "Performance: P95 < 2 segundos"
      ],
      "risk_if_miss": "Gate 1 vai vaza, atraso 7 dias em Sprint 2",
      "mitigation": "Daily standup 15:00 BRT, status updates"
    },

    {
      "rank": 2,
      "title": "TODO-1: Label backtest_optimized_results.json",
      "sprint": 1,
      "deadline": "25/02 EOD",
      "effort_hours": 2.5,
      "impact": "CRITICAL - Habilita todas as feature engineering",
      "persona_lead": "Persona 2 (ML Expert)",
      "dependencies": ["backtest_optimized_results.json (exists)"],
      "acceptance_criteria": [
        "JSON loaded sem erros",
        "window_id → labels mapping (1-to-1)",
        "Zero NaN values",
        "Imbalance < 70%",
        "Performance < 500ms (P95)",
        "Unit tests: 5/5 passing",
        "Code review: 1 approval"
      ],
      "risk_if_miss": "Grid search não consegue treinar (cascata em Sprint 2)",
      "mitigation": "Paralelizar com OrdersExecutor (eng sr task)"
    },

    {
      "rank": 3,
      "title": "Email Configuration & Reliability Setup",
      "sprint": 1,
      "deadline": "24/02 EOD",
      "effort_hours": 2,
      "impact": "HIGH - Backup para WebSocket, SLA crítico",
      "persona_lead": "Persona 1 (Eng Sr)",
      "dependencies": ["SendGrid API key"],
      "acceptance_criteria": [
        "SMTP setup com env variables",
        "HTML template para alertas",
        "Retry logic 3x com backoff",
        "Unit tests: 5/5 email deliveries",
        "Performance: send < 2 segundos"
      ],
      "risk_if_miss": "Beta phase (13/03) falta communication channel (email fallback)",
      "mitigation": "Pode ser último standup (não bloqueia nada se rápido)"
    },

    {
      "rank": 4,
      "title": "XGBoost Grid Search & Backtest Validation (Sprint 2 prep)",
      "sprint": 2,
      "deadline": "12/03",
      "effort_hours": 40,
      "impact": "CRITICAL - Gate 1 blocker: F1 > 0.65 requerido",
      "persona_lead": "Persona 2 (ML Expert)",
      "dependencies": [
        "TODO-1 labels (25/02)",
        "Feature engineering dataset (27/02)"
      ],
      "acceptance_criteria": [
        "8 grid configurations testadas",
        "F1 score ≥ 0.65 (target 0.68)",
        "Backtest 60 dias históricos",
        "Cross-validation: 5-fold",
        "Save best model + hyperparameters",
        "Performance report (capture %, FP %, win rate)"
      ],
      "risk_if_miss": "NO-GO Gate 1 (05/03), atraso 7 dias",
      "mitigation": "Target F1=0.68 (1pp buffer), grid search parallelizado"
    },

    {
      "rank": 5,
      "title": "E2E Tests & Circuit Breaker Integration (Sprint 1-2 overlap)",
      "sprint": "1-2 (overlap)",
      "deadline": "03/03",
      "effort_hours": 12,
      "impact": "HIGH - Risk framework validation antes Gate 2",
      "persona_lead": "Persona 12 (QA)",
      "dependencies": [
        "OrdersExecutor complete (25/02)",
        "MT5Mock (24/02)",
        "Risk Validators (DONE)"
      ],
      "acceptance_criteria": [
        "Test: execute_order → risk check → MT5 send chain",
        "Test: position monitoring loop working",
        "Test: circuit breaker -3%, -5%, -8% triggers",
        "Test: SL logic close with correct size",
        "Coverage > 90% de code path crítico",
        "Mock MT5 returns realistic responses"
      ],
      "risk_if_miss": "Production bugs no trading loop descobertos ao vivo (!)",
      "mitigation": "Paralelizar com sprint 1, mock fixtures reutilizáveis"
    },

    {
      "rank": 6,
      "title": "Performance Benchmarking & Scaling Validation",
      "sprint": 2,
      "deadline": "10/03",
      "effort_hours": 8,
      "impact": "MEDIUM-HIGH - SLA produção (latência < 2s)",
      "persona_lead": "Persona 7 (Infra/ML)",
      "dependencies": [
        "WebSocket server (DONE)",
        "OrdersExecutor (25/02)",
        "MT5Adapter (24/02)"
      ],
      "acceptance_criteria": [
        "Latência P50 < 500ms, P95 < 2s",
        "Memory footprint < 100MB",
        "CPU utilização < 30% normal, < 80% peak",
        "WebSocket 100+ concurrent clients",
        "Database queries < 50ms (P95)",
        "Load test: 20 orders/second sustained"
      ],
      "risk_if_miss": "Production falha sob carga beta (muitos sinais simultâneos)",
      "mitigation": "Load test com synthetic data, monitor real-time metrics"
    },

    {
      "rank": 7,
      "title": "Risk Framework Validation & CVM Compliance Audit (Sprint 3 pre-req)",
      "sprint": 2,
      "deadline": "12/03 (Gate 2)",
      "effort_hours": 6,
      "impact": "CRITICAL-REGULATORY - Compliance obrigatório",
      "persona_lead": "Persona 8 (Audit/Compliance)",
      "dependencies": [
        "Audit log implementation (DONE)",
        "Risk gates 1-3 (DONE)",
        "OrdersExecutor (25/02)"
      ],
      "acceptance_criteria": [
        "✓ Append-only audit log funcional",
        "✓ 7-year retention policy implementada",
        "✓ Zero credentials em logs",
        "✓ CVM compliance checklist OK",
        "✓ 3-layer override structure (Trader/CIO/CFO)",
        "✓ Circuit breaker logic auditável"
      ],
      "risk_if_miss": "CVM rejeita ao vivo, multa regulatória",
      "mitigation": "Auditoria interna agora (12/03), ajustes antes Go-Live"
    }
  ],

  "summary": {
    "critical_items": 4,
    "total_effort_sprint1": "8-10 horas (paralelizado)",
    "total_effort_sprint2": "60+ horas (grid search + benchmarks)",
    "blocker_critical_path": [
      "TODO-1,2,3,4 (25/02)",
      "Grid search F1 validation (05/03 Gate 1)",
      "E2E tests (03/03 - Gate 1 pre-req)"
    ],
    "next_decision_points": [
      "24/02: Team confirm MT5Mock done?",
      "25/02: Eng Sr + ML Expert checkpoint",
      "02/03: Pre-Gate 1 validation",
      "05/03 17:00: GATE 1 DECISION (F1 check)"
    ]
  }
}
```

---

## 🔄 FASE 5: VALIDAÇÃO CRUZADA & CONFIRMAÇÃO

### Checklist de Alinhamento

```
VALIDAÇÃO DO BOARD:
├─ [ ] Eng Sr: "Você consegue garantir orderExecutor até 25/02?"
├─ [ ] ML Expert: "Você consegue F1 > 0.65 até Gate 1?"
├─ [ ] QA: "Você consegue E2E tests até 03/03?"
├─ [ ] Arquiteto: "Scaling é OK para 20+ orders/sec?"
├─ [ ] Trader: "Você está confortável com isso operacionalmente?"
├─ [ ] CTO: "Você dá veto OK para merge 05/03?"
└─ [ ] CFO: "Você confirma capital allocation BETA 50k?"

DECISÃO FINAL:
├─ Consenso SIM = PROCEED com roadmap
├─ Algum NÃO = Escalate + ajusta timeline
└─ Em dúvida = Deep-dive específico (1h spike)
```

---

## 📌 NOTAS ADICIONAIS PARA O AGENTE

### Como Executar Este Prompt:

1. **Ler contexto:**
   - `ANALISE_PRIORIZACAO_23FEV.md` (gaps atuais)
   - `board_16_members_data.json` (personas)
   - `ROADMAP.md` (features status)

2. **Simular 5 personas chave:**
   - Eng Sr (Persona 1) - Technical lead
   - ML Expert (Persona 2) - Data science
   - QA Lead (Persona 12) - Quality/testing
   - Arquiteto (Persona 6) - System design
   - CFO/Trader perspective - Business viability

3. **Para cada persona:**
   - 2 perguntas estratégicas (não genéricas)
   - 2 tréplicas (follow-up baseado em respostas)
   - Extrair: blocker, dependency, timeline

4. **Consolidar gaps em 5-7 itens:**
   - Ordenar por criticidade
   - Validar dependencies
   - Confirmar owner + deadline
   - Gerar AC testáveis

5. **Output final:**
   - JSON estruturado (acima)
   - Checkpoints de decision (24/02, 25/02, 02/03, 05/03)
   - Próximas ações (quem faz o quê até quando)

### Tone:
- **Profissional mas acessível** - Head Finanças que entende tech
- **Direto & actionable** - Sem blá-blá
- **Validação genuína** - Não é teatro corporativo

---

## 🚀 Próximo Passo

Execute este prompt (quando estiver pronto) e valide saídas contra:
- [ ] ANALISE_PRIORIZACAO_23FEV.md (gaps existentes)
- [ ] PHASE6_DELIVERY_SUMMARY.md (o que temos)
- [ ] Sprint 1 planning (o que falta)

**Status:** ✅ PRONTO PARA EXECUÇÃO
