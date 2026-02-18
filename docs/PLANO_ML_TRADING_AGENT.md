<!-- pyml disable md013 -->
<!-- pyml disable md022 -->
<!-- pyml disable md040 -->
<!-- pyml disable md031 -->
<!-- pyml disable md032 -->

# Plano de Machine Learning para o Agente de Trading WINFUT

## Deliberação Técnica: Head de Finanças × Especialista em Machine Learning

**Data:** 11 de Fevereiro de 2026
**Contexto:** O sistema atual opera com scores heurísticos (macro_score + micro_score) e regras determinísticas para gerar oportunidades de trading no WINFUT (mini-índice B3). Existe infraestrutura RL parcial (coleta de dados via `rl_episodes`, `rl_rewards`, `rl_correlation_scores`) e um modelo XGBoost supervisionado básico que não consome os dados RL. O objetivo é evoluir para um modelo de ML que aprenda com o mercado e com suas próprias decisões.

---

## 20 Rodadas de Perguntas, Respostas e Tréplicas

---

### Rodada 1 — Qual problema estamos resolvendo?

**Head de Finanças (HF):** Temos um agente que analisa ~104 correlações de mercado, 15 indicadores técnicos, estrutura VWAP/Pivot/SMC e gera um score macro (-100 a +100) e micro (-20 a +20). As regras de decisão são determinísticas: score > 5 → BUY, score < -5 → SELL. Ontem o mercado subiu 3.045 pontos e o agente fez ZERO trades. Qual abordagem de ML resolve isso?

**Especialista ML (ML):** O problema tem duas camadas: (1) **classificação da ação ótima** dado o estado do mercado, e (2) **calibração de confiança** — decidir QUANDO agir e com QUANTO de convicção. Regras fixas como "score > 5 → BUY" são lineares demais para capturar interações complexas entre 150+ features. Um modelo de ML aprenderia que "ADX=35 + macro_score=40 + SMC=PREMIUM" pode ser BUY com alta confiança, mesmo que as regras individuais digam "espere".

**HF (Tréplica):** Mas não podemos ter um modelo que opera cegamente. Precisamos de interpretabilidade — o Head de Finanças precisa entender POR QUE o modelo está comprando. Como conciliar isso?

**ML (Resposta):** Modelos baseados em árvore (XGBoost, LightGBM) oferecem feature importance e SHAP values nativos. Podemos gerar explicações como "Este BUY foi 40% motivado pelo macro_score alto, 25% pelo ADX indicando tendência, 20% pelo pullback em VWAP". É a melhor combinação de performance e interpretabilidade para dados tabulares.

---

### Rodada 2 — Supervisionado, RL ou Híbrido?

**HF:** Já temos dois paradigmas no código: XGBoost supervisionado (classificação BUY/SELL/HOLD) e infraestrutura RL (episódios + recompensas multi-horizonte). Qual modelo é melhor para trading?

**ML:** Nenhum isolado. A abordagem ideal é **híbrida em 3 camadas**:

| Camada | Modelo | Função |
|--------|--------|--------|
| 1 — Predição | Gradient Boosting (XGBoost/LightGBM) | Prever probabilidade de movimento UP/DOWN/NEUTRAL nos próximos 5-30 min |
| 2 — Política | RL (DQN ou PPO) | Decidir a ação (BUY/SELL/HOLD) e o sizing dado o estado + predição |
| 3 — Meta-learner | Online Learning (bandit) | Calibrar confiança e selecionar qual horizonte priorizar baseado no regime de mercado |

**HF (Tréplica):** Três modelos parece overengineering. Podemos simplificar?

**ML (Resposta):** Sim. Para o MVP, combinamos as camadas 1 e 2: um **XGBoost que prediz reward esperado por ação** (regression, não classification). Em vez de classificar BUY/SELL/HOLD, prediz o reward_continuous para cada ação. A ação com maior reward esperado vence. Isso já incorpora a lógica de "quando agir" naturalmente — se o reward esperado de HOLD é maior que BUY, o modelo segura.

---

### Rodada 3 — Que dados temos e são suficientes?

**HF:** Temos ~270 episódios/dia com 150+ features cada. O sistema roda desde quando? Quantos dados acumulamos?

**ML:** Precisamos verificar, mas a estrutura de dados é excelente:
- **rl_episodes**: estado completo (preço, scores, indicadores, regime, sentimento)
- **rl_correlation_scores**: 85 correlações de ativos por episódio
- **rl_indicator_values**: 15 indicadores técnicos com scores
- **rl_rewards**: recompensa real em 5 horizontes (5/15/30/60/120 min)

Para um XGBoost com ~200 features, precisamos de **mínimo 5.000 episódios** para treinar de forma robusta, idealmente 20.000+. Isso são **~20-75 dias úteis** de dados.

**HF (Tréplica):** E se não tivermos dados suficientes ainda? Data augmentation funciona para dados financeiros?

**ML (Resposta):** Data augmentation financeira é perigosa — gerar dados sintéticos pode criar padrões que não existem no mercado. Alternativas melhores: (1) usar **dados M1 históricos do MT5** para simular episódios retroativos, (2) **transfer learning** — pré-treinar com dados do mini-dólar (WDO) que tem estrutura similar, (3) iniciar com o modelo heurístico atual e fazer **warm-start** gradual substituindo regras por predições do modelo conforme dados acumulam.

---

### Rodada 4 — Feature Engineering: O que é sinal e o que é ruído?

**HF:** Temos 85+ correlações de mercado (PETR4, VALE3, S&P500, DXY, petróleo, DI futuro...). Todas são relevantes? Muitas features podem causar overfitting?

