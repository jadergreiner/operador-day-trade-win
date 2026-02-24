# ✅ CHECKLIST DEPLOYMENT ESTÁGIO 1 - 23/02/2026

**Data:** 23 de Fevereiro de 2026
**Hora Início:** 20:00 BRT (23:00 UTC)
**Hora Deploy:** 20:30 BRT (23:30 UTC)
**Duração Estimada:** 2 horas
**Owner:** Eng Sr + QA Lead
**Status:** 🟢 **PRONTO PARA COMEÇAR AGORA**

---

## 📋 PRÉ-DEPLOYMENT CHECKLIST

### Validações Ambiente

```
PRÉ-REQUISITOS TÉCNICOS:

[ ] Python 3.11+ instalado
    └─ Command: python --version
    └─ Expected: Python 3.11.x ou superior

[ ] pip/poetry atualizado
    └─ Command: pip --version
    └─ Expected: pip 23.0+

[ ] Dependências instaladas (requirements.txt)
    └─ Command: pip install -r requirements.txt
    └─ Expected: fastapi, websockets, pandas, numpy, xgboost, pytest

[ ] Diretórios estrutura existem
    └─ src/
    └─ tests/
    └─ config/
    └─ scripts/
    └─ logs/
    └─ data/

[ ] Arquivo backtest_optimized_results.json existe
    └─ Command: ls -lh backtest_optimized_results.json
    └─ Expected: File size > 1MB

[ ] Porta 8765 disponível (WebSocket)
    └─ Command: netstat -tln | grep 8765
    └─ Expected: Port not in use

[ ] .env configurado (ou criado com defaults)
    └─ WEBSOCKET_PORT=8765
    └─ LOG_LEVEL=INFO
    └─ RISK_CIRCUIT_THRESHOLD_1=0.03
```

---

## 🚀 DEPLOYMENT CHECKLIST - ESTÁGIO 1

### Componente 1: WebSocket Server

```
CÓDIGO PRONTO:
[ ] src/application/websocket_server.py (270 LOC)
    └─ Status: 100% completo
    └─ Testes: 6/6 passing
    └─ Latência: <500ms validada

TESTES:
[ ] test_websocket_direct.py rodando
    └─ Command: pytest tests/test_websocket_direct.py -v
    └─ Expected: 6/6 passed

DEPLOY:
[ ] Imports validados
    □ from src.application.websocket_server import WebSocketServer
    □ from src.application.websocket_server import ConnectionManager

[ ] Configuração aplicada
    □ Host: 127.0.0.1
    □ Port: 8765
    □ Max connections: 100
    □ Log level: INFO

[ ] Health check
    □ Server pode iniciar sem erro
    □ Responde a conexões mock
    □ Logs sendo escritos

✓ READY: WebSocket Server LIVE
```

### Componente 2: Risk Validator

```
CÓDIGO PRONTO:
[ ] src/application/risk_validator.py (180 LOC)
    └─ Status: 100% completo
    └─ Testes: 5/5 passing
    └─ Gates: 3 validadores implementados

TESTES:
[ ] Testes de risk validation
    └─ Command: pytest tests/ -k risk -v
    └─ Expected: 5/5 passed

GATES VALIDADOS:
[ ] Gate 1: Capital Adequacy
    └─ Verifica capital disponível
    └─ Rejeita se capital < mínimo

[ ] Gate 2: Correlation Check
    └─ Verifica correlação portfolio
    └─ Máximo 70% permitido
    └─ Rejeita se > 70%

[ ] Gate 3: Volatility Bands
    └─ Verifica bandas de volatilidade
    └─ Rejeita se fora da banda

CIRCUIT BREAKERS:
[ ] -3% threshold
    └─ Ativa: ALERTA (trader continua)

[ ] -5% threshold
    └─ Ativa: SLOW MODE (50% tamanho ticket, 90% ML score)

[ ] -8% threshold
    └─ Ativa: HALT (tudo para)

OVERRIDE MANUAL:
[ ] Operador pode vetar qualquer ordem
    └─ 100% do tempo disponível
    └─ Log auditado

✓ READY: Risk Validator LIVE
```

### Componente 3: BDI Detector

```
CÓDIGO PRONTO:
[ ] src/application/bdi_processor.py com pattern_detector (210 LOC)
    └─ Status: 100% completo
    └─ Detecção spike: 300+ validada
    └─ Logging: Ativo

VALIDAÇÕES:
[ ] Carrega velas BDI sem erro
    └─ Command: pytest test_bdi_integration.py -v
    └─ Expected: 10 velas processadas, zero erros

[ ] Detecta padrões corretamente
    └─ Spike detection: Ativo
    └─ Pattern recognition: Ativo
    └─ False positive rate: < 5%

DEPLOYMENT:
[ ] Configuração aplicada
    └─ Data source: BDI velas (MT5)
    └─ Sensitivity: Normal
    └─ Logging: Ativo

[ ] Health check
    └─ Detector responde em < 100ms
    └─ Logs sendo escritos

✓ READY: BDI Detector LIVE
```

### Componente 4: Feature Pipeline

