"""
EXEMPLOS DE LOG: SIGNAL GENERATION & MONITORING (Camada 1)

Demonstração realista de como sinais AC1 serão exibidos em logs
quando integrados com INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat

Reference: docs/prompts/OPERATIVE_BRIEF_BACKTEST_V1_2.md (AC1-AC3)
Date: 05/03/2026
"""

# ============================================================================
# EXEMPLO 1: SIGNAL GENERATION LOG (Camada 1 - Detection Phase)
# ============================================================================

LOG_SIGNAL_GENERATION = """
============================================================================
[2026-03-05 14:23:15.342] OPERADOR MICRO TENDENCIA - v1.2.3 START
============================================================================

[PRE-FLIGHT] Verificando saude do sistema v1.2.3...
  [OK] Python version: 3.11.9
  [OK] SQLite: data/db/trading.db (45.2 MB, accessible)
  [OK] ML Dataset: 1,000 samples loaded (24 features)
  [OK] MT5 Connection: Connected to account 1234567 (DEMO)
  [PASS] Pre-flight check PASSED

[SYNC] Sincronizando operacoes MT5...
  [OK] MT5 trades sincronizados (3 days back)

[BDI] Aplicando licoes BDI...
  [OK] Licoes BDI aplicadas (06/03/2026)

[JOURNAL] Iniciando Diario RL em background...
  [OK] Diario RL iniciado

============================================================================
[14:23:45.123] AGENT EXECUTOR INICIADO - Aguardando sinais em M5
============================================================================

[14:24:00.000] [M5-CANDLE-CLOSED] Timeframe=M5, Symbol=WIN, Candle_Index=2845

[14:24:00.001] [DETECTOR] Processando candle M5...
  ├─ Open:  123.450
  ├─ High:  123.650
  ├─ Low:   123.250
  ├─ Close: 123.600
  ├─ Volume: 450 contratos
  └─ Prev_High: 123.450 | Prev_Low: 123.200

[14:24:00.005] [AC1-Signal] BOS detectado (score=+1.50)
  ├─ Tipo: COMPRA (rompimento de estrutura de alta)
  ├─ Detector: BOS (Fechamento 123.600 > Máxima_Anterior 123.450)
  ├─ Pontuação: +1.50 (intervalo: [-3, +3])
  ├─ Preço_Entrada: 123.600
  └─ Índice_Vela: 2845

[14:24:00.008] [MARKET-CONTEXT] Capturando contexto de mercado...
  ├─ RSI(14): 65.5 (zona de sobre-compra)
  ├─ ATR(14): 50.0 pontos
  ├─ Bollinger Bands:
  │  ├─ Superior: 123.750
  │  └─ Inferior: 123.150
  ├─ Volume: 450 (acima da média: 280)
  ├─ Spread: 2.0 pontos
  ├─ Direção_Tendência: ALTA (últimas 5 velas)
  └─ Último_Fechamento: 123.450

[14:24:00.012] [SIGNAL-CRIADO] Sinal gerado e pronto para Camada 2
  ├─ signal_id: d4a82f1c-3e91-4f22-9c2e-7b4a8d2e5c1f
  ├─ timestamp: 2026-03-05T14:24:00.012Z
  ├─ symbol: WIN
  ├─ tipo_sinal: COMPRA
  ├─ pontuação_smc: +1.50
  ├─ detector_smc: BOS
  ├─ preço_entrada: 123.600
  └─ contexto_mercado: CAPTURADO (8 campos)

[14:24:00.015] [AC1-PERSISTÊNCIA] Persistindo sinal em DB...
  ├─ Tabela: signals
  ├─ ID_Sinal: d4a82f1c-3e91-4f22-9c2e-7b4a8d2e5c1f
  ├─ Status: INSERIDO com sucesso
  └─ Pronto para Camada 2 (Motor de Decisão)

============================================================================
[14:24:00.020] [CAMADA-1-COMPLETA] Geração de sinal FINALIZADA
  └─ Aguardando Camada 2 (Motor de Decisão) para ENTRAR/FICAR_DE_FORA
============================================================================

"""

