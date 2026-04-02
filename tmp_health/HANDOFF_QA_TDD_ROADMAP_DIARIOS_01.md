# HANDOFF DE QA/TDD PARA SOFTWARE ENGINEER

## 1. Identificacao

| Campo | Valor |
|---|---|
| `id_demanda` | PO-2026-04-02-ROADMAP-DIARIOS-01 |
| `titulo` | Watchdog de threads e observabilidade dos diarios |
| `estado_qa_tdd` | QA_TDD_APROVADO_COM_RISCO_CONTROLADO |
| `prioridade` | ALTA |
| `data` | 02/04/2026 |
| `executor_primario` | INICIAR_DIARIOS.bat |
| `bloqueado_por` | BUG-DIARIOS-01 DONE (18/03) — prerequisito ja entregue |

---

## 2. Leitura de QA do Problema

**Problema a validar:**
O `INICIAR_DIARIOS.bat` ja conta com `ThreadWatchdog` (21 testes, producao)
que reinicia threads mortas. O problema seguinte e de **observabilidade**:
o operador nao consegue ver em tempo real o estado de cada diario
(rodando/pausado/com_erro), nao sabe ha quanto tempo cada um nao grava,
e eventos de falha/restart nao sao persistidos no SQLite para auditoria.

**Objetivo verificavel:**
Ao final desta entrega, o operador que olha o terminal ve um painel
atualizado a cada 60s com o estado de cada thread de diario, alerta de
inatividade apos 20 min sem gravacao, e o banco SQLite contem historico de
eventos de cada sessao consultavel.

**Contexto considerado:**

- `ThreadWatchdog` (ciclo de vida das threads) ja existe e funciona —
  **nao deve ser substituido**
- `ObservabilidadeDiarios` ja existe com 4 nomes logicos
  (`MICRO_TENDENCIA`, `RL_5000`, `RL_DIRETO`, `DIARIOS`) —
  **mismatch confirmado em codigo** com os 5 nomes reais do launcher
  (`TradingJournal`, `AIReflection`, `RLDiary`, `MacroGuardian`,
  `DiarioExecucao`)
- `thread_watchdog_advanced.py` existe com API deterministica
  `monitor_once()` — segundo o SA, deve ser **absorvido como padrao de
  testabilidade**, nao substituir o watchdog atual
- Tabela `diarios_watchdog_eventos` **nao existe** (grep confirmou 0 matches)
- ADR-001: SQLite como persistencia primaria — **obrigatorio**
- Falha do SQLite deve acionar **fail-open** (warning + fallback em
  memoria, nunca crash)
- Codigo 100% PT-BR, type hints 100%, mypy --strict

**Suposicoes adotadas:**

1. O conjunto canonico monitorado sera **5 threads** (4 primarios +
   MacroGuardian como auxiliar + DiarioExecucao com heartbeat apenas),
   nao 4 — especificado na secao de contratos abaixo
2. O painel existente (`ObservabilidadeDiarios`) sera **estendido**,
   nao reescrito — a classe deve receber novos metodos e adaptar a logica
   de nomes
3. O `registrar_heartbeat()` e distinto de `registrar_gravacao()` —
   heartbeat indica "thread viva", gravacao indica "dados persistidos no
   banco do diario"

---

## 3. Escopo de Validacao

### Inclui

- Mapeamento canonico de nomes logicos para nomes reais de threads
  (5 threads)
- Novos contratos: `registrar_heartbeat()`, `registrar_falha()`,
  `gerar_snapshot_operacional()`
- Maquina de estados operacionais:
  `rodando` / `pausado` / `com_erro` / `reiniciando`
- Thresholds por thread (5min, 10min, 15min, 20min cadencias diferentes)
- Alerta de inatividade: apenas dentro da janela operacional E apos 20 min
  sem gravacao
- Persistencia SQLite em `diarios_watchdog_eventos` com `session_id`
- Exportacao JSON atomica em
  `outputs/diarios/diarios_status_latest.json`
- Fail-open: SQLite indisponivel → log WARNING → continua em memoria
- Painel atualizado a cada 60s (nao bloqueante)
- Isolamento: falha em uma thread nao bloqueia painel das demais
- Regressao: `INICIAR_DIARIOS.bat` continua inicializando sem degradacao

