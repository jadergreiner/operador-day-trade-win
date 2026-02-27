# 📖 GUIA DO FACILITADOR - Transição p/ Diagnóstico Data Engineer

**Para:** Facilitador Reunião Virtual
**Contexto:** Terminou apresentação BLOCKER #2 (15:15) → Próxima: Diagnóstico (15:30)
**Duração preparação:** 2-3 minutos
**Estilo:** Conversacional, objetivo, transparente

---

## 🎬 SCRIPT DE TRANSIÇÃO (Ler/Adaptar)

### Abertura (15:15)

```
"Pessoal, vamos fazer uma pausa técnica rápida antes de continuar.

Como vimos, a questão de múltiplos bancos foi resolvida - trading.db é a
fonte de verdade, sem ambiguidades.

Agora preciso que o Data Engineer (#11) execute alguns diagnósticos rápidos
sobre se os 3 trades de 26/02 fazem parte dessa solução para a gente ter
100% de confiança.

Data Engineer, você está aí? Vamos começar?"
```

---

## 📋 INSTRUÇÕES PARA DATA ENGINEER

### Se respondeu SIM (está pronto):

```
"Ótimo! Então aqui está o que preciso:

Tenho 4 documentos prontos para você:

1. Um SCRIPT PYTHON que você executa (3-5 min)
   → scripts/DIAGNOSTICO_26FEV_TRADES.py

2. Um TEMPLATE para preencher as respostas
   → TEMPLATE_RESPOSTA_DATA_ENGINEER_S1-4.md

3. Uma CHEATSHEET de comandos SQL (backup)
   → SQL_QUICK_REFERENCE_DIAGNOSTICO.md

4. Um CHECKLIST de entrega
   → DATA_ENGINEER_ENTREGA_CHECKLIST.md

Objetivo: Responder 4 perguntas críticas:

  Q1: Os 3 trades de 26/02 estão em trading.db?
  Q2: Trade #1 (Order 2276170194) foi executado SEM SL/TP?
  Q3: Qual é o DELAY entre MT5 e persistência em BD?
  Q4: RLs foram gerados das 3 trades?

Você tem 25 minutos (até 15:30). Entrega esperada:
→ docs/DIAGNOSTICO_DELAY_PERSISTENCIA_26FEV.md

Consegue fazer? Perguntas antes de começar?"
```

### Se respondeu NÃO (não está ready):

```
"Sem problema. Então vamos fazer diferente.

Vou compartilhar os materiais via chat/email:
[SHARE LINKS]

[Timeout] Se em 15 minutos você não conseguir acessar,
avisa que vamos chamar arquivo Eng Sr para ajudar ou
adiamos o diagnóstico para 15:45.

Você tem 15 minutos de 'working time' enquanto continuamos."
```

---

## ⏰ ENQUANTO DATA ENGINEER TRABALHA (15:15-15:30)

### Para o Facilitador:

**Opção A: Continuar com temas do Board**
```
"Enquanto Data Engineer está trabalhando, pergunta importante:

Há MAIS algum blocker crítico que precisa ser endereçado
antes que S1-4-LOGGING seja aprovado?

Quem mais tem problemas ou riscos?

[Chame próximo blocker - Arquiteto #6 sobre Performance Cache?]"
```

**Opção B: Preparar board para decisão**
```
"Enquanto aguardamos, deixa eu recapitular os cenários
que vamos avaliar em 15 minutos quando Data Engineer retorna:

[Mostrar SLIDE 5-7 de SLIDE_APRESENTACAO_BOARD_15_30.md]

Se tudo OK → Verde: S1-4-LOGGING HOJE
Se problema → Vermelho: Escalação imediata
Se incerteza → Amarelo: Investigação +30min

Vocês entendem a separação?"
```

---

## 🔴 EM CASO DE DATA ENGINEER ATRASAR

### Se 15:25 e ainda não terminou:

```
"Data Engineer, tudo bem? Você está em qual etapa?

Se for questão de tempo, pode enviar resposta parcial -
a gente vê o que você tem até agora e continua depois.

Ou você quer que adiemos para 15:45 com mais 15 minutos?"
```