# ============================================================================
# EXEMPLO 2: SIGNAL MONITORING LOG (Camada 1 - Lifecycle Tracking)
# ============================================================================

LOG_SIGNAL_MONITORING = """
============================================================================
[14:24:05.000] [SIGTRACKER] Iniciando rastreamento de signals...
============================================================================

[AC1-RASTREAMENTO] Sinal gerado: d4a82f1c-3e91-4f22-9c2e-7b4a8d2e5c1f
  ├─ Tipo: COMPRA (score +1.50)
  ├─ Preço_Entrada: 123.600
  ├─ Tempo_Ativo: 5s
  └─ Status: ABERTO (aguardando Camada 2)

[14:24:10.000] [M5-CANDLE-CLOSED] Timeframe=M5, Index=2846

[AC1-CHECK] Sinal d4a82f1c ainda em rastreamento...
  ├─ Current_Close: 123.620
  ├─ High desde geração: 123.750
  ├─ Low desde geração: 123.250
  ├─ P&L se tivesse entrado: +20 pontos
  └─ Status: WINNING_POTENTIAL (não entrou, mas sinalizava certo)

[14:24:15.000] [M5-CANDLE-CLOSED] Timeframe=M5, Index=2847

[AC1-CHECK] Sinal d4a82f1c ainda em rastreamento...
  ├─ Current_Close: 123.750 (NEW HIGH)
  ├─ High máximo desde geração: 123.750
  ├─ P&L se tivesse entrado: +150 pontos
  └─ Status: WINNING_SIGNAL (rastreado com sucesso)

[14:24:30.000] [M5-CANDLE-CLOSED] Timeframe=M5, Index=2848

[AC1-CHECK] Sinal d4a82f1c rastreado por 30s...
  ├─ Fechamento_Atual: 123.680
  ├─ Máxima_Pico: 123.750 (atingida 15s atrás)
  ├─ Mínima_Atual: 123.150
  ├─ P&L máximo: +150 pontos
  ├─ P&L atual: +80 pontos
  └─ Status: SINAL_VENCEDOR (descendo de pico)

[14:25:00.000] [M5-CANDLE-CLOSED] Timeframe=M5, Index=2849

[AC1-FINALIZE] Sinal d4a82f1c encerrado...
  ├─ Preço_Fechamento: 123.595
  ├─ Duração: 60 segundos (12 velas M5)
  ├─ P&L_Pico: +150 pontos
  ├─ P&L_Final: -5 pontos (toque e vai)
  ├─ Resultado: CHICOTE (movimentou para cima, depois retraiu)
  └─ Razão encerramento: Modelo detectou reversão, sinal encerrado

[AC1-ARCHIVED] Sinal armazenado para Camada 3 Learning...
  ├─ signal_id: d4a82f1c-3e91-4f22-9c2e-7b4a8d2e5c1f
  ├─ status: ARQUIVADO
  ├─ tipo_resultado: CHICOTE
  ├─ pnl_resultado: -5 pontos
  ├─ dias_aberto: 0.001 (1 minuto)
  └─ Aguardando Camada 3: Análise de feedback de aprendizado

============================================================================
[14:25:02.000] [SUMMARY-AC1] Primeira hora de operacao
============================================================================

[AC1-MÉTRICAS]
  ├─ Sinais gerados: 8
  ├─ Sinais VENCEDORES: 5 (62.5%)
  ├─ Sinais CHICOTE: 2 (25%)
  ├─ Sinais OPORTUNIDADE_PERDIDA: 1 (12.5%)
  ├─ Duração_Média: 45s
  ├─ P&L_Máximo: +150 pontos
  ├─ P&L_Mínimo: -45 pontos
  └─ Distribuição_Resultado:
     ├─ SINAL_VENCEDOR: 62.5%
     ├─ CHICOTE: 25%
     └─ OPORTUNIDADE_PERDIDA: 12.5%

[AC1-PERSISTÊNCIA] Status DB
  ├─ Tabela: signals
  ├─ Total registrado: 8
  ├─ Com contexto_mercado: 8 (100%)
  ├─ Pronto para Camada 2: 8
  └─ Aguardando Camada 3: 8

"""

