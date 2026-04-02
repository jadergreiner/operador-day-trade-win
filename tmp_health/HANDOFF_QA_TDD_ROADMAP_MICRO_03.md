# HANDOFF DE QA/TDD PARA SOFTWARE ENGINEER

## 1. Identificacao

- **id_demanda:** `ROADMAP-MICRO-03`
- **titulo:** Resultado DESCONHECIDO — eliminar do vocabulario operacional
- **estado_qa_tdd:** `QA_TDD_APROVADO_COM_RISCO_CONTROLADO`
- **prioridade:** ALTA
- **data:** 02/04/2026

---

## 2. Leitura de QA do Problema

- **problema a validar:** Fechamentos persistidos com `resultado IS NULL` em
  `HistoricoFechamento` alimentam sinal ruido nos modulos AC5.9/AC6.7/AC6.8.
  O pipeline de reconciliacao em `src/application/reconciliadores/` existe como
  skeleton, mas com **interfaces divergentes** do contrato especificado pelo
  arquiteto. A reconciliacao deve classificar `WIN/LOSS/BREAKEVEN` usando
  `pnl_pct`, com fallback ao MT5 quando o dado local nao estiver disponivel,
  respeitando isolamento por `magic_number`.
- **objetivo verificavel:** Zero registros com `resultado IS NULL` apos
  reconciliacao de sessao completa para qualquer `agent_id` e `magic_number`
  validos.
- **contexto considerado:**
  - Os 3 skeletons em `reconciliadores/` existem e **29 testes passam** — mas
    esses testes cobrem a interface *atual* dos skeletons, nao a interface
    *requerida* pelo arquiteto.
  - `HistoricoFechamento` (linha 102 de `motor_decisao_isolado.py`) nao tem
    campo `resultado` — este e o primeiro gap a fechar.
  - `ITradeRepository` nao tem `atualizar_resultado_fechamento()` — extensao
    necessaria.
  - `MT5Adapter` nao tem `obter_pnl_fechado()` publico — apenas
    `obter_preco_saida_por_ticket()` (retorna preco, nao profit).
  - `reconciliadores/` nao tem `__init__.py`.
  - `OutcomeType` e `BREAKEVEN_THRESHOLD_PCT = 0.05` ja existem em
    `p1_learning_closure.py` linha 208 — **devem ser importados, nao
    duplicados**.
- **suposicoes adotadas:**
  - Os 29 testes existentes nos skeletons *nao precisam ser deletados* — devem
    continuar passando se a interface antiga for mantida ou evoluida com
    compatibilidade. Se a interface mudar de forma incompativel, os testes
    antigos devem ser atualizados junto com a implementacao.
  - O motor reporta 25 testes (nao 24 como o handoff menciona) — todos devem
    seguir passando apos adicao do campo `resultado`.

---

## 3. Escopo de Validacao

### Inclui

- Campo `resultado: Optional[str] = None` em `HistoricoFechamento`
- `_classificar_resultado(pnl_pct)` com threshold `+/-0.05%` importado de
  `p1_learning_closure.py`
- `detectar_lacunas(agent_id, magic_number, ordens_locais, ordens_mt5)` com
  filtro obrigatorio de `magic_number`
- `detectar_por_db(db_path)` consultando SQLite diretamente
- `reconciliar_ordem(ticket, agent_id)` com fluxo `LOCAL → MT5 → ERRO`
- `gerar_relatorio_sessao(session_id, outputs_path)` gerando JSON valido em
  `outputs/`
- `obter_pnl_fechado(ticket, magic_number)` no `MT5Adapter`
- `atualizar_resultado_fechamento(ticket, resultado, pnl)` na interface
  `ITradeRepository`
- `validar_sincronizacao(session_id, agent_id)` comparando contagem local vs
  MT5 (interface nova)
- `ValidationReport` com `SyncStatus.SINCRONIZADO` / `DIVERGENCIA_CRITICA`
- `reconciliation_log` — tabela nova no SQLite
- `__init__.py` exportando as 3 classes publicas
- Regressao dos 25 testes do motor (campo `resultado` nao pode quebra-los)
- Regressao dos 27 testes de `p1_learning_closure.py`
- Regressao dos 21 testes de `ac5_9_feedback_validator.py`
- Integracao AC5.9: nenhum `DESCONHECIDO` chega ao `validate_feedback_health()`

### Nao inclui

