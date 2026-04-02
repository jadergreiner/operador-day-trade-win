# HANDOFF PARA PROJECT MANAGER

## 1. Identificacao

- **id_demanda:** `PO-2026-04-02-ROADMAP-DIARIOS-01`
- **titulo:** Watchdog de threads e observabilidade dos diarios (v1.1)
- **estado_documentacao:** `PRONTO_PARA_APROVACAO`
- **prioridade:** `P0`
- **data:** `02/04/2026`
- **versao_handoff:** `v2 — integracao operacional completa`

---

## 2. Resumo da Entrega

- **objetivo da demanda:** ampliar a observabilidade dos diarios com
  watchdog, maquina de estados, persistencia SQLite e snapshot JSON atomico.
- **problema resolvido:** infraestrutura documental e tecnica da
  observabilidade criada e integrada ao runtime do launcher.
- **valor esperado pelo PO:** o operador enxergar claramente as **5 threads
  canonicas** em runtime no fluxo de `INICIAR_DIARIOS.bat`.
- **valor efetivamente entregue:** painel operacional completo com estado,
  heartbeat, gravacoes e reinicializacoes das 5 threads em tempo real,
  exportacao JSON atomica a cada 60s e registro de falhas no SQLite.

---

## 3. Pendencias do Handoff Anterior (v1) — TODAS RESOLVIDAS

1. Integrar `registrar_heartbeat`, `registrar_falha`,
   `gerar_snapshot_operacional` e `exportar_snapshot_json`
   no fluxo real de `scripts/start_journals_full_display.py`
   - **Status:** `CONCLUIDO`
2. Atualizar `exibir_painel_terminal()` para refletir
   as 5 threads canonicas
   - **Status:** `CONCLUIDO`
3. Alinhar o banco padrao para `trading_diarios.db`
   - **Status:** `CONCLUIDO`
4. Rerodar `pytest` e `mypy` em ambiente provisionado
   - **Status:** `CONCLUIDO COM RESSALVA`
   - `.venv` provisionado
   - `pytest` relevante: `71/71 PASSING`
   - `mypy`: divida tecnica preexistente fora do escopo

---

## 4. Mudancas Implementadas

### 4.1 `src/application/diario_observability_panel.py`

**`DIARIOS_MONITORADOS` — corrigido**

```python
# ANTES (4 nomes legados — nao refletia o contrato canonico)
DIARIOS_MONITORADOS = ["MICRO_TENDENCIA", "RL_5000", "RL_DIRETO", "DIARIOS"]

# DEPOIS (5 nomes canonicos — alinhados com ThreadWatchdog e MAPEAMENTO_THREADS_CANONICO)
DIARIOS_MONITORADOS = [
    "TradingJournal", "AIReflection", "RLDiary",
    "MacroGuardian", "DiarioExecucao",
]
```

**`CAMINHO_BANCO_DIARIOS_PADRAO` — corrigido**

```python
# ANTES
CAMINHO_BANCO_DIARIOS_PADRAO = Path("data/db/trading.db")

# DEPOIS
CAMINHO_BANCO_DIARIOS_PADRAO = Path("data/db/trading_diarios.db")
```

**`exibir_painel_terminal()` — reescrito**

- Itera `_status_estendido` (5 threads canonicas) em vez do dicionario
  legado `_status`.
- Exibe por thread: estado operacional, tempo desde ultima gravacao,
  tempo desde ultimo heartbeat, total de gravacoes e reinicializacoes.
- Mapeamento de estado:
  `rodando` / `pausado` / `reiniciando` / `com_erro` / `aguardando` /
  `ALERTA`

### 4.2 `scripts/start_journals_full_display.py`

#### Instancia global e reinicializacao em `main()`

```python
_painel_obs = ObservabilidadeDiarios(
    limite_inatividade_min=20,
    report_dir=project_root / "outputs" / "analysis",
    caminho_banco=(
        project_root / "data" / "db" / "trading_diarios.db"
    ),
)
```

#### Integracao de heartbeat e falha nas 5 threads

- `TradingJournal`
  - `registrar_heartbeat`: topo do `while True`
  - `registrar_gravacao`: apos `journal.save_entry()`
  - `registrar_falha`: `except` fatal
- `AIReflection`
  - `registrar_heartbeat`: topo do `while True`
  - `registrar_gravacao`: apos `journal.save_entry()`
  - `registrar_falha`: `except` fatal
- `RLDiary`
  - `registrar_heartbeat`: topo do `while True`
  - `registrar_gravacao`: apos `save_diary_feedback()`
  - `registrar_falha`: `except` fatal
- `MacroGuardian`
  - `registrar_heartbeat`: topo do `while True`
  - `registrar_gravacao`: apos feedback `CRITICAL`
  - `registrar_falha`: `except` fatal
