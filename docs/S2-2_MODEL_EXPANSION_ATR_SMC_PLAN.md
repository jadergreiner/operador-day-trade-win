# 🧠 Plano de Implementação S2-2: Expansão Lógica (ATR + SMC M1/M5)

**Status:** Planejamento
**Owner:** ML Expert / Eng Sr
**Prioridade:** P1 (Should)

---

## 🎯 Objetivo
Evoluir a lógica do modelo para incluir fatores de confluência direcional de curto prazo e adaptabilidade à volatilidade do mercado em tempo real.

## 🏗️ Proposta de Melhoria

### 1. Calibrador ATR Dinâmico (Adaptive ATR)
- **Implementação:** Cálculo de ATR dinâmico nos últimos 15 minutos.
- **Uso:** Ajustar automaticamente a distância do `Trailing Stop` e os alvos de `Take Profit` parciais.
- **Benefício:** Evitar ser "estopado" por volatilidade normal em dias agitados e garantir lucros maiores em tendências fortes.

### 2. Confluência SMC M1/M5 (Convicção Máxima)
- **Implementação:** Identificar Price Action nos timeframes cursíveis (M1 e M5).
- **Lógica:** Caso o sinal consolidado e o SMC M1/M5 concordem, o `Score` base deve sofrer um `boost` de confiança (ex: *1.15).
- **Benefício:** Aumentar a assertividade das entradas, filtrando ruídos de M1.

### 3. Probabilidade Direcional T+60 (Predictive)
- **Implementação:** Nova feature de regressão/classificação para prever o fechamento da próxima janela de 60 min.
- **Uso:** Influenciar a agressividade da entrada (Ticket Size) baseada na prob de continuidade.

## 📋 Critérios de Aceite
- [ ] Implementação de Teste A/B em Backtest para validar o ganho de eficiência do ATR Adaptativo.
- [ ] Nova coluna `boost_smc` no DataFrame de decisão.
- [ ] Win Rate esperado em Backtest: > 65% (Longo prazo).

## 📅 Roadmap Interno
1. **Dia 1-2:** Feature engineering para ATR e SMC Multi-tf.
2. **Dia 3-4:** Treinamento do modelo v1.2.
3. **Dia 5-6:** Backtesting e validação de Sharpe Ratio.