**ML:** Risco real. Com 200+ features e poucos milhares de amostras, overfitting é o principal inimigo. A estratégia é:

1. **Feature selection agressiva** — usar importância de Gini + SHAP + correlação com target para reduzir para ~50-80 features
2. **Grouped features** — as 85 correlações podem ser resumidas em 6-8 "group scores" (já existem: `AÇÕES_BR`, `COMMODITIES`, `ÍNDICES_US`, `CÂMBIO`, `DI_FUTURO`, `CRIPTO`)
3. **Features temporais derivadas** — delta do macro_score (velocidade de mudança), média móvel do micro_score, streak de decisões corretas do RL
4. **Regularização forte** — max_depth=3-4, min_child_weight=10, L1/L2 regularization

**HF (Tréplica):** As correlações mudam ao longo do dia. Às 10h, S&P500 não está operando. A importância de PETR4 muda quando petróleo dispara. O modelo captura isso?

**ML (Resposta):** Excelente ponto. Precisamos de **features de contexto temporal**: (1) `session_phase` (abertura/consolidação/encerramento), (2) `hora_decimal` (9.0 a 17.9), (3) `mercado_us_aberto` (bool), (4) `minutes_since_open`. O modelo aprenderá interações como "quando mercado US está aberto, peso de ES/NQ sobe; quando fechado, DI futuro e USDBRL dominam".

---

### Rodada 5 — Target Variable: O que estamos predizendo exatamente?

**HF:** O sistema atual decide BUY/SELL/HOLD como classificação. Mas a confiança é crucial — um BUY com 30% de confiança é inútil. O que o modelo deve predizer?

**ML:** Proposta: **Multi-output regression**, não classificação. O modelo prediz 3 valores:

```
expected_reward_BUY    → reward em pontos se comprar
expected_reward_SELL   → reward em pontos se vender
expected_reward_HOLD   → reward em pontos se não operar
```

A ação é `argmax(expectations)`. A confiança é `max(exp) - second_max(exp)` — quanto maior a diferença entre a melhor e segunda melhor ação, maior a confiança.

**HF (Tréplica):** Mas o reward de 5 minutos é diferente do de 120 minutos. Qual horizonte usar?

**ML (Resposta):** Para day trade de mini-índice com a volatilidade que observamos (~3.045 pts/dia), o horizonte **15-30 minutos** é o sweet spot. Motivo: SL médio de 150-200 pts → trade resolve em 10-30 min. Treinar com reward_30min como target principal, e usar reward_5min e reward_60min como features auxiliares (momentum de curto prazo e regime de longo prazo).

---

### Rodada 6 — Overfitting: O assassino silencioso

**HF:** Já vi dezenas de modelos que performam 85% no backtest e 50% em produção. Como evitar isso com dados financeiros?

**ML:** Protocolo anti-overfitting em 5 camadas:

1. **Walk-forward validation** — nunca treinar com dados futuros. Split temporal estrito: treino até dia D-5, validação D-5 a D-1, teste no dia D
2. **Purging + Embargo** — remover 60min de dados entre treino e validação para eliminar leakage por autocorrelação
3. **Combinatorial Purged Cross-Validation (CPCV)** — método do Marcos Lopez de Prado, gera múltiplos paths de backtest
4. **Feature importance stability** — se as top-10 features mudam radicalmente entre folds, o modelo está memorizando ruído
5. **Drift detection** — monitorar se a distribuição das features em produção diverge do treino (PSI > 0.2 = red flag)

**HF (Tréplica):** E se o mercado muda de regime? O que funcionava no range de janeiro não funciona no trend de fevereiro.

**ML (Resposta):** Exatamente por isso precisamos de **re-treinamento contínuo com janela deslizante**. Modelo retreinado toda sexta-feira com os últimos 60 dias úteis de dados. Features de regime (`market_regime`, `adx_level`, `volatility_bracket`) permitem ao modelo se adaptar, mas o retreino frequente é a única garantia real contra regime change.

---

### Rodada 7 — RL verdadeiro faz sentido aqui?

**HF:** Reinforcement Learning é o hot topic. Todo mundo quer usar PPO/DQN para trading. Funciona na prática?

**ML:** Honestamente, **RL puro para trading é extremamente difícil** e geralmente underperforma abordagens supervisionadas simples. Motivos:

1. **Espaço de ação contínuo** — sizing, SL, TP tornam o espaço de ação enorme
2. **Recompensa atrasada e ruidosa** — mercado tem alta variância, reward signal é fraco
3. **Não-estacionariedade** — a distribuição de transição muda diariamente
4. **Custo de exploração** — explorar BUY quando deveria HOLD custa dinheiro real

**Onde RL brilha no nosso caso:** como **otimizador de política sobre o modelo preditivo**. O XGBoost prediz rewards; o RL decide:
- Qual threshold de confiança usar (adaptativo por regime)
- Quanto arriscar (position sizing)
- Quando override o modelo (ex: Guardian kill switch baseado em RL)

**HF (Tréplica):** Então o RL não substitui o XGBoost, mas senta em cima dele?

**ML (Resposta):** Exato. Arquitetura **Model-Based RL**: o XGBoost é o "world model" (prediz consequências), o RL é a "política" (decide o que fazer dado as predições). É mais sample-efficient que RL puro porque não precisa descobrir como o mercado funciona — o XGBoost já sabe.

---

### Rodada 8 — E as 85 correlações? São features ou dados de treino?

**HF:** Cada episódio tem 85 linhas em `rl_correlation_scores` com `price_change_pct` e `final_score` de PETR4, VALE3, S&P500, DXY, etc. Como usar isso?

