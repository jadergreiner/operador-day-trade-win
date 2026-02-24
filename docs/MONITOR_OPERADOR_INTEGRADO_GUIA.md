# Monitor Operador Integrado v2.0 - Guia Operacional

## 🎯 Visão Geral: Sincronização 100% Tempo Real

O **Monitor Operador Integrado v2.0** implementa a governança do ROADMAP:
> **"Sincronia Operador x Monitor: Toda evolução técnica no motor de trading DEVE ser testada e aplicada simultaneamente"**

Este monitor sincroniza o **Operador de Execução** (`INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`) com o **S2-6 Analytics** em 100% tempo real.

---

## 📋 Componentes da Integração

### 1️⃣ Monitor Operador Integrado (`monitor_operador_integrado.py`)
Exibe em um único painel:
- ✅ **Status Operador**: Componentes do operador de execução
- ✅ **S2-6 Analytics**: Estatísticas em tempo real
- ✅ **Breakdown de Ações**: Tipos de intervenção (OVERRIDE, PAUSE, CANCEL, EXECUTE)
- ✅ **Timeline Recente**: Últimas operações com P&L
- ✅ **Risk Validators**: Status dos 3 gates + circuit breakers

### 2️⃣ S2-6 Analytics Dashboard (`monitor_s2_6_dashboard.py`)
Dashboard isolado focado apenas em analytics:
- 📊 Estatísticas gerais (Win rate, P&L, Ticket médio)
- 💱 Stats por símbolo (Top 10)
- 🎯 Breakdown de ações
- ⏱️ Últimas operações (Top 10)
- 🏥 Saúde do sistema

### 3️⃣ Menu Unificado (`MONITOR_OPERADOR.bat` v2.0)
Interface de seleção oferecendo 3 modos:
1. **Monitor Integrado**: Visão completa (Operador + Analytics)
2. **Analytics Dashboard**: Analytics ONLY (isolado)
3. **Status Operador**: Operador ONLY (isolado)

---

## 🚀 Como Usar

### Pré-requisitos
Antes de iniciar o monitor, certifique-se de que:

#### 1. S2-6 Analytics API está rodando
```bash
# Terminal 1: Inicie a API S2-6
python -m uvicorn src.interfaces.websocket_server:app --host 0.0.0.0 --port 8000
```

#### 2. Operador está em execução
```bash
# Terminal 2: Inicie o operador auto-trade
INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
```

#### 3. Monitor disparado
```bash
# Terminal 3: Menu do monitor
MONITOR_OPERADOR.bat
```

---

## 📊 Interface do Monitor Integrado

### Layout Padrão

```
╔════════════════════════════════════════════════════════════════╗
║  MONITOR OPERADOR INTEGRADO v2.0 - SINCRONIZAÇÃO 100% TEMPO REAL
║  Governança ROADMAP: Sincronia Operador x Monitor
║  HH:MM:SS DD/MM/YYYY
╚════════════════════════════════════════════════════════════════╝

[OPERADOR DE EXECUÇÃO] Status Geral
────────────────────────────────────────────────────────────
  [LIVE] Componentes operacionais ativos

[S2-6 ANALYTICS] Estatísticas em Tempo Real
────────────────────────────────────────────────────────────
  [✓] S2-6 Analytics ONLINE
    └─ Total de Intervenções: 150
    └─ 🟢 Win Rate: 62.50%
    └─ 🟢 P&L Total: R$ 15.300,00
    └─ Ticket Médio: R$ 102,00

[BREAKDOWN DE AÇÕES] Tipos de Intervenção
────────────────────────────────────────────────────────────
  [OVERRIDE    ] Override Manual         → 45x
  [EXECUTE     ] Executar Ordem          → 89x
  [PAUSE       ] Pausar Operação         → 12x
  [CANCEL      ] Cancelar Ordem          → 4x

[ÚLTIMAS OPERAÇÕES] Timeline Recente
────────────────────────────────────────────────────────────
  1. HH:MM:SS | WDOIT | EXECUTE    | 🟢 🟢 R$+120,00
  2. HH:MM:SS | WINFUT | OVERRIDE  | 🟢 🟢 R$+85,50
  3. HH:MM:SS | MDIA3 | EXECUTE    | 🔴 🔴 R$-45,20
  ...

[RISK VALIDATORS] Gates de Segurança
────────────────────────────────────────────────────────────
  🟢 ATIVO Gate 1: Capital Adequacy
  🟢 ATIVO Gate 2: Correlation Check
  🟢 ATIVO Gate 3: Volatility Band
  🟢 MONITORANDO Circuit Breaker (-3%)
  🟢 PRONTO Circuit Breaker (-5%)
  🟢 PRONTO Circuit Breaker (-8%)

═════════════════════════════════════════════════════════════
[STATUS] Sincronização: 100% | Atualização a cada 5s
[ATALHOS] Ctrl+C = Sair
═════════════════════════════════════════════════════════════
```

---

## 📱 Interpretando as Métricas

### Win Rate (🟢 / 🟡 / 🔴)
- 🟢 **Verde**: ≥ 60% (Excelente)
- 🟡 **Amarelo**: 50-59% (Aceitável)
- 🔴 **Vermelho**: < 50% (Atenção)

