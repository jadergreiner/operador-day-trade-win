# 🤖 INÍCIO - Inicialização do Projeto

**Operador Day Trade Win - Sistema de Execução Automática para Mini Índice**

**Versão:** 2.0 | **Data:** 16 de março de 2026 | **Status:** ✅ Production Ready

---

## ⚡ Quick Start (5 minutos)

### 1️⃣ Pré-requisitos

```bash
# ✅ Requisitos do Sistema:
- Windows 10+ (PowerShell ou CMD)
- Python 3.9+ (no PATH)
- MT5 instalado e logado em conta real/demo
- ~500 MB livre em disco
```

### 2️⃣ Inicializar Ambiente

```bash
# Clone/Abra o projeto:
cd c:\repo\operador-day-trade-win

# Verificar instalação (primeira vez):
python scripts/diagnostico_modelo_rl.py

# Se passar: ✅ Pronto para operar
# Se falhar: 💬 Ver troubleshooting abaixo
```

### 3️⃣ Iniciar Agentes

```bash
# Opção A: Interface Gráfica (recomendado)
double-click INICIAR_DIARIOS.bat                        # Terminal 1
double-click INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat    # Terminal 2
double-click INICIAR_AGENTE_RL_5000.bat                # Terminal 3

# Opção B: Via Terminal (advanced)
python scripts/start_journals_full_display.py           # Terminal 1
python scripts/agente_micro_tendencia_winfut.py         # Terminal 2
python scripts/operar_novo_agente_rl_real_antiovertrading.py  # Terminal 3
```

### 4️⃣ Monitorar Operação

```bash
# Em tempo real nos terminais abertos:
        Terminal 1 (Diários)        →  Registra eventos a cada 5 min
        Terminal 2 (Micro)          →  Novos sinais aparecem aqui
        Terminal 3 (RL)             →  Trades executados [COMPRA/VENDA]

# Desempenho:
        Arquivos gerados em:        →  data/diarios/ + outputs/ + data/db/
        Ver último trade:           →  sqlite3 data/db/trading.db "SELECT * FROM rl_episodes ORDER BY id DESC LIMIT 5;"
```

### 5️⃣ Encerrar Sessão

```bash
# Pressione Ctrl+C em cada terminal (na sequência reversa):
Terminal 3 (RL)         → Ctrl+C  (encerra posição aberta se houver)
Terminal 2 (Micro)      → Ctrl+C
Terminal 1 (Diários)    → Ctrl+C

# Verificar fechamento:
Todos os terminais devem exibir "[OK] Agente encerrado" ou similar
```

---

## 📋 Arquitetura (3 camadas)

