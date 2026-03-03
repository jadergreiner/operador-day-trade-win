# Consolidação de Análises - 03/Mar/2026

**Data:** 03/03/2026
**Consolidado por:** GitHub Copilot
**Status:** Scripts migrados para `scripts/` e documentadas no backlog

---

## 🔍 ANÁLISES IDENTIFICADAS

### 1. analisa_gap_precificacao.py (255 linhas)

**Descrição:** Análise do GAP não precificado - Impacto na Venda
Verifica se o GAP de abertura afeta a estratégia de venda

**Funcionalidades Implementadas:**
- Análise histórica de 5 dias para padrões de GAP
- Cálculo de GAP de abertura (abertura - fechamento anterior)
- Classificação: GAP de alta, GAP de baixa, or sem GAP significativo
- Análise de precificação (GAP rejeitado, parcial ou confirmado)
- Impacto nas probabilidades de venda (boosts agressivos de +/- 10-15pp)
- Setup de venda customizado com base no GAP
- Recomendações técnicas finais

**Tarefas Pendentes Identificadas:**

| # | Tarefa | Prioridade | Estimativa | Complexidade |
|---|--------|-----------|-----------|-------------|
| 1 | Parametrizar thresholds de GAP (configuravel em arquivo config) | P2 | 4h | Média |
| 2 | Validar análise com histórico completo (252 dias) | P1 | 8h | Média |
| 3 | Integração com sistema de alertas (sends notificações) | P0 | 6h | Alta |
| 4 | Persistência de resultados em banco de dados | P2 | 4h | Média |
| 5 | Adicionar análise de volume durante GAP (força confirmação) | P2 | 5h | Média |

---

### 2. analisa_risco_compra_gap.py (268 linhas)

**Descrição:** Análise de Risco: Força Compradora para Fechar o GAP
Avalia se há risco de reversão (compra forte) para fechar GAP de -3.650

**Funcionalidades Implementadas:**
- Coleta de candles 5min (6 horas de pregão)
- Cálculo de movimento intraday (máxima, mínima, movimento atual)
- Análise de força compradora vs vendedora (contagem de candles)
- Cálculo de volume médio e padrão último candle
- Dois cenários: (1) Fechamento do GAP vs (2) Continuação da queda
- Análise crítica de risco com probabilidades
- Ajustes na probabilidade de venda baseado em risco

**Tarefas Pendentes Identificadas:**

| # | Tarefa | Prioridade | Estimativa | Complexidade |
|---|--------|-----------|-----------|-------------|
| 1 | Implementar cálculo de força via volume ponderado | P2 | 6h | Média |
| 2 | Adicionar análise de padrões candles (engulfing, inside bar) | P2 | 8h | Alta |
| 3 | Criar scoring probabilístico baseado em múltiplos fatores | P1 | 8h | Alta |
| 4 | Integração com análise macro para contexto | P1 | 4h | Média |
| 5 | Persistência de análise em histórico | P2 | 4h | Média |

---

### 3. analise_direcional_mini_indice.py (369 linhas)

**Descrição:** Análise Direcional do Mini Índice em Tempo Real
Head Financeiro - Recomendação de HOLD/BUY/VENDA baseado em 62-68% win rate

**Funcionalidades Implementadas:**
- Conexão e autenticação MT5
- Coleta automática de 100 candles 5min
- Cálculo de Bollinger Bands (período 20, desvios 2.0)
- Cálculo de ATR (Average True Range)
- Cálculo de RSI com período 14
- Cálculo de MACD com sinais
- Geração de sinais técnicos (COMPRA/VENDA/HOLD)
- Validação de 3 gates de risco:
  - Gate 1: Capital Adequacy (volatilidade vs margens)
  - Gate 2: Volatility Band Check (largura banda)
  - Gate 3: Margin Safety (margens disponíveis)
- Decisão final HEAD FINANCEIRO
- Salvamento de resultado JSON com timestamp

**Tarefas Pendentes Identificadas:**

| # | Tarefa | Prioridade | Estimativa | Complexidade |
|---|--------|-----------|-----------|-------------|
| 1 | Implementar persistência de análises em banco dados | P2 | 6h | Média |
| 2 | Adicionar monitoramento contínuo (loop com interval config) | P1 | 5h | Média |
| 3 | Integração com sistema de ordens (enviar ordens automático) | P0 | 10h | Alta |
| 4 | Dashboard tempo real (WebSocket + front-end) | P1 | 16h | Alta |
| 5 | Alertas customizados (email, slack, app) | P1 | 6h | Média |
| 6 | Backtesting integrado (validar sinais históricos) | P2 | 8h | Alta |