### P&L (🟢 / 🔴)
- 🟢 **Verde**: P&L positivo
- 🔴 **Vermelho**: P&L negativo

### Componentes ([✓] / [✗])
- [✓] **OK**: Ativo/Funcionando
- [✗] **Erro**: Inativo/Aguardando

### Resultado de Trade (🟢 / 🟡 / 🔴 / ⏳)
- 🟢 **WIN**: Operação com ganho
- 🟡 **PARTIAL**: Ganho parcial
- 🔴 **LOSS**: Operação com prejuízo
- ⏳ **PENDING**: Aguardando resultado

---

## 🔄 Fluxo de Sincronização

Quando o **Operador** executa um trade:

```
1. Operador executa trade
   └─ Calls: operador.on_trade_executed(symbol, action, ...)

2. AnalyticsAdapter registra no S2-6
   └─ POST /api/intervention/log (TradeEvent)
   └─ Returns: intervention_id

3. Trade fecha com resultado
   └─ Calls: operador.on_trade_closed(p_and_l, result)

4. Result é atualizado no S2-6
   └─ POST /api/intervention/{id}/result (result, p_and_l)

5. Monitor carrega estatísticas
   └─ GET /api/analytics/stats (cada 5s)
   └─ GET /api/analytics/dashboard (cada 5s)

6. Dashboard exibe em TEMPO REAL
   └─ Win rate atualizado
   └─ P&L recalculado
   └─ Últimas operações mostradas
```

---

## 🛠️ Troubleshooting

### Problema: "S2-6 Analytics OFFLINE"

**Causa**: API não está rodando na porta 8000

**Solução**:
```bash
cd c:\repo\operador-day-trade-win
python -m uvicorn src.interfaces.websocket_server:app --host 0.0.0.0 --port 8000
```

**Verificar**:
```bash
curl -s http://localhost:8000/health
# Deve retornar: {"status": "ok"}
```

### Problema: "Nenhuma operação recente"

**Causa**: Operador não está registrando trades no S2-6

**Solução**:
1. Verificar se Operador está usando `OperadorComAnalytics` wrapper
2. Confirmar que `on_trade_executed()` está sendo chamado
3. Verificar logs: `logs/analytics_adapter.log`

### Problema: "Status Operador: DESCONHECIDO"

**Causa**: Arquivo `logs/deployment_status.json` não existe

**Solução**:
```bash
# Garantir que o operador foi inicializado
INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
```

---

## 📊 Exemplos de Interpretação

### Cenário 1: Sistema Saudável ✅

```
[✓] S2-6 Analytics ONLINE
  └─ Total de Intervenções: 157
  └─ 🟢 Win Rate: 64.33%
  └─ 🟢 P&L Total: R$ 18.750,00
```

**Interpretação**: Operador com bom desempenho, nenhuma ação necessária.

### Cenário 2: Atenção ⚠️

```
[✓] S2-6 Analytics ONLINE
  └─ Total de Intervenções: 89
  └─ 🟡 Win Rate: 55.06%
  └─ 🔴 P&L Total: R$-2.340,00
```

**Interpretação**: Win rate caindo, começar a revisar decisões. Considerar pausar operação temporariamente.

### Cenário 3: Crítico 🔴

```
[✗] S2-6 Analytics OFFLINE
```

**Interpretação**: S2-6 não está respondendo. Verifique logs de erro e reinicie API.

---

## 🔐 Governança ROADMAP

Este monitor implementa a exigência crítica do ROADMAP:

> **"Toda evolução técnica no motor de trading DEVE ser testada e aplicada
> simultaneamente em Operador + Monitor"**

### Checklist: Sincronização Automática

- ✅ **Monitor exibe**: Status em tempo real do Operador
- ✅ **Monitor integrável**: Com S2-6 Analytics automaticamente
- ✅ **Monitor atualizável**: A cada 5 segundos (configurável)
- ✅ **Monitor rastreável**: 100% de intervenções documentadas
- ✅ **Monitor resiliente**: Reconecta automaticamente se API reiniciar

---

## 📈 Próximos Passos

1. **Integrar com Agente**:
   ```python
   from src.adapters.s2_6_analytics_adapter import AnalyticsAdapter
   from examples.operador_com_s2_6_analytics import OperadorComAnalytics

   # No seu agente principal:
   operador = OperadorComAnalytics(adapter_api_url="http://localhost:8000")
   ```

2. **Configurar Alertas**:
   - Implementar AlertManager para notificações em tempo real
   - Setup Slack/Email para eventos críticos

3. **Estender Analytics**:
   - Adicionar métricas de Sharpe ratio
   - Incluir análise de drawdown
   - Implementar correlação com macro indicators

---

## 📚 Documentação Relacionada

- [S2-6 Analytics Adapter](../src/adapters/s2_6_analytics_adapter.py)
- [Operador com Analytics](../examples/operador_com_s2_6_analytics.py)
- [Testes de Integração](../tests/integration/test_s2_6_analytics_integration.py)
- [ROADMAP - Governança](../docs/ROADMAP.md#-governança-de-implementação)

---

**Status**: ✅ Pronto para Produção | **Sincronização**: 100% Tempo Real | **Governança**: COMPLIANT