- Mudancas no caminho critico de execucao de ordens (restrito por arquitetura)
- Novo canal de alerta (adiado intencional)
- Configurabilidade do threshold de breakeven (adiada para ROADMAP futuro)
- Estrategia de retry automatico na proxima sessao para tickets ERRO
- Testes de carga ou performance da reconciliacao

---

## 4. Matriz de Rastreabilidade

| Criterio / Contrato / Regra | Teste(s) associado(s) | Evidencia esperada |
|---|---|---|
| `HistoricoFechamento.resultado` e `Optional[str]` | `test_historico_fechamento_criacao_com_resultado_none`, `test_historico_fechamento_com_resultado_win` | Campo existe, aceita `None` e literais `WIN/LOSS/BREAKEVEN`, 25 testes existentes passam |
| `_classificar_resultado(0.03)` → `BREAKEVEN` | `test_classificar_resultado_breakeven_positivo`, `test_classificar_resultado_breakeven_negativo`, `test_classificar_resultado_breakeven_limite_inclusivo` | Retorno literal `"BREAKEVEN"` |
| `_classificar_resultado(0.50)` → `WIN` | `test_classificar_resultado_win` | Retorno literal `"WIN"` |
| `_classificar_resultado(-0.30)` → `LOSS` | `test_classificar_resultado_loss` | Retorno literal `"LOSS"` |
| `detectar_lacunas` filtra por `magic_number` | `test_detectar_lacunas_filtra_por_magic_number`, `test_detectar_lacunas_ignora_ticket_de_outro_agente` | Tickets de outro agente nao aparecem na lista |
| `reconciliar_ordem` usa dado local sem chamar MT5 | `test_reconciliar_usa_local_nao_chama_mt5` | Mock do adapter *nao chamado* |
| `reconciliar_ordem` chama MT5 quando dado local ausente | `test_reconciliar_fallback_mt5_chamado` | Mock do adapter chamado exatamente 1 vez |
| MT5 retorna `None` → `ReconcileStatus.ERRO` sem excecao | `test_reconciliar_mt5_none_registra_erro` | `ReconcileStatus.ERRO`, nenhuma excecao |
| Idempotencia: segundo call para ticket ja preenchido e noop | `test_reconciliar_idempotencia_nao_sobrescreve` | Mock do repository nao chamado no segundo call |
| Isolamento: agent_A nao toca registros de agent_B | `test_reconciliar_rejeita_magic_number_diferente` | `ValueError` com mensagem clara |
| `validar_sincronizacao` → `SINCRONIZADO` contagem igual | `test_validator_sessao_sincronizada` | `SyncStatus.SINCRONIZADO` |
| `validar_sincronizacao` → `DIVERGENCIA_CRITICA` delta > 0 | `test_validator_sessao_divergencia_critica` | `SyncStatus.DIVERGENCIA_CRITICA` |
| `gerar_relatorio_sessao` produz JSON valido em `outputs/` | `test_gerar_relatorio_json_valido` | Arquivo existe, `json.loads()` sem excecao |
| Sessao com zero ordens — relatorio gerado sem erro | `test_relatorio_sessao_vazia` | `n_total=0`, arquivo gerado |
| `obter_pnl_fechado(ticket, magic_number)` retorna `float` | `test_obter_pnl_deals_com_magic_correto` | `float` retornado |
| `obter_pnl_fechado` com `magic_number` errado retorna `None` | `test_obter_pnl_magic_errado_retorna_none` | `None` retornado |
| `atualizar_resultado_fechamento` persiste no SQLite | `test_atualizar_resultado_persiste` | Query confirma valor no banco |

---

## 5. Estrategia de TDD

### Primeiro teste a escrever

```python
# tests/unit/test_motor_decisao_isolado.py — adicionar na classe TestDataClasses
def test_historico_fechamento_resultado_none_por_padrao():
    h = HistoricoFechamento(
        ticket=1001, agent_id="ag_5000", tipo=TipoPosicao.COMPRA,
        preco_entrada=120000.0, preco_saida=120500.0, volume=1.0,
        pnl_reais=25.0, pnl_pct=0.42, motivo=MotivoFechamento.TP,
        duracao_minutos=12.0,
        timestamp_abertura="2026-04-02T09:00:00",
        timestamp_fechamento="2026-04-02T09:12:00",
    )
    assert h.resultado is None  # campo novo, valor padrao
```

Este teste **falha primeiro** porque o campo nao existe. Adiciona-se o campo,
o teste passa — sem quebrar os 25 existentes.

