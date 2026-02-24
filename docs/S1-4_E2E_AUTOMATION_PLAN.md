# 📋 Plano de Execução S1-4 — Testes E2E Automação

**ID da Tarefa:** S1-4
**Sprint:** Sprint 1 — Operacionalização
**Liderança:** [QA Automation](BOARD_MULTIDISCIPLINAR.json)

---

## 👥 Squad Multidisciplinar (ID: S1-4)

| Membro | Papel na S1-4 | Ação / Responsabilidade |
|:---|:---|:---|
| **QA Automation (12)** | Lead | Desenvolver e executar suite de testes E2E. |
| **Eng Sr (3)** | Architect | Validar consistência do OrdersExecutor e RiskValidator. |
| **ML Expert (4)** | ML Reviewer | Garantir que o classifier (F1 > 0.65) está sendo processado. |
| **Arquiteto de Sistemas (6)** | Perf Reviewer | Validar se latência P95 em teste é < 500ms. |
| **Infra DevOps (7)** | Infra Support | Configurar ambiente MT5 Demo seguro para testes. |
| **Data Engineer (11)** | Data Steward | Verificar integridade dos dados no SQLite (candles/trades). |
| **Product Owner (14)** | Stakeholder | Validar critérios de aceite final (Go-Live Gate). |
| **Doc Advocate (8)** | Sync Lead | Garantir que docs refletem os resultados dos testes. |
| **Coordenadora de Gov (2)** | Facilitator | Registrar progresso e deliberações em STATUS_ENTREGAS. |
| **Operações (9)** | Ops Reviewer | Avaliar viabilidade operacional pós-testes. |

---

## 🎯 Escopo do Teste E2E

1. **Setup**: Iniciar `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` em modo TESTE.
2. **Input**: Injetar sinais via `scripts/backtest_optimizado.py` ou mock manual.
3. **Execution**: Verificar `scripts/agente_micro_tendencia_winfut.py` enviando ordens.
4. **Platform**: Validar recebimento da ordem no MetaTrader 5 (Conta Demo).
5. **Persistence**: Consultar `winfut_data.db` para garantir registro do trade.
6. **Closing**: Validar fechamento da posição por Stop Loss ou Take Profit.

---

## 📅 Timeline de Execução

- **Dia 1**: Setup de ambiente Demo e Mock de Sinais.
- **Dia 2**: Desenvolvimento dos scripts de QA Automation.
- **Dia 3**: Execução de bateria de 50 trades simulados.
- **Dia 4**: Análise de logs, latência e integridade de dados.
- **Dia 5**: Relatório final e Sign-off da Governança.

---
> **Doc Advocate Sync:** [SYNC] S1-4 Documento de Plano de Ação criado em 24/02/2026.