**ML:** Duas abordagens:

**Abordagem 1 — Flatten (recomendada para MVP):**
Pivotear os 85 itens em colunas: `corr_PETR4_change_pct`, `corr_VALE3_score`, `corr_ES_score`, etc. Resultado: +170 features (change_pct + score para cada item). Combinar com feature selection para reduzir.

**Abordagem 2 — Embeddings (avançada):**
Tratar as 85 correlações como uma sequência e usar um encoder (Transformer ou LSTM) para gerar um embedding de 16-32 dimensões. Esse embedding captura relações entre os ativos que o flatten perde. Porém, exige muito mais dados e complexidade.

**HF (Tréplica):** Já temos os group_scores (`AÇÕES_BR`, `COMMODITIES`, etc.) que resumem os 85 itens em 6-8 grupos. Isso não é suficiente?

**ML (Resposta):** É um excelente meio-termo para o MVP. Usar os group_scores + os top-5 itens individuais por importância (provavelmente ES, DXY, USDBRL, PETR4, DI). Depois, quando tivermos 20.000+ episódios, testar se o flatten completo ou embeddings melhoram.

---

### Rodada 9 — Online Learning: Aprender durante o pregão?

**HF:** Um dos requisitos é que o modelo "reaprenda com o próprio mercado e com as decisões". O modelo pode se adaptar intra-day?

**ML:** Sim, mas com cuidado. Três níveis de adaptação:

| Nível | Frequência | Mecanismo | Risco |
|-------|-----------|-----------|-------|
| **Batch retrain** | Semanal (sexta) | Re-treinar XGBoost com últimos 60 dias | Mínimo — dados validados |
| **Incremental update** | Diário (pós-pregão) | `xgb_model.fit()` com `xgb_model=old_model` como base | Baixo — dados do dia completo |
| **Online calibration** | A cada N ciclos (intra-day) | Ajustar threshold de confiança via bandit/bayesian | Médio — pode reagir a ruído |

Para o MVP, nível 1 + 2. O nível 3 é o que o Diary já faz parcialmente (ajustando thresholds intra-session), mas sem ML formal.

**HF (Tréplica):** O nível 3 é o mais valioso. Se o modelo erra 5 decisões seguidas de manhã, ele deveria se recalibrar à tarde. Como?

**ML (Resposta):** **Thompson Sampling com janela deslizante.** Mantenha uma distribuição Beta(α, β) para cada ação. A cada ciclo: se BUY foi correto → α_buy += 1; se errado → β_buy += 1. Amostra da distribuição para "boost" ou "penalize" a confiança do modelo. Decaimento exponencial (janela de ~50 ciclos = últimas ~1.5 horas) para esquecer erros do início do dia.

---

### Rodada 10 — Backtesting: Como validar sem enganar a nós mesmos?

**HF:** Backtest é o maior ponto de falha. Como fazer um backtest honesto com nossos dados?

**ML:** Framework de backtesting em 3 camadas:

**Camada 1 — Replay de episódios RL (offline):**

```
Para cada episódio histórico:
   1. Reconstruir estado (features)
   2. Modelo prediz ação + confiança
   3. Comparar com reward_real (já temos em rl_rewards)
   4. Calcular PnL líquido (incluindo custos de B3: R$0.32/contrato + emolumentos)
```

**Camada 2 — Walk-forward simulation:**
- Treinar com dias 1-40, testar no dia 41
- Retreinar com dias 2-41, testar no dia 42
- Repetir. Isso simula o que aconteceria com re-treino semanal real.

**Camada 3 — Paper trading (shadow mode):**
- Modelo roda em paralelo com o agente heurístico por 2-4 semanas
- Ambos geram decisões, apenas o heurístico executa
- Comparar performance diária: se ML > heurístico em 70%+ dos dias → promover

**HF (Tréplica):** E os custos? Slippage? O modelo precisa considerar que entrar e sair tem custo real.

**ML (Resposta):** Absolutamente. No backtesting, descontar: (1) **spread médio**: 5 pontos WIN, (2) **slippage**: 10 pontos em entrada + 10 em saída = 20 pts, (3) **custos B3**: ~R$0.65 round-trip por contrato, (4) **timing delay**: o modelo roda a cada 120s, adicionar 1-2 candles de atraso na execução. Um trade precisa lucrar >25 pts líquido para ser viável.

---

### Rodada 11 — Arquitetura do modelo: XGBoost vs LightGBM vs Neural?

**HF:** Decidimos gradient boosting. Mas qual implementação? E redes neurais não seriam melhores com tantos dados?

**ML:** Comparação para nosso caso específico (dados tabulares, ~200 features, milhares de amostras):

| Critério | XGBoost | LightGBM | TabNet (Neural) |
|----------|---------|----------|-----------------|
| Performance tabular | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Velocidade treino | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| Velocidade inferência | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Interpretabilidade | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| Dados pequenos (<10k) | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐ |
| Deploy local | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

**Recomendação: LightGBM** para o MVP. 3-5× mais rápido que XGBoost no treino (crucial para re-treino frequente), performance igual ou superior em dados tabulares, e suporte nativo a features categóricas (market_regime, session_phase, smc_equilibrium).

**HF (Tréplica):** E se quisermos capturar padrões temporais? Sequências de scores nos últimos 10 ciclos, por exemplo?

**ML (Resposta):** Para padrões temporais, criar **lag features** manualmente: `macro_score_lag1`, `macro_score_lag5`, `macro_score_delta_5`, `micro_score_ema10`. LightGBM com lag features captura 90% do que um LSTM faria, sem a complexidade. Se depois quisermos o último 10%, um **ensemble LightGBM + LSTM** é o caminho, mas não para o MVP.

