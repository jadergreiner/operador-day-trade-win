# HANDOFF TECNICO PARA QA/TDD

## 1. Identificacao

- **id_demanda:** `ROADMAP-MICRO-03`
- **titulo:** Resultado DESCONHECIDO — eliminar do vocabulario operacional
- **estado_arquitetura:** `ARQUITETURA_APROVADA`
- **prioridade:** ALTA
- **data:** 02/04/2026

---

## 2. Leitura Arquitetural do Problema

**Problema arquitetural:**
O campo `resultado` de fechamentos registrados pelo `MotorDecisaoIsolado`
fica como `DESCONHECIDO` quando o rastreamento local perde o evento de
fechamento (timeout de monitoramento, reinicio do processo, falha
silenciosa da thread do agente). Sem resultado definitivo, nenhum dos
modulos downstream — AC5.9, AC6.7, AC6.8, AC6.9 — consegue produzir
aprendizado correto. O sinal que alimenta o loop de ML/RL e ruido.

**Objetivo da solucao:**
Garantir que toda ordem fechada tenha resultado `WIN`, `LOSS` ou
`BREAKEVEN` persistido ao final da sessao, com zero ocorrencias de
`DESCONHECIDO` em operacao normal. Quando o dado local estiver ausente,
o sistema consulta o MT5 como autoridade canonica e escreve de volta.

**Contexto considerado:**

- `src/application/motor_decisao_isolado.py` [DONE, 24 tests] — gerencia
  posicoes por agent_id + session_id com `MotivoFechamento` enum mas
  **sem campo `resultado`** em `HistoricoFechamento`.
- `src/application/reconciliadores/` — package com 3 skeletons
  funcionais criados: `unknown_result_detector.py`,
  `trade_outcome_reconciler.py`, `mt5_sync_validator.py`.
  **Nenhum tem testes.** Sao stubs operacionais prontos para implementacao.
- `src/infrastructure/adapters/mt5_adapter.py` — metodo
  `obter_preco_saida_historico()` ja chama `history_deals_get()` com
  lookback configuravel. A camada de infraestrutura ja e capaz de
  resolver o PnL real de um ticket fechado.
- `src/application/p1_learning_closure.py` [DONE, 27 tests] —
  define `OutcomeType(WIN/LOSS/BREAKEVEN)` com threshold +/-0.05% de
  pnl_pct. Este e o contrato canonico de classificacao de resultado.
- `src/application/ac5_9_feedback_validator.py` [DONE, 21 tests] —
  espera resultados `WIN`/`LOSS`/`BREAKEVEN` para o health check.
  Atualmente recebe fallback `DESCONHECIDO` que degrada as metricas.

**Suposicoes adotadas:**

- MT5 e autoridade canonica de PnL quando dado local estiver ausente
  (ADR-003: REST Adapter como unica interface com MT5).
- A reconciliacao e assincrona: acontece pos-fechamento, nao no caminho
  critico de execucao de ordens.
- Agentes em execucao paralela (234500, 234600, 234700, 234800) devem
  ser reconciliados de forma isolada — nenhum magic_number interfere
  no outro.

---

## 3. Aderencia e Restricoes

**ADRs consultados:**

- **ADR-001** (SQLite como unica persistencia local) — toda escrita de
  resultado reconciliado vai para o SQLite em `data/db/trading.db`.
- **ADR-003** (MT5 REST Adapter) — uso obrigatorio do adapter para
  consultar `history_deals_get`. Proibido chamar MetaTrader5 diretamente.
- **ADR-011** (Isolamento por session_id) — reconciliacao filtra por
  `agent_id` e `magic_number` antes de qualquer operacao.
- **ADR-012** (Magic Number unico por agente) — a query ao MT5 deve ser
  filtrada por magic_number para nao cruzar posicoes entre agentes.

**Aderencia a arquitetura-alvo:**

- `reconciliadores/` pertence a `src/application/` (camada de aplicacao).
  Correto — logica de negocio sem dependencia direta de infra.
- O acesso ao MT5 ocorre via `MT5Adapter`
  (`src/infrastructure/adapters/`) — nao ha violacao de camada.
- Resultado reconciliado escrito via `ITradeRepository`
  (`src/infrastructure/repositories/trade_repository.py`) — nao ha
  acesso direto a SQLite na camada de aplicacao.

**Restricoes obrigatorias:**

