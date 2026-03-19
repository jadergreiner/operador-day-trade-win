# 🤖 Operação dos 4 Agentes Executores

**Versão:** 3.0 | **Data:** 17 de março de 2026 |
**Status:** Execução principal concluída em código e testes; validação operacional em staging/UAT/Gate 2

## Índice

- [Visão Geral](#visão-geral)
- [Agente 1: Diários](#agente-1-iniciar_diariosbat)
- [Agente 2: Micro Tendência](#agente-2-iniciar_micro_tendencia_auto_tradebat)
- [Agente 3: RL 5000](#agente-3-iniciar_agente_rl_5000bat)
- [Agente 4: RL Direto](#agente-4-iniciar_agente_rl_diretobat)
- [Fluxo de Operação](#fluxo-de-operação)
- [Isolamento por Magic Number](#isolamento-por-magic-number)
- [Troubleshooting](#troubleshooting)

---

## Visão Geral

O projeto operacionaliza **4 agentes paralelos** para trading de Mini Índice
(WIN$N no MetaTrader 5):

### Governança de versão do Micro Tendência

O histórico de evolução do micro é documentado em:

- [docs/MICRO_TENDENCIA_CHANGELOG_GOVERNANCA.md](MICRO_TENDENCIA_CHANGELOG_GOVERNANCA.md)
- [docs/MICRO_TENDENCIA_CHANGELOG_TEMPLATE.md](MICRO_TENDENCIA_CHANGELOG_TEMPLATE.md)
- `data/models/micro_tendencia/CHANGELOG.md` no runtime

### Governança de aprendizado do Micro Tendência

- Threshold de retreino: `500` rewards novos
- Cooldown mínimo entre retreinos: `180` minutos
- O LGBM do micro recarrega automaticamente após retreino bem-sucedido
- O terminal mostra episódios acumulados, rewards acumuladas, rewards desde o último treino, cooldown restante e a última versão/data persistida

| **Agente** | **Função** | **Script** | **Magic** |
|---|---|---|---|
| Diários | Operador contextual + IA + features intraday | `start_journals_*.py` | 234800 |
| Micro Tendência | Sinais ML | `agente_micro_*.py` | 234700 |
| RL 5000 | Trades RL | `operar_*_rl_*.py` | 234500 |
| RL Direto | Trades paralelo | `agente_rl_direto_*.py` | 234600 |

Cada agente envia ordens com **Magic Number** (EA ID)
único no MT5, garantindo isolamento total.
Ver [ADR-012](ADRS.md) para a decisão formal.

As ordens também carregam comentário padronizado no MT5:

- `agente|EA<magic>|MA<order_prefix>`

Isso facilita auditoria e triagem visual por agente.

**Fluxo Lógico:**

```
MT5 (Dados de Mercado)
    ↓
[Micro Tendência] → Gera ~29 sinais/dia (magic=234700)
[Diários] → Opera, publica features intraday e registra auditoria (magic=234800)
[RL 5000] → Trades com proteção lucro (magic=234500)
[RL Direto] → Alternativa paralela (magic=234600)
    ↓
SQLite (trading.db) → trades.magic_number filtra por agente
```

---

## Agente 1: INICIAR_DIARIOS.bat

**Magic Number:** 234800 (operador contextual ativo)

### 📋 Propósito

Opera como **primeira camada contextual intraday** e também captura
**três streams de dados paralelos**:

1. **Trading Daily Journal** - O que aconteceu (5 min)
2. **AI Reflection** - Análise do dia (10 min)
3. **RL Performance** - Métricas de aprendizado (15 min)

Além disso, publica um snapshot canônico em `outputs/analysis/diario_market_features_latest.json`
e histórico append-only em `diario_market_features` no SQLite para que
Micro, RL 5000 e RL Direto consumam:

1. reversão intraday
2. exaustão de movimento
3. estresse/compra forte de dólar
4. confirmações ou contradições por PETR4, VALE3, IBOV e EWZ

Dados alimentam o ciclo de ML/RL para evolução contínua dos modelos.

### 🚀 Como Usar

```bash
# Na raiz do projeto:
double-click INICIAR_DIARIOS.bat

# Ou via terminal:
cd c:\repo\operador-day-trade-win
INICIAR_DIARIOS.bat
```

### ⚙️ Componentes

- **TradingJournalService**: Registra sinais, execução, P&L
- **AIReflectionJournalService**: IA gera reflexões sobre operações
- **RLPerformanceReader**: Lê episódios do banco e calcula métricas
- **MacroScoreEngine**: Score de macro (direcional/pessimismo/volatilidade)

### 📁 Saídas

```
data/diarios/
  ├── trading_journal_[DATA].json      # O que aconteceu
  ├── trading_journal_[DATA].txt       # Versão legível
  ├── ai_reflection_[DATA].json        # Reflexão IA
  ├── rl_performance_[DATA].json       # Métricas RL
  └── consolidated_[DATA].json         # Tudo junto
```

### ✅ Validação

```bash
# Verificar se rodou corretamente:
ls -la data/diarios/
tail -50 data/diarios/consolidated_[DATA].json
```

### ⚠️ Problemas Comuns

| **Problema** | **Causa** | **Solução** |
|---|---|---|
| "No such table: trading_sessions" | BD não inicializado | Inicialize os outros agentes primeiro |
| IA Reflection muito lento | Chama OpenAI/Claude | Reduzir frequência em config |
| Sem dados de RL Performance | Nenhum RL correu ainda | Execute RL_5000 ou RL_DIRETO antes |

---

## Agente 2: INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat

**Magic Number:** 234700

### 📋 Propósito

**Gera sinais automáticos** de compra/venda baseado em:

- **Score Macro** (direção do mercado) via BDI/HML
- **Indicadores Técnicos** (RSI, MACD, Bollinger)
- **ML Filter** (LightGBM classifica qualidade do sinal)
- **Anti-repetição** (DEDUP) para evitar sinais falaciosos

Frequência esperada: **~29 sinais/dia** (após filtros).

> **Filtro por agente:** A contagem diária de trades
> (`daily_trade_count`) e o P&L acumulado são
> reidratados da tabela `trades` filtrando por
> `magic_number = 234700`. Isso evita que trades de
> outros agentes (RL 5000, RL Direto) inflem a
> contagem e bloqueiem o limite diário.

### 🚀 Como Usar

```bash
# Na raiz do projeto:
double-click INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat

# Ou via terminal:
cd c:\repo\operador-day-trade-win
INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
```

### ⚙️ Componentes

- **MT5Adapter**: Conecta ao MetaTrader 5
- **MacroScoreEngine**: Calcula direção macro (BDI/HML)
- **Indicadores Técnicos**: RSI, MACD, Bollinger, VWAP, Pivot Points
- **LightGBM Integrator**: Filtra sinais de alta qualidade (94% acurácia)
- **SMC/FVG Detector**: Identificação de estrutura de mercado
- **Anti-overtrading Manager**: Evita sinais repetidos

### 📊 Fluxo de Decisão

```
[Lê candle M5/M15]
    ↓
[Score Macro > threshold?] → SIM
    ↓
[RSI em zona ótima?] → SIM
    ↓
[MACD confirma?] → SIM
    ↓
[LightGBM score > 0.6?] → SIM
    ↓
[Último sinal > 5 min atrás?] → SIM
    ↓
[GERA SINAL] ✅
```

### 📁 Saídas

```
data/diarios/
  ├── micro_trend_decisions_[DATA].json
  └── opportunities_[DATA].json

logs/
  └── agente_micro_tendencia.log
```

### 📊 Características de Gate 1 (aprovado 06/03)

- ✅ AC1: Score Macro (BDI/HML/ML) funcional
- ✅ AC2: Detecção de tendências (RSI, MACD) OK
- ✅ AC3: LightGBM filter integrado (94% acurácia)
- ✅ AC4: Anti-overtrading (7 filtros) ativo
- ✅ AC5: Logging completo dos sinais
- ✅ AC6: Posição tracking em tempo real

### ⚠️ Problemas Comuns

| **Problema** | **Causa** | **Solução** |
|---|---|---|
| "ConnectionError: MT5 não conecta" | Terminal fechado/desconectado | Abra MT5, faça login |
| Nenhum sinal gerado | Score macro muito baixo | Mercado fora de hora/parado |
| Muito ruído de sinais | Filtros muito permissivos | Aumentar LightGBM threshold |

---

## Agente 3: INICIAR_AGENTE_RL_5000.bat

**Magic Number:** 234500

### 📋 Propósito

**Executa trades automaticamente** usando modelo RL:

- Modelo Q-Learning treinado em **5000 episódios**
- **Proteção de lucros** com SL/TP **dinâmicos**
- **Anti-overtrading**: 7 filtros automáticos
- **Win Rate esperado**: 65-68% (histórico)
- **Isolamento**: filtra posições por `tickets_proprios`
  e `magic_number` — nunca modifica SL/TP de outro
  agente

### 🚀 Como Usar

```bash
# Na raiz do projeto:
double-click INICIAR_AGENTE_RL_5000.bat

# Selecione uma opção:
# [1] AVALIAR MODELO (teste com histórico)
# [2] OPERAR MERCADO REAL (execução ao vivo)
# [3] MODO ORIGINAL (sem proteções extras)
# [4] Sair

# Ou via terminal:
cd c:\repo\operador-day-trade-win
python scripts/operar_novo_agente_rl_real_antiovertrading.py
```

### ⚙️ Componentes

- **MT5Adapter**: Conexão ao broker
- **PipelineTrainingRL**: Carrega modelo e define ações
- **AgenteQLearningMiniIndice**: Q-Network (15 features → 3 ações)
- **SqliteRLRepository**: Persiste episódios para feedback
- **ProfitProtectionEngine**: Calcula SL/TP dinâmicos
- **AntiOvertrading Manager**: Evita trades repetitivos (cooldown 5 min)

### ⚙️ Modelo RL

**Localização:** `data/models/novo_agente_rl/modelo_final/q_network.pkl` (392 KB)

**Arquitetura:**
- **Estados**: 5000 (discretizados das 15 features)
- **Ações**: 3 opções
  - 0 = Aguardar (Wait)
  - 1 = Comprar (Buy)
  - 2 = Vender (Sell)
- **Features** (15):
  - Volatilidade (ATR, HV20, Bollinger)
  - Momentum (RSI, MACD, ROC)
  - Preço (SMA20, SMA50, slopes)
  - Macro (BDI score, volatilidade do dia)
  - Padrões (suporte/resistência)

### 📊 Paramétros Operacionais

| **Parâmetro** | **Valor** | **Notas** |
|---|---|---|
| **Alvo de Lucro** | R$ 140.00 | Por sinal |
| **Stop Loss** | -R$ 250.00 | Máximo por sinal |
| **Cooldown** | 5 minutos | Entre trades |
| **Intervalo Ciclos** | 30 segundos | Verificação de oportunidades |
| **Confirmação Sinal** | 2 velas | Evita ruído de candle |

### 📊 SL/TP Dinâmicos

```python
# Análise dos últimos 20 topos/fundos
SL = último_fundo - ATR * 1.5
TP = último_topo + ATR * 2.0

# Se BUY:  SL = fundo, TP = topo
# Se SELL: SL = topo, TP = fundo
```

### 📁 Saídas

```
outputs/
  ├── agente_rl_real_[TIMESTAMP].log
  └── agente_[DATA]_episodes.json

data/db/
  └── trading.db → Episódios registrados
```

### ✅ Validação

```bash
# Verificar se o modelo carregou:
python scripts/diagnostico_modelo_rl.py

# Ver últimos episódios:
sqlite3 data/db/trading.db "SELECT * FROM rl_episodes ORDER BY id DESC LIMIT 10;"

# Verificar SL/TP últimos:
sqlite3 data/db/trading.db "SELECT action, stop_loss, take_profit FROM rl_episodes WHERE date(timestamp) = date('now') LIMIT 5;"
```

### ⚠️ Problemas Comuns

| **Problema** | **Causa** | **Solução** |
|---|---|---|
| "Modelo não encontrado" | `q_network.pkl` deletado/movido | Rodar: `python scripts/diagnostico_modelo_rl.py` |
| Win rate baixa (<60%) | Mercado em range ou trending forte | Revisar features/model retraining |
| Muitos trades (overtrading) | Anti-OT filters inefetivos | Aumentar `cooldown` ou `min_volatility` |
| SL/TP muito apertados | Análise de tops/bottoms incorreta | Revisar `CONFIRM_SIGNAL_BARS` |

---

## Agente 4: INICIAR_AGENTE_RL_DIRETO.bat

**Magic Number:** 234600

### 📋 Propósito

**Alternativa ao RL 5000** para operação paralela:

- Mesmo modelo RL (compartilhado)
- **Isolamento completo** de session ID
- **Posições independentes** filtradas por magic
- Verificação de posição por **ticket MT5** a cada
  **15 segundos** (em vez de 60s blind wait)
- Sem wrapper de supervisão (mais simples)

### 🚀 Como Usar

```bash
# Terminal 1:
cd c:\repo\operador-day-trade-win
python scripts/agente_rl_direto_independente.py

# Terminal 2 (em paralelo):
cd c:\repo\operador-day-trade-win
python scripts/agente_rl_direto_independente.py --mode fixo

# Ambos rodam ao mesmo tempo, criando posições independentes
```

### ⚙️ Componentes

**Idênticos ao RL 5000**, mas com:

- Session ID isolado (não compartilhado)
- Logs separados por timestamp
- Magic Number próprio (234600 vs 234500)
- `AgentePosicaoStatus` com ticket/preço/direção
- Verificação via `verificar_posicao_no_mt5()` a
  cada 15s (detecta SL/TP hit em tempo real)

### 📊 Modo: Dinâmico vs Fixo

```bash
# Modo Dinâmico (default):
python scripts/agente_rl_direto_independente.py
# SL/TP calculados dinamicamente

# Modo Fixo:
python scripts/agente_rl_direto_independente.py --mode fixo
# SL: 150 pontos, TP: 300 pontos (hardcoded)
```

### 📁 Saídas

```
outputs/
  ├── agente_direto_[TIMESTAMP].log      # Log principal
  └── agente_direto_debug_[TIMESTAMP].log # Debug detalhado

data/db/
  └── trading.db → Episódios registrados (session isolada)
```

### ⚠️ Diferenças vs RL 5000

| **Aspecto** | **RL 5000** | **RL Direto** |
|---|---|---|
| **Magic Number** | 234500 | 234600 |
| **Wrapper** | Com supervisão | Sem wrapper |
| **Session ID** | Via env variable | Geração autônoma |
| **Paralelizável** | ✅ Sim | ✅ Sim |
| **Heartbeat** | ✅ Sim | ❌ Não |
| **Verif. posição** | Por tickets_proprios | Por ticket MT5 (15s) |
| **Complexidade** | Média | Simples |

### ⚠️ Problemas Comuns

| **Problema** | **Causa** | **Solução** |
|---|---|---|
| "Erro de session isolada" | Conflito de database locks | Aguarde 5s entre inicializações |

---

## Fluxo de Operação

### 📅 Dia Típico (Horário BRT)

```
08:00 → Abrir MT5, fazer login
         └─ Terminal 1: INICIAR_DIARIOS.bat (inicia logs em background)

08:15 → Segunda janela/terminal: INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
         └─ Gera sinais durante o pregão (até 17:55)

08:30 → Terceira janela/terminal: INICIAR_AGENTE_RL_5000.bat
         └─ Operador escolhe: [2] OPERAR MERCADO REAL
         └─ Executa trades com RL até target (R$ 140) ou SL (R$-250)

17:55 → Pregão encerra
         └─ Encerrar todos os agentes (Ctrl+C)
         └─ Diários finalizam automaticamente

18:30 → Verificar saídas:
         ├─ data/diarios/ → Relatórios gerados
         ├─ data/db/trading.db → Episódios + trades
         └─ outputs/ → Logs detalhados
```

### 🔀 Alternativa: Operação Paralela RL

```
# Se quiser testar RL Direto paralelamente:

Terminal 1: INICIAR_AGENTE_RL_5000.bat       [opção 2]
Terminal 2: python agente_rl_direto_independente.py

# Ambos rodam simultaneamente, posições isoladas
# Cuidado: Não ultrapasse capital alocado em ambas operações
```

### 📊 Fluxo de Dados

```
MT5 (MarketData)
    ↓ (atualizado a cada 5 min)
├─ TradingJournalService (Diários)
│   └─ Registra eventos (signals, trades, P&L)
│
├─ Micro Tendência
│   ├─ Score Macro (BDI/HML)
│   ├─ Indicadores (RSI/MACD/Bollinger)
│   ├─ LightGBM Filter
│   └─ Gera ~29 sinais/dia
│
├─ RL Agentes (5000 ou Direto)
│   ├─ Lê estado (15 features)
│   ├─ Q-Network → ação (magic_number na ordem)
│   ├─ Executa trade (MT5 com EA ID isolado)
│   ├─ Registra episódio (SQLite)
│   └─ Filtra posições por magic/ticket próprio
│
└─ SQLite (trading.db)
    ├─ Episodes (RL reward/action/state)
    ├─ Trades (com magic_number por agente)
    ├─ Trading Sessions
    ├─ Positions
    └─ RL Correlation Scores
        ↓ (feedback para próximo dia)
    Diários (AI Reflection)
    └─ Evoluem modelos
```

---

## Isolamento por Magic Number

Cada agente usa um **Magic Number** (EA ID) único
ao enviar ordens ao MT5. Isso garante:

1. **Sem interferência** — um agente nunca modifica
   SL/TP de posição alheia (erro MT5 10013
   eliminado)
2. **Contagem correta** — cada agente conta apenas
   seus próprios trades para limites diários
3. **Auditoria** — toda linha na tabela `trades`
   identifica o agente de origem

### Mapa de Magic Numbers

| Magic | Agente | Uso |
|---|---|---|
| 234000 | Default (legado) | Trades anteriores à v3.0 |
| 234500 | RL 5000 | Produção |
| 234600 | RL Direto | Produção (paralelo) |
| 234700 | Micro Tendência | Produção |
| 234800 | Diários | Operador contextual + publicador de features |

### Sync de Magic Numbers

O script `sync_mt5_trades_to_db.py` lê o campo
`magic` de cada deal do MT5 e grava na coluna
`trades.magic_number`:

```bash
# Re-sincronizar trades com magic correto:
python scripts/sync_mt5_trades_to_db.py --days-back 3
```

### TradeClosureReason

O campo `closure_reason` na tabela `trades` indica
como a posição foi encerrada:

| Valor | Significado |
|---|---|
| `TP_HIT` | Take Profit atingido |
| `SL_HIT` | Stop Loss atingido |
| `MANUAL_CLOSE` | Fechamento manual |
| `TIMEOUT` | Expirado por tempo |
| `CANCELLED` | Cancelado antes de executar |

### Verificar trades por agente

```bash
# Distribuição de trades por Magic Number:
python -c "
import sqlite3
conn = sqlite3.connect('data/db/trading.db')
for r in conn.execute('''
    SELECT magic_number, COUNT(*)
    FROM trades
    WHERE substr(entry_time,1,10) = date('now')
    GROUP BY magic_number
''').fetchall():
    print(f'  magic={r[0]} trades={r[1]}')
conn.close()
"
```

---

## Troubleshooting

### ❓ "Qual agente usar?"

| **Cenário** | **Agente** | **Por Quê** |
|---|---|---|
| ✅ Rodar tudo (dia normal) | Diários + Micro + RL_5000 | Máxima auditoria + proteção |
| 🔄 Testar modelo novo | RL_DIRETO em paralelo | Isolamento por magic |
| 📊 Apenas análise/feedback | DIARIOS | Sem trading |
| 🧪 Teste de mercado | Micro Tendência | Geração de sinais, sem execução |

### ❓ "O agente parou. Posição aberta. O que fazer?"

```bash
# 1. Verificar última ação:
sqlite3 data/db/trading.db \
  "SELECT timestamp, action, stop_loss, take_profit FROM rl_episodes
   WHERE DATE(timestamp) = DATE('now') ORDER BY timestamp DESC LIMIT 1;"

# 2. Verificar posições no MT5:
# (abrir MT5 manualmente)

# 3. Se precisa retomar:
# - Encerre manualmente no MT5 (se desejar)
# - Reinicie o agente
# - Reset de state: python scripts/diagnostico_modelo_rl.py --reset

# 4. Verificar logs:
tail -100 outputs/agente_rl_real_*.log
```

### ❓ "Como resetar estado entre dias?"

```bash
# Automático:
# - SQLite persiste entre dias (OK - auditoria)
# - Cooldown timer reseta à meia-noite
# - Diários geram automaticamente (DATA = novo dia)

# Manual (se necessário):
sqlite3 data/db/trading.db "DELETE FROM rl_episodes WHERE DATE(timestamp) != DATE('now');"
rm outputs/agente_*.log  # Limpar logs antigos
```

### ❓ "Qual é a configuração ótima?"

```python
# Em src/application/services/novo_agente/pipeline_treinamento.py:

TARGET_LUCRO_DIARIO = 140.00    # Por sinal
STOP_PERDA_DIARIA = -250.00     # Por sinal
COOLDOWN_MINUTOS = 5            # Entre trades
CONFIRM_SIGNAL_BARS = 2         # Velas de confirmação
MIN_VOLATILIDADE = 0.05         # % mínima

# Ajuste conforme mercado (trending/range/volatilidade)
```

### ✅ Checklist Pré-Operação

```bash
□ MT5 aberto e logado
□ Conta ao vivo (ou demo se teste)
□ Saldo > R$ 1000 (mínimo recomendado)
□ Modelo RL existe: ls data/models/novo_agente_rl/modelo_final/q_network.pkl
□ BD criado: python scripts/diagnostico_modelo_rl.py
□ Network estável (ping google.com OK)
□ Timeframe servidor = BRT (sincronizar relógio)
□ Não há processo Python anterior rodando (ps)
```

---

## 📚 Referências Adicionais

- [BACKLOG.md](BACKLOG.md) — Status de desenvolvimento
- [ARQUITETURA_ALVO.md](ARQUITETURA_ALVO.md) — Contrato
  arquitetural e isolamento por Magic Number
- [REGRAS_DE_NEGOCIO.md](REGRAS_DE_NEGOCIO.md) — Regras
  operacionais e verificação por ticket
- [AGENTES_RL_PARALELOS.md](AGENTES_RL_PARALELOS.md) —
  Isolamento entre agentes RL (3 camadas)
- [ADRS.md](ADRS.md) — ADR-012: Magic Number por agente
- [MODELAGEM_DE_DADOS.md](MODELAGEM_DE_DADOS.md) —
  Schema da tabela `trades` com `magic_number`
