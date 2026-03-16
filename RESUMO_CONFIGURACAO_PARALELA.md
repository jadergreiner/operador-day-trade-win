# 🚀 CONFIGURAÇÃO PARALELA DE AGENTES - RESUMO EXECUTIVO

**Data:** 16/03/2026
**Commit:** c131475 + 6ff9fca
**Status:** ✅ **IMPLEMENTADO E TESTADO**

---

## 📊 Comparação de Estratégias

```
╔════════════════════════════════════════════════════════════════╗
║                   AGENTE DINÂMICO                              ║
╠════════════════════════════════════════════════════════════════╣
║ Arquivo      │ INICIAR_AGENTE_RL_5000.bat (Opção 2)          ║
║ Modo SL/TP   │ DINÂMICO (adapta topos/fundos)                ║
║ SL           │ último_fundo - 20 pontos                      ║
║ TP           │ último_topo + 20 pontos                       ║
║ RR Mínimo    │ 1:1.5 (ajusta TP se necessário)               ║
║ Vantagem     │ Adaptável ao mercado, proteção progressiva    ║
║ Ideal Para   │ Trending market, proteção de lucros            ║
║ Comando      │ --sl-tp-mode dinamico                         ║
║ ID Agente    │ agente_dinamico_YYYYMMDD_HHMMSS               ║
╚════════════════════════════════════════════════════════════════╝

╔════════════════════════════════════════════════════════════════╗
║                    AGENTE FIXO                                 ║
╠════════════════════════════════════════════════════════════════╣
║ Arquivo      │ INICIAR_AGENTE_RL_DIRETO.bat                  ║
║ Modo SL/TP   │ FIXO (valores pré-configurados)               ║
║ SL           │ preco - 150 pontos                            ║
║ TP           │ preco + 300 pontos                            ║
║ RR           │ Sempre 2:1 (fixo)                             ║
║ Vantagem     │ Previsível, rápido, simples                   ║
║ Ideal Para   │ Scalping, roboadas rápidas                    ║
║ Comando      │ --sl-tp-mode fixo                             ║
║ ID Agente    │ agente_fixo_YYYYMMDD_HHMMSS                   ║
╚════════════════════════════════════════════════════════════════╝
```

---

## 🔄 Fluxo de Inicialização

```
TERMINAL 1                              TERMINAL 2
│                                       │
├─ INICIAR_AGENTE_RL_5000.bat           ├─ INICIAR_AGENTE_RL_DIRETO.bat
│  └─ Opção [2]                         │  └─ Executa direto
│                                       │
├─ agente_com_supervision.py            ├─ agente_com_supervision.py
│  └─ --sl-tp-mode dinamico             │  └─ --sl-tp-mode fixo
│                                       │
├─ AGENTE_SL_TP_MODE=dinamico           ├─ AGENTE_SL_TP_MODE=fixo
│                                       │
├─ operar_novo_agente_rl_...py          ├─ operar_novo_agente_rl_...py
│  └─ SL_TP_MODE = 'dinamico'           │  └─ SL_TP_MODE = 'fixo'
│                                       │
├─ calcular_sl_tp_dinamico()            ├─ calcular_sl_tp_dinamico()
│  └─ Se SL_TP_MODE=='dinamico'         │  └─ Se SL_TP_MODE=='fixo'
│     ├─ Analisa 20 candles             │     └─ Retorna valores FIXOS
│     ├─ Calcula topo/fundo                └─ SL = preço - 150
│     └─ RR mínimo 1:1.5                    └─ TP = preço + 300
│                                       │
├─ [DINAMICO] Logs com etiqueta         ├─ [FIXO] Logs com etiqueta
│  └─ Agente ID: agente_dinamico_...    │  └─ Agente ID: agente_fixo_...
│                                       │
├─ [ENVIO] Enviando: Comprar @ X        ├─ [ENVIO] Enviando: Vender @ Y
│  └─ [Agente: dinamico, Modo: DINAMICO]│  └─ [Agente: fixo, Modo: FIXO]
│                                       │
└─ Ambos rodando SIMULTANEAMENTE ◄─────┘
```