### Nao inclui

- Refatoracao da logica interna de `ThreadWatchdog` (fora de escopo)
- Substituicao de `thread_watchdog_advanced.py` (manter como esta)
- Interface web / dashboard HTTP (nao solicitado nesta entrega)
- Mudanca nos scripts de diario individuais
  (TradingJournal, AIReflection etc)
- Migracao de dados historicos (tabela e nova, nao ha dados previos)
- Integracao com sistema de alertas externo (email/telegram)

---

## 4. Matriz de Rastreabilidade

| Criterio / Contrato / Regra | Teste(s) associado(s) | Evidencia esperada |
|---|---|---|
| 5 threads monitoradas com nomes canonicos | `test_mapeamento_canonico_5_threads` | dict com 5 entradas, nomes corretos |
| `registrar_heartbeat()` atualiza timestamp sem incrementar contador | `test_heartbeat_nao_incrementa_contador_gravacao` | `total_registros` invariante, `ultimo_heartbeat` novo |
| `registrar_gravacao()` incrementa contador E atualiza timestamp | `test_gravacao_incrementa_e_atualiza` | `total_registros += 1`, `ultimo_registro` novo |
| `registrar_falha()` muda estado para `com_erro` sem afetar outras threads | `test_falha_isolada_nao_contamina_painel` | estado `com_erro` apenas na thread afetada |
| Estado inicial e `rodando` apos primeiro heartbeat | `test_estado_inicial_rodando_apos_heartbeat` | `estado == "rodando"` |
| Transicao `rodando` para `pausado` apos N min sem heartbeat | `test_transicao_rodando_para_pausado` | threshold por thread respeitado |
| Transicao `com_erro` para `reiniciando` quando watchdog dispara | `test_transicao_erro_para_reiniciando` | evento gravado no SQLite |
| Alerta de inatividade apenas dentro da janela operacional | `test_alerta_ignorado_fora_da_janela` | lista de alertas vazia fora do pregao |
| Alerta gerado apos 20 min sem gravacao dentro da janela | `test_alerta_apos_20_min_sem_gravacao` | lista com nome da thread em alerta |
| Painel contem estado de todas as 5 threads | `test_painel_exibe_5_threads` | string do painel contem os 5 nomes |
| SQLite: evento gravado a cada `registrar_gravacao()` | `test_evento_gravado_no_sqlite` | 1 linha em `diarios_watchdog_eventos` |
| SQLite: evento gravado a cada `registrar_falha()` | `test_falha_gravada_no_sqlite` | linha com `evento='FALHA'`, stack_trace preenchido |
| SQLite indisponivel → fail-open → warning logado | `test_fail_open_sqlite_indisponivel` | sem excecao, WARNING no log |
| `session_id` separa eventos de sessoes diferentes | `test_session_id_isola_eventos` | query por session_id retorna so eventos da sessao |
| JSON exportado de forma atomica | `test_exportacao_json_atomica` | arquivo existe, JSON valido, campos obrigatorios |
| Painel nao bloqueia quando thread esta morta | `test_painel_nao_bloqueia_thread_morta` | painel renderiza em < 1s mesmo com `com_erro` |
| Regressao: 21 testes do BUG-DIARIOS-01 continuam passando | suite `test_diarios_watchdog.py` | 21/21 PASSING |

---

## 5. Estrategia de TDD

### Primeiro teste a escrever

```python
def test_mapeamento_canonico_5_threads_existe():
    """O modulo define mapeamento canonico de nomes logicos para threads reais."""
    from src.application.diario_observability_panel import (
        MAPEAMENTO_THREADS_CANONICO,
    )
    assert len(MAPEAMENTO_THREADS_CANONICO) == 5
    assert "TradingJournal" in MAPEAMENTO_THREADS_CANONICO
    assert "DiarioExecucao" in MAPEAMENTO_THREADS_CANONICO
```

Este teste falha primeiro porque `MAPEAMENTO_THREADS_CANONICO` nao existe.
A implementacao comeca por ele — todos os contratos dependem do mapeamento.

### Sequencia sugerida de testes (ordem de implementacao)

