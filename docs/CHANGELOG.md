# CHANGELOG

## 2026-04-02 — Profit Protection v2

- Adicionado: Externalizacao de thresholds do ProfitProtectionEngine
  para `config/profit_protection.yaml` (perfilizacao e shadow_mode).
- Adicionado: Planejamento de calibracao A/B via
  `scripts/calibrar_profit_protection.py` (backtest + relatorio).
- Recomendado: Incluir `pydantic` e `pyyaml` nas dependencias do projeto
  e reiniciar os agentes RL (`INICIAR_AGENTE_RL_DIRETO.bat`,
  `INICIAR_AGENTE_RL_5000.bat`) apos o deploy.
- Observacao: implementacao deve rodar em shadow_mode em staging antes de
  ativacao em producao; gerar artefatos em `outputs/` para auditoria.

---