### Sequencia sugerida de testes (ordem de implementacao)

**Grupo 1 — Motor (Fatia 1):** campo `resultado` no dataclass

1. `test_historico_fechamento_resultado_none_por_padrao`
2. `test_historico_fechamento_aceita_resultado_win`
3. `test_historico_fechamento_aceita_resultado_loss`
4. `test_historico_fechamento_aceita_resultado_breakeven`
5. Confirmar regressao: todos os 25 testes existentes passam

**Grupo 2 — MT5 Adapter (Fatia 2):** metodo `obter_pnl_fechado`

6. `test_obter_pnl_fechado_retorna_float_com_magic_correto`
7. `test_obter_pnl_fechado_retorna_none_com_magic_errado`
8. `test_obter_pnl_fechado_retorna_none_quando_deals_vazio`
9. `test_obter_pnl_fechado_trata_excecao_mt5_graciosamente`

**Grupo 3 — Repository (Fatia 2 paralela):** `atualizar_resultado_fechamento`

10. `test_atualizar_resultado_persiste_win_no_sqlite`
11. `test_atualizar_resultado_persiste_loss_no_sqlite`
12. `test_atualizar_resultado_rejeita_valor_invalido`

**Grupo 4 — UnknownResultDetector (Fatia 3):** com filtro de magic_number

13. `test_detectar_lacunas_filtra_por_magic_number`
14. `test_detectar_lacunas_ignora_ticket_de_outro_agente`
15. `test_detectar_lacunas_retorna_vazio_quando_todos_tem_resultado`
16. `test_detectar_por_db_filtra_resultado_null_no_sqlite`
17. `test_detectar_por_db_nao_retorna_posicoes_abertas`
18. `test_detectar_lacunas_agent_id_invalido_levanta_value_error`

**Grupo 5 — TradeOutcomeReconciler (Fatia 4):**
`_classificar_resultado` + fluxo completo

19. `test_classificar_resultado_win` — pnl_pct = +0.50
20. `test_classificar_resultado_loss` — pnl_pct = -0.30
21. `test_classificar_resultado_breakeven_zero` — pnl_pct = 0.0
22. `test_classificar_resultado_breakeven_limite_positivo_inclusivo`
    — pnl_pct = +0.05
23. `test_classificar_resultado_breakeven_limite_negativo_inclusivo`
    — pnl_pct = -0.05
24. `test_classificar_resultado_loss_alem_do_limite` — pnl_pct = -0.0500001
25. `test_reconciliar_usa_local_quando_disponivel`
26. `test_reconciliar_nao_chama_mt5_quando_dado_local_existe`
27. `test_reconciliar_fallback_mt5_sucesso`
28. `test_reconciliar_mt5_none_registra_erro_sem_excecao`
29. `test_reconciliar_idempotencia`
30. `test_reconciliar_rejeita_magic_number_diferente`
31. `test_gerar_relatorio_sessao_json_valido`
32. `test_gerar_relatorio_sessao_vazia`
33. `test_counters_n_desconhecido_e_n_erro_incrementados`

**Grupo 6 — MT5SyncValidator (Fatia 5):** contagem de sessao

34. `test_validar_sessao_sincronizada_delta_zero`
35. `test_validar_sessao_divergencia_critica_delta_positivo`
36. `test_validar_sessao_json_salvo_em_outputs`
37. `test_validar_sessao_vazia_gera_relatorio_sem_erro`

**Grupo 7 — Integracao (Fatia 6)**

38. `test_integracao_ac5_9_nao_recebe_desconhecido`
39. `test_integracao_pipeline_completo_zero_desconhecido`

### Ordem de implementacao guiada por teste

```
[Fatia 1] Adicionar campo → rerun 25 testes existentes (todos passam)
    ↓
[Fatia 2] obter_pnl_fechado + atualizar_resultado_fechamento (Grupos 2 e 3)
    ↓
[Fatia 3] UnknownResultDetector com magic_number (Grupo 4)
    ↓
[Fatia 4] TradeOutcomeReconciler._classificar_resultado + reconciliar_ordem
    (Grupo 5)
    ↓
[Fatia 5] MT5SyncValidator.validar_sincronizacao de sessao (Grupo 6)
    ↓
[Fatia 6] Teste de integracao end-to-end (Grupo 7)
```

### Mocks / stubs / fixtures necessarios