```
Fase 1 — Mapeamento e contratos de dados (dataclasses)
  1. test_mapeamento_canonico_5_threads_existe
  2. test_evento_observabilidade_campos_obrigatorios
  3. test_snapshot_saude_campos_obrigatorios
  4. test_config_threshold_por_thread

Fase 2 — Contratos de metodos (sem persistencia)
  5. test_heartbeat_nao_incrementa_contador_gravacao
  6. test_gravacao_incrementa_e_atualiza
  7. test_falha_muda_estado_para_com_erro
  8. test_falha_isolada_nao_contamina_painel
  9. test_snapshot_contem_todas_as_threads

Fase 3 — Maquina de estados
  10. test_estado_inicial_none_antes_primeiro_heartbeat
  11. test_estado_inicial_rodando_apos_heartbeat
  12. test_transicao_rodando_para_pausado_por_threshold
  13. test_transicao_rodando_para_com_erro_por_falha
  14. test_transicao_com_erro_para_reiniciando
  15. test_transicao_reiniciando_para_rodando_sucesso
  16. test_alerta_nao_disparado_em_transicoes_repetidas

Fase 4 — Persistencia SQLite
  17. test_tabela_criada_na_inicializacao
  18. test_evento_gravado_no_sqlite_apos_gravacao
  19. test_falha_gravada_com_stack_trace_no_sqlite
  20. test_session_id_isola_eventos
  21. test_fail_open_sqlite_indisponivel

Fase 5 — Alertas e janela operacional
  22. test_alerta_ignorado_fora_da_janela_operacional
  23. test_alerta_apos_20_min_sem_gravacao_dentro_janela
  24. test_sem_alerta_quando_heartbeat_recente

Fase 6 — Painel e exportacao
  25. test_painel_exibe_5_threads_com_estado
  26. test_painel_nao_bloqueia_thread_morta
  27. test_exportacao_json_atomica_campos_obrigatorios
  28. test_exportacao_json_sobrescreve_sem_corromper

Fase 7 — Regressao
  29. Rodar suite completa de test_diarios_watchdog.py (21 testes)
  30. Rodar suite de test_diario_observability_panel.py
```

### Mocks / stubs / fixtures necessarios

| Dependencia | Tecnica | Justificativa |
|---|---|---|
| `datetime.now()` | `unittest.mock.patch` ou `freezegun` | Controlar clock para thresholds sem esperar tempo real |
| `time.sleep()` | `unittest.mock.patch` | Impedir bloqueio real em testes do loop de 60s |
| Banco SQLite | `tmp_path` do pytest | Isolamento entre testes, sem estado residual |
| Arquivo JSON de exportacao | `tmp_path` | Evitar gravacao em `outputs/` real durante testes |
| `logging` | `caplog` do pytest | Verificar WARNING emitido no fail-open |
| `ThreadWatchdog.gerar_relatorio_saude()` | mock/stub | Simular estado sem iniciar threads reais |

### Pontos que exigem integracao real

- Verificar que `INICIAR_DIARIOS.bat` ainda inicia sem erro apos as
  mudancas — rodar `start_journals_full_display.py` em modo dry-run
- 1 teste de integracao leve com thread real que lanca excecao para
  verificar comportamento do painel com falha real

---

## 6. Cenarios Obrigatorios

### Cenarios felizes

1. **TradingJournal grava a cada 5 min**: `registrar_gravacao("TradingJournal")`
   chamado 3 vezes em 15 min simulados → `total_registros == 3`,
   `ultimo_registro` atualizado, estado `rodando`, 3 eventos no SQLite

2. **DiarioExecucao emite apenas heartbeat**:
   `registrar_heartbeat("DiarioExecucao")` chamado → `total_registros == 0`
   (nao e gravacao), `ultimo_heartbeat` atualizado, estado `rodando`

3. **Painel renderiza todas as 5 threads**:
   `gerar_snapshot_operacional()` apos registros em todas as threads →
   dict com 5 chaves, cada uma com estado, ultimo_registro, total_registros

4. **Exportacao JSON**: snapshot gerado → arquivo
   `diarios_status_latest.json` valido, JSON-parseable, contem `session_id`

5. **Session_id separa sessoes**: dois paineis com session_ids diferentes →
   eventos SQLite de cada um consultaveis de forma independente