1. `motor_decisao_isolado.py` aceita **apenas uma mudanca**: adicionar
   `resultado: Optional[str] = None` ao `HistoricoFechamento`. Nenhuma
   logica de negocio nova entra no motor.
2. A reconciliacao nao pode bloquear o loop principal de nenhum agente.
   Executa em thread separada ou job agendado pos-pregao.
3. O adapter MT5 e chamado somente se o dado local estiver ausente.
   Chamadas desnecessarias ao broker sao proibidas.

**Conflitos identificados:**

- Conflito de nomenclatura: `src/application/trade_outcome_reconciler.py`
  (AC5.8) e `src/application/reconciliadores/trade_outcome_reconciler.py`
  (ROADMAP-MICRO-03) tem o mesmo nome de arquivo. A documentacao de
  QA/TDD deve referenciar sempre pelo path completo.
- `UnknownResultDetector.detectar_lacunas()` no skeleton atual nao
  recebe `agent_id` nem `magic_number` — precisa ser adicionado antes
  da implementacao de producao.

---

## 4. Desenho da Solucao

### Componentes impactados

| Componente | Mudanca | Tipo |
|---|---|---|
| `src/application/motor_decisao_isolado.py` | Adicionar `resultado: Optional[str] = None` em `HistoricoFechamento` | Minima |
| `src/application/reconciliadores/unknown_result_detector.py` | Implementar completamente | Preenchimento de skeleton |
| `src/application/reconciliadores/trade_outcome_reconciler.py` | Implementar completamente | Preenchimento de skeleton |
| `src/application/reconciliadores/mt5_sync_validator.py` | Implementar completamente | Preenchimento de skeleton |
| `src/infrastructure/adapters/mt5_adapter.py` | Expor metodo dedicado `obter_pnl_fechado(ticket, magic_number)` | Extensao minima |
| `src/infrastructure/repositories/trade_repository.py` | Adicionar `atualizar_resultado_fechamento(ticket, resultado, pnl)` | Extensao |
| `src/application/ac5_9_feedback_validator.py` | Nenhuma mudanca — apenas garante que recebe resultado valido | Zero |

### Componentes novos

- `src/application/reconciliadores/__init__.py` — exportar as 3 classes
  principais para import limpo.
- `outputs/reconciliacao_YYYYMMDD.json` — artefato de auditoria por
  sessao.

### Fluxo proposto

```
[Encerramento de sessao / trigger por resultado DESCONHECIDO]
        |
        v
1. UnknownResultDetector.detectar_lacunas(agent_id, magic_number)
   - Consulta SQLite: SELECT * FROM historico_fechamentos
     WHERE resultado IS NULL AND magic_number = ?
   - Retorna List[str] de tickets sem resultado
        |
        v
2. Para cada ticket sem resultado:
   TradeOutcomeReconciler.reconciliar_ordem(ticket, agent_id)
   - Consulta SQLite local: tem pnl_reais E pnl_pct?
     SIM: classificar diretamente via _classificar_resultado()
     NAO: chamar mt5_adapter.obter_pnl_fechado(ticket, magic_number)
          MT5 retorna PnL: classificar e escrever de volta
          MT5 retorna None: registrar ERRO + alertar operador
   - Escreve resultado (WIN/LOSS/BREAKEVEN) via trade_repository
   - Registra ReconciliationResult com source (LOCAL/MT5/ERRO)
        |
        v
3. MT5SyncValidator.validar_sincronizacao(session_id, agent_id)
   - Compara total_fechamentos_locais vs total_deals_mt5
     (com filtro magic_number)
   - Gera ValidationReport com SyncStatus
   - Persiste outputs/reconciliacao_YYYYMMDD.json
        |
        v
4. Emitir metrica de sessao:
   n_desconhecido_inicial / n_total_fechamentos = % resolvido
   Alvo: 0% DESCONHECIDO apos reconciliacao
        |
        v
5. AC5.9 FeedbackValidator.validate_feedback_health() recebe
   apenas WIN/LOSS/BREAKEVEN validos
```

### Entradas e saidas logicas

- **Entrada:** `List[HistoricoFechamento]` com `resultado = None`.
- **Processamento:**
  1. Detector identifica lacunas por agent_id + magic_number.
  2. Reconciliador classifica via pnl local ou fallback MT5.
  3. Validador confirma consistencia local vs MT5.