---

### Rodada 12 — Reward shaping: Recompensa por acertar ou por lucrar?

**HF:** O sistema atual calcula `was_correct` (direção certa) e `reward_continuous` (pontos). Um BUY que acerta a direção mas fica 5 pontos de lucro é "bom"? E um HOLD quando o mercado subiu 500 pontos é "ruim"?

**ML:** Precisamos de **reward shaping sofisticado**. O reward puro (pontos ganhos) tem problemas:

1. Um BUY correto de +5 pts tem reward quase zero, mas foi uma boa decisão
2. Um HOLD durante rally de +500 pts tem reward zero (não perdeu), mas foi um custo de oportunidade enorme
3. Um BUY que faz +200 pts em 5 min mas -50 pts em 30 min é bom ou ruim?

**Proposta de reward composto:**

```python
reward = (
    0.40 × reward_continuous_30min     # resultado real
  + 0.20 × mfe_30min                   # máximo favorável (capturou?)
  + 0.15 × (1 - mae_30min/200)         # mínimo adverso (risco controlado?)
  + 0.15 × direction_bonus             # +1 se acertou direção, -0.5 se errou
  + 0.10 × opportunity_cost_penalty    # penaliza HOLD quando |move| > 100pts
)
```

**HF (Tréplica):** O `opportunity_cost_penalty` é crucial. Ontem o sistema perdeu 860 pontos de oportunidade ficando em HOLD. Como quantificar isso?

**ML (Resposta):** Para HOLD: `opportunity_cost = -max(0, |price_change_30min| - 50) / 200`. Isso penaliza HOLD quando o mercado moveu mais de 50 pontos (metade de um SL típico). Se moveu 500 pontos, a penalidade é forte: `-(500-50)/200 = -2.25`. Normalizado para o mesmo range que outros rewards. Isso **ensina o modelo que ficar parado em tendência é tão ruim quanto perder**.

---

### Rodada 13 — Deploy: Como o modelo roda em produção?

**HF:** O agente roda localmente em Python 3.11 com ciclo de 120 segundos. O modelo precisa inferir em menos de 1 segundo. Como fazemos o deploy?

**ML:** Deploy local é o cenário mais simples. Arquitetura:

```
[Agente Micro Tendência]
    ├── Ciclo 120s: coleta dados → calcula features
    ├── ML Inference Engine (novo)
    │   ├── load_model("data/models/lgbm_latest.pkl")
    │   ├── build_feature_vector(result, correlations, indicators)
    │   ├── predict_rewards(feature_vector)  → [reward_buy, reward_sell, reward_hold]
    │   ├── calculate_confidence(rewards) → 0-100%
    │   └── return MLDecision(action, confidence, explanation)
    ├── Fusão: ML + Heurístico com peso configurável
    └── generate_opportunities(ml_decision)
```

O modelo LightGBM em `.pkl` faz inferência em **<5ms** para um vetor de 200 features. Cabe perfeitamente no ciclo de 120s.

**HF (Tréplica):** E se o modelo discordar do heurístico? Quem vence?

**ML (Resposta):** **Fusão ponderada com ramp-up gradual:**

| Fase | Peso ML | Peso Heurístico | Duração |
|------|---------|-----------------|---------|
| Shadow | 0% | 100% | 2-4 semanas |
| Blend 1 | 30% | 70% | 2 semanas |
| Blend 2 | 50% | 50% | 2 semanas |
| ML Lead | 70% | 30% | Contínuo |
| Full ML | 100% | 0% | Quando win_rate_ML > win_rate_heurístico por 30 dias |

Nunca tiramos o heurístico de vez até termos evidência estatística (p-value < 0.05) que o ML é superior.

---

### Rodada 14 — Que métricas realmente importam?

**HF:** Acurácia de 60% pode significar nada se os 40% de erros são trades grandes. Quais métricas usar?

**ML:** Para trading, métricas tradicionais de ML (accuracy, F1) são **insuficientes**. Métricas relevantes:

**Métricas de modelo (offline):**
- **Profit Factor** = gross_profit / gross_loss (> 1.5 bom, > 2.0 excelente)
- **Sharpe Ratio** = mean_return / std_return (> 1.5 para day trade)
- **Max Drawdown** = pior sequência de perdas (< 2000 pts WIN)
- **Win Rate ajustado** = wins / total_trades × avg_win / avg_loss (> 1.2)
- **Calmar Ratio** = annual_return / max_drawdown (> 2.0)

**Métricas de calibração:**
- **Brier Score** = calibração de probabilidade (confiança de 70% deve acertar ~70%)
- **Expected Calibration Error (ECE)** < 0.05

**Métricas operacionais:**
- **Trades por dia** — 3-8 é saudável. 0 é catastrófico (como ontem). >15 é overtrading.
- **Hit rate por regime** — modelo deve performar >55% em TRENDING e >50% em RANGING
- **Latência** — inferência < 100ms

**HF (Tréplica):** E o custo de oportunidade? A métrica mais importante de ontem (860 pts perdidos) não aparece em nenhuma dessas.

**ML (Resposta):** Excelente. Adicionar **Opportunity Capture Rate (OCR)**: `OCR = PnL_model / PnL_oracle_perfeito`. Um oráculo que sempre BUY no low e SELL no high gera o PnL máximo teórico. Se o mercado fez +3045 pts, o oráculo captura digamos 2000 pts. Se o modelo capturou 400 pts, OCR = 20%. Meta: **OCR > 15% em dias de tendência, > 5% em dias de range**.

