# 🚀 Operador Day Trade WIN - Comece Aqui

**Bem-vindo ao sistema de trading automatizado!**

---

## ⚡ Quick Start (5 minutos)

### Passo 1: Abra o Terminal/CMD

```text
Windows Key + R
cmd
Enter
```

### Passo 2: Vá para a raiz do projeto

```bash
cd /d c:\Users\Usuario\Documents\03_Trade\operador-day-trade-win
```

### Passo 3: Execute os launchers na ordem recomendada

**Core obrigatório:**

1. `INICIAR_DIARIOS.bat`
   Aguarde 2-3 minutos até ver o bootstrap completo e o
   `daily_confidence_gate`.
2. `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`
   Aguarde a confirmação do auto trade e dos filtros ML.

**Complementares com valor real:**
3. `INICIAR_MONITOR_QUANTICO.bat`
   Abre o painel web em `http://localhost:8765/` com contexto global do dia.
4. `INICIAR_AGENTE_RL_5000.bat`
   Execução RL em produção estrita quando o mercado estiver pronto.
5. `INICIAR_AGENTE_RL_DIRETO.bat`
   Alternativa paralela e isolada para validação ou contingência.

---

## ✅ Você Está Pronto

O sistema agora:

- ✅ Monitora continuamente o mercado
- ✅ Analisa setups de entrada automaticamente
- ✅ Envia ordens quando critérios confirmados
- ✅ Gerencia posições (Stop Loss / Take Profit)
- ✅ Registra todas as operações em logs

---

## 📋 Launchers Prioritários

| Arquivo | Valor entregue | Quando usar | Papel |
| ------- | -------------- | ----------- | ----- |
| **INICIAR_DIARIOS.bat** | Journaling, contexto e retraining diário | Antes do pregão | **CORE** ⭐ |
| **INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat** | Geração de sinais com filtros ML | Após Diários | **CORE** ⭐ |
| **INICIAR_MONITOR_QUANTICO.bat** | Dashboard web e tendência do dia | Paralelo à operação | Observabilidade |
| **INICIAR_AGENTE_RL_5000.bat** | Execução RL em produção estrita | Quando houver janela operacional | Execução |
| **INICIAR_AGENTE_RL_DIRETO.bat** | Operação paralela isolada | Validação/contingência | Execução paralela |

`INICIAR_DIARIOS.bat` e `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`
continuam sendo o núcleo mínimo. Os outros 3 launchers ampliam execução,
observabilidade e contingência.

---

## 🔍 Acompanhe a Operação

Enquanto os operadores estão rodando, você pode:

1. **Pela linha de comando:** Ver os logs em tempo real (mesma janela dos scripts)
2. **Pelo Dashboard:** Abra o monitor visual (se configurado)
3. **Verificar Posições:** Execute `VERIFICAR_POSICOES.bat` em outra janela

---

## ⚠️ Fechando no Fim do Pregão

Quando o pregão fecha (17:00 BRT):

1. Feche o terminal de **INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat** (Ctrl+C ou X)
2. Feche o terminal de **INICIAR_DIARIOS.bat** (Ctrl+C ou X)
3. Sistema encerrado - registre lucros/perdas do dia

---

## 🎯 ENTREGA DE VALOR & INIT OPERACIONAL

Pronto para ativar o sistema em produção?

**Documentação canônica para onboarding rápido:**

1. **`docs/sessoes/INIT_DO_PROJETO.md`** ← init detalhado dos launchers
2. **`docs/OPERACAO_4_AGENTES.md`** ← operação dos 5 launchers
3. **`docs/ARQUITETURA_ALVO.md`** ← contrato arquitetural e isolamento
4. **`docs/REGRAS_DE_NEGOCIO.md`** ← regras operacionais e limites
5. **`docs/STATUS_ENTREGAS.md`** ← status atual e entregas

**Referências complementares:**

- **`docs/AGENTES_RL_PARALELOS.md`** - isolamento entre RL 5000 e RL Direto
- **`docs/MODELAGEM_DE_DADOS.md`** - bancos SQLite e artefatos
- **`scripts/README.md`** - padrões dos scripts operacionais

---

## 📞 Referência Rápida

**Sistema não inicia?**

- Execute `python scripts/diagnostico_modelo_rl.py` para validar ambiente

**Erro de conexão?**

- Verifique internet: `ping google.com`
- Verifique conta MT5 em `config/.env`

**Dúvidas?**

- Revise `docs/OPERACAO_4_AGENTES.md` para fluxo completo
- Use `INICIAR_MONITOR_QUANTICO.bat` para acompanhar o contexto visual

---

**Status:** ✅ Production-Ready
**Última Atualização:** 02/04/2026
**Contato:** Documentação em `docs/`