6. **Painel atualizado sem bloqueio**: thread morta com estado `com_erro`
   presente → painel renderizado em < 1s, outros estados exibidos
   corretamente

### Cenarios de erro

1. **Thread falha com exception**:
   `registrar_falha("RLDiary", ValueError("conexao"), "stack...")` →
   estado `com_erro`, stack_trace persistido no SQLite,
   `total_registros` inalterado, outras threads intactas

2. **SQLite indisponivel**: inicializar painel com caminho de banco invalido
   → sem exception levantada, WARNING logado, operacoes continuam em
   memoria (fail-open)

3. **Thread inexistente**: `registrar_gravacao("NomeInvalido")` →
   `ValueError` com mensagem clara em PT-BR

4. **Stack trace nulo na falha**:
   `registrar_falha("TradingJournal", RuntimeError("x"), None)` →
   aceito sem erro, campo `stack_trace` gravado como `None` no SQLite

5. **Exportacao com banco indisponivel**: `_exportar_snapshot_json()`
   quando SQLite indisponivel → usa estado em memoria, arquivo JSON gerado
   com `"fonte": "memoria"` no metadata

### Cenarios de borda

1. **Heartbeat apos gravacao**: thread recebe `registrar_heartbeat()` depois
   de `registrar_gravacao()` → `total_registros` nao e alterado pelo
   heartbeat posterior

2. **Threshold diferente por thread**: AIReflection tem cadencia 10min →
   alerta deve disparar apos 20 min sem gravacao (nao apos 10 min),
   pois threshold_alerta e 20 min para todas

3. **Gravacao imediatamente antes do threshold**: thread sem gravacao por
   19m59s → nenhum alerta; 1 gravacao → OK; apos mais 20 min sem gravar
   → alerta (testar com time mock)

4. **Alerta nao duplicado**: thread em alerta → painel renderizado 3 vezes
   consecutivas → alerta aparece uma vez por consulta

5. **Ciclo completo de restart**: `registrar_falha()` → `com_erro` →
   watchdog chama `registrar_reinicio()` → `reiniciando` →
   `registrar_heartbeat()` → `rodando`; evento de cada transicao no SQLite

6. **Estado inicial antes do primeiro sinal**: thread registrada mas sem
   nenhum sinal → estado deve ser `None` ou `"aguardando_sinal"`,
   nao `"rodando"`

### Cenarios de regressao

1. `pytest tests/unit/test_diarios_watchdog.py` → **21/21 PASSING**

2. `pytest tests/unit/test_diario_observability_panel.py` →
   **100% PASSING**

3. `python -c "import scripts.start_journals_full_display"` →
   sem ImportError

4. `pytest tests/unit/test_diarios_health_monitor.py` → **100% PASSING**

### Cenarios de observabilidade

1. **Alerta logado com contexto**: `logging.WARNING` deve conter nome da
   thread, ultimo timestamp de gravacao e minutos desde a ultima gravacao

2. **Evento SQLite consultavel**: apos `registrar_falha()`,
   `SELECT * FROM diarios_watchdog_eventos WHERE evento='FALHA'` retorna
   a linha com todos os campos preenchidos

3. **JSON exportado com todos os campos do contrato**: `session_id`,
   `timestamp_exportacao`, por thread: `nome`, `estado`,
   `total_registros_sessao`, `ultimo_registro`, `em_alerta`,
   `restarts_sessao`

---

## 7. Contratos e Invariantes a Validar

### Contratos logicos

**Mapeamento canonico (unica fonte de verdade):**

```python
MAPEAMENTO_THREADS_CANONICO: dict[str, ConfiguracaoMonitoramento] = {
    "TradingJournal": ConfiguracaoMonitoramento(
        nome_logico="TRADING_JOURNAL",
        cadencia_min=5,
        threshold_alerta_min=20,
        tipo_monitoramento="GRAVACAO_E_HEARTBEAT",
    ),
    "AIReflection": ConfiguracaoMonitoramento(
        nome_logico="AI_REFLECTION",
        cadencia_min=10,
        threshold_alerta_min=20,
        tipo_monitoramento="GRAVACAO_E_HEARTBEAT",
    ),
    "RLDiary": ConfiguracaoMonitoramento(
        nome_logico="RL_PERFORMANCE",
        cadencia_min=15,
        threshold_alerta_min=20,
        tipo_monitoramento="GRAVACAO_E_HEARTBEAT",
    ),
    "MacroGuardian": ConfiguracaoMonitoramento(
        nome_logico="MACRO_GUARDIAN",
        cadencia_min=0,
        threshold_alerta_min=20,
        tipo_monitoramento="GRAVACAO_E_HEARTBEAT",
    ),
    "DiarioExecucao": ConfiguracaoMonitoramento(
        nome_logico="DIARIO_EXECUCAO",
        cadencia_min=0,
        threshold_alerta_min=20,
        tipo_monitoramento="APENAS_HEARTBEAT",
    ),
}
```

