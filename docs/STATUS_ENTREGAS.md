# Status
[SYNC] Ativo

## Snapshot Atual

- Verdade operacional canônica: [docs/BACKLOG.md](BACKLOG.md), [docs/STATUS_ENTREGAS.md](STATUS_ENTREGAS.md) e [docs/PLANO_MULTI_AGENTES.md](PLANO_MULTI_AGENTES.md). O PRD espelha esses documentos.
- Governança do micro tendência: [docs/MICRO_TENDENCIA_CHANGELOG_GOVERNANCA.md](MICRO_TENDENCIA_CHANGELOG_GOVERNANCA.md) e [docs/MICRO_TENDENCIA_CHANGELOG_TEMPLATE.md](MICRO_TENDENCIA_CHANGELOG_TEMPLATE.md).
- O Gate 2 de escala de capital permanece válido a partir do PASS de 12/03/2026; ele não substitui o gate final operacional.
- Bloqueadores reais desta rodada: `TECH-001`, `TECH-002`, `TECH-003`, `INFRA-1`, `BL-07` canônico, `BL-08` UAT operacional e fechamento diário por agente.
- Evidência confirmada: `BL-01` estrutural verde; testes de `guardian/release_gates/documentation` verdes; a coleta completa do `pytest tests` ainda não está verde por ATI-5 (`shap/numba` x `NumPy 2.4`).
- Execução real do pipeline em 19/03/2026: `BL-01` OK, `BL-08` OK e `NO_GO` concentrado em `BL-07` por `mypy`, `black`, `isort` ausente e warnings do `pytest_cov`.

## Estratégia 3 Agentes

- Agente 1 — Runtime RL/MT5: fechar `TECH-001/002/003` e `INFRA-1`, unificando preço de saída real, rastreio por ticket da sessão atual e backoff/rollover `10006`.
- Agente 2 — Release Gates/UAT: manter `BL-01`, tornar `BL-07` executável com allowlist explícita, adicionar `BL-08` operacional e persistir `go_live_decision.json`.
- Agente 3 — Produto/Observabilidade/PRD: entregar fechamento diário por agente, alinhar schema/contrato e reclassificar o PRD para refletir código entregue versus validação operacional pendente.

## Critério Go/No-Go

- Liberar somente quando `TECH-001/002/003` e `INFRA-1` estiverem fechados, `BL-07` e `BL-08` aprovados e o fechamento por agente não mostrar `preco_saida=0.0`, `DESCONHECIDO` persistente ou contaminação entre sessões.