---

### Rodada 15 — Feature drift e model decay

**HF:** Mercado muda. O que funciona em tendência não funciona em range. Correlações se quebram (exemplo: PETR4 e petróleo descorrelacionaram por 2 meses em 2024). Como detectar e reagir?

**ML:** Framework de monitoramento contínuo:

```
A cada dia (pós-pregão):
  1. PSI (Population Stability Index) por feature
     → PSI > 0.1: warning, > 0.2: alerta, > 0.25: trigger retrain
  2. Accuracy roll-30: acurácia dos últimos 30 dias
     → < 52%: warning, < 48%: trigger retrain urgente
  3. Feature importance drift: comparar top-20 features treino vs produção
     → > 5 features mudaram de posição: retrain
  4. Calibration drift: Brier score rolling
     → > 0.3: confiança descalibrada, retrain
```

**Ação automática:** Se 2+ alertas simultâneos → re-treinar modelo com janela mais curta (30 dias em vez de 60).

**HF (Tréplica):** E se o regime muda fundamentalmente? Por exemplo, B3 implementa nova regra de circuit breaker, ou o tick mínimo muda?

**ML (Resposta):** **Structural breaks** exigem reset parcial. Protocolo: (1) Marcar data do evento, (2) Dar peso 0 a dados pré-evento no treino, (3) Iniciar com modelo conservador (high threshold, low sizing) por 10 dias úteis, (4) Acumular 2.000+ novos episódios antes de treinar com dados apenas pós-evento. Enquanto isso, o heurístico assume o controle (blend weight reverte para 0% ML).

---

### Rodada 16 — Position sizing e gestão de risco no modelo

**HF:** O modelo deve decidir SÓ a direção ou também QUANTO arriscar? Hoje o agente sempre opera 1 mini-contrato.

**ML:** O sizing é tão importante quanto a direção. Proposta: **Kelly Criterion adaptado**:

```python
kelly_fraction = (win_prob × avg_win - (1 - win_prob) × avg_loss) / avg_win
position_size = kelly_fraction × fraction_kelly  # fraction = 0.25 (conservador)
```

Mas para o MVP, simplificar:

| Confiança ML | Posição |
|-------------|---------|
| < 55% | Não opera |
| 55-65% | 1 mini |
| 65-75% | 1-2 mini |
| 75-85% | 2-3 mini |
| > 85% | 3 mini (máximo) |

**HF (Tréplica):** O Guardian já tem controle de exposição. Como integrar com o sizing do ML?

**ML (Resposta):** O Guardian tem **veto power** sobre o sizing. O ML sugere, o Guardian limita:

```
final_size = min(ml_suggested_size, guardian_max_exposure)
if guardian_kill_switch: final_size = 0
if guardian_penalty > 15%: final_size = max(1, final_size - 1)
```

Hierarquia clara: Guardian > ML > Heurístico.

---

### Rodada 17 — Como treinar o primeiro modelo?

**HF:** Vamos ao prático. Temos as tabelas RL com dados. Qual é o script de treino, passo a passo?

**ML:** Pipeline de treinamento end-to-end:

```
1. EXTRAÇÃO (extract_rl_dataset.py)
   - Query rl_episodes JOIN rl_rewards (horizon=30min, is_evaluated=1)
   - Pivot rl_correlation_scores → colunas por item
   - Pivot rl_indicator_values → colunas por indicador
   - Merge tudo por episode_id → DataFrame com ~200 colunas + target

2. FEATURE ENGINEERING (feature_engineering.py)
   - Lag features: macro_score_lag{1,3,5,10}, micro_score_lag{1,3,5}
   - Delta features: macro_score_delta5, adx_delta3
   - Rolling features: macro_score_ema10, rsi_rolling_std_5
   - Interações: macro_score × adx, rsi × smc_equilibrium_encoded
   - Temporal: hora_decimal, minutos_desde_abertura, dia_da_semana

3. TARGET ENGINEERING (target_engineering.py)
   - target_reward = reward_composite (fórmula da Rodada 12)
   - Separar em 3 subsets por ação: reward_if_buy, reward_if_sell, reward_if_hold
   - OU: target_class = argmax(reward) → BUY/SELL/HOLD

4. TREINO (train_lgbm_trading.py)
   - Walk-forward split com purging (60 min gap)
   - LightGBM regression × 3 (um modelo por ação) OU classificação 3-class
   - Hyperparameter tuning via Optuna (50 trials, TimeSeriesSplit)
   - Salvar modelo + metadata + feature importance

5. AVALIAÇÃO (evaluate_model.py)
   - Walk-forward PnL simulation
   - Métricas: Profit Factor, Sharpe, Max Drawdown, OCR
   - SHAP analysis: top-20 features, interaction plots
   - Calibration plot: confiança vs acurácia real
```

**HF (Tréplica):** Quantas horas de desenvolvimento para ter o MVP rodando?

**ML (Resposta):** Com a infraestrutura de dados RL que já existe no código:

| Componente | Horas estimadas |
|-----------|----------------|
| Extract + Feature Engineering | 16h |
| Target Engineering + Treino | 12h |
| Backtesting framework | 16h |
| Integração no agente (inference) | 8h |
| Shadow mode + monitoramento | 8h |
| Testes + debug | 12h |
| **Total** | **~72h (9 dias úteis)** |

---

### Rodada 18 — Explainability: O Diary precisa entender o ML

**HF:** O Diary (Thread 3) analisa as decisões do agente e dá nota. Se o modelo ML tomar a decisão, o Diary precisa entender POR QUE. Como?