- **Saida:**
  - `HistoricoFechamento.resultado` preenchido no SQLite.
  - `outputs/reconciliacao_YYYYMMDD.json` com auditoria completa.
  - Log `WARNING` para cada caso que necessitou fallback ao MT5.
  - Metrica `pct_desconhecido_sessao` disponivel para dashboards.

---

## 5. Impactos por Dominio

**Execucao:**
Nenhum impacto no caminho critico de envio de ordens. Reconciliacao
ocorre pos-fechamento (thread separada ou job ao final do pregao).
Latencia adicional ao agente: zero (assicrono).

**Dados:**

- Coluna nova `resultado TEXT` em `historico_fechamentos` (confirmar
  schema em `src/infrastructure/database/schema.py`).
- Nova tabela `reconciliation_log` para auditoria dos casos resolvidos.
- Arquivo `outputs/reconciliacao_YYYYMMDD.json` gerado por sessao.

**Modelos / treinamento / RL:**

- AC5.9 recebe resultados validos — health check mais preciso.
- AC6.7 drift detector recebe dados sem ruido de DESCONHECIDO.
- AC6.8 online learning tem outcomes corretos para treino incremental.
- `pipeline_episodios_micro.py`: campo `resultado` em `diario_episodios`
  sera preenchido corretamente.

**Risco:**
Eliminacao de DESCONHECIDO reduz ambiguidade de risco. Fallback ao MT5
aumenta dependencia de conectividade — tratar timeout graciosamente
(registrar como ERRO, nao levantar excecao).

**Observabilidade:**

- `pct_desconhecido_sessao` — nova metrica por sessao.
- `n_reconciliados_mt5` — quantos precisaram de fallback ao broker.
- `n_erro_reconciliacao` — falhas irrecuperaveis (MT5 sem dado).
- Log WARNING auditavel para cada reconciliacao forcada.

**Operacao:**
Sem mudanca de interface de usuario. Relatorio
`outputs/reconciliacao_YYYYMMDD.json` legivel pelo operador. Alertas
de nivel WARNING no log do agente quando reconciliacao for necessaria.

---

## 6. Contratos e Regras Tecnicas

### Contratos logicos

**`UnknownResultDetector.detectar_lacunas(agent_id, magic_number)`**

```python
async def detectar_lacunas(
    self,
    agent_id: str,
    magic_number: int,
    ordens_locais: List[Dict[str, Any]],
    ordens_mt5: List[Dict[str, Any]],
) -> List[str]:
    ...
```

Filtra `ordens_locais` por `magic_number` antes de comparar. Retorna
apenas tickets que existem no MT5 mas nao tem `resultado` local.

**`TradeOutcomeReconciler._classificar_resultado(pnl_pct)`**

```python
def _classificar_resultado(
    self, pnl_pct: float
) -> Literal["WIN", "LOSS", "BREAKEVEN"]:
    BREAKEVEN_THRESHOLD = 0.05  # +/-0.05% igual ao EpisodeClosureEngine
    if abs(pnl_pct) <= BREAKEVEN_THRESHOLD:
        return "BREAKEVEN"
    return "WIN" if pnl_pct > 0 else "LOSS"
```

**`MT5SyncValidator.validar_sincronizacao(session_id, agent_id)`**

Compara contagem de deals fechados no MT5 (filtro magic_number, janela
de data da sessao) vs registros locais com `resultado NOT NULL`. Retorna
`SyncStatus.SINCRONIZADO` se delta <= tolerance (default 0). Retorna
`SyncStatus.DIVERGENCIA_CRITICA` se delta > 0.

### Validacoes obrigatorias

- Nenhuma escrita de resultado para ticket de outro agente (invariante
  de isolamento ADR-011/ADR-012).
- `pnl_pct` nao pode ser `None` antes de chamar
  `_classificar_resultado`. Se for `None`, obter do MT5 primeiro.
- `resultado` so pode receber os valores literais `"WIN"`, `"LOSS"`,
  `"BREAKEVEN"` — validacao de enum em camada de persistencia.

### Invariantes

- **Isolamento:** Reconciliacao de agent_id=A nao pode ler ou escrever
  em registros de agent_id=B.
- **Idempotencia:** Chamar reconciliacao duas vezes para o mesmo ticket
  nao cria registros duplicados nem altera resultado ja preenchido.
- **Fallback seguro:** Se MT5 nao devolver dado para um ticket, registra
  `ReconcileStatus.ERRO` e loga — nunca levanta excecao nao tratada.