```python
# Adicionar em tests/unit/reconciliadores/conftest.py

@pytest.fixture
def mock_mt5_adapter():
    """Mock do MT5Adapter com obter_pnl_fechado controlavel."""
    adapter = MagicMock()
    adapter.obter_pnl_fechado.return_value = 25.0  # padrao: retorna float
    return adapter


@pytest.fixture
def mock_trade_repository():
    """Mock do ITradeRepository com atualizar_resultado_fechamento."""
    repo = MagicMock(spec=ITradeRepository)
    repo.atualizar_resultado_fechamento.return_value = True
    return repo


@pytest.fixture
def sqlite_em_memoria(tmp_path):
    """Banco SQLite em memoria para testes de detectar_por_db."""
    db = tmp_path / "test_trading.db"
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE historico_fechamentos (
            ticket INTEGER PRIMARY KEY,
            agent_id TEXT NOT NULL,
            magic_number INTEGER NOT NULL,
            resultado TEXT,
            pnl_reais REAL,
            pnl_pct REAL,
            status TEXT DEFAULT 'FECHADA'
        )
    """)
    conn.commit()
    return db, conn


@pytest.fixture
def ordens_agente_5000():
    """Ordens simuladas do agente 5000 (magic_number=234500)."""
    return [
        {"ticket": "1001", "magic_number": 234500,
         "resultado": None, "pnl_pct": 0.42},
        {"ticket": "1002", "magic_number": 234500,
         "resultado": None, "pnl_pct": -0.15},
    ]


@pytest.fixture
def ordens_agente_direto():
    """Ordens do agente direto (magic_number=234600) — nao devem cruzar."""
    return [
        {"ticket": "2001", "magic_number": 234600,
         "resultado": None, "pnl_pct": 0.08},
    ]
```

### Pontos que exigem integracao real

- `test_detectar_por_db_filtra_resultado_null_no_sqlite` — usa
  `sqlite_em_memoria`, sem mock do banco
- `test_atualizar_resultado_persiste_win_no_sqlite` — usa `tmp_path` +
  `sqlite_em_memoria`
- `test_gerar_relatorio_sessao_json_valido` — escreve arquivo real em
  `tmp_path`, valida via `json.load()`
- `test_integracao_pipeline_completo_zero_desconhecido` — exercita o pipeline
  3 etapas de ponta a ponta com banco em memoria e adapter mockado

---

## 6. Cenarios Obrigatorios

### Cenarios felizes

1. **Ticket com dado local completo:** `pnl_reais` e `pnl_pct` presentes →
   `_classificar_resultado()` chamado localmente, MT5 adapter *nunca chamado*,
   resultado escrito no banco.
2. **Ticket sem dado local, MT5 retorna profit:** adapter chamado, profit
   convertido em `pnl_pct`, resultado classificado e escrito.
3. **Sessao com todos os tickets ja com resultado preenchido:**
   `detectar_lacunas()` retorna lista vazia, nenhuma escrita feita, log INFO
   "nenhuma lacuna detectada".
4. **Reconciliacao chamada duas vezes para mesmo ticket:** segundo call detecta
   `resultado NOT NULL`, nenhuma write no banco (noop idempotente).
5. **`validar_sincronizacao` com contagem local == contagem MT5:** retorna
   `SyncStatus.SINCRONIZADO`, JSON gerado corretamente.

### Cenarios de erro

1. **MT5 retorna `None` para ticket:** `ReconcileStatus.ERRO` gravado em
   `reconciliation_log`, log `WARNING` emitido, **nenhuma excecao propagada**,
   reconciliacao dos demais tickets continua.
2. **MT5 levanta excecao de conexao:** excecao capturada dentro do
   reconciliador, ticket registrado como ERRO, mesma garantia de nao
   propagacao.
3. **`magic_number` da ordem nao confere com o do agente chamador:**
   `ValueError` levantado com mensagem descritiva contendo o ticket e os dois
   magic_numbers.
4. **`pnl_pct` calculado como `None`** (preco_entrada zero, divisao por zero):
   tratar como `BREAKEVEN`, registrar em log `DEBUG` com contexto.

### Cenarios de borda

1. **`pnl_pct = -0.05` (exatamente no limite inferior):** deve retornar
   `"BREAKEVEN"` (limite inclusivo — `abs(-0.05) <= 0.05` e `True`).
2. **`pnl_pct = -0.0500001` (um epsilon alem do limite):** deve retornar
   `"LOSS"`.
3. **`pnl_pct = +0.05` (exatamente no limite superior):** deve retornar
   `"BREAKEVEN"`.