**ML:** Integrar **SHAP (SHapley Additive exPlanations)** no pipeline de inferência:

```python
import shap

explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(feature_vector)

# Top-5 features que motivaram a decisão
top_features = sorted(
    zip(feature_names, shap_values[action_idx]),
    key=lambda x: abs(x[1]), reverse=True
)[:5]

explanation = f"BUY motivado por: {top_features[0][0]} (+{top_features[0][1]:.1f}), "
              f"{top_features[1][0]} (+{top_features[1][1]:.1f}), ..."
```

O campo `reason` da Opportunity incluiria: `"[ML] BUY conf=72%: macro_score=+42 (↑28%), ADX=35 (↑18%), pullback_vwap (↑15%), ES_up (↑12%), DI_stable (↑8%)"`.

**HF (Tréplica):** O Diary poderia usar SHAP para detectar quando o modelo está "louco"? Ex: decidindo BUY porque PETR4 caiu?

**ML (Resposta):** Sim! **Sanity check via SHAP**: se as top features contradizem a lógica financeira (ex: "BUY porque RSI=85" — sobrecompra deveria inibir BUY), o Diary reduz a confiança ou veta. Regras de sanidade: RSI>70 + BUY → warning, DXY_up + BUY_WIN → warning (correlação inversa histórica), volume_zero + qualquer ação → warning. Isso cria um **loop de feedback humano-ML** via Diary.

---

### Rodada 19 — Riscos e mitigações

**HF:** Quais são os maiores riscos de colocar ML num sistema de trading real?

**ML:** Top 5 riscos e mitigações:

| # | Risco | Impacto | Probabilidade | Mitigação |
|---|-------|---------|--------------|-----------|
| 1 | **Overfitting → perdas em produção** | Alto | Alta | Walk-forward rigoroso, shadow mode 4 semanas, ramp-up gradual |
| 2 | **Flash crash → modelo não preparado** | Muito Alto | Baixa | Guardian kill switch independente do ML, max loss diário = 500 pts |
| 3 | **Data leak no treino** | Alto | Média | Purging + embargo no split, audit manual do dataset |
| 4 | **Model decay silencioso** | Médio | Alta | PSI monitoring diário, accuracy rollling, alertas automáticos |
| 5 | **Over-trading (muitos sinais)** | Médio | Média | Max 8 trades/dia hard limit, cooldown 10min entre trades |

**HF (Tréplica):** E o risco de o modelo ser MENOS conservador que o heurístico? Se ele dispara 20 BUYs numa bolha?

**ML (Resposta):** **Circuit breakers no ML:**
1. Max 8 trades/dia
2. Max 3 trades perdedores consecutivos → pausa 30min
3. Max drawdown intraday -500 pts → kill for the day
4. Se acurácia roll-10 < 30% → silenciar ML, retornar ao heurístico
5. Guardian permanece ativo e independente — se Guardian diz STOP, nenhum modelo overrides

---

### Rodada 20 — Roadmap final e prioridades

**HF:** Resumindo tudo: qual é o plano de ação concreto, com fases e deliverables?

**ML:** Roadmap em 4 fases:

**Fase 1 — Fundação (Semanas 1-2):**
- [ ] Criar `scripts/ml/extract_rl_dataset.py` — extrai e prepara dataset das tabelas RL
- [ ] Criar `src/application/services/ml/feature_engineering_v2.py` — features avançadas (lags, deltas, temporais)
- [ ] Criar `src/application/services/ml/target_engineering.py` — reward composto
- [ ] Benchmark: validar que dataset tem >5.000 episódios com rewards avaliados

**Fase 2 — Modelo (Semanas 3-4):**
- [ ] Criar `scripts/ml/train_lgbm_trading.py` — treino com LightGBM + walk-forward + Optuna
- [ ] Criar `scripts/ml/evaluate_model.py` — métricas financeiras + SHAP
- [ ] Criar `scripts/ml/backtest_simulation.py` — simulação de PnL com custos reais
- [ ] Meta: Profit Factor > 1.5, Sharpe > 1.0 no walk-forward

**Fase 3 — Integração (Semanas 5-6):**
- [ ] Criar `src/application/services/ml/inference_engine.py` — inferência em produção
- [ ] Integrar no agente micro tendência (fusão ML + heurístico)
- [ ] SHAP explanations no campo `reason` das Opportunities
- [ ] Shadow mode: ML roda em paralelo, não executa, compara

**Fase 4 — Produção (Semanas 7-8+):**
- [ ] Monitoramento: PSI, accuracy rolling, calibration drift
- [ ] Re-treino automático semanal (sexta pós-pregão)
- [ ] Ramp-up: 0% → 30% → 50% → 70% peso ML
- [ ] Dashboard: métricas em tempo real via logs/SQLite

---

## Plano de Desenvolvimento Detalhado

### 1. Extração do Dataset (`scripts/ml/extract_rl_dataset.py`)

**Input:** SQLite `data/db/trading.db`
**Output:** `data/ml/training_dataset.parquet`

```python
# Pseudocódigo
episodes = query("SELECT * FROM rl_episodes WHERE source='MICRO_AGENT'")
rewards = query("SELECT * FROM rl_rewards WHERE horizon_minutes=30 AND is_evaluated=1")
correlations = query("SELECT * FROM rl_correlation_scores").pivot(
    index='episode_id', columns='symbol', values=['final_score', 'price_change_pct']
)
indicators = query("SELECT * FROM rl_indicator_values").pivot(
    index='episode_id', columns='indicator_code', values=['value', 'score']
)

dataset = episodes.merge(rewards).merge(correlations).merge(indicators)
dataset.to_parquet("data/ml/training_dataset.parquet")
```