### Tolerancia a falhas

- MT5 indisponivel: registra ERRO no `reconciliation_log`, nao aborta
  a reconciliacao dos demais tickets.
- SQLite bloqueado (WAL): retry com backoff exponencial (3x, 0.5s,
  1s, 2s).
- Thread de reconciliacao com timeout de 60s — se ultrapassar, registra
  aviso e encerra sem impactar o loop principal.

### Idempotencia / consistencia

Antes de escrever `resultado`, verificar se ja esta preenchido. Se
preenchido e consistente, nao sobrescrever. Se preenchido e
inconsistente (ex: `resultado="WIN"` mas `pnl_reais < 0`), registrar
divergencia no log mas nao alterar (decisao de auditoria manual).

---

## 7. Estrategia de Implementacao

**Abordagem recomendada:**
Implementar as 3 classes existentes (skeletons) em ordem de
dependencia, sem alterar interfaces publicas ja existentes.

### Fatiamento tecnico (ordem sugerida)

**Fatia 1 — Campo `resultado` no modelo (30 min)**

- Adicionar `resultado: Optional[str] = None` em `HistoricoFechamento`
  em `motor_decisao_isolado.py`.
- Validar que os 24 testes existentes continuam passando.
- Validar que `mypy --strict` nao aponta novos erros.

**Fatia 2 — Metodo de PnL no adapter (30 min)**

Expor metodo publico dedicado em `mt5_adapter.py`:

```python
def obter_pnl_fechado(
    self, ticket: int, magic_number: int
) -> Optional[float]:
```

Reutiliza logica ja existente em `obter_preco_saida_historico()`,
retornando `profit` do deal e nao o preco. Filtrar por `magic_number`
via `getattr(deal, "magic", 0)`.

**Fatia 3 — `UnknownResultDetector` completo (1h)**

- Adicionar `agent_id: str` e `magic_number: int` como parametros
  de instancia (injetados no `__init__`).
- Reescrever `detectar_lacunas()` para aceitar somente ordens do
  proprio agente.
- Adicionar `detectar_por_db(db_path: Path) -> List[str]` que
  consulta SQLite diretamente.

**Fatia 4 — `TradeOutcomeReconciler` completo (2h)**

- Implementar `_classificar_resultado()` com threshold +/-0.05%.
- Implementar `reconciliar_ordem()` completo: local -> MT5 fallback
  -> escrita de volta.
- Adicionar `gerar_relatorio_sessao(session_id, outputs_path) -> Path`
  que serializa `List[ReconciliationResult]` em JSON.
- Adicionar counters `n_desconhecido_resolvido` e `n_erro` por sessao.

**Fatia 5 — `MT5SyncValidator` completo (1h)**

- Implementar `validar_sincronizacao()` com query ao MT5
  (history_deals) e contagem local.
- Gerar `ValidationReport` com campos obrigatorios.
- Salvar em `outputs/reconciliacao_YYYYMMDD.json`.

**Fatia 6 — Integracao com AC5.9 (30 min)**

Garantir que `FeedbackValidator.validate_feedback_health()` recebe
apenas `["WIN", "LOSS", "BREAKEVEN"]` — sem `DESCONHECIDO`. Isso nao
requer codigo novo — apenas garantia via teste de integracao.

### Feature flag

Nao necessario. Reconciliacao e pos-execucao e nao afeta o caminho
critico.

### Rollback

O campo `resultado` e `Optional` — remover a coluna de volta ao estado
anterior nao quebra nenhum codigo existente. Os skeletons ja existem;
a pior situacao de rollback e revertelos para o estado atual (stubs).

---

## 8. Dados e Observabilidade

### Dados novos ou alterados

| Tabela/Campo | Tipo de mudanca | Destino |
|---|---|---|
| `historico_fechamentos.resultado` | Campo novo `TEXT NULL` | `trading.db` |
| `reconciliation_log` | Tabela nova (id, ticket, agent_id, source, status, ts) | `trading.db` |
| `outputs/reconciliacao_YYYYMMDD.json` | Arquivo novo por data | `outputs/` |

### Telemetria necessaria

- `pct_desconhecido_sessao`: float — calculado ao fim de cada sessao.
- `n_reconciliados_local`: int — resolvidos com dado local.
- `n_reconciliados_mt5`: int — precisaram de fallback ao broker.
- `n_erro_reconciliacao`: int — irrecuperaveis, precisam auditoria
  manual.

