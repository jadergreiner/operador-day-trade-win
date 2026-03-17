# Prompt de Fechamento Diário — Operador Quântico

## Visão Geral

Este prompt é executado **até três vezes ao dia** pelo script
`prompts/fechamento_diario.py` com o parâmetro `--foco`:

| Foco | Horário | Objetivo |
| --- | --- | --- |
| `abertura` | ~08:00 | Planejar o pregão com base no contexto |
| `meio_dia` | ~12:00 | Ajuste de rota e captura de eventos |
| `fechamento` | ~17:00 | Consolidação, backlog e aprendizados |

**Uso:**

```bash
python prompts/fechamento_diario.py --foco abertura
python prompts/fechamento_diario.py --foco meio_dia
python prompts/fechamento_diario.py --foco fechamento
python prompts/fechamento_diario.py --foco fechamento --data 2026-02-20
```

---

## Seção 1 — CAPTURA DO DIA

Registre os dados operacionais do período analisado.

### 1.1 Identificação da Sessão

```yaml
timestamp: "<YYYY-MM-DDTHH:MM:SSZ>"
foco: "<abertura | meio_dia | fechamento>"
data_pregao: "<YYYY-MM-DD>"
operador: "Agente Autônomo — Operador Quântico"
```

### 1.2 Volume Operacional

```yaml
analises_rodadas: <número inteiro>
trades_executados: <número inteiro>
trades_encerrados: <número inteiro>
posicoes_abertas_no_momento: <número inteiro>
```

### 1.3 Desempenho Financeiro

```yaml
resultado_dia_pts: <pontos — positivo ou negativo>
resultado_dia_pct: "<+X.X% | -X.X%>"
maior_ganho_pts: <pontos>
maior_perda_pts: <pontos>
win_rate_dia_pct: <0–100>
relacao_risco_retorno: "<ex: 1:2.5>"
```

### 1.4 Contexto de Mercado

```yaml
simbolo: "WINFUT"
preco_abertura: <pontos>
preco_atual_ou_fechamento: <pontos>
maxima_dia: <pontos>
minima_dia: <pontos>
variacao_dia_pct: "<+X.X% | -X.X%>"
volume_relativo_pct: "<+X% acima | -X% abaixo da média 3 dias>"
```

### 1.5 Eventos de Mercado Relevantes

```yaml
eventos_macro:
  - descricao: "<evento>"
    impacto: "<alto | medio | baixo>"
    hora: "<HH:MM>"
eventos_locais:
  - descricao: "<evento>"
    impacto: "<alto | medio | baixo>"
    hora: "<HH:MM>"
```

---

## Seção 2 — APRENDIZADOS OPERACIONAIS

Registre os aprendizados **por agente**. Cada agente tem estratégia própria
e deve ser avaliado de forma independente — um agente lucrativo não pode
mascarar um agente perdedor.

Repita o bloco 2.A para cada agente ativo no pregão:
`MICRO_TENDENCIA` | `DIARIOS` | `RL_5000` | `RL_DIRETO`

### 2.A Análise por Agente — `<NOME_DO_AGENTE>`

#### 2.A.1 Desempenho Individual

```yaml
agente: "<MICRO_TENDENCIA | DIARIOS | RL_5000 | RL_DIRETO>"
executor: "<INICIAR_*.bat>"
resultado_reais: <valor em R$ — positivo ou negativo>
trades_executados: <número inteiro>
trades_encerrados: <número inteiro>
wins: <número inteiro>
losses: <número inteiro>
win_rate_pct: <0–100>
maior_ganho_reais: <valor>
maior_perda_reais: <valor negativo>
relacao_risco_retorno: "<ex: 1:2.5>"
veredicto: "<LUCRATIVO | NEUTRO | DEFICITARIO>"
```

> **Regra:** `DEFICITARIO` não é aceitável como estado permanente.
> Agente deficitário por 3 pregões consecutivos entra automaticamente
> em revisão de estratégia (item P1 no backlog).

#### 2.A.2 Análise das 4 Dimensões

```yaml
dimensoes:
  macro:
    sinal: "<BULLISH | BEARISH | NEUTRAL>"
    funcionou: <true | false>
    observacao: "<o que o sinal indicou e se confirmou para este agente>"
  fundamentos:
    sinal: "<BULLISH | BEARISH | NEUTRAL>"
    funcionou: <true | false>
    observacao: "<impacto nos fundamentos da estratégia do agente>"
  sentimento:
    sinal: "<BULLISH | BEARISH | NEUTRAL>"
    funcionou: <true | false>
    observacao: "<como o sentimento intraday afetou as entradas do agente>"
  tecnica:
    sinal: "<BULLISH | BEARISH | NEUTRAL>"
    funcionou: <true | false>
    observacao: "<setups, rompimentos, suportes/resistências relevantes>"
```

