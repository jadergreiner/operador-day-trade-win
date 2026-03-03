# 🚀 Operadores Core - Entrada Diária

**Operador Day Trade WIN - Entry Points Principais**

Este diretório contém os scripts de automação Windows (.bat) que iniciam e gerenciam os operadores automáticos de trading.

---

## 📌 OPERADORES CORE (Executar a cada dia)

### ✅ 1. INICIAR_DIARIOS.bat (Morning Startup)
**Execução:** Início do pregão (09:30 BRT)
- Inicializa sistemas de logging diário
- Carrega configurações de operação do dia
- Conecta aos feeds de mercado
- Ativa monitoramento de indicadores
- Aguarda sinais de entrada

**Comando:**
```batch
double-click INICIAR_DIARIOS.bat
```

---

### ✅ 2. INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat (Auto Trading Engine)
**Execução:** Após INICIAR_DIARIOS.bat estar operacional
- Ativa o engine automático de trading (Micro + Tendência)
- Executa análise contínua de setup
- Envia ordens automaticamente quando confirmados critérios
- Monitora posições abertas
- Gerencia riscos (Stop Loss / Take Profit)

**Comando:**
```batch
double-click INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
```

---

## 📋 Fluxo Diário Recomendado

```
09:30 (Abertura do pregão)
└─ Executar: INICIAR_DIARIOS.bat
   │
   ├─ Aguardar ✅ Sistema pronto (2-3 min)
   │
   └─ Executar: INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
      │
      ├─ ✅ Auto trading ativado
      ├─ ✅ Monitorando setups
      ├─ ✅ Enviando ordens automaticamente
      └─ ✅ Gerenciando posições

17:00 (Fechamento do pregão)
└─ Encerrar INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
   └─ Encerrar INICIAR_DIARIOS.bat
      └─ ✅ Prégo finalizado
```

---

## 🔧 Outros Scripts Disponíveis

Os outros scripts (.bat) neste diretório são **utilitários e ferramentas de suporte**:
- **MONITOR_*.bat** - Monitoramento de estado dos operadores
- **DIAGNOSTICO_*.bat** - Diagnóstico de problemas
- **TESTE_BASICO.bat** - Verifição de conectividade

Esses scripts auxiliam no gerenciamento diário mas **NÃO são obrigatórios** no fluxo normal de operação.

---

## ⚠️ Notas Importantes

1. **Ordem de Execução:** SEMPRE execute INICIAR_DIARIOS.bat ANTES de INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
2. **Aguarde Inicialização:** Aguarde 2-3 minutos entre os dois scripts
3. **Terminal Aberto:** Mantenha o terminal/cmd aberto durante todo o pregão
4. **Fechamento:** Feche os scripts NO FIM DO PREGÃO (17:00)
5. **Logs:** Monitore os logs de execução para detecção de erros

---

## 📊 Métricas Esperadas

- **Win Rate:** 60-68% (backtest validado)
- **Sharpe Ratio:** > 1.0
- **Drawdown Máximo:** < 15% (circuit breakers ativam)
- **Latência P95:** < 500ms

---

**Última Atualização:** 03/03/2026
**Status:** ✅ Production-Ready