```
CÓDIGO PRONTO:
[ ] src/application/ml_feature_engineer.py (24 features)
    └─ Status: 100% pronto para staging
    └─ Dataset: 17.280 velas
    └─ NaN values: 0 (100% limpo)

FEATURES ENGINEERED:
[ ] Volatilidade (4): Bollinger Bands, ATR, Historical Vol, 3-Sigma
[ ] Momentum (4): RSI, MACD, ROC, OBV
[ ] Moving Averages (5): SMA 50, EMA 9/21, slopes
[ ] Padrões (3): Mean reversion, Volume spike, Impulse
[ ] Lags (9): Return lags, Close/volume lags
[ ] Correlação (2): 20-period correlation, Trend strength

DATA QUALITY:
[ ] Zero NaN values
    └─ Command: python -c "import pandas as pd; df=pd.read_json(...); print(df.isna().sum())"
    └─ Expected: 0 NaN in all columns

[ ] StandardScaler aplicado
    └─ Mean = 0, Std = 1 para cada feature
    └─ Status: Validado

DEPLOYMENT:
[ ] Dataset carregado para staging
    └─ File: 17.280 x 24 features
    └─ Format: CSV/Parquet/JSON

[ ] Health check
    └─ Data pode ser carregado em < 500ms
    └─ Shape correto: (17280, 24)

✓ READY: Feature Pipeline LIVE (STAGING)
```

---

## 🔄 TESTES SMOKE (Validação Rápida)

```
TESTE 1: Imports
┌─────────────────────────────────────────┐
└─ python -c "
    from src.application.websocket_server import WebSocketServer
    from src.application.risk_validator import RiskValidator
    from src.application.bdi_processor import BDIProcessor
    from src.application.ml_feature_engineer import FeatureEngineer
    print('✓ Todos imports OK')
  "
└─ Expected: ✓ Todos imports OK

TESTE 2: Configuração
┌─────────────────────────────────────────┐
└─ Verificar config/deployment_config.json existe
└─ Verificar .env configurado
└─ Expected: Ambos arquivos com valores corretos

TESTE 3: Logs
┌─────────────────────────────────────────┐
└─ mkdir -p logs/
└─ Verificar logs/ criado
└─ Expected: Diretório pronto para logs

TESTE 4: Health URLs
┌─────────────────────────────────────────┐
└─ WebSocket: ws://127.0.0.1:8765
└─ Risk API: http://127.0.0.1:8000/health (quando ativo)
└─ Expected: Porta 8765 responsiva
```

---

## 📦 DEPLOYMENT - APLICAR CONFIGURAÇÕES

### Step 1: Validações Finais

```
[ ] Todos pré-requisitos checados
[ ] Todos testes smoke passos
[ ] Nenhum erro crítico identificado
[ ] Board approval confirmado ✓
```

### Step 2: Aplicar Configurações

```
[ ] WebSocket configurado
    └─ Host: 127.0.0.1
    └─ Port: 8765
    └─ Max connections: 100

[ ] Risk configurado
    └─ Capital adequacy: ativo
    └─ Correlation max: 70%
    └─ Circuit breakers: -3%/-5%/-8%

[ ] BDI configurado
    └─ Spike sensitivity: normal
    └─ Pattern recognition: ativo
    └─ Audit logging: ativo

[ ] Features configurado
    └─ Features count: 24
    └─ Candles loaded: 17.280
    └─ Scaling: StandardScaler
```

### Step 3: Iniciar Componentes

```
[ ] WebSocket iniciando
    └─ Comando: python scripts/run_websocket_server.py
    └─ Esperado: Server listening on 0.0.0.0:8765

[ ] Risk Validator ready
    └─ Validar import sem erro
    └─ Status: Ready to validate orders

[ ] BDI Detector ready
    └─ Validar padrões carregados
    └─ Status: Ready to monitor spikes

[ ] Features Pipeline ready
    └─ Validar 17.280 velas carregadas
    └─ Status: Ready for Grid Search
```

### Step 4: Iniciar Monitoramento

```
[ ] Health checks ativado (30seg intervals)
    └─ WebSocket: Port 8765 listening
    └─ Risk: Memory < 100MB
    └─ BDI: Detector responding < 100ms
    └─ Features: Data loaded correctly

[ ] Logging ativado
    └─ logs/websocket.log
    └─ logs/risk_validator.log
    └─ logs/bdi_detector.log
    └─ logs/features.log

[ ] Dashboard criado
    └─ logs/deployment_status.txt
    └─ Status: Updated a cada 5min
    └─ Alertas: Enviados se problemas
```

---

## ⏱️ TIMELINE DETALHADA

