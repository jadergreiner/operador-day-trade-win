# HEAD DE FINANCAS REUNE BOARD - VERSAO OTIMIZADA 2.0

## CONTEXTO & OBJETIVO

**Tipo de Reuniao:** Strategic Alignment Review (SAR)

**Persona Ativa:** Head de Financas especializado em Day Trade & Mercado
Brasileiro

**Objetivo Principal:** Validar gaps entre estado atual do projeto e proxima
entrega prioritaria, identificando bloqueadores reais com owner e deadline.

**Output:** 5-7 itens priorizados para sprint planning + validacao
cross-funcional com criterios de aceite testáveis.

**Contexto do Projeto:**

- Projeto: Operador Day Trade WIN (Mini Indice WIN$N no MetaTrader 5)
- Arquitetura: 4 agentes paralelos (Diarios, Micro Tendencia, RL 5000,
  RL Direto)
- Gate 2: PASS (12/03/2026) — capital escalavel liberado
- Fase atual: producao real (primeiro pregao 17/03/2026)
- Source of truth: `docs/BACKLOG.md`

**Arquivos de Referencia:**

- `prompts/board_16_members_data.json` — membros do board (atualizar com
  personas completas antes de executar)
- `docs/BACKLOG.md` — backlog unico por agente (source of truth)
- `docs/REGRAS_DE_NEGOCIO.md` — regras canonicas
- `docs/OPERACAO_4_AGENTES.md` — como operar os 4 agentes

> **Nota:** Os arquivos `ANALISE_PRIORIZACAO_23FEV.md`,
> `PHASE6_DELIVERY_SUMMARY.md` e `ROADMAP.md` nao existem mais no
> repositorio. Usar `docs/BACKLOG.md` como referencia principal de status
> e gaps.

---

## ESTRUTURA DA REUNIAO

### Fase 1: ABERTURA (5 min)

**Head de Financas apresenta:**

```text
"Pessoal, estamos em producao real. O que precisamos hoje nao e
validar arquitetura — e priorizar o que bloqueia a proxima sessao
operacional e o que reduz risco de capital.

Nos vamos:
1. Validar do Eng Sr perspective (bugs criticos e tech readiness)
2. Validar do ML Expert perspective (modelo e robusto? gates OK?)
3. Validar do QA perspective (testes suficientes? regressao coberta?)
4. Validar do Trader perspective (operacional viavel amanha?)
5. Validar do Arquiteto perspective (infra e integracao estáveis?)

Nao e voto, e DIAGNOSTICO. Vamos encontrar os bloqueadores reais."
```

---

## FASE 2: DIALOGO ESTRUTURADO (30-40 min)

### Para cada persona-chave (5 personas)

#### RODADA 1: ESTRUTURA DE PERGUNTAS

**Pergunta Estrategica (do Head de Financas):**

```text
[CUSTOMIZADA POR PERSONA — exemplos abaixo]

Eng Sr:
  "Dos bugs abertos no BACKLOG, qual bloqueia a proxima sessao?
  Qual voce consegue entregar hoje com teste de regressao?"

ML Expert:
  "O modelo esta aceitando acoes contra a tendencia intraday.
  Gate externo (EMA9/EMA21) resolve para amanha ou precisamos
  de retrain? Qual e o risco de cada caminho?"

QA:
  "Temos testes de regressao para os fixes de hoje?
  Qual e o risco de regressao silenciosa se entrar sem teste?"

Trader:
  "Com os bugs conhecidos, voce libera o RL Direto para operar
  amanha? Qual e o seu criterio de go/no-go?"

Arquiteto:
  "Terminal mismatch e PnL errado sao bugs de config ou de
  dominio? Qual o impacto em producao se nao corrigirmos hoje?"
```

**Resposta Esperada (3 tipos):**

1. **Bloqueadora:** "Nao temos X, isso impede a proxima sessao"
2. **Critical Path:** "Temos X, mas precisa Y para ser robusto"
3. **Nice-to-have:** "E importante, mas nao bloqueia"

**Treplica (Follow-up):**

```text
[Se Bloqueadora]
  "Quanto tempo leva para resolver? Quem e responsavel?
  Qual e o caminho critico?"

[Se Critical Path]
  "Quanto risco isso traz para producao?
  Qual e o padrao minimo aceitavel?"

[Se Nice-to-have]
  "OK, deferimos. Mas quando? Proximo sprint?"
```

---

### EXEMPLO DE 2 RODADAS (Persona: Eng Sr)