```
┌─────────────────────────────────────────────────────────┐
│  CAMADA DE APRESENTAÇÃO                                │
│  [INICIAR_DIARIOS.bat] [INICIAR_MICRO...] [RL_5000.bat]│
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  CAMADA DE NEGÓCIO (src/ + scripts/)                   │
│  - MacroScoreEngine (BDI/HML analysis)                 │
│  - RL Pipeline (Q-Learning 5000 eps)                   │
│  - Anti-Overtrading Manager (7 filtros)               │
│  - Profit Protection Engine (SL/TP dinamicos)          │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  CAMADA DE INFRA (infrastructure)                      │
│  - MT5Adapter (conexão broker)                         │
│  - SQLiteRLRepository (persistência)                   │
│  - TradingJournalService (auditoria)                   │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  DATA: MT5 (broker) + SQLite (trading.db)              │
│  [WIN$N Candles] ←→ [Episodes, Trades, Sessions]      │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Os 4 Agentes

### **Agente 1: INICIAR_DIARIOS.bat** 📝

Captura operacional em 3 streams (Trading Journal, AI Reflection, RL Performance)

```
INICIAR_DIARIOS.bat
├─ start_journals_full_display.py
├─ TradingJournalService → Registra signals + trades + P&L
├─ AIReflectionJournalService → IA reflete sobre operações
└─ Saída: data/diarios/consolidated_[DATA].json
```

**Quando usar:** ✅ Sempre (auditoria + feedback)

---

### **Agente 2: INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat** 📊

Geração de sinais intraday (~29/dia) com Score Macro + ML

```
INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
├─ agente_micro_tendencia_winfut.py
├─ MacroScoreEngine (BDI/HML) → direção do mercado
├─ Indicadores (RSI/MACD/Bollinger) → entrada
├─ LightGBM Filter (94% acurácia) → qualidade
├─ AntiOT Manager (7 filtros) → evita ruído
└─ Saída: data/diarios/micro_trend_decisions_[DATA].json
```

**Quando usar:** ✅ Normal (fornece sinais para RL executar)

---

### **Agente 3: INICIAR_AGENTE_RL_5000.bat** 🤖

Execução automática com Q-Learning (modelo treinado 5000 eps)

```
INICIAR_AGENTE_RL_5000.bat
├─ operar_novo_agente_rl_real_antiovertrading.py
├─ Q-Network (5000 estados × 3 ações)
├─ ProfitProtectionEngine (SL/TP dinâmicos)
├─ Modo: [1] Avaliar  [2] Mercado Real  [3] Original
└─ Saída: outputs/agente_rl_real_[TIMESTAMP].log
```

**Quando usar:** ✅ Após mercado abrir (executa trades reais)

**Parâmetros:**
- Target: R$ 140.00 / Stop: -R$ 250.00
- Cooldown: 5 min entre trades
- Win Rate esperado: 65-68%

---

### **Agente 4: INICIAR_AGENTE_RL_DIRETO.bat** 🚀

Alternativa ao RL_5000 com isolamento completo (uso paralelo)

```
INICIAR_AGENTE_RL_DIRETO.bat
├─ agente_rl_direto_independente.py
├─ Mesmo modelo RL que RL_5000
├─ Session ID isolada → posições independentes
├─ Sem wrapper → mais simples
└─ Saída: outputs/agente_direto_[TIMESTAMP].log
```

**Quando usar:** 🔄 Para testar/validar em paralelo com RL_5000

---

## 📁 Estrutura de Pastas

```
c:\repo\operador-day-trade-win\
│
├─ BAT/                            ← Scripts launcher (futura consolidação)
│  ├─ INICIAR_DIARIOS.bat
│  ├─ INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
│  ├─ INICIAR_AGENTE_RL_5000.bat
│  └─ INICIAR_AGENTE_RL_DIRETO.bat
│
├─ scripts/                         ← Python scripts principal
│  ├─ start_journals_full_display.py      (Diários)
│  ├─ agente_micro_tendencia_winfut.py    (Micro Tendência)
│  ├─ operar_novo_agente_rl_real_antiovertrading.py  (RL 5000)
│  ├─ agente_rl_direto_independente.py    (RL Direto)
│  ├─ diagnostico_modelo_rl.py            (Health Check)
│  └─ ... outros scripts
│
├─ src/                             ← Código reutilizável
│  ├─ application/                  (Serviços + Lógica)
│  ├─ infrastructure/               (MT5Adapter, DB, etc)
│  └─ domain/                       (Entidades, Enums)
│
├─ data/                            ← Dados operacionais
│  ├─ db/
│  │  └─ trading.db                 (BD SQLite de trading)
│  ├─ models/novo_agente_rl/        (Modelo RL treinado)
│  │  └─ modelo_final/q_network.pkl (Modelo Q-Learning 5000 eps)
│  ├─ diarios/                      (Outputs dos diários)
│  ├─ BDI/                          (Cache de dados macro)
│  └─ logs/                         (Logs debug)
│
├─ outputs/                         ← Saídas de operação
│  ├─ agente_rl_real_[TS].log
│  ├─ agente_direto_[TS].log
│  └─ ... outros logs
│
├─ config/                          ← Configurações
│  ├─ settings.py                   (TradingConfig principal)
│  ├─ rl_scheduler_config.json
│  └─ ... configs específicos
│
├─ docs/                            ← Documentação
│  ├─ OPERACAO_4_AGENTES.md         ← Leia isto (detalhe operacional)
│  ├─ BACKLOG.md
│  ├─ ARQUITETURA_ALVO.md
│  └─ ... outros docs
│
├─ tests/                           ← Testes unitários
│  ├─ unit/
│  └─ integration/
│
├─ .github/
│  └─ copilot-instructions.md       ← Padrões do projeto
│
├─ INIT_DO_PROJETO.md               ← Você está aqui! 👈
├─ START_HERE.md                    ← Guia rápido anterior
├─ README.md                        ← Visão geral do projeto
│
└─ pyproject.toml, pytest.ini, etc. ← Configurações build
```

---

## 🔍 Verificação de Saúde

### Checklist Pré-Operação

```bash
# 1. Python + Dependências
python --version                                    # Deve ser 3.9+
pip list | grep -E "MetaTrader5|lightgbm|sqlalchemy"   # Verificar libs