### Se 15:30 e não terminou:

```
"Pessoal, vamos dar +15 minutos. Data Engineer está quase lá.

Enquanto isso, vou passar para o próximo blocker [OUTRO TEMA]
e quando Data Engineer terminar, ele grita no chat que
temos as respostas prontas."
```

---

## ✅ QUANDO DATA ENGINEER RETORNA (15:30-15:45)

### Recepção (2 minutos)

```
"Data Engineer, bem-vindo de volta!

Você conseguiu o diagnóstico?

[Esperar resposta]

Se SIM → Ótimo, apresenta para gente em 30 segundos
Se NÃO → Sem problema, explica o que encontrou mesmo que parcial
Se PROBLEMA → Avisa que foi e vamos ver próximos passos
```

### Apresentação Data Engineer (4 minutos)

```
"Pessoal, Data Engineer vai apresentar achados de 4 questões:

Q1: Trades estão em trading.db? [Deixe responder]
Q2: Trade #1 sem SL/TP? [Deixe responder]
Q3: Delay entre MT5 e BD? [Deixe responder]
Q4: RLs foram gerados? [Deixe responder]

[Fazer 1-2 perguntas de esclarecimento se necessário]

Sua conclusão para S1-4-LOGGING: SIM/NÃO/DEIXAR_PENDENTE?
"
```

---

## 🚦 DECISÃO COLEGIAL (15:45-16:00)

### Se Data Engineer disse SIM (Tudo OK):

```
"OK pessoal, vamos para a decisão.

Data Engineer confirmou:
✅ Os dados estão corretos em trading.db
✅ Logging pode prosseguir com confiança

Executor Técnico (#10), você está ready?

Se SIM → Vamos aprovar S1-4-LOGGING para implementação HOJE
   Você inicia Fase 2 (design) já para atingir 18:30 como meta

Alguma objeção? [Pausa 10 segundos]

APROVADO: S1-4-LOGGING Opção A implementação HOJE ✅
"
```

### Se Data Engineer disse NÃO (Problemas):

```
"Pessoal, Data Engineer encontrou problema(s).

A recomendação é NÃO implementar S1-4-LOGGING hoje.

CTO (#2), você ouviu. Qual é o plano B?

[CTO responde]

Presidente, como você quer proceder?

[ OPÇÃO: Formar task force | OPÇÃO: Adiamento | OPÇÃO: Escalação ]
"
```

### Se Data Engineer disse DEIXAR_PENDENTE (Incerteza):

```
"Temos uma incerteza. Data Engineer recomenda mais investigação.

Então aqui está minha sugestão:

Opção 1: Data Engineer + Executor Técnico (30 min deep dive) → reporta de novo
Opção 2: Adiamos S1-4-LOGGING e continuamos com outros temas

O que acham melhor? Presidente?

[Deixar líder decidir]

Se deep dive → Reconnect em 16:15
Se adiamento → Marcar para 28/02
"
```

---

## 📊 APÓS A DECISÃO: Próximos Passos

### Se APROVADO (SIM):

```
"Excelente! Então:

🎬 Executor Técnico: Inicia S1-4-LOGGING Fase 2 AGORA
   └─ Target: 18:30 hoje com logging em produção

📞 Comunicação: Toda hora tem sync update neste chat

⏰ Próxima reunião: 28/02 09:00 (status S1-4 + novos blockers)

Executor, você pronto? Alguma coisa que precisa antes de começar?
"
```

### Se REJEITADO (NÃO):

```
"OK, vamos tratar isso como BLOCKER #3 (escalado).

CTO: Você é DRI dessa investigação
Data Engineer: Você é de apoio técnico
Presidente: Você aprova timeline nova

Quero que amanhã (28/02) pela manhã eu tenha:
- Relatório de causa raiz
- Plano de remediar
- Nova timeline para S1-4

Pessoal conseguem? Ou vocês precisam de mais suporte?"
```

### Se INCERTEZA (DEIXAR_PENDENTE):

