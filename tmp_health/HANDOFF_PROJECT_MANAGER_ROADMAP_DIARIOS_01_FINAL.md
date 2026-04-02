# HANDOFF PARA PROJECT MANAGER

## 1. Identificacao

- **id_demanda:** `PO-2026-04-02-ROADMAP-DIARIOS-01`
- **titulo:** Watchdog de threads e observabilidade dos diarios (v1.1)
- **estado_documentacao:** `DEVOLVER_TECH_LEAD`
- **prioridade:** `P0`
- **data:** `02/04/2026`

---

## 2. Resumo da Entrega

- **objetivo da demanda:** ampliar a observabilidade dos diarios com
  watchdog, maquina de estados, persistencia SQLite e snapshot JSON atomico.
- **problema parcialmente resolvido:** a infraestrutura documental e tecnica
  da observabilidade foi criada, mas a integracao operacional do launcher
  ainda esta incompleta.
- **valor esperado pelo PO:** o operador enxergar claramente as **5 threads
  canonicas** em runtime no fluxo de `INICIAR_DIARIOS.bat`.
- **valor efetivamente entregue:** melhora estrutural de observabilidade,
  porem com **exposicao humana parcial** e sem evidencia final de validacao
  operacional.

---

## 3. Impacto no Produto

- **melhoria funcional:** parcial, concentrada em monitoramento e diagnostico
  do agente de diarios.
- **melhoria tecnica:** positiva; separacao entre aplicacao e persistencia
  esta coerente com `ADR-001`.
- **impacto operacional:** **medio**, pois o operador ainda pode interpretar a
  feature como pronta sem ver o painel final refletindo o contrato canonico.

---

## 4. Evolucao Arquitetural

- **mudancas estruturais:**
  - uso de SQLite como persistencia primaria;
  - exportacao JSON com estrategia atomica (`.tmp` + `os.replace`);
  - base pronta para heartbeat, alertas e historico de reinicios.
- **decisoes tecnicas relevantes:**
  - fail-open mantido nas operacoes de I/O;
  - retrocompatibilidade preservada nas assinaturas;
  - launcher alvo correto: `INICIAR_DIARIOS.bat`.
- **compatibilidade preservada:** **sim**, mas com lacunas na integracao do
  runtime principal.

---

## 5. Documentacao Atualizada

- **`docs/ADRS.md`:** sem nova alteracao necessaria agora; `ADR-001` segue
  valido e aderente.
- **`docs/ARQUITETURA_ALVO.md`:** ja cobre o contrato operacional dos
  diarios, mas a implementacao ainda nao o espelha por completo.
- **`docs/DIAGRAMAS.md`:** ja antecipa as **5 threads** no bootstrap diario.
- **`docs/BACKLOG.md`:** o item
  `ROADMAP-DIARIOS-01 Watchdog de threads e observabilidade dos diarios`
  **ja esta pendente**, o que permanece correto neste momento.
- **`docs/MODELAGEM_DE_DADOS.md`:** ainda **nao** ha consolidacao final do
  contrato de eventos `HEARTBEAT` e `ALERTA`.
- **`docs/REGRAS_DE_NEGOCIO.md`:** ainda **pendente** formalizar o contrato
  operacional final do launcher.

---

## 6. Evidencias Tecnicas

### Evidencias positivas

- `get_errors` retornou **No errors found** para:
  - `src/application/diario_observability_panel.py`
  - `src/infrastructure/persistence/repositorio_watchdog_eventos.py`
  - `tests/unit/test_diario_observability_panel_estendido.py`
- validacao estatica executada com sucesso:
  - comando: `python -m py_compile ...`
  - resultado: `PY_COMPILE_OK`

### Evidencias que bloqueiam aprovacao final

- validacao operacional **nao pode ser comprovada** neste ambiente:
  - `python -m pytest ...` -> `No module named pytest`
  - `python -m mypy ...` -> `No module named mypy`

### Evidencia direta no codigo atual

