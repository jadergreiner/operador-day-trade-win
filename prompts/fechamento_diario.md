# Prompt de Fechamento Diário — Operador Quântico

## Visão Geral

Este prompt é executado **até três vezes ao dia** pelo script
`prompts/fechamento_diario.py` com o parâmetro `--foco`:

| Foco | Horário | Objetivo |
|---|---|---|
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

Registre os aprendizados por categoria de análise.

### 2.1 Análise das 4 Dimensões

```yaml
dimensoes:
  macro:
    sinal: "<BULLISH | BEARISH | NEUTRAL>"
    funcionou: <true | false>
    observacao: "<o que o sinal macro indicou e se se confirmou>"
  fundamentos:
    sinal: "<BULLISH | BEARISH | NEUTRAL>"
    funcionou: <true | false>
    observacao: "<o que os fundamentos indicaram e se confirmou>"
  sentimento:
    sinal: "<BULLISH | BEARISH | NEUTRAL>"
    funcionou: <true | false>
    observacao: "<como o sentimento intraday se desenvolveu>"
  tecnica:
    sinal: "<BULLISH | BEARISH | NEUTRAL>"
    funcionou: <true | false>
    observacao: "<setups que apareceram, rompimentos, suportes/resistências>"
```

### 2.2 Setups Que Funcionaram

```yaml
setups_sucesso:
  - nome: "<nome do setup>"
    descricao: "<descrição breve>"
    condicoes: "<condições presentes>"
    resultado_pts: <pontos>
    confianca_pct: <0–100>
    frequencia_no_dia: <vezes>
    dimensoes_alinhadas: ["macro", "tecnica"]
```

### 2.3 Setups Que Falharam

```yaml
setups_falha:
  - nome: "<nome do setup>"
    descricao: "<descrição breve>"
    motivo_falha: "<por que falhou>"
    resultado_pts: <pontos negativos>
    licao: "<o que deve ser ajustado>"
```

### 2.4 Decisões Corretas vs Incorretas

```yaml
decisoes_corretas:
  - acao: "<COMPRA | VENDA | AGUARDAR>"
    contexto: "<situação de mercado>"
    resultado: "<resultado obtido>"
decisoes_incorretas:
  - acao: "<COMPRA | VENDA | AGUARDAR>"
    contexto: "<situação de mercado>"
    resultado: "<resultado obtido>"
    ajuste_necessario: "<o que deve ser mudado>"
```

### 2.5 Comportamento do Algoritmo vs Expectativa

```yaml
comportamento_algoritmo:
  alinhado_com_expectativa: <true | false>
  observacoes:
    - "<observação sobre o comportamento do algoritmo>"
  divergencias:
    - "<onde o algoritmo divergiu do esperado>"
  sugestoes_ajuste:
    - "<sugestão de ajuste no modelo>"
```

---

## Seção 3 — CAPTURA DE MELHORIAS

Liste as melhorias identificadas, classificadas por categoria e prioridade.

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
    tipo_aprendizado: "<supervised | reinforcement | unsupervised>"
    sync_com:
      - "AGENTE_AUTONOMO_RL.md"
```

---

## Seção 4 — SÍNTESE PARA BACKLOG

Esta seção é gerada automaticamente pelo script `fechamento_diario.py`
e deve ser revisada antes de ser importada para o backlog.

### 4.1 Resumo Executivo

```yaml
resumo_executivo:
  timestamp: "<YYYY-MM-DDTHH:MM:SSZ>"
  foco: "<abertura | meio_dia | fechamento>"
  desempenho:
    analises_rodadas: <número>
    trades_executados: <número>
    resultado_financeiro: "<+X.X% | -X.X%>"
    win_rate_pct: <0–100>
  total_melhorias_capturadas: <número>
  melhorias_por_categoria:
    tecnico: <número>
    funcional: <número>
    governanca: <número>
    ml_rl: <número>
```

### 4.2 Itens Críticos para Ação Imediata

```yaml
itens_criticos:
  - id: "<ID>"
    titulo: "<título>"
    categoria: "<tecnico | funcional | governanca | ml_rl>"
    prioridade: "alta"
    responsavel: "Agente Autônomo"
    prazo: "<YYYY-MM-DD>"
```

### 4.3 Referências de Sincronização

```yaml
sincronizacao:
  documentos_atualizados:
    - "docs/agente_autonomo/AGENTE_AUTONOMO_BACKLOG.md"
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