**`EventoObservabilidadeDiario` (dataclass frozen):**

```python
@dataclass(frozen=True)
class EventoObservabilidadeDiario:
    session_id: str
    nome_thread: str
    evento: str  # GRAVACAO | HEARTBEAT | FALHA | REINICIO | ALERTA
    estado_resultante: str  # rodando | pausado | com_erro | reiniciando
    mensagem: Optional[str]
    stack_trace: Optional[str]
    gravacoes_sessao: int
    timestamp: datetime
```

**`SnapshotSaudeDiario` (dataclass):**

```python
@dataclass
class SnapshotSaudeDiario:
    session_id: str
    timestamp_exportacao: datetime
    threads: dict[str, StatusDiarioEstendido]

@dataclass
class StatusDiarioEstendido:
    nome_thread: str
    nome_logico: str
    estado: Optional[str]  # rodando/pausado/com_erro/reiniciando/None
    ultimo_registro: Optional[datetime]
    ultimo_heartbeat: Optional[datetime]
    total_registros_sessao: int
    restarts_sessao: int
    em_alerta: bool
    minutos_sem_gravacao: Optional[float]
```

### Invariantes obrigatorios

- `total_registros_sessao` apenas incrementa — nunca decrementa
- `registrar_heartbeat()` nao altera `total_registros_sessao` nem
  `ultimo_registro`
- `registrar_gravacao()` sempre altera `ultimo_registro` e
  `total_registros_sessao`
- Estado `com_erro` nao pode ir diretamente para `rodando` sem passar
  por `reiniciando`
- Alerta de inatividade so gerado para
  `tipo_monitoramento == "GRAVACAO_E_HEARTBEAT"`
- `DiarioExecucao` nunca gera alerta de inatividade
- Eventos SQLite sao append-only — nenhum DELETE, nenhum UPDATE

### Consistencia / idempotencia

- Multiplos `registrar_heartbeat()` seguidos: estado permanece `rodando`,
  nenhum evento duplicado no SQLite
- `registrar_falha()` chamado duas vezes consecutivas: dois eventos no
  SQLite, estado permanece `com_erro`
- Exportacao JSON: sobrescreve o arquivo existente de forma atomica
  (write em `.tmp` → rename), nao corrompivel por crash

### Tolerancia a falhas

- Thread A em `com_erro` → painel mostra thread A com erro,
  threads B-E com estados corretos
- SQLite cheio → fail-open → WARNING logado, estado mantido em memoria,
  exportacao JSON ainda ocorre
- Arquivo JSON com permissao negada → WARNING logado, sem excecao para
  o chamador

### Regras que nao podem quebrar

- **ADR-001**: nenhum dado persistido fora do SQLite (exceto JSON derivado)
- **Fail-open**: excecao de SQLite nunca propaga para o loop principal de
  `start_journals_full_display.py`
- **Nomeacao PT-BR**: todos os novos simbolos publicos em portugues
- **Type hints 100%**: `mypy src/application/ --strict` zero erros

---

## 8. Dados e Integracoes

### Dados afetados

**Nova tabela SQLite** `diarios_watchdog_eventos`:

```sql
CREATE TABLE IF NOT EXISTS diarios_watchdog_eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    nome_thread TEXT NOT NULL,
    evento TEXT NOT NULL
        CHECK(evento IN
              ('GRAVACAO','HEARTBEAT','FALHA','REINICIO','ALERTA')),
    estado_resultante TEXT NOT NULL
        CHECK(estado_resultante IN
              ('rodando','pausado','com_erro','reiniciando',
               'aguardando_sinal')),
    mensagem TEXT,
    stack_trace TEXT,
    gravacoes_sessao INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
        DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_watchdog_session
    ON diarios_watchdog_eventos(session_id);
CREATE INDEX IF NOT EXISTS idx_watchdog_thread
    ON diarios_watchdog_eventos(nome_thread, created_at);
```