```
20:00 BRT (23:00 UTC) - COMEÇA
└─ Eng Sr + QA synchronize
└─ ML Expert começa TODO-1 labels (paralelo)

20:05 BRT - PRÉ-DEPLOYMENT VALIDATION
└─ [ ] Todas validações acima completadas

20:15 BRT - PREPARAÇÃO DEPLOYMENT
└─ [ ] Scripts preparados
└─ [ ] Configurações aplicadas
└─ [ ] Ambientes prontos

20:30 BRT (23:30 UTC) - DEPLOYMENT INFRASTRUCTURE COMÇA
└─ [ ] WebSocket server inicia
└─ [ ] Risk validator ativa
└─ [ ] BDI detector ativa
└─ [ ] Features pipeline carrega

21:00 BRT (00:00 UTC do dia 24) - SMOKE TESTS
└─ [ ] Health checks passando
└─ [ ] Imports validados
└─ [ ] Logging ativo

21:30 BRT (00:30 UTC do dia 24) - STAGE 1 LIVE
└─ [ ] Todos 4 componentes LIVE
└─ [ ] Monitoramento 24/7 ativo
└─ [ ] Status dashboard updated
└─ ✅ ESTÁGIO 1 DEPLOYMENT COMPLETO

03:00 BRT (06:00 UTC do dia 24) - TODO-1 LABELS COMPLETO
└─ [ ] ML Expert termina TODO-1
└─ [ ] Labels validados (zero NaN, imbalance OK)
└─ [ ] Dataset pronto para Grid Search

09:00 BRT (12:00 UTC do dia 24) - NOVO DIA COMÇA
└─ [ ] OrdersExecutor START (Eng Sr)
└─ [ ] Grid Search START (ML Expert)
└─ [ ] Daily Standup 15:00
```

---

## 📊 VALIDAÇÕES PÓS-DEPLOYMENT

### Verificações Críticas (30 min após deploy)

```
✓ WebSocket
  └─ nc -zv 127.0.0.1 8765
  └─ Expected: Connection successful

✓ Risk Validator
  └─ Verificar 3 gates respondendo
  └─ Expected: Gates validando orders

✓ BDI Detector
  └─ Verificar spikes detectados últimos 5min
  └─ Expected: Detector ativo

✓ Features
  └─ Verificar arquivo carregado
  └─ Expected: 17.280 x 24 shape

✓ Monitoramento
  └─ Verificar health checks rodando
  └─ Expected: 0 critical alerts
```

### Validações Estendidas (2h após deploy)

```
✓ Performance
  └─ Latência média WebSocket: < 500ms
  └─ CPU usage: < 30%
  └─ Memory usage: < 200MB total

✓ Erros
  └─ Zero erros críticos em logs
  └─ Warnings aceitáveis (atualizações, deprecations)

✓ Audit Trail
  └─ Todos eventos registrados em logs
  └─ Timestamps corretos
  └─ Correlations rastreáveis

✓ Scaling
  └─ WebSocket: 100 mock connections
  └─ Risk: 50 validations/segundo
  └─ BDI: 1000+ datapoints processados
```

---

## 🎯 SUCESSO CRITERIA

```
Stage 1 Deployment é SUCESSO se:

✅ Todos 4 componentes LIVE e respondendo
✅ Zero erros críticos nos logs
✅ Health checks 100% passing
✅ Monitoramento ativo e alertas funcionando
✅ TODO-1 Labels pronto antes Grid Search
✅ Board approval confirmado (7/7 personas)
✅ Documentação atualizada
✅ Status enviado em 21:30 BRT (após 1h live)
```

---

## 🚨 PLANO DE ROLLBACK

Se problemas encontrados durante deployment:

```
CRITICIDADE 🔴 (Rollback imediato):
├─ WebSocket não inicia → Parar deployment, debug
├─ Risk validator exceptions → Parar deployment
├─ CPU/Memory spike anormal → Parar deployment
└─ Logs com erros críticos → Parar deployment

AÇÃO:
  git checkout HEAD~1  (reverter última mudança)
  Restart componentes

CRITICIDADE 🟠 (Observar, corrigir):
├─ Warnings em logs (não critério)
├─ Performance degradada < 20%
├─ Memory creep baixo
└─ Alertas não-críticos

AÇÃO:
  Continuar monitorando
  Debug conforme encontrado
  Escalate se piora

CRITICIDADE 🟢 (Proceder normalmente):
├─ Status OK
├─ Performance within targets
├─ Zero critical issues
└─ All 4 components healthy

AÇÃO:
  Continue deployment
  Monitoramento 24h
  Prepare próximas tarefas (TODO-1, Orders)
```

---

## ✅ SIGN-OFF FINAL

```
Após completion de todos itens acima:

[ ] Eng Sr: Deployment checks OK, sign-off ___________

[ ] QA Lead: Validation checks OK, sign-off ___________

[ ] Arquiteto: Architecture review OK ___________

[ ] Risk Officer: Risk profile acceptable ___________

Status: ✅ STAGE 1 DEPLOYMENT APPROVED & LIVE

Hora: _____________ BRT (UTC: _____________)

Próxima ação: TODO-1 Labels (paralelo já em andamento)
              + Monitoramento 24h contínuo
```

---

**Documento:** CHECKLIST_DEPLOYMENT_STAGE1_23FEV.md
**Status:** ✅ PRONTO PARA SEGUIR
**Owner:** Eng Sr + QA Lead
**Data:** 23 de Fevereiro de 2026