**Features finais (~120-200 colunas):**
- Episódio direto: 30 features
- Correlações (group_scores + top-10 individuais): 20-30 features
- Indicadores técnicos pivoteados: 30 features
- Lag/Delta/Rolling: 30-50 features
- Temporais: 5 features

### 2. Feature Engineering V2

**Lag features (janela de ciclos anteriores):**

```python
for lag in [1, 3, 5, 10]:
    df[f'macro_score_lag{lag}'] = df['macro_score_final'].shift(lag)
    df[f'micro_score_lag{lag}'] = df['micro_score'].shift(lag)
    df[f'rsi_lag{lag}'] = df['rsi_14_value'].shift(lag)
```

**Delta features (velocidade de mudança):**

```python
df['macro_score_delta3'] = df['macro_score_final'] - df['macro_score_final'].shift(3)
df['adx_delta5'] = df['adx_14_value'] - df['adx_14_value'].shift(5)
df['price_momentum_5'] = df['win_price'] / df['win_price'].shift(5) - 1
```

**Rolling features (estatísticas deslizantes):**

```python
df['macro_score_ema10'] = df['macro_score_final'].ewm(span=10).mean()
df['rsi_rolling_std5'] = df['rsi_14_value'].rolling(5).std()
df['micro_score_streak'] = (df['micro_score'] > 0).astype(int).groupby(
    (df['micro_score'] > 0).ne((df['micro_score'] > 0).shift()).cumsum()
).cumcount() + 1
```

**Features de contexto:**

```python
df['hora_decimal'] = df['timestamp'].dt.hour + df['timestamp'].dt.minute / 60
df['minutos_desde_abertura'] = (df['timestamp'] - abertura_9h).dt.total_seconds() / 60
df['dia_semana'] = df['timestamp'].dt.dayofweek  # 0=seg, 4=sex
df['mercado_us_aberto'] = df['hora_decimal'].between(10.5, 17.0)  # 10:30 BRT
df['range_intraday'] = df['win_high_of_day'] - df['win_low_of_day']
```

### 3. Target Engineering

**Reward composto para target de treino:**

```python
def compute_composite_reward(row):
    """Reward composto que penaliza HOLD em tendência."""
    base_reward = row['reward_continuous_30min']
    mfe = row.get('max_favorable_points_30min', 0) or 0
    mae = row.get('max_adverse_points_30min', 0) or 0
    correct = row.get('was_correct_30min', 0)
    change = abs(row.get('price_change_points_30min', 0) or 0)
    action = row['action']

    # Componentes
    result_comp = base_reward / 200  # normalizado por ATR
    mfe_comp = min(1, mfe / 300) if mfe else 0  # captura de movimentos
    mae_comp = 1 - min(1, mae / 200) if mae else 1  # controle de risco
    direction_comp = 1.0 if correct else -0.5

    # Penalidade de oportunidade para HOLD
    opp_cost = 0
    if action == 'HOLD' and change > 50:
        opp_cost = -min(2, (change - 50) / 200)

    return (0.40 * result_comp + 0.20 * mfe_comp + 0.15 * mae_comp
            + 0.15 * direction_comp + 0.10 * opp_cost)
```

### 4. Treinamento LightGBM

**Hiperparâmetros base (tunar com Optuna):**

```python
params = {
    'objective': 'multiclass',  # ou 'regression' para reward direto
    'num_class': 3,
    'metric': 'multi_logloss',
    'boosting_type': 'gbdt',
    'num_leaves': 31,
    'max_depth': 5,
    'learning_rate': 0.05,
    'n_estimators': 500,
    'min_child_samples': 20,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'reg_alpha': 0.1,  # L1
    'reg_lambda': 1.0,  # L2
    'random_state': 42,
    'verbose': -1,
    'categorical_feature': ['market_regime', 'session_phase',
                             'smc_equilibrium', 'smc_direction',
                             'micro_trend', 'macro_signal'],
}
```

**Walk-forward com purging:**

```python
from sklearn.model_selection import TimeSeriesSplit

tscv = TimeSeriesSplit(n_splits=5, gap=30)  # gap=30 episódios (~60min)
for train_idx, val_idx in tscv.split(X):
    X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
    y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

    model = lgb.LGBMClassifier(**params)
    model.fit(X_train, y_train,
              eval_set=[(X_val, y_val)],
              callbacks=[lgb.early_stopping(50)])
```

### 5. Integração no Agente

**Novo serviço: `MLInferenceEngine`**

```python
class MLInferenceEngine:
    def __init__(self, model_path: str):
        self.model = joblib.load(model_path)
        self.explainer = shap.TreeExplainer(self.model)
        self.feature_names = self.model.feature_names_

    def predict(self, feature_vector: dict) -> MLDecision:
        X = pd.DataFrame([feature_vector])[self.feature_names]
        probs = self.model.predict_proba(X)[0]  # [p_buy, p_sell, p_hold]

        action_idx = probs.argmax()
        action = ['BUY', 'SELL', 'HOLD'][action_idx]
        confidence = probs[action_idx] * 100

        # SHAP explanation
        shap_values = self.explainer.shap_values(X)
        top_features = self._top_features(shap_values[action_idx][0], 5)

        return MLDecision(
            action=action,
            confidence=confidence,
            probabilities={'BUY': probs[0], 'SELL': probs[1], 'HOLD': probs[2]},
            explanation=top_features,
            model_version=self.model_version
        )
```

**Fusão com heurístico no `_generate_opportunities()`:**

