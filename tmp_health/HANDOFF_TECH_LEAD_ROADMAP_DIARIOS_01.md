# HANDOFF DO TECH LEAD PARA DOC ADVOCATE

## 1. Identificacao

- **id_demanda:** `PO-2026-04-02-ROADMAP-DIARIOS-01`
- **titulo:** Watchdog de threads e observabilidade dos diarios (v1.1)
- **estado_review:** `TECH_REVIEW_DEVOLVER_ENGENHARIA`
- **prioridade:** `P0`
- **data:** `02/04/2026`

---

## 2. Resumo da Revisao

- **objetivo da demanda:** estender a observabilidade dos diarios com 5
  threads canonicas, maquina de estados, persistencia SQLite, exportacao
  JSON atomica e alertas de inatividade.
- **leitura tecnica:** o nucleo em `src/application/diario_observability_panel.py`
  e `src/infrastructure/persistence/repositorio_watchdog_eventos.py` ficou
  bem estruturado e aderente ao uso de SQLite com fail-open.
- **conclusao da revisao:** a base tecnica esta boa, mas a integracao
  operacional com `INICIAR_DIARIOS.bat` ainda ficou parcial; por isso a
  entrega deve retornar para engenharia antes da consolidacao final.

---

## 3. Validacao Arquitetural

- **aderencia a ADRs:**
  - ✅ `ADR-001` respeitado com SQLite como persistencia primaria.
  - ✅ separacao entre camada de aplicacao e persistencia esta adequada.
- **aderencia a arquitetura alvo:**
  - ✅ foco correto no launcher `INICIAR_DIARIOS.bat`.
  - ⚠️ valor operacional prometido ainda nao esta completamente conectado ao
    runtime principal.
- **conflitos detectados:**
  1. `scripts/start_journals_full_display.py` ainda usa apenas
     `_painel_obs.registrar_gravacao("DIARIOS")` em fluxo legado.
  2. `exibir_painel_terminal()` continua renderizando apenas os 4 nomes de
     `DIARIOS_MONITORADOS`, nao as 5 threads canonicas.
  3. coexistem `_status` e `_status_estendido`, mas a interface humana atual
     continua olhando majoritariamente para o estado legado.
  4. o caminho padrao do banco no painel aponta para `data/db/trading.db`,
     enquanto o launcher usa `trading_diarios.db`.
- **decisoes confirmadas:**
  - manter retrocompatibilidade de assinatura.
  - manter fail-open em toda I/O.
  - manter JSON atomico com `.tmp` + `os.replace`.

---

## 4. Qualidade da Implementacao

- **clareza do codigo:** boa; nomes, dataclasses e estrutura geral estao
  consistentes.
- **complexidade:** controlada e aceitavel para o escopo.
- **extensibilidade:** boa; o design permite integracao futura com watchdog
  e consumers externos.
- **robustez:** boa na camada de persistencia/serializacao; parcial na
  integracao operacional completa do launcher.

---

## 5. Validacao de Testes

- **evidencia estatica verificada:**
  - `py_compile` executado com sucesso nos arquivos entregues:
    `PY_COMPILE_OK`.
  - `get_errors` sem erros em:
    - `src/application/diario_observability_panel.py`
    - `src/infrastructure/persistence/repositorio_watchdog_eventos.py`
    - `tests/unit/test_diario_observability_panel_estendido.py`
- **evidencia operacional nao reproduzida localmente:**
  - o ambiente atual falhou ao executar validacoes completas por ausencia de
    dependencias:
    - `No module named pytest`
    - `No module named mypy`
    - `ModuleNotFoundError: No module named 'pydantic'`
- **cobertura declarada no handoff:** 71/71 testes passados.
- **status de confiabilidade da evidencia:** nao confirmada localmente neste
  ambiente, embora a estrutura dos testes e do codigo esteja coerente.

---

## 6. Observabilidade

- **logs:** `logger.warning` presente para falhas de I/O e alertas.
- **metricas/sinais:** snapshot estruturado por thread, com estado,
  heartbeat, registros, reinicios e alerta.
- **ressalva operacional:** a observabilidade visivel ao operador no terminal
  ainda permanece parcial porque o painel ASCII segue no modo legado.

---

## 7. Impacto Sistemico