# ============================================================================
# EXEMPLO 3: INTEGRATION WITH INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
# ============================================================================

LOG_BAT_INTEGRATION = """
============================================================================
[14:23:00] INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat v1.2.3
============================================================================

[PRE-FLIGHT] Verificando saude do sistema v1.2.3...
   [✓] Python 3.11.9 detectado
   [✓] Banco de dados SQLite acessível
   [✓] Dataset ML carregado: 1,000 amostras
   [✓] MT5 API online

[SYNC] Sincronizando operacoes MT5...
   [✓] 3 dias anteriores importados nas estatísticas

[BDI] Aplicando licoes BDI...
   [✓] Lições do dia anterior carregadas

[JOURNAL] Iniciando Diario RL...
   [✓] Logger em background iniciado

[GATE2] Validando GATE 2 (prontidão de backtest)...
   [✓] GATE 2 PASSOU - Escalando para R$ 100k

============================================================================
[14:23:45] AGENT EXECUTOR - Hook de Detecção de Sinal AC1
============================================================================

Chamando: python scripts/agent_executor_with_ml.py --mode auto-trade

  ├─ Carregando modelo ML: XGBoost (F1=0.68, Taxa de Vitória=62%)
  ├─ Inicializando detector SMC para M5...
  ├─ Conectando ao feed MT5 ao vivo...
  └─ Aguardando velas M5...

[14:24:00] EVENTO DE VELA M5 AO VIVO
  └─ Gatilho: vela M5 fechada @14:24:00

[AC1-ATIVAÇÃO] Pipeline de Geração de Sinal Iniciado
  ├─ Extrair M5 OHLC (open, high, low, close, volume)
  ├─ Detectar padrão SMC (BOS/CHoCH/FVG)
  ├─ Calcular pontuação [-3, +3]
  ├─ Capturar contexto de mercado (RSI, ATR, BB, volume, spread, tendência)
  └─ Gerar signal_id (UUID)

[AC1-BARRAMENTO-SINAL] Publicando sinal para Fila de Mensagens
  └─ Sinal pronto para Camada 2 (Motor de Decisão)
     └─ [FILA-DECISÃO] ENTRAR ou FICAR_DE_FORA?

============================================================================
[14:24:05] VELAS SUBSEQUENTES - AC1 Monitoramento Ativo
============================================================================

[14:24:10] [M5-VELA] Atualização de rastreamento de sinal
  ├─ Sinal: d4a82f1c-3e91-4f22-9c2e-7b4a8d2e5c1f
  ├─ Preço_Atual: 123.620
  ├─ Preço_Sinal: 123.600
  ├─ P&L: +20 pontos
  └─ Status: POTENCIAL_VENCEDOR

[14:24:15] [M5-VELA] Atualização de rastreamento de sinal
  ├─ Preço_Atual: 123.750 (NOVA MÁXIMA)
  ├─ P&L: +150 pontos
  └─ Status: SINAL_VENCEDOR

============================================================================
[14:25:00] PAINEL DE MONITORAMENTO (Visualização AC1)
============================================================================

┌─────────────────────────────────────────────────────────────────────────┐
│ CAMADA 1: GERAÇÃO E MONITORAMENTO DE SINAL                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│ ID_Sinal              │ Tipo  │ Pontu. │ Status      │ P&L      │ Idade │
│ d4a82f1c-3e91-4f22... │ CMPR  │ +1.50  │ VENCEDOR    │ +150pts  │ 1m    │
│ a7c3f9d2-5e71-2d...   │ VENDA │ -2.00  │ CHICOTE     │ -5pts    │ 25s   │
│ b1e4a8f3-9d82-4b...   │ CMPR  │ +1.00  │ ABERTO      │ +45pts   │ 8s    │
│                                                                         │
│ Sinais em monitoramento: 3                                             │
│ Sinais completados hoje: 5                                             │
│ Taxa de vitória (hoje): 60%                                            │
│ Duração média: 45 segundos                                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

"""