**Arquivo JSON de exportacao**:
`outputs/diarios/diarios_status_latest.json` — gerado a cada 60s,
sobrescreve o anterior atomicamente.

### Cenarios de persistencia

- Thread grava → `INSERT` com `evento='GRAVACAO'`, `estado_resultante='rodando'`
- Thread falha → `INSERT` com `evento='FALHA'`, `stack_trace` preenchido,
  `estado_resultante='com_erro'`
- Watchdog reinicia thread → `INSERT` com `evento='REINICIO'`,
  `estado_resultante='reiniciando'`
- Heartbeat confirma volta → `INSERT` com `evento='HEARTBEAT'`,
  `estado_resultante='rodando'`
- Alerta gerado → `INSERT` com `evento='ALERTA'`, mensagem com nome e
  minutos de inatividade

### Cenarios de compatibilidade

- `CREATE TABLE IF NOT EXISTS` — sem migracao necessaria
- `ObservabilidadeDiarios`: metodos atuais mantem assinatura atual;
  novos metodos sao adicionados, nao substituicoes
- `DIARIOS_MONITORADOS` pode ser mantida por compatibilidade retroativa,
  mas comportamento real usa `MAPEAMENTO_THREADS_CANONICO`

### Integracoes a mockar

- `datetime.now()` — freeze para testar thresholds
- `sqlite3.connect()` — mock para simular falha e testar fail-open
- Gravacao de arquivo JSON — `tmp_path` do pytest
- `ThreadWatchdog.gerar_relatorio_saude()` — stub com relatorio fixo

### Integracoes a validar ponta a ponta

- 1 teste de integracao: inicializar painel com banco temporario,
  chamar `registrar_gravacao("TradingJournal")`, consultar banco e
  verificar evento gravado
- 1 teste de regressao: importar `start_journals_full_display` e
  verificar ausencia de ImportError

---

## 9. Evidencias de Aceite

### Testes minimos esperados

| Classe de teste | Minimo |
|---|---|
| `TestEventoObservabilidadeDiario` | 3 |
| `TestSnapshotSaudeDiario` | 2 |
| `TestConfiguracaoMonitoramento` | 3 |
| `TestMapeamentoCanonicoThreads` | 4 |
| `TestObservabilidadeDiariosEstendida` | 8 |
| `TestMaquinaDeEstados` | 6 |
| `TestAlertasInatividade` | 4 |
| `TestPersistenciaSQLite` | 5 |
| `TestExportacaoJSON` | 3 |
| `TestPainelTerminal` | 3 |
| `TestIntegracao` | 2 |
| **Total novo** | **43 testes** |

### Cobertura esperada

- Modulos novos/modificados: **>= 85%**
- `diario_observability_panel.py` novos metodos: >= 85%
- Repositorio de eventos (se em arquivo separado): >= 80%
- Sem regressao: `test_diarios_watchdog.py` 21/21,
  `test_diario_observability_panel.py` 100%

### Evidencias de contrato

- `mypy src/application/diario_observability_panel.py --strict` →
  0 erros
- `mypy src/application/diarios_watchdog.py --strict` → 0 erros
- `MAPEAMENTO_THREADS_CANONICO` tem exatamente 5 entradas validas
- `SnapshotSaudeDiario.para_dict()` produz JSON valido
  (testado com `json.dumps`)

### Evidencias de observabilidade

- `SELECT COUNT(*) FROM diarios_watchdog_eventos WHERE session_id='...'`
  retorna > 0 apos uma sessao com gravacoes
- Arquivo `outputs/diarios/diarios_status_latest.json` existe e tem
  todos os campos do contrato
- `logging.WARNING` registrado quando SQLite falha
  (verificado via `caplog`)
- Painel em string contem estado de todas as 5 threads

### Evidencias de nao regressao

