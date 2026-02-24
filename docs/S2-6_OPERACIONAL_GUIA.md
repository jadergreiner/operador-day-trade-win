<!-- pyml disable md013 -->
<!-- pyml disable md040 -->

# S2-6 GUIA OPERACIONAL — Analytics de Intervenção Manual

**Versão:** v1.0
**Data:** 2026-02-24
**Público:** Traders, Operadores MT5
**Objetivo:** Manual de uso do sistema de feedback de intervenção manual

---

## 📋 O que é?

Sistema que coleta feedback quando você (trader) encerra uma posição manualmente.
O sistema aprende seus critérios subjetivos para melhorar a IA ao longo do tempo.

---

## 🎯 Quando aparece o menu?

O menu aparece **automaticamente** quando:

1. ✅ Uma operação é executada pela IA
2. ✅ A posição fica aberta (esperando resultado)
3. ✅ Você **encerra manualmente** (não fechamento automático)

---

## 📺 Menu de Feedback (Aspecto)

```
╔════════════════════════════════════════════════╗
║  FEEDBACK DE INTERVENÇÃO MANUAL                ║
║  Posição Encerrada: WINFUT-2026-02-24 13:45:30║
║  Score IA: 0.85 | Volatilidade: 1.20          ║
║  Win Rate Sessão: 62.0% | P&L Sessão: R$ 456 ║
╚════════════════════════════════════════════════╝

Selecione o motivo da intervenção (1-8):

  1. Falha Técnica (MT5 lag, reconexão, erro)
  2. Risco Externo (notícia importante, evento)
  3. Lucro Satisfatório (meta atingida, cansaço)
  4. Stop Hit + Reentrada (quer tentar novamente)
  5. Volatilidade Extrema (mercado nervoso, parou)
  6. Falta de Confiança IA (não confiou no score)
  7. Pausa Operacional (vai sair, parou o robô)
  8. Outro / Livre (motivo customizado)

Código? > _
```

---

## 🔢 Como responder?

### Passo 1: Leia as 8 opções

Identifique qual melhor descreve o motivo de você ter encerrado.

### Passo 2: Digite o número

Digite **1 a 8** (apenas um dígito) e pressione **ENTER**

```
Código? > 3
```

### Passo 3: Se escolheu "8" (Outro)

Se escolheu "Outro", digite uma descrição breve (máximo 200 caracteres):

```
Código? > 8
Descreva brevemente (máx 200 caracteres):
> Saiu noticia de corte de taxa, mercado entrou em pânico
```

### Passo 4: Confirmação

Sistema exibirá:

```
✅ Feedback registrado: Lucro Satisfatório
✅ Feedback registrado: Outro / Livre
```

---

## 📊 O que acontece depois?

| O que faz | Prazo | Benefício |
|:---:|:---:|:---|
| **Coleta o feedback** | Imediato | Sem overhead (< 100ms) |
| **Persiste em BD local** | < 1s | Histórico acessível |
| **Enriquece dataset** | Diário | Retrainamento mais próximo da realidade |
| **Melhora próxima IA** | Sprint seguinte | +1-2% win rate esperado |

---

## 🎯 8 Categorias Explicadas

### 1️⃣ Falha Técnica

**Quando usar:**
- MT5 desconectou na hora exata
- Ordem não foi enviada
- Interface travou
- Reconexão automática demorou muito
- Erro de comunicação com corretora

**Impacto IA:**
"Este trade foi bom, mas a execução falhou."
→ IA não desconta o erro dele

---

### 2️⃣ Risco Externo

**Quando usar:**
- Notícia importante saiu durante a operação
- Evento econômico de alto impacto
- Mudança repentina de legislação
- Falha de sistema da corretora
- Gatilho externo impossível de prever

**Impacto IA:**
"O sinal era bom, mas o mundo mudou."
→ IA aprendeque existe risco exógeno

---

### 3️⃣ Lucro Satisfatório

**Quando usar:**
- Atingiu a meta diária de lucro
- Cansou de operar (mentalmente)
- Qualidade do sinal piorou muito
- Quer sair com lucro seguro
- Fim do expediente/turno

**Impacto IA:**
"O trade seria válido, mas encerrei por preservação."
→ IA refina dimensionamento de tickets

---

### 4️⃣ Stop Hit + Reentrada

**Quando usar:**
- Tomou stop loss
- Vê que o mercado **entra em tendência FORTE** após o stop
- Quer reentrar com score menor ou tamanho reduzido

**Impacto IA:**
"Mesmo com stop, havia reentrada possível."
→ IA melhora detecção pós-stop

