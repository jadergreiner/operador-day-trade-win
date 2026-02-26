# 🚀 SPRINT 2 - TAREFAS PRIORITIZADAS (SEM DATAS)

**Situação:** ✅ Pronto para execução
**Equipe:** 8 personas
**Formato:** Organizado por Prioridade e Atividades

---

## 📋 TAREFAS (Ordem de Execução)

### 🔴 P0-1: ENG-003 - API REST MT5 (BLOQUEADOR)

**Responsável:** Eng Sr
**Equipe:** 3 Desenvolvedores Backend (4 total)
**Horas:** 160 horas de desenvolvimento
**Situação:** Pronto para começar

**Entregas:**
- 14 endpoints API REST (Autenticação, Ordens, Posições)
- Autenticação OAuth 2.0
- Fila async RabbitMQ + retry (3x backoff exponencial)
- WebSocket (< 100ms tempo real)
- Cache Redis + rastreamento de auditoria PostgreSQL
- 100% cobertura de testes (unitário + integração + E2E)
- Desempenho: P95 < 200ms

**CA (8):** Autenticação, Atualização de token, Ordens async, Lógica de retry, Rastreamento de ordens, Latência WebSocket, Atualizações de conta, Health checks

**Critérios de Sucesso:**
- ✅ 8/8 CA aprovados
- ✅ Latência P95 < 500ms
- ✅ 35+ testes aprovados
- ✅ Código revisado (2+ revisores)

**Desbloqueia:** ML-004 pode começar quando isto estiver pronto

---

### 🟡 P1-1: ML-003 - Análise de Features (INDEPENDENTE)

**Responsável:** Especialista ML
**Equipe:** Especialista ML + Cientista de Dados (2 total)
**Horas:** 88 horas de desenvolvimento
**Situação:** Pronto para começar (sem dependências)

**Entregas:**
- Valores SHAP (top 10 features ordenadas)
- Mapa de calor de matriz de correlação 24×24
- Regras de detecção de drift (3 regras):
  - Teste de mudança de média (µ ± 2σ)
  - Teste KS (p > 0.05)
  - Mudança de correlação (Δr > 0.1)
- Limiares de alerta (Verde/Amarelo/Laranja/Vermelho)
- Análise de sensibilidade de limiar (±0.05)
- Configuração de monitoramento de produção
- Relatório 20+ páginas + visualizações

**CA (18):** Análise SHAP, Matriz de correlação, Regras de drift, Configuração de alertas, Análise de sensibilidade, Configuração de monitoramento, Relatórios completos

**Critérios de Sucesso:**
- ✅ 18/18 CA aprovados
- ✅ Todas as regras de drift testadas
- ✅ Configuração de monitoramento pronta
- ✅ Relatórios aprovados

**Dependências:** Nenhuma

---

### 🔴 P0-2: ML-004 - Backtest Estendido (SEQUENCIAL)

**Responsável:** Especialista ML
**Equipe:** Especialista ML + Cientista de Dados
**Horas:** 88 horas de desenvolvimento
**Situação:** Bloqueado (aguarda ENG-003)

**Começa Quando:** ENG-003 estar completo

**Entregas:**
- Backtest histórico de 252 dias (ano completo)
- Métricas de desempenho:
  - Cálculo de razão de Sharpe
  - Taxa de vitória (VP / (VP+FP))
  - Análise de redução máxima
  - Consistência mensal
- Importância de features durante negociações
- Análise de regime de mercado
- Relatório 20+ páginas + curva de patrimônio + gráfico de redução

**AC (20):** Data validation, Feature extraction, Backtest logic, Metrics calculation, Reports generation, Visualizations, Peer review

**GATE 2 Criteria (Must ALL Pass):**
- ✅ Sharpe >= 1.0
- ✅ Win rate >= 59%
- ✅ Drawdown < 15%
- ✅ Consistency: Std(monthly) < 30% mean

**Decisão de Capital:**
- Se TODOS os critérios PASSAREM: Ativar R$ 100k Fase 2
- Se QUALQUER critério FALHAR: Mantém-se com R$ 50k Fase 1

---

## 📊 MODELO DE EXECUÇÃO

```
EXECUÇÃO PARALELA:
┌─────────────────────┬──────────────────┐
│  ENG-003            │  ML-003          │
│  (Infraestrutura)   │  (Análise)       │
│  ✅ Pronto          │  ✅ Pronto       │
│  Quando pronto      │  Quando pronto   │
│  → Desbloqueia      │  → Independente  │
│    ML-004           │                  │
└─────────────────────┴──────────────────┘
                  ↓
        ┌─────────────────────┐
        │  ML-004             │
        │  (Validação)        │
        │  ⏳ Bloqueado       │
        │  Quando ENG-003 ok  │
        │  → GATE 2 Decisão   │
        └─────────────────────┘
```