- `pytest tests/unit/test_diarios_watchdog.py` → **21/21 PASSING**
- `pytest tests/unit/test_diario_observability_panel.py` →
  **100% PASSING**
- `python -c "import scripts.start_journals_full_display"` →
  sem ImportError
- `pytest tests/unit/test_diarios_health_monitor.py` →
  **100% PASSING**

---

## 10. Riscos de Qualidade

### Riscos principais

| Risco | Prob. | Impacto | Mitigacao |
|---|---|---|---|
| `ObservabilidadeDiarios` estendida quebra testes existentes | MEDIA | ALTO | Adicionar metodos, nao alterar assinaturas; rodar suite antiga antes de commitar |
| Mocking de `datetime.now()` inconsistente | MEDIA | MEDIO | Usar `freezegun` ou centralizar patch em fixture |
| Fail-open mal implementado propaga excecao | MEDIA | ALTO | Testar com `sqlite3.connect` mockado para `OperationalError` |
| `session_id` nao isolado — testes interferem | ALTA | MEDIO | `tmp_path` + `uuid4()` por teste |
| Thread name mismatch nao documentado | BAIXA | ALTO | Comentario obrigatorio no mapeamento |

### Pontos sensiveis

- Onde exatamente `registrar_reinicio()` e chamado no `ThreadWatchdog`
  existente — o SE decide e documenta
- Alerta fora da janela operacional: janela hardcoded e risco para testes
  executados em diferentes fusos

### Lacunas conhecidas

- SA nao especificou ponto exato de chamada de `registrar_reinicio()` no
  `ThreadWatchdog` — SE deve decidir
- Cadencia de `MacroGuardian` e variavel — usar `threshold_alerta_min=20`
  como unico criterio

### Mitigacoes sugeridas

- Janela operacional configuravel via parametro no construtor
  (default `("09:00", "17:30")`)
- Constante `JANELA_OPERACIONAL_PADRAO: tuple[str, str]` em modulo ou
  `config/settings.py`
- `DiarioExecucao` tipo `APENAS_HEARTBEAT` exclui do alerta de inatividade
  por gravacao

---

## 11. Instrucoes para Implementacao

### Comportamento a implementar primeiro

**Passo 1**: Definir `ConfiguracaoMonitoramento` e
`MAPEAMENTO_THREADS_CANONICO` em `diario_observability_panel.py`.
Escrever `test_mapeamento_canonico_5_threads_existe`. Implementar ate passar.

**Passo 2**: Definir `EventoObservabilidadeDiario` e
`SnapshotSaudeDiario`. Escrever testes de dataclass. Implementar.

**Passo 3**: Adicionar `registrar_heartbeat()` e `registrar_falha()` a
`ObservabilidadeDiarios`. Escrever testes de contrato. Implementar.

**Passo 4**: Implementar maquina de estados. Escrever testes de transicao.
Implementar.

**Passo 5**: Implementar repositorio SQLite
(`diarios_watchdog_eventos`). Escrever testes de persistencia e
fail-open. Implementar.

**Passo 6**: Implementar `gerar_snapshot_operacional()` e exportacao
JSON. Escrever testes de exportacao. Implementar.

**Passo 7**: Rodar suite completa de regressao.

### Restricoes que o codigo deve respeitar

- **Nao alterar assinatura de `registrar_gravacao(nome_diario: str)`** —
  adicionar logica interna, nao mudar parametros
- **Nenhuma dependencia externa nova** — apenas `sqlite3`, `json`,
  `logging`, `datetime`, `threading`, `pathlib`, `uuid` (todos stdlib)
- **Fail-open em toda operacao de I/O** — `sqlite3.OperationalError` ou
  `OSError` capturado, logado como WARNING, operacao continua em memoria
- **`session_id` gerado no construtor** — `str(uuid.uuid4())` ou
  `f"diarios_{datetime.now().strftime('%Y%m%d_%H%M%S')}"` — nunca receber
  do exterior sem validacao
- **Arquivo JSON escrito atomicamente**: escrever em `.tmp` → `os.rename`
  → nunca escrever diretamente no destino final

### Testes que devem nascer antes do codigo (Red-Green-Refactor)