# 2. Modelo RL
ls -la data/models/novo_agente_rl/modelo_final/q_network.pkl

# 3. BD Inicial
python scripts/diagnostico_modelo_rl.py             # Valida tudo

# 4. Configuração MT5
cat config/settings.py | grep -E "mt5_login|mt5_server"   # Verificar chaves

# 5. Estrutura de Pastas
ls -la data/diarios/
ls -la outputs/
ls -la data/db/
```

### Problemas Comuns

| **Erro** | **Causa** | **Solução** |
|---|---|---|
| "No module named 'MetaTrader5'" | Lib não instalada | `pip install MetaTrader5` |
| "q_network.pkl not found" | Modelo deletado/movido | `python scripts/diagnostico_modelo_rl.py --copy` |
| "ConnectionError: MT5" | Terminal desconectado | Abra MT5, faça login, reconecte |
| "Permission denied: trading.db" | DB travado | `python scripts/diagnostico_modelo_rl.py --reset-db` |

---

## 📊 Fluxo de Operação (Dia Típico)

```
08:00 ─────────────────────────────────────────────────────────────
      (Mercado não abriu, MT5 offline)

08:15 MT5 ABRE │ Fazer login manual no MT5
      ├─ Terminal 1: INICIAR_DIARIOS.bat
      │  └─ [*] Aguardando dados de mercado...
      │  └─ [*] Sessão iniciada

08:30 │ Mercado inicia
      ├─ Terminal 2: INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
      │  └─ [*] Score Macro = +0.65 (bullish)
      │  └─ [*] Procurando sinais...

08:45 │ Primeiro sinal!
      ├─ [SINAL] Compra em 121.500 (RSI=65, MACD positivo, LGB score=0.78)
      └─ Diário registra: Signal(BUY, conf=0.78)

09:00 │ RL monitor na Terminal 3
      ├─ Terminal 3: INICIAR_AGENTE_RL_5000.bat (Opção [2] Real)
      │  └─ [OK] Modelo RL carregado (prob=0.72)
      │  └─ [TRADE] Comprando 1 contrato @ 121.500
      │  └─ [SL/TP] SL=121.200, TP=121.800

09:15 │ Trade em andamento
      ├─ Preço sobe para 121.700
      ├─ Terminal 1: "[P&L] +0.16% (R$ +118.00)"
      └─ Diário registra estado

09:30 │ TP atingido!
      ├─ [VENDA] Fechando @ 121.800 (+300 pontos)
      ├─ [LUCRO] R$ +140.00 ✅ (ate meta diária)
      ├─ Terminal 1: "[CICLO] Dia bem-sucedido, encerrando"
      └─ Diário registra: Episode(reward=+140, episodes=1)

17:55 MERCADO FECHA │
      ├─ Terminal 3: CTRL+C
      ├─ Terminal 2: CTRL+C
      ├─ Terminal 1: CTRL+C (finaliza e gera relatório)

17:56 RELATORIO FINAL
      ├─ data/diarios/consolidated_[16MAR].json
      │  └─ Sinal 1: BUY @ 121.500 (P&L +0.16%)
      │  └─ Episódios: 1
      │  └─ P&L dia: +R$ 140.00
      │  └─ RL reward: +140 (otimizado)
      │  └─ AI Reflection: "Mercado em tendência, modelo performou bem"
      └─ Pronto para próximo dia!
```

---

## 🚀 Próximos Passos

### 1️⃣ Primeira Operação (Teste)

```bash
# Modo: Começar em DEMO (conta demo do MT5)
# Objetivo: Validar fluxo, ver logs, entender tempos

