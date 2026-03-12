# Diagramas Canonicos

## Visao de Fluxo - Gate 2

```text
INICIAR_DIARIOS.bat
  -> run_p0_2_backtest.py (background)
    -> backtest_engine.py
    -> backtest_reporter.py
    -> backtest_validator.py
    -> data/backtest/{backtest_results.json, gate2_decision.json, p0_2_status.json}

INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
  -> check_p0_2_status.py
    -> CAPITAL_SCALE (100k ou 50k)
  -> launch_agent_with_ml_v1_2_3.py
```

## Visao de Dependencias

```text
ARQUITETURA_ALVO.md
  -> define contrato Gate 2
REGRAS_DE_NEGOCIO.md
  -> define fallback conservador
MODELAGEM_DE_DADOS.md
  -> define schema dos artefatos JSON
ADRS.md
  -> registra decisoes e trade-offs
BACKLOG.md
  -> define entrega ativa e criterios
```

## Notas

- Diagramas legados (`DIAGRAMA_CLASSES.md`, `DIAGRAMA_DADOS.md`) sao historicos.
- Este documento e a visao canonica de alto nivel para P0-2 Gate 2.
