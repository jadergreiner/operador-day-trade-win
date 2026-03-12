# Arquitetura Alvo

## Objetivo

Definir o contrato arquitetural ativo para operacao dos launchers:

- `INICIAR_DIARIOS.bat`
- `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`

Este documento e canonico para decisoes de fluxo operacional.

## Fluxo Macro

1. Preparacao de ambiente e pre-flight.
2. Sincronizacao local MT5 -> SQLite.
3. Aplicacao de contexto diario (BDI/ML).
4. Consulta de status P0-2 (Gate 2) para escala de capital.
5. Bootstrap Python e execucao do agente.
6. Sincronizacao final e encerramento rastreavel.

## Contrato Gate 2 (P0-2)

Entrada: `scripts/check_p0_2_status.py` (exit code).

- `0`: PASS -> capital ampliado.
- `1`: FAIL -> capital conservador.
- `2`: em execucao -> capital conservador.
- `3`: indefinido/erro -> capital conservador.

Artefatos obrigatorios:

- `data/backtest/backtest_results.json`
- `data/backtest/gate2_decision.json`
- `data/backtest/p0_2_status.json`

## Invariantes de Compatibilidade

- Gate 2 altera somente escala de capital.
- Nenhuma regra de entrada/saida do runtime e alterada por este fluxo.
- Falhas de pipeline nao podem liberar capital ampliado.

## Referencias Canonicas

- [ADRS.md](ADRS.md)
- [BACKLOG.md](BACKLOG.md)
- [DIAGRAMAS.md](DIAGRAMAS.md)
- [MODELAGEM_DE_DADOS.md](MODELAGEM_DE_DADOS.md)
- [REGRAS_DE_NEGOCIO.md](REGRAS_DE_NEGOCIO.md)