- `DiarioExecucao`
  - `registrar_heartbeat`: topo do `while True`
  - `registrar_gravacao`: nao se aplica
    (`APENAS_HEARTBEAT`)
  - `registrar_falha`: `except` fatal

#### Exportacao JSON atomica no loop principal

```python
# A cada 60s, apos exibir_painel_terminal():
print(_painel_obs.exibir_painel_terminal())
_painel_obs.exportar_snapshot_json()
```

---

## 5. Impacto Arquitetural

- **ADR-001:** aderente — persistencia em SQLite separado (`trading_diarios.db`),
  aplicacao desacoplada da infraestrutura.
- **Retrocompatibilidade:** preservada — `registrar_gravacao` com nomes
  legados ainda funciona via fallback silencioso.
- **Fail-open:** mantido — falha de I/O no SQLite ou no JSON nao derruba
  a thread.

---

## 6. Evidencias Tecnicas

- `get_errors` em `diario_observability_panel.py`
  - **Resultado:** `No errors found`
- `get_errors` em `start_journals_full_display.py`
  - **Resultado:** `No errors found`
- `py_compile diario_observability_panel.py`
  - **Resultado:** `PY_COMPILE_OK`
- `py_compile start_journals_full_display.py`
  - **Resultado:** `PY_COMPILE_OK`
- `pytest test_diario_observability_panel_estendido.py -q`
  - **Resultado:** `39 passed in 1.79s`
- `pytest` legado + regressao dos diarios
  - **Resultado:** `71 passed in 6.61s`
- validacao runtime do snapshot
  - **Resultado:** `THREADS=5 / JSON_OK=True`
- `mypy` nos modulos tocados
  - **Ressalva:** divida tecnica preexistente em
    `mt5_adapter.py` e `schema.py`

> O ambiente foi provisionado e os testes relevantes da entrega passaram.
> A unica ressalva aberta e de tipagem estrita em modulos antigos fora do
> escopo desta feature.

---

## 7. Matriz de Impacto nos 5 Launchers

- `INICIAR_DIARIOS.bat`
  - **Impacto:** `ALTO`
  - **Tipo:** `DIRETO`
  - **Acao:** painel canonico funcional
- `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`
  - **Impacto:** `NENHUM`
  - **Tipo:** `SEM IMPACTO`
  - **Acao:** nenhuma
- `INICIAR_AGENTE_RL_5000.bat`
  - **Impacto:** `NENHUM`
  - **Tipo:** `SEM IMPACTO`
  - **Acao:** nenhuma
- `INICIAR_AGENTE_RL_DIRETO.bat`
  - **Impacto:** `NENHUM`
  - **Tipo:** `SEM IMPACTO`
  - **Acao:** nenhuma
- `INICIAR_MONITOR_QUANTICO.bat`
  - **Impacto:** `NENHUM`
  - **Tipo:** `SEM IMPACTO`
  - **Acao:** nenhuma

---

## 8. Arquivos Modificados

```text
src/application/diario_observability_panel.py
scripts/start_journals_full_display.py
```

---

## 9. Riscos Residuais

- `mypy --strict` ainda acusa divida tecnica preexistente em
  `src/infrastructure/adapters/mt5_adapter.py` e
  `src/infrastructure/database/schema.py`. Nao foi introduzida por esta
  entrega e permanece fora do escopo imediato do launcher de diarios.
- Contrato de eventos `HEARTBEAT` e `ALERTA` em
  `docs/MODELAGEM_DE_DADOS.md` ainda pendente de formalizacao documental
  (fora do escopo desta tarefa).

---

## 10. Definition of Ready para Project Manager

- [x] documentacao consolidada como entrega final
- [x] decisao tecnica registrada
- [x] impacto arquitetural documentado
- [x] backlog sinalizado corretamente
- [x] evidencia fresca de `py_compile` (PY_COMPILE_OK)
- [x] evidencia de `get_errors` (No errors found)
- [x] integracao operacional completa no launcher (5 threads)
- [x] observabilidade humana final adequada (painel com 5 threads canonicas)
- [x] evidencia fresca de `pytest` relevante (71/71 PASSING)
- [ ] limpeza da divida global de `mypy` (fora do escopo desta entrega)

---

## 11. Recomendacao

### Aprovar para commit e push para `main`

A unica ressalva remanescente e a divida global de `mypy` em modulos
antigos fora do escopo imediato desta entrega. O valor operacional
comprometido com o PO foi integralmente entregue: o painel reflete as
5 threads canonicas em runtime com rastreamento de heartbeat,
gravacoes, reinicializacoes e exportacao JSON.