# ============================================================================
# EXEMPLO 4: DETAILED SIGNAL LOG WITH ALL FIELDS (Technical Reference)
# ============================================================================

LOG_DETAILED_SIGNAL_FIELDS = """
============================================================================
[14:24:00.012] [AC1-SIGNAL-JSON] Full Signal Object (DB Insert Preview)
============================================================================

{
  "signal_id": "d4a82f1c-3e91-4f22-9c2e-7b4a8d2e5c1f",
  "timestamp": "2026-03-05T14:24:00.012Z",
  "symbol": "WIN",
  "signal_type": "BUY",
  "smc_score": 1.50,
  "smc_detector": "BOS",
  "entry_price": 123.600,
  "candle_index": 2845,
  
  "market_context": {
    "rsi": 65.5,
    "atr": 50.0,
    "bb_upper": 123.750,
    "bb_lower": 123.150,
    "volume": 450,
    "spread": 2.0,
    "trend_direction": "UP",
    "last_close": 123.450
  },
  
  "created_at": "2026-03-05T14:24:00.012Z",
  "updated_at": null,
  "outcome_type": null,
  "outcome_pnl": null,
  "outcome_days_open": null,
  "closed_at": null
}

============================================================================
[14:24:00.015] [AC1-DB-INSERT] SQL Statement Generated
============================================================================

INSERT INTO signals (
  signal_id, timestamp, symbol, signal_type, smc_score, smc_detector, 
  entry_price, candle_index, market_context_json, created_at
) VALUES (
  'd4a82f1c-3e91-4f22-9c2e-7b4a8d2e5c1f',
  '2026-03-05 14:24:00.012',
  'WIN',
  'BUY',
  1.50,
  'BOS',
  123.600,
  2845,
  '{\"rsi\":65.5,\"atr\":50.0,\"bb_upper\":123.750,\"bb_lower\":123.150,\"volume\":450,\"spread\":2.0,\"trend_direction\":\"UP\",\"last_close\":123.450}',
  '2026-03-05 14:24:00.012'
)

============================================================================
[14:25:00.000] [AC1-DB-UPDATE] Signal Closing (Outcome Known)
============================================================================

UPDATE signals SET
  outcome_type = 'WHIPSAW',
  outcome_pnl = -5.0,
  outcome_days_open = 0.001,
  closed_at = '2026-03-05 14:25:00.000',
  updated_at = '2026-03-05 14:25:00.000'
WHERE signal_id = 'd4a82f1c-3e91-4f22-9c2e-7b4a8d2e5c1f'

"""

# ============================================================================
# EXEMPLO 5: ERROR CASES & EDGE CASES (Logging)
# ============================================================================

