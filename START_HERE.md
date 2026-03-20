# 🚀 Operador Day Trade WIN - Comece Aqui!

**Bem-vindo ao sistema de trading automatizado!**

---

## ⚡ Quick Start (5 minutos)

### Passo 1: Abra o Terminal/CMD
```
Windows Key + R
cmd
Enter
```

### Passo 2: Vá para a pasta BAT
```
cd BAT
```

### Passo 3: Execute os dois operadores (pela manhã)

**Primeiro operador:**
```
INICIAR_DIARIOS.bat
```
Aguarde 2-3 minutos até ver ✅ "Sistema Pronto"
O bootstrap do terminal agora também mostra o `daily_confidence_gate` antes do Python iniciar.

**Segundo operador (em outra janela de CMD):**
```
INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
```
Aguarde ✅ "Auto Trading Ativado"

---

## ✅ Você Está Pronto!

O sistema agora:
- ✅ Monitora continuamente o mercado
- ✅ Analisa setups de entrada automaticamente
- ✅ Envia ordens quando critérios confirmados
- ✅ Gerencia posições (Stop Loss / Take Profit)
- ✅ Registra todas as operações em logs

---

## 📋 Operadores Core

| Arquivo | Função | Quando | Status |
|---------|--------|--------|--------|
| **INICIAR_DIARIOS.bat** | Startup diário | 09:30 BRT | **CRÍTICO** ⭐ |
| **INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat** | Engine automático | Após sistema pronto | **CRÍTICO** ⭐ |

Estes dois arquivos são o **CORE** do produto. Todo o sistema é construído para que você execute esses dois no começo do dia e feche no fim do pregão.

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

## 🎯 ENTREGA DE VALOR & BACKLOG

Pronto para ativar o sistema em produção?

**Documentação Essential (Backlog Refatorado - v5.0):**
1. **`docs/BACKLOG_UNIFICADO.md`** ← SINGLE SOURCE OF TRUTH (sem datas, avaliação dual PO+CFO)
2. **`docs/QUICK_START.md`** ← Quick start rápido (3 minutos)
3. **`docs/ENTREGA_DE_VALOR.md`** ← Financeiro + ROI
4. **`docs/GO_LIVE_CHECKLIST.md`** ← Dia da execução

**Documentação Completa:**
- **`docs/PACOTE_ENTREGA_VALOR.md`** - Tudo em detalhes
- **`docs/APRESENTACAO_BOARD_GOLIVE.md`** - Para reuniões
- **`docs/INDEX_FINAL_ENTREGA.md`** - Mapa de navegação
- **`outputs/ENTREGA_RESUMO.txt`** ← 1 minuto de resumo

---

## 📞 Referência Rápida

**Sistema não inicia?**
- Execute `BAT/DIAGNOSTICO_INSTALACAO.bat` para verificar dependências

**Erro de conexão?**
- Verifique internet: `ping google.com`
- Verifique conta MT5 em `config/.env`

**Dúvidas?**
- Revise `BAT/README.md` para fluxo completo
- Monitore logs da execução na linha de comando

---

**Status:** ✅ Production-Ready
**Última Atualização:** 03/03/2026
**Contato:** Documentação em `docs/`