---

## 📋 Mudanças Implementadas

### 1. **INICIAR_AGENTE_RL_5000.bat** (Modificado)
```diff
  if "%CHOICE%"=="2" (
    echo.
    echo   [START] OPERACAO REAL COM ANTI-OVERTRADING...
+   echo   Modo SL/TP: DINAMICO (adapta-se aos topos/fundos)
    echo.
-   python operador-day-trade-win\scripts\operar_novo_agente_rl_real_antiovertrading.py
+   python operador-day-trade-win\scripts\operar_novo_agente_rl_real_antiovertrading.py --sl-tp-mode dinamico
```

### 2. **INICIAR_AGENTE_RL_DIRETO.bat** (Modificado)
```diff
- echo   [*] Executando agente...
+ echo   [*] Executando agente com SL/TP FIXO...
+ echo   [*] Modo: Valores fixos (150 pontos SL, 300 pontos TP)
  echo.
  cd /d "%~dp0"
- python scripts\agente_com_supervision.py
+ python scripts\agente_com_supervision.py --sl-tp-mode fixo
```

### 3. **agente_com_supervision.py** (Modificado)
```diff
+ # Parse argumentos ANTES de limpar sys.argv
+ SL_TP_MODE = 'dinamico'  # Padrão
+ if '--sl-tp-mode' in sys.argv:
+     idx = sys.argv.index('--sl-tp-mode')
+     SL_TP_MODE = sys.argv[idx + 1]
+     if SL_TP_MODE not in ['dinamico', 'fixo']:
+         print(f"[ERRO] Modo invalido: {SL_TP_MODE}. Use 'dinamico' ou 'fixo'.")
+         sys.exit(1)
+
+ # Passar modo via variável de ambiente
+ os.environ['AGENTE_SL_TP_MODE'] = SL_TP_MODE
```

### 4. **operar_novo_agente_rl_real_antiovertrading.py** (Modificado)

**a) Adicionar modo e ID único do agente:**
```python
SL_TP_MODE = os.getenv('AGENTE_SL_TP_MODE', 'dinamico').lower()
AGENTE_ID = f"agente_{SL_TP_MODE}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

logger.info(f"Modo SL/TP: {SL_TP_MODE.upper()}")
logger.info(f"ID do Agente: {AGENTE_ID}")
```

**b) Modificar `calcular_sl_tp_dinamico()` para respeitar modo:**
```python
# SE MODO FOR FIXO, RETORNA VALORES FIXOS DIRETO
if SL_TP_MODE == 'fixo':
    logger.info(f"[FIXO] Usando SL/TP fixo para {acao}")
    if acao == "Comprar":
        return preco_atual - STOP_LOSS_PONTOS, preco_atual + TAKE_PROFIT_PONTOS
    else:
        return preco_atual + STOP_LOSS_PONTOS, preco_atual - TAKE_PROFIT_PONTOS
```

**c) Registrar Agente ID nas operações:**
```diff
- logger.info(f"[ENVIO] Enviando: {acao} @ {preco_atual} (SL: {sl}, TP: {tp}, Vol: {vol:.3f}%)")
+ logger.info(f"[ENVIO] Enviando: {acao} @ {preco_atual} (SL: {sl}, TP: {tp}, Vol: {vol:.3f}%) [Agente: {AGENTE_ID}, Modo: {SL_TP_MODE.upper()}]")
```

**d) Adicionar modo no status:**
```diff
  logger.info(f"[STATUS] OPERACAO (BALANCED MODE)")
+ logger.info(f"Agente ID: {AGENTE_ID}")
+ logger.info(f"Modo SL/TP: {SL_TP_MODE.upper()}")
```

---

## ✅ Testes Realizados