### Logs

- `WARNING` — cada ticket reconciliado via MT5 (nao era esperado).
- `WARNING` — cada ticket que permaneceu ERRO apos tentativa.
- `INFO` — relatorio de sessao (total reconciliado, % sucesso).
- `DEBUG` — detalhes internos de cada ReconciliationResult.

### Metricas

- `pct_desconhecido_sessao`: alvo `0.0` em sessoes normais.
- `n_erro_reconciliacao`: alvo `0`; qualquer valor > 0 exige
  investigacao manual.

### Alertas

Nenhum novo canal de alerta necessario nesta entrega. Os logs de nivel
WARNING ja sao capturados pelo sistema de monitoramento existente.

---

## 9. Riscos e Trade-offs

### Riscos tecnicos

| Risco | Probabilidade | Impacto | Mitigacao |
|---|---|---|---|
| MT5 indisponivel durante reconciliacao | MEDIA | MEDIO | Registrar ERRO, nao abortar; retry na proxima sessao |
| `history_deals_get` retorna deals de outros agentes | BAIXA | ALTO | Filtrar obrigatoriamente por `magic_number` |
| Conflito de escrita no SQLite (WAL) com agente rodando | MEDIA | BAIXO | `sqlite_write_lock.py` existente; usar transacao unica |
| Threshold de breakeven diverge de `p1_learning_closure.py` futuro | BAIXA | MEDIO | Centralizar constante em `src/domain/` ou `config/` |

### Riscos operacionais

Se reconciliacao for chamada durante o pregao com agente ativo, risco
de leitura inconsistente de posicoes abertas. Mitigacao: reconciliacao
deve filtrar apenas `status = FECHADA` (nao posicoes abertas).

### Trade-offs assumidos

- **Simplicidade vs automacao total:** Tickets que permanecem ERRO apos
  fallback MT5 sao registrados para auditoria manual — nao tentamos
  heuristica adicional. Isso e intencional para nao introduzir dados
  fabricados no loop de ML.
- **Threshold fixo vs configuravel:** Usar 0.05% do `EpisodeClosureEngine`
  como constante por ora. Configurabilidade pode ser adicionada em
  ROADMAP futuro sem quebra de interface.

---

## 10. Criterios Arquiteturais Testaveis

### Comportamentos esperados

1. Apos reconciliacao de sessao completa, zero registros com
   `resultado IS NULL` no SQLite para o `agent_id` processado.
2. `_classificar_resultado(pnl_pct=0.03)` retorna `"BREAKEVEN"`.
3. `_classificar_resultado(pnl_pct=0.50)` retorna `"WIN"`.
4. `_classificar_resultado(pnl_pct=-0.30)` retorna `"LOSS"`.
5. Ticket do agente A nunca aparece no processo de reconciliacao
   do agente B.

### Cenarios felizes

- Ticket tem `pnl_reais` e `pnl_pct` local — resultado calculado
  sem chamar MT5.
- Ticket sem dado local — MT5 retorna profit — resultado calculado
  e persistido.
- Reconciliacao chamada duas vezes para mesmo ticket — segundo call
  e noop (idempotencia).

### Cenarios de erro

- MT5 retorna `None` para ticket — `ReconcileStatus.ERRO` gravado,
  log WARNING, nenhuma excecao propagada.
- `pnl_pct` calculado como `0.0` por divisao por zero (preco_entrada
  igual a zero) — tratar como `BREAKEVEN` e registrar em log DEBUG.
- `magic_number` da ordem nao confere com `magic_number` do agente
  chamador — `ValueError` levantado com mensagem clara.

### Cenarios de borda

- Sessao com zero ordens fechadas — relatorio gerado com `n_total=0`,
  sem erro.
- Todos tickets ja tem `resultado` preenchido — reconciliacao retorna
  imediatamente sem writes, log INFO "nenhuma lacuna detectada".
- Ticket com `pnl_pct = -0.05` (exatamente no limite) —
  `"BREAKEVEN"` (limite inclusivo).
- Ticket com `pnl_pct = -0.0500001` — `"LOSS"`.

### Cenarios de regressao

- 24 testes de `motor_decisao_isolado.py` continuam passando apos
  adicao do campo `resultado`.
- 27 testes de `p1_learning_closure.py` continuam passando — nenhuma
  mudanca de threshold.
