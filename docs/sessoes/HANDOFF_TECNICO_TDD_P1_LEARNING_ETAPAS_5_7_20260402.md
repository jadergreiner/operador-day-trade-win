# Handoff Técnico/TDD — P1-LEARNING Etapas 5-7

## Status da execução

**Estado:** em execução em `02/04/2026`

A base das Etapas 5-7 já existe e foi validada nesta sessão. O foco
imediato agora é **acoplar o pipeline ao encerramento real das sessões** dos
agentes, para gerar aprendizado observável em produção.

## Evidências verificadas agora

- `pytest tests/unit/test_p1_learning_etapas_5_7.py -q`
  - **Resultado:** `28 passed in 1.13s`
- Módulos já implementados em `src/application/`:
  - `p1_learning_l1_analysis.py`
  - `p1_learning_l2_causal.py`
  - `p1_learning_regras.py`
  - `p1_learning_relatorio.py`
- Bloqueio atual de tipagem:
  - `mypy --strict` ainda falha por baseline antigo em
    `src/infrastructure/adapters/mt5_adapter.py`
    e `src/infrastructure/database/schema.py`

## Gap técnico restante

As Etapas 5-7 passam na suíte unitária, mas ainda não estão ligadas ao
encerramento operacional do agente. Nesta revisão, não foi encontrado uso
runtime desses módulos em `scripts/`.

## Objetivo do handoff

Ao fim desta entrega, cada sessão deve produzir:

1. `data/models/l1_analysis_YYYYMMDD.jsonl`
2. `data/models/learning_rules_YYYYMMDD.json`
3. `outputs/p1_learning_report_YYYYMMDD_<sessao>.md`

## Escopo técnico imediato

### 1. Orquestração do pipeline

Criar ou consolidar uma função de orquestração, por exemplo:
`executar_pipeline_aprendizado_sessao(...)`, responsável por:

- carregar os `ClosureRecord` da sessão;
- executar a análise L1;
- executar a análise causal L2;
- gerar regras observáveis;
- salvar o relatório em Markdown;
- registrar sucesso/erro sem quebrar o agente.

### 2. Integração no runtime

Acoplar o pipeline ao ponto de encerramento real da sessão em:

- `scripts/agente_rl_direto_independente.py`
- opcionalmente depois em `scripts/operar_novo_agente_rl_real_antiovertrading.py`

### 3. Persistência operacional

Garantir escrita consistente em:

- `data/models/`
- `outputs/`

## Handoff TDD acionável

### RED — escrever o teste que falha primeiro

Criar `tests/integration/test_p1_learning_pipeline_runtime.py` com estes
cenários mínimos:

1. sessão com fechamentos válidos gera `l1_analysis_*.jsonl`;
2. sessão com erros recorrentes gera `learning_rules_*.json`;
3. sessão encerrada gera `p1_learning_report_*.md`;
4. falha em uma etapa do relatório não derruba o fluxo do agente.

### GREEN — implementação mínima

- reutilizar `AnalisadorDecisaoL1`;
- reutilizar `DetectorCausalL2`;
- reutilizar `GeradorRegraAprendizado`;
- reutilizar `RelatorioSessao`;
- integrar ao fechamento da sessão com o menor diff possível.

### REFACTOR — endurecimento final

- extrair thresholds para config;
- padronizar `sessao_id` e nomes de artefatos;
- adicionar logs estruturados por etapa;
- preparar fallback silencioso para erro de escrita em disco.

## Critérios de aceite

- cada sessão gera artefatos de aprendizado legíveis;
- sessão com erro operacional gera `>= 1` regra observável;
- nenhuma exceção nova vaza para o loop principal;
- testes unitários e de integração ficam verdes.

## Comandos de validação

```bash
pytest tests/unit/test_p1_learning_etapas_5_7.py -q
pytest tests/integration/test_p1_learning_pipeline_runtime.py -q
mypy src/application/p1_learning_*.py --strict
```

## Donos sugeridos

- **QA/TDD:** definir RED phase e fixtures reais de fechamento
- **Software Engineer:** integrar o pipeline ao runtime do agente
- **Tech Lead:** validar artefatos e impacto no Gate 2