#### 2.A.3 Setups Que Funcionaram

```yaml
setups_sucesso:
  - nome: "<nome do setup>"
    descricao: "<descrição breve>"
    condicoes: "<condições presentes>"
    resultado_reais: <valor>
    confianca_pct: <0–100>
    frequencia_no_dia: <vezes>
    dimensoes_alinhadas: ["macro", "tecnica"]
```

#### 2.A.4 Setups Que Falharam

```yaml
setups_falha:
  - nome: "<nome do setup>"
    descricao: "<descrição breve>"
    motivo_falha: "<por que falhou>"
    resultado_reais: <valor negativo>
    licao: "<o que deve ser ajustado neste agente>"
```

#### 2.A.5 Decisões Corretas vs Incorretas

```yaml
decisoes_corretas:
  - acao: "<COMPRA | VENDA | AGUARDAR>"
    contexto: "<situação de mercado>"
    resultado: "<resultado obtido>"
decisoes_incorretas:
  - acao: "<COMPRA | VENDA | AGUARDAR>"
    contexto: "<situação de mercado>"
    resultado: "<resultado obtido>"
    ajuste_necessario: "<o que deve ser mudado neste agente>"
```

#### 2.A.6 Comportamento do Algoritmo vs Expectativa

```yaml
comportamento_algoritmo:
  alinhado_com_expectativa: <true | false>
  observacoes:
    - "<observação sobre o comportamento do agente>"
  divergencias:
    - "<onde o agente divergiu do esperado>"
  sugestoes_ajuste:
    - "<sugestão de ajuste específica para este agente>"
```

---

## Seção 3 — CAPTURA DE MELHORIAS

Liste as melhorias identificadas. Toda melhoria deve indicar qual agente
ela impacta — melhorias transversais (múltiplos agentes) devem ser
explicitadas como tal.

**Referência de Prioridade:**

- `alta` — Impacto imediato em segurança, capital ou decisões críticas
- `media` — Melhoria relevante sem urgência imediata
- `baixa` — Nice-to-have, melhoria incremental

**Referência de Esforço:**

- `pequeno` — Menos de 1 hora
- `medio` — Entre 1 e 4 horas
- `grande` — Mais de 4 horas

### 3.1 Backlog Técnico

```yaml
backlog_tecnico:
  - id: "TECH-<NNN>"
    titulo: "<título da melhoria>"
    descricao: "<descrição detalhada>"
    prioridade: "<alta | media | baixa>"
    esforco: "<pequeno | medio | grande>"
    agente_impactado: "<MICRO_TENDENCIA | DIARIOS | RL_5000 | RL_DIRETO | TODOS>"
    arquivo_afetado: "<caminho/do/arquivo.py>"
    sync_com: []
```

### 3.2 Backlog Funcional

```yaml
backlog_funcional:
  - id: "FEAT-<NNN>"
    titulo: "<título da feature>"
    descricao: "<descrição detalhada>"
    prioridade: "<alta | media | baixa>"
    esforco: "<pequeno | medio | grande>"
    agente_impactado: "<MICRO_TENDENCIA | DIARIOS | RL_5000 | RL_DIRETO | TODOS>"
    estrategia_relacionada: "<nome da estratégia>"
    sync_com:
      - "AGENTE_AUTONOMO_FEATURES.md"
      - "AUTOTRADER_MATRIX.md"
```

### 3.3 Backlog de Governança

```yaml
backlog_governanca:
  - id: "GOV-<NNN>"
    titulo: "<título>"
    descricao: "<descrição>"
    prioridade: "<alta | media | baixa>"
    esforco: "<pequeno | medio | grande>"
    agente_impactado: "<MICRO_TENDENCIA | DIARIOS | RL_5000 | RL_DIRETO | TODOS>"
    documento_afetado: "<nome-do-documento.md>"
    sync_com:
      - "SYNC_MANIFEST.json"
      - "VERSIONING.json"
```

### 3.4 Backlog de ML/RL