```python
# No ciclo do agente
ml_decision = self.ml_engine.predict(feature_vector)

# Fusão ponderada
ml_weight = self.config.ml_weight  # 0.0 a 1.0, ramp-up gradual
heuristic_action = 'BUY' if result.macro_score >= buy_threshold else ...

if ml_weight > 0:
    # ML boost ou penalty na confiança da oportunidade
    if ml_decision.action == opp.direction:
        ml_boost = Decimal(str(ml_decision.confidence * ml_weight / 100 * 20))
        opp.confidence += ml_boost
        opp.reason += f" [ML_AGREE: {ml_decision.confidence:.0f}%]"
    else:
        ml_penalty = Decimal(str(ml_decision.confidence * ml_weight / 100 * 15))
        opp.confidence -= ml_penalty
        opp.reason += f" [ML_DISAGREE: {ml_decision.action} {ml_decision.confidence:.0f}%]"
```

### 6. Backtesting Framework

```python
def backtest_walk_forward(dataset, model_class, train_days=60, test_days=5):
    """Simula trading com re-treino periódico — walk-forward real."""
    results = []

    for start in range(train_days, len(unique_days), test_days):
        train_data = dataset[day_idx < start]
        test_data = dataset[day_idx.between(start, start + test_days)]

        # Treinar
        model = model_class().fit(train_data[features], train_data[target])

        # Simular trades
        for row in test_data.itertuples():
            pred = model.predict_proba(row[features])
            action = ['BUY', 'SELL', 'HOLD'][pred.argmax()]
            conf = pred.max()

            if action != 'HOLD' and conf > threshold:
                # Simular trade com custos
                pnl = row.reward_continuous_30min
                pnl -= 25  # spread + slippage + custos B3
                results.append({
                    'date': row.timestamp,
                    'action': action,
                    'confidence': conf,
                    'pnl_gross': row.reward_continuous_30min,
                    'pnl_net': pnl,
                    'was_correct': row.was_correct_30min,
                })

    return compute_metrics(results)
```

### 7. Monitoramento em Produção

```python
class MLMonitor:
    """Monitora drift e performance do modelo em produção."""

    def check_daily(self, today_predictions, today_outcomes):
        alerts = []

        # 1. Acurácia rolling
        accuracy_30d = self.rolling_accuracy(30)
        if accuracy_30d < 0.48:
            alerts.append(Alert("CRITICAL", f"Accuracy 30d = {accuracy_30d:.1%}"))

        # 2. PSI por feature
        for feat in self.top_features:
            psi = self.compute_psi(feat, reference='training', current='last_5d')
            if psi > 0.2:
                alerts.append(Alert("WARNING", f"PSI({feat}) = {psi:.3f}"))

        # 3. Calibração
        brier = self.brier_score(today_predictions, today_outcomes)
        if brier > 0.3:
            alerts.append(Alert("WARNING", f"Brier score = {brier:.3f}"))

        # 4. Profit factor rolling
        pf = self.profit_factor(30)
        if pf < 1.0:
            alerts.append(Alert("CRITICAL", f"Profit Factor 30d = {pf:.2f}"))

        return alerts
```

### 8. Re-treino Automático

```python
# Executar toda sexta-feira pós-pregão (18h)
# Pode ser agendado via Windows Task Scheduler ou cron

def weekly_retrain():
    """Re-treina modelo com últimos 60 dias úteis."""
    dataset = extract_dataset(days=60)

    if len(dataset) < 5000:
        logger.warning(f"Dataset pequeno: {len(dataset)} episódios")
        return

    model, metrics = train_and_evaluate(dataset)

    # Só aceita se melhor que modelo atual
    current_metrics = load_current_metrics()
    if metrics['profit_factor'] < current_metrics['profit_factor'] * 0.9:
        logger.warning("Novo modelo inferior. Mantendo modelo atual.")
        return

    # Deploy
    save_model(model, f"data/models/lgbm_{datetime.now():%Y%m%d}.pkl")
    update_symlink("data/models/lgbm_latest.pkl")
    save_metrics(metrics)
    logger.info(f"Modelo atualizado. PF={metrics['profit_factor']:.2f}")
```

---

## Resumo Executivo

| Aspecto | Decisão |
|---------|---------|
| **Modelo principal** | LightGBM (multi-class classification ou regression) |
| **Features** | ~120-200 (episódio + correlações agrupadas + indicadores + lags + temporais) |
| **Target** | Reward composto 30min (resultado + MFE + MAE + opp_cost) |
| **Validação** | Walk-forward com purging, 5 folds temporais |
| **Backtesting** | Replay de episódios RL com custos reais B3 |
| **Deploy** | Local, `.pkl`, inferência <5ms no ciclo de 120s |
| **Integração** | Fusão ponderada ML + heurístico com ramp-up gradual |
| **Re-treino** | Semanal (sexta), janela deslizante 60 dias |
| **Monitoramento** | PSI, accuracy rolling, Brier score, profit factor |
| **Interpretabilidade** | SHAP values no campo `reason` das Opportunities |
| **Gestão de risco** | Guardian independente do ML, circuit breakers, max drawdown diário |
| **Timeline MVP** | ~9 dias úteis de desenvolvimento |
| **Meta de performance** | Profit Factor > 1.5, Sharpe > 1.0, OCR > 15% em tendência |

---

## Dependências Python (adicionar ao requirements.txt)

```
lightgbm>=4.0
shap>=0.42
optuna>=3.0
pyarrow>=14.0  # para parquet
```

---

*Documento gerado pela deliberação entre Head Global de Finanças e Especialista em Machine Learning. Próximo passo: verificar volume de dados em `rl_episodes` e iniciar Fase 1.*