4. **Sessao com zero ordens fechadas:** relatorio JSON gerado com `n_total=0`,
   sem erro, `pct_desconhecido_sessao=0.0`.
5. **`history_deals_get` com deals de multiplos agentes:** apenas o deal com
   `magic == magic_number` buscado e considerado; os demais descartados
   silenciosamente.
6. **`preco_entrada=0.0` causaria divisao por zero ao calcular `pnl_pct`:**
   tratar explicitamente, retornar `0.0` como `pnl_pct` e classificar
   `BREAKEVEN`.

### Cenarios de regressao

1. **25 testes de `motor_decisao_isolado.py`:** sem nenhuma quebra apos adicao
   do campo `resultado`. O campo e `Optional` com default `None`, portanto
   todos os construtores existentes funcionam sem mudanca.
2. **27 testes de `p1_learning_closure.py`:** nao podem ser afetados —
   nenhuma mudanca nesse arquivo. Confirmar com
   `pytest tests/unit/test_p1_learning_closure.py -q`.
3. **21 testes de `ac5_9_feedback_validator.py`:** nao podem ser afetados —
   nenhuma mudanca nesse arquivo. Confirmar com
   `pytest tests/unit/test_ac5_9_feedback_validator.py -q`.
4. **29 testes existentes de `reconciliadores/`:** devem continuar passando.
   Se a evolucao das classes mudar interfaces de forma incompativel, os testes
   existentes devem ser atualizados *junto* com a implementacao.

### Cenarios de observabilidade

1. **Reconciliacao via MT5:** log `WARNING` contendo ticket, agent_id e
   source="MT5" emitido.
2. **Ticket permanece ERRO:** log `WARNING` contendo ticket, agent_id e
   motivo emitido.
3. **Relatorio de sessao gerado:** log `INFO` com `n_total`, `n_resolvidos`,
   `n_erro` e `pct_desconhecido_sessao`.
4. **Nenhuma lacuna detectada:** log `INFO`
   "nenhuma lacuna detectada para agent_id=X".
5. **Arquivo `outputs/reconciliacao_YYYYMMDD.json` legivel:** estrutura JSON
   com campos obrigatorios (`session_id`, `agent_id`, `n_total`,
   `n_reconciliados_local`, `n_reconciliados_mt5`, `n_erro`,
   `pct_desconhecido_sessao`, `timestamp_geracao`).

---

## 7. Contratos e Invariantes a Validar

**Contratos logicos:**

- `_classificar_resultado(pnl_pct)` implementa exatamente
  `abs(pnl_pct) <= 0.05 → BREAKEVEN` (importado de
  `p1_learning_closure.EpisodeClosureEngine.BREAKEVEN_THRESHOLD_PCT`). O
  threshold **nao pode ser redefinido como constante local** — importar
  diretamente.
- `detectar_lacunas()` so retorna tickets cujo `magic_number` bate com o
  parametro passado — invariante de isolamento.
- `reconciliar_ordem()` retorna `ReconciliationResult.reconciled = True`
  **apenas quando** a escrita no banco foi confirmada.
- `validar_sincronizacao()` retorna `SyncStatus.SINCRONIZADO` quando
  `abs(contagem_local - contagem_mt5) <= 0` (tolerancia zero por padrao).
- Arquivo JSON gerado por `gerar_relatorio_sessao()` e valido e tem todos os
  campos obrigatorios.

**Invariantes obrigatorios:**

- **Isolamento por magic_number:** nenhuma operacao de leitura ou escrita deve
  cruzar `agent_id` ou `magic_number`.
- **Idempotencia:** reconciliar duas vezes o mesmo ticket nao duplica registros
  em `reconciliation_log` nem altera `resultado` ja preenchido.
- **Fallback seguro:** excecao do MT5 nunca propaga para fora do
  `reconciliar_ordem()` — sempre capturada internamente.
- **Enumeracao fechada:** `resultado` aceita somente `"WIN"`, `"LOSS"`,
  `"BREAKEVEN"` — validacao na camada de persistencia.

**Consistencia / idempotencia:**

- `reconciliation_log` deve ter constraint de unicidade: `(ticket, agent_id)` —
  sem registro duplicado para o mesmo ticket ja reconciliado.

**Tolerancia a falhas:**

- Thread de reconciliacao com timeout de 60s — se ultrapassar, registrar aviso
  e encerrar sem impactar o loop principal. Testar com `asyncio.wait_for`
  (mock de timeout).

**Regras que nao podem quebrar:**