```yaml
backlog_ml_rl:
  - id: "ML-<NNN>"
    titulo: "<título>"
    descricao: "<padrão identificado para aprendizagem por reforço>"
    prioridade: "<alta | media | baixa>"
    esforco: "<pequeno | medio | grande>"
    agente_impactado: "<MICRO_TENDENCIA | DIARIOS | RL_5000 | RL_DIRETO | TODOS>"
    tipo_aprendizado: "<supervised | reinforcement | unsupervised>"
    sync_com:
      - "AGENTE_AUTONOMO_RL.md"
```

---

## Seção 4 — SÍNTESE PARA BACKLOG

Esta seção é gerada automaticamente pelo script `fechamento_diario.py`
e deve ser revisada antes de ser importada para o backlog.

### 4.1 Resultado Consolidado

```yaml
resultado_consolidado:
  timestamp: "<YYYY-MM-DDTHH:MM:SSZ>"
  foco: "<abertura | meio_dia | fechamento>"
  resultado_total_reais: <soma de todos os agentes>
  resultado_total_pct: "<+X.X% | -X.X%>"
  win_rate_geral_pct: <0–100>
```

### 4.2 Resultado por Agente

```yaml
resultado_por_agente:
  - agente: "MICRO_TENDENCIA"
    executor: "INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat"
    resultado_reais: <valor>
    trades: <número>
    win_rate_pct: <0–100>
    veredicto: "<LUCRATIVO | NEUTRO | DEFICITARIO>"
  - agente: "DIARIOS"
    executor: "INICIAR_DIARIOS.bat"
    resultado_reais: <valor>
    trades: <número>
    win_rate_pct: <0–100>
    veredicto: "<LUCRATIVO | NEUTRO | DEFICITARIO>"
  - agente: "RL_5000"
    executor: "INICIAR_AGENTE_RL_5000.bat"
    resultado_reais: <valor>
    trades: <número>
    win_rate_pct: <0–100>
    veredicto: "<LUCRATIVO | NEUTRO | DEFICITARIO>"
  - agente: "RL_DIRETO"
    executor: "INICIAR_AGENTE_RL_DIRETO.bat"
    resultado_reais: <valor>
    trades: <número>
    win_rate_pct: <0–100>
    veredicto: "<LUCRATIVO | NEUTRO | DEFICITARIO>"
```

> **Invariante:** nenhum agente `DEFICITARIO` pode ser omitido ou
> compensado pelo resultado dos demais. Se o total consolidado é positivo
> mas um agente individual é `DEFICITARIO`, isso deve aparecer como
> alerta explícito na seção 4.4.

### 4.3 Melhorias Capturadas

```yaml
total_melhorias_capturadas: <número>
melhorias_por_categoria:
  tecnico: <número>
  funcional: <número>
  governanca: <número>
  ml_rl: <número>
melhorias_por_agente:
  MICRO_TENDENCIA: <número>
  DIARIOS: <número>
  RL_5000: <número>
  RL_DIRETO: <número>
  TODOS: <número>
```

### 4.4 Itens Críticos para Ação Imediata

```yaml
itens_criticos:
  - id: "<ID>"
    titulo: "<título>"
    categoria: "<tecnico | funcional | governanca | ml_rl>"
    agente_impactado: "<nome do agente ou TODOS>"
    prioridade: "alta"
    responsavel: "Agente Autônomo"
    prazo: "<YYYY-MM-DD>"
agentes_em_alerta:
  - agente: "<nome>"
    motivo: "<DEFICITARIO | bug_critico | divergencia_estrategia>"
    acao_requerida: "<descrição da ação>"
```

### 4.5 Referências de Sincronização

```yaml
sincronizacao:
  documentos_atualizados:
    - "docs/BACKLOG.md"
  checksums_validados: <true | false>
  sync_manifest_atualizado: <true | false>
  versioning_atualizado: <true | false>
  timestamp_sincronizacao: "<YYYY-MM-DDTHH:MM:SSZ>"
```

---

## Notas de Execução

- O script lê variáveis de ambiente opcionais: `FECHAMENTO_SIMBOLO`,
  `FECHAMENTO_VERBOSE`.
- A saída YAML é validada contra
  `prompts/schema_fechamento_diario.json` antes de ser gravada.
- O backlog é atualizado em
  `docs/agente_autonomo/AGENTE_AUTONOMO_BACKLOG.md`.
- `SYNC_MANIFEST.json` e `VERSIONING.json` são atualizados
  automaticamente ao final de cada execução com foco `fechamento`.
