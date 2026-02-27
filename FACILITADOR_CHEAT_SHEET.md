# ⚡ CHEAT SHEET FACILITADOR - S1-4-LOGGING Diagnóstico

**Imprimir ou guardar aberto durante 15:15-15:45**

---

## 🎯 RESUMO EM 30 SEGUNDOS

```
BLOCKER #2 ✅ RESOLVIDO
→ trading.db é a fonte de verdade (45 scripts validados)
→ Data Engineer vai validar 3 trades de 26/02 em 15 min

PRÓXIMAS 30 MIN:
→ 15:15-15:30: Data Engineer execute diagnóstico
→ 15:30-15:45: Apresentação + decisão

DECISÃO: SIM/NÃO/DEIXAR_PENDENTE para S1-4-LOGGING
```

---

## 📞 CONTATOS CRÍTICOS

| Pessoa | ID | Função | Escalação |
|--------|----|---------|----|
| **Presidente** | #1 | Decisão final | CTO+Presidente |
| **CTO** | #2 | Validação técnica | Se problema |
| **Executor** | #10 | S1-4 implementação | Se aprovado |
| **Data Eng** | #11 | Diagnóstico NOW | Chamar em 15:15 |

---

## 🔧 MATERIAIS PARA DATA ENGINEER (Compartilhar 15:15)

```
1. scripts/DIAGNOSTICO_26FEV_TRADES.py
2. TEMPLATE_RESPOSTA_DATA_ENGINEER_S1-4.md
3. SQL_QUICK_REFERENCE_DIAGNOSTICO.md
4. DATA_ENGINEER_ENTREGA_CHECKLIST.md
```

**Deadline:** 15:30 BRT
**Entrega:** docs/DIAGNOSTICO_DELAY_PERSISTENCIA_26FEV.md

---

## 4 PERGUNTAS CRÍTICAS

| # | Pergunta | Respostas Possíveis | Crítica |
|---|----------|-------------------|---------|
| Q1 | 3 trades em trading.db? | SIM / NÃO / PARCIAL | 🔴 CRÍTICA |
| Q2 | Trade #1 sem SL/TP? | SIM / NÃO / DESCONHEÇO | 🔴 CRÍTICA |
| Q3 | Delay MT5→BD? | XXXms / XXXs / DESCONHECIDO | 🟡 ALTA |
| Q4 | RLs gerados? | SIM / NÃO / PARCIAL | 🟡 ALTA |

---

## 🚦 DECISÃO (3 CAMINHOS)

### ✅ CENÁRIO 1: Tudo OK
```
Data Eng: "Tudo confirmado, dados OK"
→ Sua ação: APROVADO SIM
→ Executor: Inicia S1-4 Fase 2 AGORA (target 18:30)
```

### ❌ CENÁRIO 2: Nada OK
```
Data Eng: "Dados não encontrados ou problema crítico"
→ Sua ação: REJEITADO NÃO
→ CTO: Escalação + Investigation (28/02 report)
```

### ⏳ CENÁRIO 3: Incerteza
```
Data Eng: "Parcial ou desconheço certos dados"
→ Sua ação: DEIXAR_PENDENTE MAIS_30min
→ Deep dive: Data Eng + Executor + (CTO se needed)
```

---

## ⏱️ TIMELINE RÁPIDA

```
15:15  Data Engineer começa diagnóstico (você gerencia reunião)
15:20  [Você] Mostra slides se ainda tem time (SLIDE_APRESENTACAO_*)
15:25  [Você] "2 minutos, Data Engineer?"
15:30  Data Engineer retorna com respostas
15:32  [Você] Apresenta na frente do board (2 min)
15:35  [Board] Votação rápida (SIM/NÃO/PENDENTE)
15:40  [Você] Comunicar resultado + próximos passos
```

---

## 💬 FRASES CHAVE (COPY-PASTE)

### Para iniciar:

```
"Data Engineer, temos 4 perguntas críticas sobre
os 3 trades de 26/02. Documents prontos para você -
pode começar agora?"
```

### Para Status Check:

```
"Data Engineer, está tudo bem? Quanto tempo ainda?"
```

### Para apresentar decisões:

```
"Pessoal, vamos aos cenários possíveis...
[SIM/NÃO/PENDENTE]"
```

### Para encerrar:

```
"Então aprovamos [DECISÃO].
Executor, você é o DRI. Próximos passos?"
```

---

## ✅ CHECKLIST PRÉ-REUNIÃO

- [ ] Documentos compartilhados com Data Engineer
- [ ] Presidente e CTO estão conectados e atentos
- [ ] Executor Técnico ready (se SIM)
- [ ] Você tem slides SLIDE_APRESENTACAO_BOARD_15_30.md
- [ ] Você leu este cheat sheet
- [ ] Timer está setado para 15:30 (parada técnica)

---

## 🆘 PROBLEMAS COMUNS & SOLUÇÕES

| Problema | Solução |
|----------|---------|
| Data Engineer não consegue acessar scripts | Compartilhar via Slack/Email + redirecionar |
| Diagnóstico > 25 min | Extend até 15:45, continua outra reunião |
| Ninguém entende cenários | Repete com exemplos simples (SIM=verde, NÃO=vermelho) |
| Executor diz "não tá pronto" | Escalate CTO → CTO decide se força ou adia |
| Presidente ausente | Pausa reunião até voltar (decisão não pode ser feita sem) |

---

## 🎯 SUCESSO =

- [x] Data Engineer conseguiu fazer diagnóstico
- [x] Board entendeu 4 perguntas
- [x] Decisão clara: SIM/NÃO/PENDENTE
- [x] Próximos passos comunicados
- [x] S1-4-LOGGING ou escalação aprovada

---

**Imprimir ou manter aberto em 2º tela durante reunião**
**Última atualização:** 27/02/2026 15:20 BRT