- `ac5_9_feedback_validator.VALID_OUTCOME_TYPES = ("WIN", "LOSS", "BREAKEVEN")`
  — esta tupla nao muda; o reconciliador deve produzir exatamente esses valores.
- `EpisodeClosureEngine.BREAKEVEN_THRESHOLD_PCT = 0.05` — o reconciliador usa
  este valor, nunca duplica.

---

## 8. Dados e Integracoes

**Dados afetados:**

- `HistoricoFechamento` em memoria (dataclass) — adicionar
  `resultado: Optional[str] = None`.
- Tabela `historico_fechamentos` no SQLite — verificar schema antes de
  implementar. **Pendencia P1:** confirmar nome exato da tabela e coluna em
  `src/infrastructure/database/schema.py`.
- Nova tabela `reconciliation_log` — criar via
  `CREATE TABLE IF NOT EXISTS` no `schema.py` ou direto no `detectar_por_db()`.
- Arquivo `outputs/reconciliacao_YYYYMMDD.json` — criado a cada sessao.

**Cenarios de persistencia:**

- `test_atualizar_resultado_win_persiste_em_sqlite_em_memoria`: INSERT de
  fechamento sem resultado, UPDATE via `atualizar_resultado_fechamento()`,
  SELECT confirma valor.
- `test_reconciliation_log_criado_apos_reconciliacao`: tabela existe apos
  primeiro call, registro inserido.

**Cenarios de compatibilidade:**

- Campo `resultado` na tabela SQLite deve ser `TEXT NULL` — compatibilidade
  retroativa com registros antigos sem o campo.
- Se a tabela ja existir sem a coluna, tratar via
  `ALTER TABLE ... ADD COLUMN resultado TEXT NULL`.

**Integracoes a mockar:**

- `MT5Adapter.obter_pnl_fechado()` — nunca chamar MT5 real em testes
  unitarios.
- `ITradeRepository.atualizar_resultado_fechamento()` — nunca escrever no banco
  real em testes unitarios.

**Integracoes a validar ponta a ponta:**

- `test_integracao_pipeline_completo_zero_desconhecido`: usa
  `sqlite_em_memoria` (banco real em `tmp_path`) + adapter mockado. Exercita
  as 3 etapas do pipeline sequencialmente e verifica que nenhum
  `resultado IS NULL` permanece.

---

## 9. Evidencias de Aceite

**Testes minimos esperados:**

| Grupo | Descricao | Qtd testes novos |
|---|---|---|
| 1 | Motor — campo `resultado` | 4 |
| 2 | MT5 Adapter — `obter_pnl_fechado` | 4 |
| 3 | Repository — `atualizar_resultado_fechamento` | 3 |
| 4 | UnknownResultDetector com magic_number | 6 |
| 5 | TradeOutcomeReconciler completo | 15 |
| 6 | MT5SyncValidator — contagem sessao | 4 |
| 7 | Integracao end-to-end | 2 |
| **Total** | | **~38 novos** |

Mais os **29 existentes dos reconciliadores** e os **73 de regressao**
(25+27+21).

**Cobertura esperada:**

- `src/application/reconciliadores/`: minimo 85%, meta 90%
- `src/infrastructure/adapters/mt5_adapter.py` (metodo novo): 100%
- `src/infrastructure/repositories/trade_repository.py` (metodo novo): 100%
- `src/application/motor_decisao_isolado.py`: manter cobertura atual

**Evidencias de contrato:**

```bash
pytest tests/unit/test_motor_decisao_isolado.py -q   # 25+ passed, 0 failed
pytest tests/unit/test_p1_learning_closure.py -q      # 27 passed, 0 failed
pytest tests/unit/test_ac5_9_feedback_validator.py -q # 21 passed, 0 failed
pytest tests/unit/reconciliadores/ -v                 # todos passam
mypy src/application/reconciliadores/ --strict        # sem erros
mypy src/application/motor_decisao_isolado.py --strict # sem erros
```

**Evidencias de observabilidade:**

- `test_gerar_relatorio_sessao_json_valido`: `json.load(arquivo)` nao levanta
  excecao, campos obrigatorios presentes.
- `test_log_warning_emitido_para_fallback_mt5`: `caplog.records` contem
  mensagem de nivel WARNING com ticket e source="MT5".
- `test_metrica_pct_desconhecido_zero_apos_reconciliacao`: campo calculado no
  relatorio == 0.0.

**Evidencias de nao regressao:**