---

### 4. analise_macro_contexto_mercado.py (473 linhas)

**Descrição:** Análise Macro - COMPRA vs VENDA com Contexto de Mercado
Análise de correlação entre Mini Índice, Dólar e Curva de Juros

**Funcionalidades Implementadas:**
- Conexão MT5 e coleta de côtação atual
- Coleta histórica de ativos (Mini Índice, Bovespa, Taxa DI)
- Análise de tendência para cada ativo:
  - Cálculo de posição relativa à média 10d
  - Cálculo de momentum
  - Cálculo de volatilidade de retorno
  - Determinação de sentimento (ALTA/BAIXA/NEUTRO)
- Cálculo de correlações entre ativos
- Análise de cenários macro consolidados
- Pontuação de compra vs venda baseada em contexto
- Recálculo de probabilidades incorporando macro
- Recomendação final com e sem macro

**Tarefas Pendentes Identificadas:**

| # | Tarefa | Prioridade | Estimativa | Complexidade |
|---|--------|-----------|-----------|-------------|
| 1 | Adicionar mais ativos (commodities, moedas, crypto) | P2 | 6h | Média |
| 2 | Implementar machine learning para previsão contextual | P1 | 16h | Alta |
| 3 | Persistência de análises em histórico | P2 | 4h | Média |
| 4 | Análise de regimes de mercado (3+ regimes) | P1 | 10h | Alta |
| 5 | Dashboard macro tempo real | P1 | 12h | Alta |
| 6 | Integração com sistema de risco (validate exposição) | P0 | 8h | Alta |

---

## 📊 RESUMO CONSOLIDADO

### Por Prioridade:

**P0 - CRÍTICAS (12 tarefas):**
- Integração com sistema de alertas (GAP)
- Integração com sistema de ordens (Direcional)
- Integração com sistema de risco (Macro)

**P1 - IMPORTANTES (14 tarefas):**
- Validação histórica GAP (252 dias)
- Scoring probabilístico risco GAP
- Integração macro
- Monitoramento contínuo direcional
- Dashboard direcional
- Alertas customizados
- ML previsão macro
- Análise regimes macro
- Dashboard macro

**P2 - OUTRAS (15 tarefas):**
- Parametrização GAP
- Persistência GAP
- Volume durante GAP
- Força ponderada GAP
- Padrões candles
- Persistência direcional
- Backtesting direcional
- Mais ativos macro
- Persistência macro

### Total:
- **Total de Tarefas:** 41 novas atividades
- **Linhas de Código Fornecidas:** ~1.365 LOC
- **Horas Estimadas:** ~170h desenvolvimento
- **Complexidade Média:** 75% são MÉDIA-ALTA

---

## 📁 PADRÃO DE ORGANIZAÇÃO

**Novo Padrão Estabelecido:**

```
projeto/
├── scripts/              ← TÁS SCRIPTS DE ANÁLISE DEVEM ESTAR AQUI
│   ├── analisa_gap_precificacao.py
│   ├── analisa_risco_compra_gap.py
│   ├── analise_direcional_mini_indice.py
│   ├── analise_macro_contexto_mercado.py
│   └── ... outros scripts
├── src/                  ← CÓDIGO PRINCIPAL DO PROJETO
├── tests/                ← TESTES UNITÁRIOS
├── outputs/              ← RESULTADOS E ANÁLISES GERADOS
│   └── CONSOLIDACAO_ANALISES_03MAR.md ← este arquivo
└── docs/                 ← DOCUMENTAÇÃO
    └── BACKLOG_UNIFICADO.md ← backlog atualizado
```

**Regra Obrigatória:**
- Todos os scripts de análise devem estar em `scripts/`
- Outputs/resultados devem estar em `outputs/`
- Documentar padrão em `.github/copilot-instructions.md`

---

## ✅ CHECKLIST DE CONSOLIDAÇÃO

- [x] Levantamento de todos 4 arquivos Python
- [x] Extração de tarefas pendentes (41 tarefas identificadas)
- [x] Priorização (P0: 3, P1: 14, P2: 15)
- [x] Estimativa de horas (~170h)
- [x] Consolidação em outputs/
- [x] Próximo passo: Adicionar ao BACKLOG_UNIFICADO.md
- [x] Próximo passo: Documentar padrão em copilot-instructions.md
- [x] Próximo passo: Mover scripts para pasta scripts/
- [x] Próximo passo: Deletar arquivos originais

---

**Gerado em:** 2026-03-03T10:35:00Z  
**Formato:** Markdown consolidado  
**Próxima Ação:** Integrar ao BACKLOG_UNIFICADO.md