```
"Então vamos para deep dive de 30 minutos.

Data Engineer + Executor + (opcionalmente Arquiteto):
Saem daqui e mergulham nos logs.

Resto do board: Continuamos com próximos temas.

[TEMAS PENDENTES:]
- Blocker #3: [próximo]
- Blocker #4: [próximo]
- etc.

Em 16:15 vocês 3 voltam com resposta final.
Deal?"
```

---

## 💬 FRASES DE TRANSIÇÃO (Use Conforme Necessário)

### Para manter board envolvido:

```
"Alguém tem perguntas antes de Data Engineer começar?"

"Enquanto aguardamos, alguém quer falar de outro blocker?"

"Ninguém tem dúvidas sobre os 4 cenários? [Mostrar slides]"

"Executor Técnico, você está preparado caso aprovado?"

"CTO, você acompanha? Alguma outra coisa importante?"
```

### Para pressionar Data Engineer amigavelmente:

```
"Data Engineer, sem pressa, mas em quanto você acha que termina?"

"Encontrou algo interessante ou ainda tem perguntas?"

"Você quer que alguém te ajude/acelera?"
```

### Para manter clima profissional:

```
"Pessoal, isso que estamos fazendo aqui é auditar integridade
de dados em produção. É chato mas CRÍTICO para confiança no sistema."

"Data Engineer está fazendo o trabalho certo - validando tudo antes
de implementar. Isso é profissionalismo."
```

---

## 🎯 MÉTRICAS DE SUCESSO

### Facilitador terá sucesso se:

✅ Data Engineer conseguiu executar diagnóstico
✅ Board entendeu 4 questões + 3 cenários possíveis
✅ Decisão foi colegial (não imposta)
✅ Próximos passos claros (SIM/NÃO/PENDENTE)
✅ Ninguém saiu confuso sobre S1-4
✅ Timeline Sprint 1 permaneça viável

### RED FLAGS (Se houver):

🚩 Data Engineer não conseguiu acessar materiais
🚩 Ninguém entendeu diferença entre 3 cenários
🚩 Executor Técnico não está comprometido com S1-4
🚩 CTO não validou dados antes de decisão
🚩 Desentendimento sobre qual banco usa aonde

**Se RED FLAG → Pausar e escalar Presidente**

---

## 📞 SUPORTE EM TEMPO REAL

Se Facilitador ficar preso:

| Questão | Quem Chamar |
|---------|-------------|
| "Qual é meu papel exato?" | CTO #2 |
| "Por que tudo isso importa?" | Presidente #1 |
| "Data Engineer, você consegue?" | Executor Técnico #10 |
| "Precisamos escalar?" | Presidente #1 |
| "Qual decisão tomamos?" | Grupo vote |

---

## ⏱️ TIMELINE DE EXECUÇÃO (USE COMO TIMER)

```
15:15 ├─ [Você] Faz transição/introduces diagnóstico (2 min)
      ├─ [Você] Briefa Data Engineer e board (1 min)
      │
15:18 ├─ [Data Engineer] Começa trabalho
      ├─ [Você] Continua com temas alternativos OU recap
      │
15:28 ├─ [Você] "2 mins, data engineering?"
      ├─ [Data Engineer] "Sim, aqui tá!" ou "5 min mais"
      │
15:30 ├─ [Data Engineer] Retorna com respostas
      ├─ [Você] Apresentação rápida (2 min)
      │
15:32 ├─ [Você] Pequeno Q&A (3 min)
      │
15:35 ├─ [Board + CTO] Votação/Decisão colegial (5 min)
      │
15:40 ├─ [Você] Comunicar resultado final
      ├─ [Executor] Confirmação próximos passos
      │
15:45 ├─ [Você] Transição para próximo blocker OU deep dive
      │
16:00 ├─ EOD sync ou continuar outros temas
```

---

**Guia Preparado:** 27/02/2026 15:20 BRT
**Para:** Facilitador Reunião Virtual
**Deadline:** Usar em 15:15-15:45 BRT
**Apoio:** Todos documentos prontos para impressão/compartilhamento