```bash
pytest tests/unit/test_motor_decisao_isolado.py \
       tests/unit/test_p1_learning_closure.py \
       tests/unit/test_ac5_9_feedback_validator.py \
       -q --tb=short
# Resultado esperado: 73 passed (25+27+21)
```

---

## 10. Riscos de Qualidade

**Riscos principais:**

1. **Conflito de nomes de arquivo:** `src/application/trade_outcome_reconciler.py`
   (AC5.8) vs `src/application/reconciliadores/trade_outcome_reconciler.py`
   (ROADMAP-MICRO-03). Todo import deve usar path completo.
   - **Mitigacao:** Verificar que `from src.application.reconciliadores...`
     nunca e confundido com `from src.application.trade_outcome_reconciler...`.

2. **Threshold duplicado:** Se o implementador definir
   `BREAKEVEN_THRESHOLD = 0.05` localmente, divergencia futura sera silenciosa.
   - **Mitigacao:** `test_threshold_importado_de_p1_learning_closure` —
     verifica que o valor usado pelo reconciliador e identico ao de
     `EpisodeClosureEngine.BREAKEVEN_THRESHOLD_PCT`.

3. **Interface dos skeletons divergente:** Os 29 testes existentes testam a
   interface *atual* dos skeletons (sem `magic_number`, sem
   `_classificar_resultado`). Se a implementacao mudar as assinaturas, os
   testes existentes devem ser atualizados *junto* — nunca separado.

4. **Schema da tabela de fechamentos desconhecido:** O `schema.py` usa
   SQLAlchemy com `TradeModel`, mas o `MotorDecisaoIsolado` pode persistir em
   JSON em `outputs/`, nao no SQLite via ORM. Verificar antes de implementar
   o write-back.
   - **Mitigacao:** Pendencias P1 e P2 devem ser resolvidas antes da Fatia 4.

5. **Sem `__init__.py` no package:** imports falharao sem esse arquivo. E o
   primeiro arquivo a criar antes de qualquer teste.

**Pontos sensiveis:**

- `obter_pnl_fechado()` deve retornar `profit` do deal (nao `price`). O deal
  no MT5 tem campo `profit` acessivel via `getattr(deal, "profit", None)`.
- `reconciliation_log` precisa de constraint de unicidade para garantir
  idempotencia — sem ela, segundo call insere duplicata.

**Lacunas conhecidas:**

- Testes de timeout (60s) considerados fora do escopo minimo desta entrega.
- Retry com backoff no SQLite WAL nao tem testes especificos.

---

## 11. Instrucoes para Implementacao

### Comportamento a implementar primeiro

`HistoricoFechamento.resultado: Optional[str] = None` — uma linha. Confirmar
com 25 (+1 novo) testes passando antes de avancar.

### Restricoes que o codigo deve respeitar

1. **Threshold de breakeven nao pode ser constante local.** Usar:
   ```python
   from src.application.p1_learning_closure import EpisodeClosureEngine
   BREAKEVEN_THRESHOLD = EpisodeClosureEngine.BREAKEVEN_THRESHOLD_PCT
   ```

2. **Adapter MT5 e chamado somente via `mt5_adapter.obter_pnl_fechado()`.**
   Proibido chamar `MetaTrader5` diretamente na camada de aplicacao.

3. **Escrita no banco somente via
   `ITradeRepository.atualizar_resultado_fechamento()`.**
   Proibido acesso direto ao SQLite na camada de aplicacao.

4. **Filtro por `magic_number` e obrigatorio em todo metodo que toca ordens.**

5. **`resultado` so aceita os literais `"WIN"`, `"LOSS"`, `"BREAKEVEN"`.**
   Qualquer outro valor e erro de programacao — lancar `ValueError`.

### Testes que devem nascer antes do codigo (por fatia)

- **Fatia 1:** `test_historico_fechamento_resultado_none_por_padrao`
- **Fatia 2:** `test_obter_pnl_fechado_retorna_float_com_magic_correto`,
  `test_atualizar_resultado_persiste_win_no_sqlite`
- **Fatia 3:** `test_detectar_lacunas_filtra_por_magic_number`
- **Fatia 4:** `test_classificar_resultado_win`, `..._loss`,
  `..._breakeven_*` (6 testes), `test_reconciliar_nao_chama_mt5_...`
- **Fatia 5:** `test_validar_sessao_sincronizada_delta_zero`
- **Fatia 6:** `test_integracao_pipeline_completo_zero_desconhecido`