```
1. test_mapeamento_canonico_5_threads_existe
2. test_evento_observabilidade_frozen_imutavel
3. test_heartbeat_nao_incrementa_contador_gravacao
4. test_estado_inicial_none_antes_primeiro_heartbeat
5. test_transicao_rodando_para_com_erro_por_falha
6. test_fail_open_sqlite_indisponivel
7. test_alerta_ignorado_fora_da_janela_operacional
8. test_exportacao_json_atomica_campos_obrigatorios
```

### Pontos que exigem cuidado especial

- **Thread name mismatch**: o launcher registra `"TradingJournal"`, nao
  `"MICRO_TENDENCIA"`. `registrar_gravacao("TradingJournal")` deve
  funcionar. O mapeamento e `nome_real → nome_logico`, nao o contrario.
- **Alerta apenas dentro da janela**: ignorar completamente fora do
  pregao. Operador que deixa processo rodando de madrugada nao deve
  receber spam.
- **SQLite write lock**: verificar se o repositorio de eventos deve usar
  `sqlite_write_lock.py` de `src/infrastructure/database/` para evitar
  conflito com outros agentes.

### Sinais de que a implementacao esta incorreta

- `total_registros_sessao` muda apos `registrar_heartbeat()` → bug
- Estado vai de `com_erro` direto para `rodando` sem `reiniciando` → bug
- Excecao de SQLite propaga para o caller → violacao de fail-open
- Arquivo JSON escrito sem `.tmp` + rename → nao atomico
- Alerta gerado para `DiarioExecucao` (tipo `APENAS_HEARTBEAT`) → bug
- `mypy --strict` reporta erros em qualquer novo arquivo → inaceitavel

---

## 12. Pendencias para Implementacao

- **Decisao do SE**: onde exatamente `registrar_reinicio()` e chamado no
  `ThreadWatchdog` existente (qual metodo, qual linha)
- **Decisao do SE**: separar repositorio SQLite em arquivo proprio
  (`src/infrastructure/persistence/repositorio_watchdog_eventos.py`) ou
  manter inline em `diario_observability_panel.py` — recomendado separar
  para testabilidade
- **Decisao do SE**: janela operacional lida de `config/settings.py` ou
  parametro no construtor de `ObservabilidadeDiarios`
- **Confirmacao do SA**: `MacroGuardian` cadencia variavel — usar
  threshold de 20 min como unico criterio (ja definido acima)

---

## 13. Definition of Ready para Software Engineer

- [x] Criterios verificaveis explicitados
      (secao 4 — matriz com 17 linhas)
- [x] Cenarios obrigatorios listados
      (secao 6 — 27 cenarios)
- [x] Contratos e invariantes mapeados
      (secao 7 — dataclasses, invariantes, tolerancias)
- [x] Mocks/stubs/fixtures identificados
      (secao 5 — tabela com 6 dependencias)
- [x] Evidencias de aceite definidas
      (secao 9 — 43 testes minimos, cobertura >= 85%)
- [x] Riscos de regressao registrados
      (secao 10 — 5 riscos; secao 9 — evidencias de nao regressao)
- [x] Sequencia de TDD definida
      (secao 5 — 30 passos em 7 fases)

---

## Avaliacao de Impacto por Agente

| Agente | Impacto | Tipo | Acao operacional |
|---|---|---|---|
| `INICIAR_DIARIOS.bat` | **ALTO** | **DIRETO** | Reiniciar apos deploy; validar painel com 5 threads em <= 60s |
| `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` | **BAIXO** | **INDIRETO** | Nenhuma acao |
| `INICIAR_AGENTE_RL_5000.bat` | **BAIXO** | **INDIRETO** | Nenhuma acao |
| `INICIAR_AGENTE_RL_DIRETO.bat` | **BAIXO** | **INDIRETO** | Nenhuma acao |
| `INICIAR_MONITOR_QUANTICO.bat` | **NENHUM** | **SEM IMPACTO** | Nenhuma acao |

**Nota operacional para `INICIAR_DIARIOS.bat`:** Apos o deploy,
interromper o processo atual e reiniciar via `INICIAR_DIARIOS.bat`.
O painel deve exibir 5 linhas de status dentro de 60s. Se aparecer apenas
4 linhas (nomes logicos antigos) ou nenhuma thread com status `rodando`,
ha regressao — reverter o deploy imediatamente.
