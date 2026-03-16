# 🤖 Operação dos 4 Agentes Executores

**Versão:** 2.0 | **Data:** 16 de março de 2026 | **Status:** ✅ Production Ready

## Índice

- [Visão Geral](#visão-geral)
- [Agente 1: Diários](#agente-1-iniciar_diariosbat)
- [Agente 2: Micro Tendência](#agente-2-iniciar_micro_tendencia_auto_tradebat)
- [Agente 3: RL 5000](#agente-3-iniciar_agente_rl_5000bat)
- [Agente 4: RL Direto](#agente-4-iniciar_agente_rl_diretobat)
- [Fluxo de Operação](#fluxo-de-operação)
- [Troubleshooting](#troubleshooting)

---

## Visão Geral

O projeto operacionaliza **4 agentes paralelos** para trading de Mini Índice
(WIN$N no MetaTrader 5):

| **Agente** | **Função** | **Script** | **Modelo** | **Decisão** |
|---|---|---|---|---|
| **1. Diários** | Rastreamento + IA reflection | `start_journals_full_display.py` | Nenhum | Apenas logging |
| **2. Micro Tendência** | Geração de sinais intraday | `agente_micro_tendencia_winfut.py` | LightGBM (ML) | Determinística + Score |
| **3. RL 5000** | Execução automated trades | `operar_novo_agente_rl_real_antiovertrading.py` | Q-Learning (5000 eps) | Reinforcement Learning |
| **4. RL Direto** | Execução paralela isolada | `agente_rl_direto_independente.py` | Q-Learning (5000 eps) | Reinforcement Learning |

**Fluxo Lógico:**

```
MT5 (Dados de Mercado)
    ↓
[Micro Tendência] → Gera ~29 sinais/dia
[Diários] → Registra tudo para auditoria + feedback RL
[RL 5000] → Executa trades com proteção lucro (SL/TP dinâmicos)
[RL Direto] → Alternativa ao RL 5000 (roda em paralelo)
    ↓
SQLite (trading.db) → Armazena episódios, trades, sessões
```

---

## Agente 1: INICIAR_DIARIOS.bat

### 📋 Propósito

Captura **três streams de dados paralelos**:

1. **Trading Daily Journal** - O que aconteceu (5 min)
2. **AI Reflection** - Análise do dia (10 min)
3. **RL Performance** - Métricas de aprendizado (15 min)

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

### 📋 Propósito

**Gera sinais automáticos** de compra/venda baseado em:

- **Score Macro** (direção do mercado) via BDI/HML
- **Indicadores Técnicos** (RSI, MACD, Bollinger)
- **ML Filter** (LightGBM classifica qualidade do sinal)
- **Anti-repetição** (DEDUP) para evitar sinais falaciosos

Frequência esperada: **~29 sinais/dia** (após filtros).

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

### 📋 Propósito

**Executa trades automaticamente** usando modelo de aprendizado (RL):

- Modelo Q-Learning treinado em **5000 episódios**
- **Proteção de lucros** com SL/TP **dinâmicos**
- **Anti-overtrading**: 7 filtros automáticos
- **Win Rate esperado**: 65-68% (histórico)

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

### 📋 Propósito

**Alternativa ao RL 5000** para operação paralela:

- Mesmo modelo RL (compartilhado)
- **Isolamento completo** de session ID
- **Posições independentes** (pode rodar 2 agentes RL simultaneamente)
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

**Idênticos ao RL 5000**, mas com:**
- Session ID isolado (não compartilhado)
- Logs separados por timestamp
- Isolamento de banco de dados (por session)

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
| **Wrapper** | Com supervisão (safe mode) | Sem wrapper (direto) |
| **Session ID** | Via environment variable | Via geração autônoma |
| **Paralelizável** | ✅ Sim (com cuidado) | ✅ Sim (sem conflitos) |
| **Heartbeat** | ✅ Sim | ❌ Não |
| **Complexidade** | Média | Simples |

### ⚠️ Problemas Comuns

| **Problema** | **Causa** | **Solução** |
|---|---|---|
| "Erro de session isolada" | Conflito de database locks | Aguarde 5s entre inicializações |
| Posições conflitantes no MT5 | Ambos abrem mesma ordem | Usar RL_5000 ou RL_DIRETO, não ambos |

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
│   ├─ Q-Network → ação
│   ├─ Executa trade (MT5)
│   └─ Registra episódio (SQLite)
│
└─ SQLite (trading.db)
    ├─ Episodes (RL reward/action/state)
    ├─ Trading Sessions
    ├─ Positions
    └─ RL Correlation Scores
        ↓ (feedback para próximo dia)
    Diários (AI Reflection)
    └─ Evoluem modelos
```

---

## Troubleshooting

### ❓ "Qual agente usar?"

| **Cenário** | **Agente** | **Por Quê** |
|---|---|---|
| ✅ Rodar tudo (dia normal) | Diários + Micro + RL_5000 | Máxima auditoria + proteção |
| 🔄 Testar modelo novo | RL_DIRETO em paralelo | Isolamento seguro |
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

- [BACKLOG.md](BACKLOG.md) - Status de desenvolvimento
- [ARQUITETURA_ALVO.md](ARQUITETURA_ALVO.md) - Contrato arquitetural
- [REGRAS_DE_NEGOCIO.md](REGRAS_DE_NEGOCIO.md) - Regras operacionais
- [.github/copilot-instructions.md](../.github/copilot-instructions.md) - Padrões do projeto