- 21 testes de `ac5_9_feedback_validator.py` continuam passando.
- Nenhum agente produz `DESCONHECIDO` como outcome apos reconciliacao
  (invariante de producao).

### Pontos criticos para mocks/stubs

- `mt5_adapter.obter_pnl_fechado()` — mockar para simular: (a) retorno
  de float, (b) retorno de `None`, (c) excecao de conexao.
- `trade_repository.atualizar_resultado_fechamento()` — mockar para
  verificar chamada correta sem banco real.
- SQLite — usar `tmp_path` do pytest com banco em memoria.

### Contratos que devem ser validados

- `detectar_lacunas()` so retorna tickets do `magic_number` correto.
- `reconciliar_ordem()` retorna `ReconciliationResult.reconciled = True`
  apenas quando escrita no banco foi confirmada.
- `validar_sincronizacao()` retorna `SyncStatus.SINCRONIZADO` quando
  contagem local == contagem MT5 (dentro da tolerancia 0).
- Arquivo `outputs/reconciliacao_YYYYMMDD.json` e gerado e e JSON
  valido.

---

## 11. ADR

- **decisao:** `ADR_NAO_NECESSARIO`
- **motivo:** A solucao segue exclusivamente padroes ja formalizados
  (ADR-001, ADR-003, ADR-011, ADR-012). O padrao Reconciler como
  componente dedicado na camada de aplicacao e consistente com a
  arquitetura-alvo. Nao ha escolha entre alternativas com trade-off
  relevante novo.

---

## 12. Pendencias para QA/TDD e Execucao

- **P1:** Confirmar campo de tabela que armazena `HistoricoFechamento`
  no SQLite (verificar `src/infrastructure/database/schema.py`) antes
  de escrever migration ou ALTER TABLE.
- **P2:** Verificar se `trade_repository.py` ja tem metodo de update de
  resultado ou se precisa ser adicionado — QA/TDD deve checar antes de
  escrever o mock.
- **P3:** Constante `BREAKEVEN_THRESHOLD = 0.05` deve ser importada de
  `p1_learning_closure.py` ou extraida para `src/domain/constants.py`
  para evitar duplicacao. Decisao a ser tomada pelo implementador.
- **P4:** Metodo `obter_pnl_fechado()` no adapter precisa filtrar por
  `magic_number`. Verificar se o deal retornado pelo MT5 tem campo
  `magic` acessivel via `getattr(deal, "magic", 0)`.

---

## 13. Definition of Ready para QA/TDD

- [x] Solucao delimitada — pipeline 3 etapas em `reconciliadores/`
- [x] Componentes impactados identificados — 3 skeletons + 2 extensoes
  minimas
- [x] Restricoes registradas — isolamento ADR-011/012,
  assincronicidade, idempotencia
- [x] Riscos conhecidos — MT5 indisponivel, conflito de magic_number,
  sqlite concorrencia
- [x] Estrategia de implementacao proposta — 6 fatias em ordem de
  dependencia
- [x] Observabilidade definida — 4 metricas, logs WARNING/INFO/DEBUG,
  relatorio JSON
- [x] Contratos testaveis explicitados — 5 invariantes + assinaturas
  de metodos
- [x] Cenarios criticos identificados — 5 felizes, 3 erro, 5 borda,
  4 regressao

---

## Referencias de Codigo

| Arquivo | Relevancia |
|---|---|
| `src/application/motor_decisao_isolado.py` | Campo `resultado` ausente em `HistoricoFechamento` — mudanca minima necessaria |
| `src/application/reconciliadores/unknown_result_detector.py` | Skeleton — implementar `detectar_lacunas` com filtro de agent_id/magic_number |
| `src/application/reconciliadores/trade_outcome_reconciler.py` | Skeleton — implementar classificacao + fallback MT5 + write-back |
| `src/application/reconciliadores/mt5_sync_validator.py` | Skeleton — implementar validacao + relatorio JSON |
| `src/infrastructure/adapters/mt5_adapter.py` (L987) | `history_deals_get` em uso — expor `obter_pnl_fechado(ticket, magic_number)` |
| `src/application/p1_learning_closure.py` | Fonte canonica de threshold 0.05% para WIN/LOSS/BREAKEVEN |
| `src/application/ac5_9_feedback_validator.py` | Receptor final — deve receber apenas outcomes validos apos reconciliacao |