LOG_ERROR_CASES = """
============================================================================
[AC1-CENÁRIOS DE ERRO E TRATAMENTO]
============================================================================

CENÁRIO 1: Rejeição de Sinal Fraco
────────────────────────────────────────────────────────────────────────

[14:26:00.000] [M5-VELA-FECHADA] Timeframe=M5, Symbol=WIN, Index=2852

[DETECTOR] Processando vela M5...
  ├─ Open:  123.400
  ├─ Close: 123.405  (movimento muito pequeno)
  └─ Máxima_Anterior: 123.400

[AC1-DETECTOR] Avaliação SMC:
  └─ Fechamento 123.405 NÃO > Máxima_Anterior 123.400 (|0.005| < 1.0)
  └─ Nenhuma estrutura detectada (BOS/CHoCH/FVG)

[AC1-REJEITADO] Sinal fraco (pontuação < |1.0|)
  ├─ Razão: Movimento insuficiente para trading
  ├─ Pontuação: 0.0 (abaixo do limite 1.0)
  └─ Status: IGNORADO (não persistido em DB)

────────────────────────────────────────────────────────────────────────

CENÁRIO 2: Captura de Contexto de Mercado com Valores NaN
────────────────────────────────────────────────────────────────────────

[14:27:00.000] [CONTEXTO-MERCADO] Cálculo de RSI indisponível

[AC1-CONTEXTO] Capturando contexto...
  ├─ RSI(14): NaN (apenas 5 velas de histórico)
  ├─ ATR(14): 45.0
  ├─ BB: OK
  ├─ Volume: OK
  ├─ Spread: OK
  ├─ Tendência: OK
  └─ último_fechamento: OK

[AC1-SINAL] Sinal criado mesmo com RSI=NaN
  └─ Raciocínio: 7/8 campos de contexto preenchidos (87.5%)
  └─ ContextoMercado(rsi=None, atr=45.0, ...)

────────────────────────────────────────────────────────────────────────

CENÁRIO 3: Rejeição de Sinal Duplicado (Mesmas condições)
────────────────────────────────────────────────────────────────────────

[14:28:00.000] [M5-VELA-FECHADA] Timeframe=M5, Index=2854

[AC1-SINAL] BOS detectado (score=+1.50)
  └─ signal_id: 9f7c2e1a-4b65-3d82-1e9f-8c4a2d5e7b3f (ÚNICO)

[14:28:05.000] [M5-VELA-FECHADA] Timeframe=M5, Index=2855

[DETECTOR] Processando vela M5...
  ├─ Mesma estrutura BOS
  ├─ Pontuação: +1.50
  └─ [AC1-SINAL] signal_id: 0a8d3f2b-5c76-4e93-2f0a-9d5b3e6f8c4a (ÚNICO!)

[RESTRIÇÃO-DB] ÚNICO(timestamp, symbol, signal_type, smc_score)
  └─ Restrição previne duplicatas exatas
  └─ Mas diferentes signal_ids rastreiam diferentes instâncias

────────────────────────────────────────────────────────────────────────

CENÁRIO 4: Caso Extremo - Preço exato mas contexto diferente
────────────────────────────────────────────────────────────────────────

[14:29:00.000] SINAL 1: BOS @ 123.600
  │
  ├─ RSI: 65.5 (sobre-compra)
  ├─ Volume: 450 (alta)
  ├─ ATR: 50.0
  └─ signal_id: A123 → CRIADO

[14:29:20.000] SINAL 2: BOS @ 123.600
  │
  ├─ RSI: 45.0 (neutro)
  ├─ Volume: 100 (baixa)
  ├─ ATR: 20.0
  └─ signal_id: B456 → CRIADO (contexto diferente!)

[AC1-CAPTURA-CONTEXTO] Ambos sinais salvos com contexto_mercado_json distinto
  │
  ├─ Sinal A: contexto_mercado = {...,\"rsi\":65.5,\"volume\":450,...}
  ├─ Sinal B: contexto_mercado = {...,\"rsi\":45.0,\"volume\":100,...}
  │
  └─ Aprendizado (Camada 3): Pode comparar resultados
      ├─ Sinal com contexto forte (RSI sobre-compra): +150 pnl (sorte?)
      ├─ Sinal com contexto fraco (RSI neutro): -5 pnl
      └─ Conclusão: contexto importa para aprendizado!

"""

if __name__ == "__main__":
    print(__doc__)
    print(LOG_SIGNAL_GENERATION)
    print(LOG_SIGNAL_MONITORING)
    print(LOG_BAT_INTEGRATION)
    print(LOG_DETAILED_SIGNAL_FIELDS)
    print(LOG_ERROR_CASES)