---

### 5️⃣ Volatilidade Extrema

**Quando usar:**
- Candela abriu +/- 3%+ em 1 minuto
- Slippage impossível de controlar
- Spread explodir drasticamente
- Gap repentino
- Liquidez desapareceu (fase de close)

**Impacto IA:**
"Sinal correto, mas execução impossível."
→ IA aprende a pausar em cenários similares

---

### 6️⃣ Falta de Confiança IA

**Quando usar:**
- Score estava 0.65 (muito baixo)
- Confluência fraca (só 1 detector bateu)
- "Sentia algo errado" (intuição)
- Histórico recente de perdas nesta faixa de score

**Impacto IA:**
"O trader não confiou. Havia razão sub-consciente?"
→ IA investiga recalibragem de threshold

---

### 7️⃣ Pausa Operacional

**Quando usar:**
- Vai sair de casa (range restrito)
- Esperando ligação importante
- Mudança de turno
- Manutenção do PC
- Simples pausa

**Impacto IA:**
"Decisão operacional, não resultado de trade."
→ IA desconta essa intervenção

---

### 8️⃣ Outro / Livre

**Quando usar:**
- Nenhuma categoria se aplica
- Motivo muito específico
- Experimentação pessoal

**Exemplo:**

```
"Identifiquei pattern visual V-shaped recovery,
 entra contra-tendência, quer testar"
```

**Impacto IA:**
"Dados qualitativos raros - revisão manual por vez em quando."

---

## ⚡ Dicas Rápidas

### ✅ FAÇA:
- Responda com sinceridade
- Escolha a categoria que MELHOR DESCREVE
- Se tem dúvida entre 2, escolha a mais específica
- Descreva em português claro (código 8)

### ❌ NÃO FAÇA:
- Responda com pressa (menu espera ~30s)
- Escolha múltiplas causas (escolha a principal)
- Abra o histórico durante pausa (IA está ocupada)
- Modifique BD de feedback manualmente

---

## 📈 Feedback > Melhoria

```
3 Meses de Dados Coletados
         ↓
Análise de Padrões
("Código 6 correlaciona com score 0.50-0.60")
         ↓
Retrainamento do Modelo ML
(Ajusta threshold decorreto)
         ↓
+1-2% de Win Rate
(15-20 trades extras lucrativos por mês)
         ↓
+R$ 2k-5k ROI mensal
```

---

## 🔍 FAQ

### P: Posso skip o menu?
**R:** Não. Menu obrigatório quando encerro manualmente.
Propósito: aprimorar IA continuamente.

### P: Meu feedback é anônimo?
**R:** Em desenvolvimento. Futuro: vincular a trader ID para
análise de "estilo pessoal de risco."

### P: Posso editar depois?
**R:** Não (v1.0). Feedback é imutável. Tenha cuidado.

### P: E se escolher código errado?
**R:** Sem undo na v1.0. Na v1.1: modal de confirmação.
Dica: releia antes de pressar ENTER.

### P: Quanto tempo leva?
**R:** 5-10 segundos (5x mais rápido que anotar à mão).

### P: Dados vão pra cloud?
**R:** Não. Armazenamento local: `data/feedback/analytics_intervencao_manual.db`
Seguro, privado, sob seu controle.

---

## 🚨 Troubleshooting

### Menu não aparece?
- Verificar se posição foi encerrada manualmente (não automático)
- Reconectar e tentar novamente

### Menu trava?
- Pressionar Ctrl+C e reiniciar agente
- Verificar disco cheio (BD cresce ~100KB/1000 feedback)

### Feedback não aparece?
- Checar permissões de arquivo em `data/feedback/`
- Rodarcript: `python -c "import checks; checks.verify_feedback_db()"`

---

## 📚 Próximos Passos (v1.1)

- [ ] Dashboard em HTML de feedback agregado
- [ ] Edição de feedback (últimas 2 horas)
- [ ] Integração com análise técnica (vinculação com padrões)
- [ ] Chatbot Q&A ("Por que o código 6 aumentou?")
- [ ] Export mensal para relatório de compliance

---

## ✅ Checklist Inicial

- [ ] Li todas as 8 categorias
- [ ] Entendi o impacto na IA
- [ ] Testei o menu (encerrar 1 posição manualmente)
- [ ] Confirmei que feedback foi persistido
- [ ] Consultei FAQ acima se dúvida

---

**Status:** 🟢 v1.0 OPERACIONAL
**Próxima Versão:** v1.1 (Dashboard + edição)
**Support:** #s2-6-feedback-squad no Slack