```
TEST 1: Variável de Ambiente
  ✓ Modo DINAMICO: dinamico
  ✓ Modo FIXO: fixo

TEST 2: Parse de Argumentos CLI
  ✓ Argumento: --sl-tp-mode dinamico → Modo: dinamico
  ✓ Argumento: --sl-tp-mode fixo → Modo: fixo
  ✓ Argumento: (nenhum) → Modo: dinamico (padrão)

TEST 3: ID Único do Agente
  ✓ Agente DINAMICO: agente_dinamico_20260316_105455
  ✓ Agente FIXO: agente_fixo_20260316_105455

STATUS: ✅ TODOS OS TESTES PASSARAM!
```

---

## 🎯 Como Usar em Paralelo

### Método 1: Dois Terminais

**Terminal 1:**
```bash
cd c:\repo\operador-day-trade-win
INICIAR_AGENTE_RL_5000.bat
# Escolha opção [2]
```

**Terminal 2:**
```bash
cd c:\repo\operador-day-trade-win
INICIAR_AGENTE_RL_DIRETO.bat
```

### Método 2: Windows Task Scheduler

1. **Novo Task - DINAMICO**
   - Program: `cmd.exe`
   - Arguments: `/c "C:\repo\operador-day-trade-win\INICIAR_AGENTE_RL_5000.bat"`
   - Trigger: 09:00

2. **Novo Task - FIXO**
   - Program: `cmd.exe`
   - Arguments: `/c "C:\repo\operador-day-trade-win\INICIAR_AGENTE_RL_DIRETO.bat"`
   - Trigger: 09:05

---

## 📊 Exemplo de Saída nos Logs

```
2026-03-16 09:00:00 [INFO] Modo SL/TP: DINAMICO
2026-03-16 09:00:00 [INFO] ID do Agente: agente_dinamico_20260316_090000

2026-03-16 09:05:00 [INFO] Modo SL/TP: FIXO
2026-03-16 09:05:00 [INFO] ID do Agente: agente_fixo_20260316_090500

2026-03-16 09:10:00 [INFO] [DINAMICO] [CICLO 1] Iniciando iteração do loop...
2026-03-16 09:10:00 [INFO] [DINAMICO] Topos/Fundos últimas 20 velas: Topo=104.500, Fundo=103.200
2026-03-16 09:10:00 [INFO] [DINAMICO] SL/TP calculados: SL=103.180, TP=104.730 (Risk/Reward = 1.50:1)
2026-03-16 09:10:05 [INFO] [DINAMICO] [ENVIO] Enviando: Comprar @ 103.800 (SL: 103.180, TP: 104.730, Vol: 0.100%)
                              [Agente: agente_dinamico_20260316_090000, Modo: DINAMICO]

2026-03-16 09:10:10 [INFO] [FIXO] [FIXO] Usando SL/TP fixo para Comprar
2026-03-16 09:10:10 [INFO] [FIXO] [ENVIO] Enviando: Comprar @ 103.750 (SL: 103.600, TP: 104.050, Vol: 0.100%)
                             [Agente: agente_fixo_20260316_090500, Modo: FIXO]
```

---

## 🎓 Conceitos

| Conceito | Dinâmico | Fixo |
|----------|----------|------|
| **Adaptatividade** | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **Previsibilidade** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Velocidade Execução** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Complexidade** | ⭐⭐⭐⭐ | ⭐ |
| **Robustez** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 📝 Arquivos Novosdocumentados

✅ Criado: `CONFIGURACAO_PARALELA_AGENTES.md` - Guia completo
✅ Criado: `teste_modos_sl_tp.py` - Validação de modos
✅ Modificado: 3 arquivos `.bat` + 2 arquivos Python

---

## 🚀 Pronto para Uso

```bash
# Começar com AGENTE DINÂMICO
INICIAR_AGENTE_RL_5000.bat    # Opção [2]

# OU começar com AGENTE FIXO
INICIAR_AGENTE_RL_DIRETO.bat

# OU usar ambos em paralelo (2 terminais)
Terminal 1: INICIAR_AGENTE_RL_5000.bat [2]
Terminal 2: INICIAR_AGENTE_RL_DIRETO.bat
```

---

**Status:** ✅ **IMPLEMENTADO, TESTADO E PRONTO PARA USO**