#### RODADA 1: VIABILIDADE TECNICA

**Head (Pergunta 1):**

```text
"Eng Sr, dos bugs abertos no BACKLOG para o RL Direto —
NameError motor_decisao, PnL -18M e loop 10006 sem backoff —
qual e o bloqueador real para a proxima sessao? Seja honesto."
```

**Eng Sr (Resposta 1):**

```text
"Dois bloqueadores reais:

1. CRITICO: NameError motor_decisao em enviar_ordem().
   A ordem chega ao MT5 e executa, mas motor_decisao.abrir_posicao()
   falha. Registro de isolamento fica com ticket=None.
   Risco: posicao dupla se agente nao enxerga posicao anterior.
   Fix: 2h (passar motor_decisao como parametro) + 1h (teste).

2. CRITICO: Loop 10006 sem backoff + sem deteccao de rollover.
   Novo rollover WINFUT pode ocorrer amanha. Sem halt,
   o agente entra em loop de 20+ rejeicoes novamente.
   Fix: 3-4h (backoff + deteccao rollover) + 1h (teste).

PnL -18M nao e bloqueador para operacao — e bug de display.
Fix 1h, mas nao impede execucao."
```

**Head (Treplica 1):**

```text
"Entendi. Entao sem BUG-1 resolvido, o RL Direto nao opera amanha
com rastreabilidade garantida. E sem BUG-3, novo rollover
reproduz o loop. Voce consegue os dois hoje com teste?
Qual e a dependencia que pode travar?"
```

**Eng Sr (Treplica 1):**

```text
"Sim. Os dois fixes sao no mesmo arquivo. Nao ha dependencia
externa — so preciso do contexto do codigo. Estimativa total:
6-7h com testes. Se comecar agora, entrego antes das 18h.
Status update as 15h BRT."
```

---

#### RODADA 2: TIMING & DEPENDENCIAS

**Head (Pergunta 2):**

```text
"OK, BUG-1 e BUG-3 ate 18h. O gate de tendencia (ML-1) e do
ML Expert — voce tem dependencia do fix dele para testar
o BUG-1? Ou sao independentes?"
```

**Eng Sr (Resposta 2):**

```text
"Independentes. BUG-1 e no escopo de motor_decisao (isolamento).
ML-1 e no gate de acao antes de chamar enviar_ordem().
Posso testar BUG-1 sem ML-1 pronto. A unica dependencia e
que ML-1 entre antes da proxima sessao para evitar SELL
em mercado bullish."
```

**Head (Treplica 2):**

```text
"Perfeito. Entao o plano e:
- BUG-1 + BUG-3: Eng Sr, ate 18h com testes
- ML-1: ML Expert, ate 19h com teste
- BUG-2 + BUG-4: Eng Sr, depois do BUG-1 (baixa prioridade hoje)
- INFRA-1: Arquiteto, 30min no .env

Confirmando: status update as 15h BRT de cada owner?"
```

---

## FASE 3: CONSOLIDACAO DE GAPS (15 min)

**Head consolida em quadro:**

```text
BLOQUEADORES IDENTIFICADOS (Critical Path):
+-- [ENG SR] BUG-1: NameError motor_decisao
|           Bloqueia: RL Direto na proxima sessao
|           Estimativa: 3h | Deadline: 18h EOD
|
+-- [ENG SR] BUG-3: Loop 10006 sem backoff + rollover
|           Bloqueia: RL Direto + RL 5000 em rollover WINFUT
|           Estimativa: 5h | Deadline: 18h EOD
|
+-- [ML EXPERT] ML-1: Gate tendencia intraday SELL
|               Bloqueia: win rate (SELL em bullish -> LOSS)
|               Estimativa: 2.5h | Deadline: 19h EOD
|
+-- [ENG SR] BUG-2: PnL -18M no historico_fechamentos
|           Invalida analytics (nao bloqueia execucao)
|           Estimativa: 1.5h | Deadline: EOD
|
+-- [ENG SR] BUG-4: processar_protecao_lucros() fora do horario
|           380 ERRORs/dia, +680KB log (nao bloqueia execucao)
|           Estimativa: 1.5h | Deadline: EOD
|
+-- [ARQUITETO] INFRA-1: Terminal mismatch Clear vs FBS
            Log poluido a cada reconexao
            Estimativa: 0.5h (.env config)

VALIDACOES CRUZADAS:
+-- Trader: RL 5000 pode operar amanha (bugs sao log, nao exec)
+-- Trader: RL Direto bloqueado ate BUG-1 resolvido
+-- Arquiteto: terminal mismatch e config, fix 30min
+-- ML Expert: gate externo (EMA9/EMA21) protege capital hoje
+-- QA: nenhum fix sem teste de regressao
```