- `scripts/start_journals_full_display.py` ainda chama apenas:
  - `_painel_obs.registrar_gravacao("DIARIOS")`
- `src/application/diario_observability_panel.py` ainda mantem:
  - `DIARIOS_MONITORADOS` com **4 nomes**
  - `CAMINHO_BANCO_DIARIOS_PADRAO = Path("data/db/trading.db")`
  - `exibir_painel_terminal()` renderizando o estado legado via
    `self._status`

---

## 7. Matriz de Impacto nos 5 Launchers

| Agente | Papel | Impacto | Tipo | Evolucao | Evidencia | Acao |
|---|---|---|---|---|---|---|
| `INICIAR_DIARIOS.bat` | Journaling + contexto + retraining | **MEDIO** | **DIRETO** | Observabilidade parcial | integracao ainda usa fluxo legado e painel incompleto | **Corrigir, revalidar e so entao aprovar** |
| `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` | Sinais intraday com ML | **NENHUM** | **SEM IMPACTO** | Sem mudanca | nenhum uso direto encontrado | Nenhuma |
| `INICIAR_AGENTE_RL_5000.bat` | Execucao RL principal | **NENHUM** | **SEM IMPACTO** | Sem mudanca | nenhum acoplamento direto | Nenhuma |
| `INICIAR_AGENTE_RL_DIRETO.bat` | Execucao RL paralela | **NENHUM** | **SEM IMPACTO** | Sem mudanca | nenhum acoplamento direto | Nenhuma |
| `INICIAR_MONITOR_QUANTICO.bat` | Observabilidade web transversal | **NENHUM** | **SEM IMPACTO** | Sem mudanca | sem integracao encontrada | Nenhuma |

---

## 8. Riscos ou Ressalvas

- a interface humana ainda **nao expoe claramente** as 5 threads canonicas;
- ha risco de divergencia entre `trading.db` e `trading_diarios.db`;
- a cobertura declarada de `71/71` **nao foi comprovada localmente** com
  evidencia fresca;
- o contrato de eventos `HEARTBEAT` e `ALERTA` ainda precisa de fechamento
  documental e operacional.

---

## 9. Valor Entregue ao Produto

- **valor esperado pelo PO:** observabilidade operacional clara, confiavel e
  canonica dos diarios.
- **valor efetivamente entregue:** fundacao tecnica solida para watchdog e
  persistencia, mas **sem fechamento completo do valor de operacao**.
- **impacto esperado no sistema apos correcao:** reducao real de risco
  operacional no launcher de diarios, com melhor diagnostico e confianca do
  operador.

---

## 10. Recomendacao

### Nao aprovar para fechamento, commit final ou push para `main` ainda

**Encaminhamento recomendado:** `DEVOLVER_TECH_LEAD / ENGENHARIA`

### Pendencias obrigatorias antes da consolidacao final

1. integrar `registrar_heartbeat`, `registrar_falha`,
   `gerar_snapshot_operacional` e `exportar_snapshot_json` no fluxo real de
   `scripts/start_journals_full_display.py`;
2. atualizar `exibir_painel_terminal()` para refletir as **5 threads
   canonicas**;
3. alinhar o banco padrao para `trading_diarios.db`;
4. rerodar `pytest` e `mypy` em ambiente provisionado e anexar logs reais.

---

## 11. Definition of Ready para Project Manager

- [ ] documentacao consolidada como entrega final
- [x] decisao tecnica registrada
- [x] impacto arquitetural documentado
- [x] backlog permanece corretamente sinalizado como pendente
- [ ] evidencia fresca de `pytest` e `mypy`
- [ ] integracao operacional completa no launcher
- [ ] observabilidade humana final adequada

---

## 12. Conclusao Executiva

A demanda esta em **bom estado tecnico**, porem **ainda nao esta pronta para
aprovacao final do Project Manager**. O correto neste ciclo e **retornar para
engenharia**, fechar a integracao runtime de `INICIAR_DIARIOS.bat` e somente
depois consolidar a documentacao final.