INICIAR_DIARIOS.bat                      (Terminal 1)
INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat   (Terminal 2)
# Deixe rodar 1-2 horas, observe sinais sendo gerados
```

### 2️⃣ RL Executando (Ainda em Demo)

```bash
# Após validar Micro Tendência:
INICIAR_AGENTE_RL_5000.bat              (Terminal 3)
# Escolha: [1] AVALIAR MODELO (backtesting histórico)
# Deixe rodar, veja performance em logs
```

### 3️⃣ Operação Real (Após validar em Demo)

```bash
# Trocar MT5 para conta real (maior risco = melhor cuidado)
# Rodar exatamente como acima, mas agora com capital real
# Capital recomendado mínimo: R$ 1.000-2.000
```

### 4️⃣ Monitoramento Contínuo

```bash
# Daily Checklist:
□ MT5 logado e disponível
□ Modelo RL carregado (sem erros)
□ Diários gerando normalmente
□ P&L dentro do esperado
□ Logs reviewados se houver erros
```

---

## 📚 Documentação Completa

Para detalhes técnicos, ver:

| **Arquivo** | **Conteúdo** |
|---|---|
| **OPERACAO_4_AGENTES.md** | →  Guia detalhado de cada agente (LEIA ISTO para operação) |
| **ARQUITETURA_ALVO.md** | →  Contrato arquitetural + componentes |
| **REGRAS_DE_NEGOCIO.md** | →  Regras operacionais de trading |
| **BACKLOG.md** | →  Status de features + histórico |
| **README.md** | →  Visão geral do projeto |
| **.github/copilot-instructions.md** | →  Padrões de código + commit |

---

## 💬 Suporte Rápido

### "Como vejo último trade executado?"

```bash
sqlite3 data/db/trading.db \
  "SELECT timestamp, action, reward FROM rl_episodes ORDER BY id DESC LIMIT 1;"
```

### "Como reseto o estado (new day)?"

```bash
# Automático: meia-noite = novo dia
# Manual: python scripts/diagnostico_modelo_rl.py --reset
```

### "Como mudo target lucro/stop loss?"

```
src/application/services/novo_agente/pipeline_treinamento.py
  LINE 50: TARGET_PROFIT = 140.00    # Altere aqui
  LINE 51: STOP_LOSS = -250.00       # E aqui
# Depois reinicie o agente
```

### "Como aumento min volatilidade para evitar fakes?"

```
scripts/operar_novo_agente_rl_real_antiovertrading.py
  LINE 60: MIN_VOLATILIDADE = 0.05    # Aumente para 0.10
# Depois reinicie
```

---

## ✅ Status do Projeto

- ✅ **Agente Diários** - Production ready
- ✅ **Agente Micro Tendência** - Production ready (Gate 1 aprovado 06/03)
- ✅ **Agente RL 5000** - Production ready (v3.0 estável)
- ✅ **Agente RL Direto** - Production ready (isolamento 100% OK)
- ✅ **Documentação** - Completa e sincronizada
- ✅ **Testes** - 95%+ de cobertura

---

## 🎓 Know Your Tech Stack

**Linguagens:**
- Python 3.9+ (Core logic)
- Batch/PowerShell (Launchers)
- SQL (SQLite queries)

**Bibliotecas Key:**
- `MetaTrader5` - Conexão broker
- `pandas` - Manipulação de dados
- `scikit-learn` + `lightgbm` - ML
- `sqlalchemy` - ORM banco
- `numpy` - Computação numérica

**Broker:**
- MetaTrader 5 (WIN$N = Mini Índice)

**Banco de Dados:**
- SQLite (data/db/trading.db)

---

## 🎯 Objetivo Final

Operacionalizar **trading automático seguro e auditável** de Mini Índice com:
- ✅ Profit protection (SL/TP dinâmicos)
- ✅ Anti-overtrading (7 filtros)
- ✅ Feedback ML/RL (diários + episódios)
- ✅ Auditoria completa (todos os eventos logados)
- ✅ Paralelização (múltiplos agentes simultâneos)

---

**Última Atualização:** 16 de março de 2026, 10:30 BRT
**Versão:** 2.0 (Production Ready)
**Status:** ✅ Operacional