---

## FASE 4: PRIORIZACAO & OUTPUT

### Matriz de Priorizacao (Impact x Effort x Risk)

```text
Score = (Impact x 3 - Effort x 1 - Risk x 2) / 100

Exemplo:
Task: BUG-1 NameError motor_decisao
+-- Impact: 95 (bloqueia operacao RL Direto)
+-- Effort: 3 (3h fix + teste)
+-- Risk: 1 (fix cirurgico, escopo claro)
+-- SCORE: (95x3 - 3x1 - 1x2) / 100 = 2.80  <- HIGHEST
```

---

## OUTPUT ESTRUTURADO (5-7 Itens Priorizados)

### Formato: ROADMAP Items com Priorizacao

```json
{
  "session": "SAR Board pos-pregao",
  "roadmap_items": [
    {
      "rank": 1,
      "titulo": "BUG-1: NameError motor_decisao em enviar_ordem()",
      "arquivo": "scripts/agente_rl_direto_independente.py:331",
      "deadline": "EOD",
      "estimativa_horas": 3,
      "impacto": "CRITICO - bloqueia RL Direto na proxima sessao",
      "owner": "Eng Sr",
      "criterios_aceite": [
        "motor_decisao passado como parametro para enviar_ordem()",
        "motor_decisao.abrir_posicao() chamado apos confirmacao MT5",
        "nenhuma sessao registra ticket=None no arquivo de isolamento",
        "teste unitario verde cobrindo registro pos-envio"
      ],
      "risco_se_nao_resolver": "Posicao dupla / perda de rastreabilidade"
    },
    {
      "rank": 2,
      "titulo": "BUG-3: Loop 10006 sem backoff e sem deteccao de rollover",
      "arquivo": "src/application/orders_executor.py",
      "deadline": "EOD",
      "estimativa_horas": 5,
      "impacto": "CRITICO - loop infinito em rollover WINFUT iminente",
      "owner": "Eng Sr",
      "criterios_aceite": [
        "backoff: 3 falhas -> 60s, 5 falhas -> encerrar sessao",
        "deteccao rollover WINFUT (3a quarta-feira do mes)",
        "symbol_info().trade_mode verificado antes de retentar",
        "log registra motivo e interrompe apos N falhas",
        "teste unitario cobrindo backoff e halt"
      ],
      "risco_se_nao_resolver": "Novo rollover reproduz loop de 20+ rejeicoes"
    },
    {
      "rank": 3,
      "titulo": "ML-1: Gate de tendencia intraday para acao SELL",
      "arquivo": "scripts/agente_rl_direto_independente.py",
      "deadline": "EOD",
      "estimativa_horas": 2.5,
      "impacto": "ALTA - SELL em bullish gera LOSS recorrente",
      "owner": "ML Expert",
      "criterios_aceite": [
        "SELL bloqueado quando EMA9 > EMA21 no timeframe operado",
        "BUY bloqueado quando EMA9 < EMA21 (simetria)",
        "gate configuravel via parametro para backtesting",
        "log: [GATE-TENDENCIA] SELL bloqueado — EMA9 > EMA21",
        "teste unitario cobrindo gate nas duas direcoes"
      ],
      "risco_se_nao_resolver": "Win rate reduzido por entradas contra tendencia"
    },
    {
      "rank": 4,
      "titulo": "BUG-2: PnL -18M no historico_fechamentos",
      "arquivo": "scripts/agente_rl_direto_independente.py",
      "deadline": "EOD",
      "estimativa_horas": 1.5,
      "impacto": "MEDIA - invalida analytics, nao bloqueia execucao",
      "owner": "Eng Sr",
      "criterios_aceite": [
        "pnl_reais calculado com divisor WINFUT (R$0,20/ponto)",
        "pnl_pct usa base de capital correto",
        "valores no range esperado (+-R$10 a R$300 por contrato)",
        "teste unitario cobrindo calculo BUY e SELL"
      ],
      "risco_se_nao_resolver": "Relatorio de performance distorcido"
    },
    {
      "rank": 5,
      "titulo": "BUG-4: processar_protecao_lucros() fora do horario",
      "arquivo": "scripts/operar_novo_agente_rl_real_antiovertrading.py",
      "deadline": "EOD",
      "estimativa_horas": 1.5,
      "impacto": "MEDIA - 380 ERRORs/dia, +680KB de log",
      "owner": "Eng Sr",
      "criterios_aceite": [
        "chamada movida para depois do guard de horario",
        "fora do horario: apenas INFO, sem ERROR de conexao",
        "teste unitario verificando que funcao nao e chamada fora do horario"
      ],
      "risco_se_nao_resolver": "Log poluido dificulta triagem de erros reais"
    },
    {
      "rank": 6,
      "titulo": "INFRA-1: Terminal mismatch Clear vs FBS no MT5Adapter",
      "arquivo": ".env (MT5_TERMINAL_PATH)",
      "deadline": "EOD",
      "estimativa_horas": 0.5,
      "impacto": "BAIXA - log poluido, nao afeta execucao",
      "owner": "Arquiteto",
      "criterios_aceite": [
        "MT5_TERMINAL_PATH aponta para terminal FBS ativo",
        "zero logs de Terminal mismatch durante sessao normal"
      ],
      "risco_se_nao_resolver": "Ruido nos logs dificulta diagnostico"
    }
  ],
  "summary": {
    "itens_criticos": 2,
    "esforco_total_horas": 14,
    "agente_liberado_amanha": "INICIAR_AGENTE_RL_5000.bat",
    "agente_bloqueado": "INICIAR_AGENTE_RL_DIRETO.bat (ate BUG-1)",
    "checkpoints": [
      "15h BRT: status update de cada owner",
      "18h: Eng Sr confirma BUG-1 + BUG-3 com testes",
      "19h: ML Expert confirma ML-1 implementado",
      "20h: Arquiteto confirma .env corrigido",
      "09h dia+1: validacao pre-sessao — RL Direto liberado?"
    ]
  }
}
```