### Pontos que exigem cuidado especial

- **Compatibilidade retroativa do dataclass:** `HistoricoFechamento` e um
  `@dataclass` sem `kw_only`. O novo campo `resultado: Optional[str] = None`
  **deve ser o ultimo** na definicao ou usar `field(default=None)` para evitar
  `non-default argument follows default argument`.
- **`__init__.py` do package** deve exportar:
  `UnknownResultDetector`, `TradeOutcomeReconciler`, `MT5SyncValidator`,
  `ReconcileStatus`, `SyncStatus`, `ReconciliationResult`, `ValidationReport`.
- **`obter_pnl_fechado` vs `obter_preco_saida_por_ticket`:** o metodo existente
  retorna *preco de saida*. O novo deve retornar *profit* diretamente do campo
  `profit` do deal — logicas distintas, nao reutilizar o retorno do existente.

### Sinais de que a implementacao esta incorreta

- `mypy --strict` reporta erros em `reconciliadores/`
- Qualquer teste de regressao (25+27+21) falha
- `_classificar_resultado(0.05)` nao retorna `"BREAKEVEN"`
- Mock do adapter e chamado quando `pnl_pct` local esta disponivel
- `reconciliation_log` tem registros duplicados para o mesmo ticket

---

## 12. Pendencias para Implementacao

1. **P1 (critica):** Confirmar nome exato da tabela que armazena registros de
   `HistoricoFechamento` no SQLite. O `schema.py` tem `TradeModel` mas nao uma
   tabela `historico_fechamentos`. O `MotorDecisaoIsolado` persiste via JSON em
   `outputs/` — verificar se ha tabela dedicada ou se `atualizar_resultado_fechamento()`
   precisa tratar arquivo JSON em vez de SQLite.
2. **P2 (critica):** Confirmar se `ITradeRepository` sera estendida ou se sera
   criado um `IFechamentoRepository` dedicado. O `ITradeRepository` atual lida
   com `Trade` (entidade de dominio), nao com `HistoricoFechamento`.
   Possivelmente necessario um repository separado.
3. **P3 (media):** Decidir se `BREAKEVEN_THRESHOLD` sera importado de
   `p1_learning_closure.EpisodeClosureEngine` ou extraido para
   `src/domain/constants.py`. Recomendacao: importacao direta por ora.
4. **P4 (media):** Verificar acesso ao campo `profit` e `magic` nos deals
   retornados por `history_deals_get`. Confirmar:
   `getattr(deal, "profit", None)` e `getattr(deal, "magic", 0)` funcionam
   com a versao do MT5 em uso.
5. **P5 (baixa):** `reconciliation_log` deve ter
   `CREATE TABLE IF NOT EXISTS` para nao falhar se ja existir. Decidir se sera
   criada em `schema.py` (SQLAlchemy) ou diretamente no `detectar_por_db`
   (sqlite3 raw).

---

## 13. Definition of Ready para Software Engineer

- [x] Criterios verificaveis explicitados — 17 combinacoes de
      contrato/teste/evidencia na matriz de rastreabilidade
- [x] Cenarios obrigatorios listados — 5 felizes, 4 erro, 6 borda, 4
      regressao, 5 observabilidade
- [x] Contratos e invariantes mapeados — threshold de breakeven, enumeracao
      fechada, isolamento por magic_number, idempotencia
- [x] Mocks/stubs/fixtures identificados — `mock_mt5_adapter`,
      `mock_trade_repository`, `sqlite_em_memoria`, `ordens_agente_5000`,
      `ordens_agente_direto`
- [x] Evidencias de aceite definidas — 73 testes de regressao + ~38 testes
      novos, cobertura 85%+, mypy --strict limpo, JSON valido
- [x] Riscos de regressao registrados — conflito de nomes de arquivo,
      threshold duplicado, interface divergente dos skeletons
- [x] Sequencia de TDD definida — 7 grupos, 39 testes em ordem de dependencia
- [x] Pendencias bloqueantes identificadas — P1 e P2 sao criticas e devem ser
      resolvidas antes da Fatia 4

---

> **Risco controlado registrado:** P1 e P2 (schema de persistencia de
> `HistoricoFechamento`) estao abertas. Fatias 1-3 podem ser implementadas sem
> depender delas. Fatia 4 em diante **requer** que P1 e P2 estejam resolvidas.
> O Software Engineer deve confirmar o mecanismo de persistencia antes de
> escrever os testes de write-back.
