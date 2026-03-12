# Backlog Canonico

## Escopo Atual

Este backlog consolida a atividade ativa: **P0-2 Etapa 4.1**.

## P0-2 Etapa 4.1 - Estabilizacao Gate 2

### Objetivo

Estabilizar pipeline de backtest P0-2 e retestar Gate 2 com contrato confiavel.

### Entregas Tecnicas

- Persistencia corrigida para `data/backtest/backtest_results.json` como arquivo.
- Contrato de consistencia padronizado para `consistency_std` com compatibilidade legada.
- Caminho de decisao unificado em `data/backtest/gate2_decision.json`.
- Execucao deterministica com `random_seed` para reduzir flakiness.
- Logging operacional seguro em ASCII para console Windows.
- Fallback conservador preservado em erro/indefinido/em execucao.

### Criterios de Aceitacao

1. Suites P0-2 passam:
   - `scripts/test_p0_2_backtest_validation.py`
   - `scripts/test_p0_2_etapa2_reporting.py`
   - `scripts/test_p0_2_etapa3_integration.py`
2. `scripts/run_p0_2_backtest.py` gera os 3 artefatos obrigatorios.
3. `scripts/check_p0_2_status.py` respeita contrato de capital conservador por default.

### Fora de Escopo

- Otimizacao de estrategia para forcar PASS de metricas.
- Mudancas em regras operacionais de runtime.

## Referencias Canonicas

- [ARQUITETURA_ALVO.md](ARQUITETURA_ALVO.md)
- [REGRAS_DE_NEGOCIO.md](REGRAS_DE_NEGOCIO.md)
- [MODELAGEM_DE_DADOS.md](MODELAGEM_DE_DADOS.md)
- [DIAGRAMAS.md](DIAGRAMAS.md)
- [ADRS.md](ADRS.md)