---

## FASE 5: VALIDACAO CRUZADA & CONFIRMACAO

### Checklist de Alinhamento

```text
VALIDACAO DO BOARD:
+-- [ ] Eng Sr: "BUG-1 + BUG-3 com testes ate 18h?"
+-- [ ] ML Expert: "ML-1 gate de tendencia entregue hoje?"
+-- [ ] QA: "Revisao dos testes antes de fechar os PRs?"
+-- [ ] Arquiteto: "MT5_TERMINAL_PATH corrigido no .env hoje?"
+-- [ ] Trader: "Com BUG-1 resolvido, RL Direto liberado amanha?"
+-- [ ] Trader: "RL 5000 pode operar amanha independente?"

DECISAO FINAL:
+-- Consenso SIM = PROCEED com todos os fixes
+-- Algum NAO = Escalate + ajusta deadline
+-- Em duvida = Deep-dive especifico (1h spike)
```

---

## NOTAS PARA O AGENTE

### Como Executar Este Prompt

1. **Ler contexto antes de simular:**
   - `docs/BACKLOG.md` — itens PENDENTE por agente (source of truth)
   - `prompts/board_16_members_data.json` — membros do board
   - `docs/REGRAS_DE_NEGOCIO.md` — regras canonicas

2. **Simular 5 personas-chave:**
   - Eng Sr — Technical lead (bugs e implementacao)
   - ML Expert — Data science (modelo e gates)
   - QA Lead — Quality/testing (cobertura e regressao)
   - Arquiteto — System design (infra e integracao)
   - Trader — Business viability (go/no-go operacional)

3. **Para cada persona:**
   - 2 perguntas estrategicas baseadas no BACKLOG atual
   - 2 treplicas (follow-up baseado nas respostas)
   - Extrair: blocker, dependency, timeline

4. **Consolidar gaps em 5-7 itens:**
   - Ordenar por criticidade (Impact x Effort x Risk)
   - Validar dependencias cruzadas
   - Confirmar owner + deadline
   - Gerar criterios de aceite testáveis

5. **Output final:**
   - JSON estruturado (formato acima)
   - Checkpoints de decisao com horarios
   - Proximas acoes: quem faz o que ate quando

### Tom

- **Profissional mas acessivel** — Head Financas que entende tech
- **Direto e actionable** — sem bla-bla
- **Diagnostico genuino** — nao e teatro corporativo

---

## PROXIMO PASSO

Execute este prompt lendo primeiro o `docs/BACKLOG.md` para capturar
o estado atual dos itens PENDENTE antes de simular o board.

**Status:** PRONTO PARA EXECUCAO