- **impacto em execucao:** medio no `INICIAR_DIARIOS.bat`, pois o codigo novo
  existe mas ainda nao esta plenamente plugado no fluxo runtime.
- **impacto em dados:** baixo e controlado; nova tabela e append-only, com
  abordagem segura.
- **impacto em arquitetura:** positivo no desenho, sem violar ADRs.
- **risco operacional:** moderado, por risco de considerar a entrega como
  completa sem que o operador veja as 5 threads no terminal.

---

## 8. Matriz de Impacto nos 5 Launchers

| Launcher | Impacto | Tipo | Evidencia | Acao operacional |
|---|---|---|---|---|
| `INICIAR_DIARIOS.bat` | **MEDIO** | **DIRETO** | importa `ObservabilidadeDiarios`, mas ainda usa `registrar_gravacao("DIARIOS")` e painel legado | **Corrigir integracao e revalidar** |
| `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` | **NENHUM** | **SEM IMPACTO** | sem uso direto encontrado | Nenhuma |
| `INICIAR_AGENTE_RL_5000.bat` | **NENHUM** | **SEM IMPACTO** | sem uso direto encontrado | Nenhuma |
| `INICIAR_AGENTE_RL_DIRETO.bat` | **NENHUM** | **SEM IMPACTO** | sem uso direto encontrado | Nenhuma |
| `INICIAR_MONITOR_QUANTICO.bat` | **NENHUM** | **SEM IMPACTO** | sem integracao encontrada | Nenhuma |

---

## 9. Riscos e Ressalvas

- a interface humana atual ainda nao mostra claramente as 5 threads canonicas.
- a maquina de estados esta preparada, mas nem todo contrato foi ligado ao
  runtime real.
- o claim de `71/71 PASSED` nao foi comprovado agora no ambiente local.
- ha risco de divergencia entre `trading.db` e `trading_diarios.db` se o
  caminho padrao nao for alinhado.

---

## 10. Pendencias

### Obrigatorias antes de aprovar

1. integrar `registrar_heartbeat`, `registrar_falha`,
   `gerar_snapshot_operacional` e `exportar_snapshot_json` no fluxo real de
   `scripts/start_journals_full_display.py`.
2. atualizar `exibir_painel_terminal()` para refletir as 5 threads canonicas
   ou documentar formalmente que o JSON e a interface oficial.
3. fechar o contrato de persistencia/uso para eventos `HEARTBEAT` e `ALERTA`.
4. alinhar o caminho padrao do banco com `trading_diarios.db`.
5. rerodar `pytest` e `mypy` em ambiente provisionado e anexar logs reais.

### Opcionais

- permitir injecao controlada de `session_id` para testes deterministas.
- enriquecer o painel terminal com estados `rodando`, `pausado`,
  `com_erro` e `reiniciando` por thread.

---

## 11. Recomendacoes Tecnicas

- priorizar o fechamento da integracao no launcher antes de qualquer
  consolidacao documental.
- validar o consumer do campo `"fonte": "memoria"` no JSON exportado.
- manter a estrategia fail-open, mas complementar com verificacao operacional
  no startup dos diarios.
- considerar um teste de integracao real com o loop principal do launcher.

---

## 12. Definition of Approved Implementation

- [x] arquitetura respeitada em grande parte
- [x] contratos principais preservados
- [x] tolerancia a falhas adequada
- [ ] testes confiaveis reproduzidos localmente com evidencia fresca
- [ ] integracao operacional completa no launcher
- [ ] observabilidade humana final adequada
- [ ] documentacao pronta para consolidacao

---

## 13. Instrucoes para Doc Advocate

- **nao consolidar como entrega final aprovada ainda**.
- aguardar retorno da engenharia com fechamento das pendencias acima.
- apos correcao, atualizar os documentos impactados com:
  - decisao final de integracao do painel canonico
  - contrato operacional do launcher `INICIAR_DIARIOS.bat`
  - evidencias reais de `pytest` e `mypy`

---

## 14. Decisao Final do Tech Lead

**Estado final:** `TECH_REVIEW_DEVOLVER_ENGENHARIA`

A implementacao tem **boa base tecnica**, mas **ainda nao entrega 100% do
valor operacional prometido ao operador dos diarios**. Aprovacao final deve
ocorrer somente apos o fechamento da integracao runtime e revalidacao com
logs reais.