**Regras de Execução:**
1. ENG-003 e ML-003 executam simultaneamente (sem dependências)
2. ML-004 aguarda ENG-003 estar completo
3. Todas as tarefas devem passar seus critérios CA
4. Revisões GATE acontecem quando tarefas completam (não em cronograma)

---

## ᴊ ALOCAÇÃO DE EQUIPE

| Função | Horas | Tarefas |
|--------|-------|----------|
| Eng Sr | 48h | Design + liderança ENG-003 |
| Dev-1 | 40h | ENG-003 Autenticação + Ordens |
| Dev-2 | 40h | ENG-003 Posições + WebSocket |
| Dev-3 | 40h | ENG-003 Fila + retry |
| Especialista ML | 48h | ML-003 + ML-004 |
| Cientista de Dados | 40h | ML-003 + ML-004 |
| Responsável QA | 32h | Estratégia de teste |
| Engenheiro de Testes | 32h | Automação de testes |
| **Total** | **320h** | — |

---

## 🎯 GATES & DECISIONS

### GATE 1: ENG-003 + ML-003 Completo

**Critérios GO:**
- ENG-003: 8/8 CA concluído
- ML-003: 18/18 CA concluído
- Revisão de código: 2+ revisores
- Testes: Todos passando

**Decisão:**
- ✅ GO: Iniciar ML-004 imediatamente
- ⚠️ CONDICIONAL: Correções menores, retentar em 1-2 dias
- ❌ NÃO-GO: Problemas maiores, refazer 3+ dias

---

### GATE 2: ML-004 Completo + UAT Pronto

**Critérios GO (TODOS devem passar):**
- Sharpe >= 1.0 ✅
- Taxa de vitória >= 59% ✅
- Redução < 15% ✅
- Consistência < 30% ✅
- 20/20 CA concluído
- Aprovação UAT do Operador

**Decisão (Ativação de Capital):**
- ✅ GO: Ativar R$ 100k Fase 2
- ⚠️ CONDICIONAL: Sharpe 0.95+ ou Taxa 58%+, análise adicional
- ❌ NÃO-GO: < 2 critérios atendidos, retornar para dev
- ❌ ADIAR: Problemas maiores, revisar depois

---

## ⚠️ CAMINHO CRÍTICO

```
Caminho Crítico = ENG-003 → ML-004
  (ML-003 é paralelo, não está no caminho crítico)

Maior duração = ENG-003 (160h) + ML-004 (88h) = 248h
Potencial paralelo = ML-003 (88h) executa junto com ENG-003

Se ENG-003 atrasa → ML-004 atrasa (bloqueador)
Se ML-003 atrasa → Sem impacto (independente)
Se ML-004 atrasa → Sem impacto (não bloqueia nada)
```

---

## ✅ RESUMO DE CRITÉRIOS DE SUCESSO

**OBRIGATÓRIO (Todas as Tarefas):**
- ✅ Todos os critérios CA passando
- ✅ Código revisado (2+ revisores)
- ✅ 100% type hints
- ✅ Testes abrangentes (80%+ cobertura)
- ✅ Documentação completa

**GATE 1 (ENG-003 + ML-003):**
- ✅ 8/8 + 18/18 CA passando
- ✅ Latência P95 da API < 500ms
- ✅ Revisão de código aprovada
- ✅ Integração testada

**GATE 2 (ML-004 + Capital):**
- ✅ Sharpe >= 1.0
- ✅ Taxa de vitória >= 59%
- ✅ Redução < 15%
- ✅ Consistência validada
- ✅ UAT do Operador aprovado

---

## 🚀 PRÓXIMOS PASSOS

### Imediato (Quando Pronto):
1. ✅ Confirmar disponibilidade da equipe
2. ✅ Configurar ambiente (repositório API, DB, filas)
3. ✅ Iniciar desenvolvimento

### Quando ENG-003 Completo:
- Revisão GATE 1
- Se GO: Iniciar ML-004
- Se NÃO-GO: Refazer

### Quando ML-004 Completo:
- Revisão GATE 2 + validação de métricas
- Se GO: Ativação de capital
- Se NÃO-GO: Analisar + iterar

### Rotina Diária:
- Standup: 15:00 BRT (15 min)
- Atualização de progresso
- Identificação de bloqueadores
- Planejamento do próximo dia

---

## 📞 ESCALATION

| Issue | Owner | Escalate To |
|-------|-------|-------------|
| ENG-003 blocker | Eng Sr | CTO |
| ML metrics off | ML Expert | Head Data |
| Gate criteria fail | PO | CFO + Board |
| Capital decision | CFO | Board |

---

## 🎊 PRONTO!

**Tudo está especificado, testável e pronto.**

Próximo step: Team standup + começar quando squad tiver ready.

---

*Formato: Activity-First (Prioridades, sem datas)*
*Gerado: 26/02/2026*
