<!-- pyml disable md013 -->
<!-- pyml disable md040 -->

# S2-6 SQUAD MULTIDISCIPLINAR — Analytics de Intervenção Manual

**ID Task:** S2-6  
**Leader:** Doc Advocate (Persona 17)  
**Squad Size:** 8 personas  
**Data Criação:** 2026-02-24  
**Data Início:** 2026-02-24 16:00  
**Data Target Conclusão:** 2026-02-27 18:00  
**Status:** 🟡 SQUAD FORMADA E ATIVADA

---

## 👥 Membros da Squad (8 personas)

| # | Persona | Role Técnico | Task Principal | Prazo |
|:---:|:---|:---|:---|:---:|
| 3 | **Eng Sr** | Tech Lead | Loop Integration + Context Capture | 25/02 |
| 4 | **ML Expert** | Data Pipeline | Dataset Feedback + Retraining | 26/02 |
| 6 | **Arquiteto Sistemas** | API Designer | REST Analytics Service | 26/02 |
| 7 | **Infra DevOps** | Deployment | DB Setup + CI/CD + Backup | 25/02 |
| 11 | **Data Engineer** | DB Optimization | Índices + Query Perf + Audit | 25/02 |
| 12 | **QA Automation** | Testing Lead | Suite 20+ testes + 98% coverage | 26/02 |
| 8 | **Head de Documentação** | Docstring Lead | 100% type hints + docstrings | 27/02 |
| 17 | **Doc Advocate** | Coordinator | Overall governance + STATUS_ENTREGAS | 27/02 |

---

## 📋 Tasks Paralelas Distribuídas

### TASK 1️⃣ — Eng Sr: Loop Integration & Context Capture

**Responsabilidade:** Integrar coleta de feedback ao loop principal do agente.

**Acceptance Criteria:**
- AC1.1: Função `solicitar_feedback()` integrada em `agente_micro_tendencia_winfut.py`
- AC1.2: Contexto capturado antes de menu (score, volatilidade, win_rate)
- AC1.3: Menu de 8 opções exibido corretamente no console
- AC1.4: Feedback persistido com `registrar_intervencao()`
- AC1.5: Timing do loop não impactado (<100ms overhead)

**Detalhes Técnicos:**

```python
# Em: scripts/agente_micro_tendencia_winfut.py
# Adicionar após "ordem_executada":

def _capture_trade_context() -> dict:
    """Captura contexto da operação para feedback."""
    return {
        "score_final": score,
        "volatilidade_atr": atr_15m,
        "win_rate_sessao": stats.win_rate,
        "p_and_l_sessao": stats.p_and_l,
        "timestamp": datetime.now().isoformat()
    }

def _handle_manual_intervention(trade_id, resultado):
    """Gerencia feedback quando posição encerrada manualmente."""
    contexto = _capture_trade_context()
    feedback = feedback_collector.solicitar_feedback(trade_id, contexto)
    feedback_collector.registrar_intervencao(feedback, resultado.outcome)
```

**Entregáveis:**
- ✅ `FeedbackCollector` instanciado no startup
- ✅ Menu amigável em português
- ✅ Validação de entrada (1-8)
- ✅ Integração com `agente_micro_tendencia_winfut.py` funcional

**Prazo:** 25/02 23:59  
**Owner:** Eng Sr  
**Status:** 🔴 TODO

---

### TASK 2️⃣ — ML Expert: Dataset Feedback Pipeline

**Responsabilidade:** Criar pipeline para reutilizar feedback em retrainamento.

**Acceptance Criteria:**
- AC2.1: Script que export intervencoes_manuais para CSV
- AC2.2: Features extraídas do JSON contexto (8+)
- AC2.3: Dataset merge com winfut_dataset.parquet
- AC2.4: Validação de distribuição de labels
- AC2.5: Pipeline automatizado (pronto para DAG)

**Detalhes Técnicos:**

```python
# Em: src/ml/feedback_dataset_pipeline.py

class FeedbackDatasetPipeline:
    """Pipeline de integração feedback -> dataset."""
  
    def export_intervencoes_para_csv(self,
                                    db_path: str) -> pd.DataFrame:
        """Export estruturado com features."""
        # feedback_csv com colunas:
        # timestamp, codigo, contexto_score, contexto_vol, resultado
        ...
  
    def enrich_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enriquece com features de contexto."""
        # Extrai: score, volatilidade, win_rate, p_and_l
        # Normaliza e une com features técnicas existentes
        ...
  
    def merge_com_dataset_principal(self,
                                   feedback_df: pd.DataFrame,
                                   principal_path: str) -> None:
        """Merge feedback com dataset principal para retraining."""
        ...
```

**Entregáveis:**
- ✅ `FeedbackDatasetPipeline` classe completa
- ✅ Script de export com 8+ features
- ✅ Validação de distribuição
- ✅ Documentação de uso

**Prazo:** 26/02 23:59  
**Owner:** ML Expert  
**Status:** 🔴 TODO

---

### TASK 3️⃣ — Arquiteto Sistemas: REST Analytics API

**Responsabilidade:** Implementar endpoints REST para consulta e análise de dados.

**Acceptance Criteria:**
- AC3.1: Endpoint POST `/api/v1/feedback/registrar` funcional
- AC3.2: Endpoint GET `/api/v1/feedback/historico` filtro data
- AC3.3: Endpoint GET `/api/v1/feedback/analise` agregação
- AC3.4: Validação Pydantic em todos endpoints
- AC3.5: Error handling + logging estruturado

**Detalhes Técnicos:**

```python
# Em: src/api/feedback_api.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator

class FeedbackRequest(BaseModel):
    codigo: int
    timestamp: str
    contexto: dict
    descricao: str = ""
  
    @validator('codigo')
    def codigo_valido(cls, v):
        if not 1 <= v <= 8:
            raise ValueError('Código deve estar entre 1 e 8')
        return v

@app.post("/api/v1/feedback/registrar")
async def registrar_feedback(req: FeedbackRequest):
    """Registra novo feedback."""
    ...

@app.get("/api/v1/feedback/historico")
async def obter_historico(data_inicio: str, data_fim: str):
    """Retorna histórico filtrado."""
    ...

@app.get("/api/v1/feedback/analise")
async def obter_analise(data_inicio: str, data_fim: str):
    """Retorna análise agregada por código."""
    ...
```

**Entregáveis:**
- ✅ `FeedbackAPI` classe com 3 endpoints
- ✅ Modelos Pydantic validados
- ✅ Rate limiting básico
- ✅ Documentação OpenAPI

**Prazo:** 26/02 23:59  
**Owner:** Arquiteto Sistemas  
**Status:** 🔴 TODO

---

### TASK 4️⃣ — Infra DevOps: DB Setup & Deployment

**Responsabilidade:** Setup do SQLite, backup automatizado e CI/CD.

**Acceptance Criteria:**
- AC4.1: `analytics_intervencao_manual.db` inicializado com schema
- AC4.2: Script de backup diário em `.backup/` com timestamp
- AC4.3: CI/CD pipeline testa schema change antes de deploy
- AC4.4: Health check do DB a cada 5 minutos (MONITOR.bat)
- AC4.5: Documentação de disaster recovery

**Detalhes Técnicos:**

```python
# Em: scripts/setup_feedback_db.py

def init_analytics_db(db_path: str):
    """Inicializa BD intervencoes_manuais."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS intervencoes_manuais (
            id_intervencao INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            codigo_intervencao INTEGER CHECK (codigo BETWEEN 1 AND 8),
            descricao_codigo TEXT,
            contexto_json TEXT,
            resultado_operacao TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def backup_analytics_db(db_path: str, backup_dir: str):
    """Backup diário com timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{backup_dir}/analytics__{timestamp}.db"
    shutil.copy(db_path, backup_path)
```

**Entregáveis:**
- ✅ Script setup com schema completo
- ✅ Backup automatizado (cron job / Windows scheduler)
- ✅ Health check integrado
- ✅ Disaster recovery runbook

**Prazo:** 25/02 23:59  
**Owner:** Infra DevOps  
**Status:** 🔴 TODO

---

### TASK 5️⃣ — Data Engineer: DB Optimization & Indexes

**Responsabilidade:** Otimizar queries, índices e auditoria do BD.

**Acceptance Criteria:**
- AC5.1: Índices em `timestamp` e `codigo_intervencao`
- AC5.2: Query `SELECT * FROM intervencoes WHERE timestamp BETWEEN ? AND ?` <10ms
- AC5.3: Procedure para cleanup de dados >6 meses (retention policy)
- AC5.4: Table de auditoria `intervencoes_auditoria` (who, when, what)
- AC5.5: Script de análise de tamanho + vacuum

**Detalhes Técnicos:**

```sql
-- Índices
CREATE INDEX idx_timestamp_intervencoes
  ON intervencoes_manuais(timestamp DESC);
CREATE INDEX idx_codigo_intervencoes
  ON intervencoes_manuais(codigo_intervencao);

-- Auditoria
CREATE TABLE intervencoes_auditoria (
  id_auditoria INTEGER PRIMARY KEY,
  operacao TEXT,  -- INSERT, UPDATE, DELETE
  timestamp_operacao DATETIME,
  usuario TEXT,
  dados_antigos TEXT,
  dados_novos TEXT
);

-- Trigger
CREATE TRIGGER audit_intervencoes_update
AFTER UPDATE ON intervencoes_manuais
BEGIN
  INSERT INTO intervencoes_auditoria
  VALUES(NULL, 'UPDATE', CURRENT_TIMESTAMP, 'system',
         OLD.contexto_json, NEW.contexto_json);
END;
```

**Entregáveis:**
- ✅ Índices criados e testados
- ✅ Queries otimizadas <10ms
- ✅ Retention policy automatizada
- ✅ Relatório de performance

**Prazo:** 25/02 23:59  
**Owner:** Data Engineer  
**Status:** 🔴 TODO

---

### TASK 6️⃣ — QA Automation: Test Suite 98% Coverage

**Responsabilidade:** Implementar suite de 20+ testes com 98% coverage.

**Acceptance Criteria:**
- AC6.1: 20+ testes unitários (CASE-THEN-WHEN format)
- AC6.2: Testes de integração: DB + API + Loop
- AC6.3: Coverage >= 98%
- AC6.4: Testes em português + descritivos
- AC6.5: CI/CD pipeline executa antes de merge

**Test Groups:**

**Group 1: FeedbackCollector Unit Tests (8 testes)**

```python
def test_feedback_collector_init_database():
    """DADO: FeedbackCollector sem BD.
    QUANDO: Inicializa.
    ENTÃO: Tabela criada com schema correto."""
    ...

def test_registrar_intervencao_codigo_valido():
    """DADO: Feedback código 1-8.
    QUANDO: Registra.
    ENTÃO: ID retornado e BD atualizado."""
    ...

def test_registrar_intervencao_codigo_invalido():
    """DADO: Feedback código 0 ou 9.
    QUANDO: Tenta registrar.
    ENTÃO: ValueError levantado."""
    ...

def test_solicitar_feedback_menu_display():
    """DADO: Loop com trade_id e contexto.
    QUANDO: Chama solicitar_feedback.
    ENTÃO: Menu exibido com 8 opções."""
    ...

def test_obter_historico_com_filtro():
    """DADO: 10 intervencoes em diferentes datas.
    QUANDO: Filtra por intervalo.
    ENTÃO: Retorna apenas intervalo especificado."""
    ...

def test_gerar_relatorio_agregado():
    """DADO: 100 intervencoes com distribuição.
    QUANDO: Gera agregação.
    ENTÃO: Percentuais corretos."""
    ...

def test_contexto_persistido_completo():
    """DADO: Feedback com contexto JSON.
    QUANDO: Registra.
    ENTÃO: JSON completo em BD sem truncamento."""
    ...

def test_timestamp_sincronizado():
    """DADO: Intervenção registrada.
    QUANDO: Consulta BD.
    ENTÃO: Timestamp sincronizado com hora do sistema."""
    ...
```

**Group 2: REST API Tests (5 testes)**

```python
def test_post_registrar_feedback_sucesso():
    """DADO: Request POST válido.
    QUANDO: POST /api/v1/feedback/registrar.
    ENTÃO: Status 201 + id retornado."""
    ...

def test_post_registrar_feedback_codigo_invalido():
    """DADO: Request com código 15.
    QUANDO: POST /api/v1/feedback/registrar.
    ENTÃO: Status 422 + erro validação."""
    ...

def test_get_historico_com_filtro():
    """DADO: GET /api/v1/feedback/historico?data_inicio=...&data_fim=...
    QUANDO: Query executa.
    ENTÃO: JSON com intervencoes do período."""
    ...

def test_get_analise_agregada():
    """DADO: GET /api/v1/feedback/analise.
    QUANDO: Query executa.
    ENTÃO: JSON com por_codigo agregado."""
    ...

def test_rate_limiting():
    """DADO: 100 requisições em 1s.
    QUANDO: Excede rate limit.
    ENTÃO: Status 429 retornado."""
    ...
```

**Group 3: Integration Tests (7 testes)**

```python
def test_loop_principal_com_intervencao():
    """DADO: Loop running com trade aberto.
    QUANDO: Trader encerra manualmente.
    ENTÃO: Menu exibido e feedback persistido."""
    ...

def test_feedback_pipeline_dataset_merge():
    """DADO: 50 intervencoes no BD.
    QUANDO: Roda FeedbackDatasetPipeline.
    ENTÃO: Feedback mergeado com dataset." ...

def test_backup_automático_executa():
    """DADO: Script backup configurado.
    QUANDO: Tempo de backup chega.
    ENTÃO: Arquivo .db criado em backup/."""
    ...

def test_health_check_monitor_bat():
    """DADO: MONITOR_OPERADOR.bat running.
    QUANDO: Check health do feedback DB.
    ENTÃO: Status exibido sem erros."""
    ...

def test_retry_conexao_db_falha():
    """DADO: BD fica indisponível por 5s.
    QUANDO: Tenta registrar feedback.
    ENTÃO: Retry automático reconecta."""
    ...

def test_concurrent_feedback_inserts():
    """DADO: 10 threads registrando feedback simultaneamente.
    QUANDO: Todos executam.
    ENTÃO: 10 registros inseridos sem conflito."""
    ...

def test_cleanup_retention_policy():
    """DADO: Intervencoes com >6 meses.
    QUANDO: Script cleanup roda.
    ENTÃO: Registros antigos removidos."""
    ...
```

**Entregáveis:**
- ✅ `tests/unit/test_s2_6_feedback_collector.py`: 8 testes
- ✅ `tests/unit/test_s2_6_feedback_api.py`: 5 testes
- ✅ `tests/integration/test_s2_6_integration.py`: 7 testes
- ✅ Coverage report: 98%+
- ✅ Todos testes verbosos em português

**Prazo:** 26/02 23:59  
**Owner:** QA Automation  
**Status:** 🔴 TODO

---

### TASK 7️⃣ — Head Documentação: 100% Docstrings

**Responsabilidade:** Documentação completa com type hints e docstrings.

**Acceptance Criteria:**
- AC7.1: 100% das funções com docstrings (Google style)
- AC7.2: 100% type hints (parameter + return)
- AC7.3: README operacional em português
- AC7.4: Exemplos de uso no docstring
- AC7.5: Lint pymarkdown PASS

**Detalhes:**

```python
# Exemplo modelo:

def registrar_intervencao(self,
                         feedback: FeedbackIntervencaoManual,
                         resultado: str) -> int:
    """Registra feedback de intervenção manual em BD.
  
    Persiste a intervenção com timestamp sincronizado, código
    de classificação (1-8) e contexto de mercado capturado.
  
    Args:
        feedback: Objeto FeedbackIntervencaoManual com os dados.
        resultado: Resultado da operação ('win', 'loss', 'closed').
  
    Returns:
        id_intervencao: ID da linha inserida (PK).
  
    Raises:
        ValueError: Se código_intervencao não está entre 1-8.
        sqlite3.Error: Se erro ao escrever BD.
  
    Examples:
        >>> feedback = FeedbackIntervencaoManual(
        ...     codigo_intervencao=3,
        ...     timestamp="2026-02-24T14:30:00Z",
        ...     contexto={"score": 0.85}
        ... )
        >>> id_new = collector.registrar_intervencao(feedback, "win")
        >>> assert id_new > 0
    """
    ...
```

**Entregáveis:**
- ✅ `src/application/feedback_collector.py`: 100% docstrings + type hints
- ✅ `src/api/feedback_api.py`: 100% docstrings + type hints
- ✅ `src/ml/feedback_dataset_pipeline.py`: 100% docstrings + type hints
- ✅ `docs/S2-6_OPERACIONAL_GUIA.md`: Guia para traders
- ✅ Lint: 0 erros pymarkdown

**Prazo:** 27/02 23:59  
**Owner:** Head Documentação  
**Status:** 🔴 TODO

---

### TASK 8️⃣ — Doc Advocate: Governance & Status Updates

**Responsabilidade:** Coordenação geral, sincronização de documentos e gates.

**Acceptance Criteria:**
- AC8.1: S2-6 STATUS marcado 🟢 COMPLETO em STATUS_ENTREGAS.md
- AC8.2: ROADMAP.md Atualizado (Oportunidade 21 ✅)
- AC8.3: CHANGELOG.md entry com descrição da entrega
- AC8.4: SYNC_MANIFEST.json atualizado (checksums)
- AC8.5: Feedback loop validado em MONITOR_OPERADOR.bat

**Detalhes:**

**STATUS_ENTREGAS.md (Nova linha):**

```markdown
| **S2-6** | Analytics de Intervenção Manual | [Doc Advocate](BOARD_MULTIDISCIPLINAR.json) | 🟢 **COMPLETO** | [S2-6] | Feedback Trader-IA persistido, 8 categorias, 98% tests |
```

**ROADMAP.md (Update Oportunidade 21):**

```markdown
- **Oportunidade 21: Analytics de Intervenção Manual:** ✅ **CONCLUÍDO 27/02**
  - Menu de feedback integrado (8 categorias)
  - Persistência em analytics_intervencao_manual.db
  - REST API endpoints (historico + analise)
  - 98% cobertura de testes
  - Expected: +1-2% win rate via feedback trader-IA
```

**CHANGELOG.md:**

```markdown
## [v1.2.0] - 2026-02-27

### Added
- S2-6: Analytics de Intervenção Manual
  - Menu de feedback integrado em loop principal
  - 8 categorias de interventação (técnica, risco, lucro, etc)
  - Banco dados SQLite com schema auditado
  - REST API endpoints para consulta e análise
  - Pipeline de retraining com feedback
  - 20+ testes unitários (98% coverage)
  - Documentação completa (docstrings + guia operacional)

### Changed
- `scripts/agente_micro_tendencia_winfut.py`: Integração com FeedbackCollector
- `MONITOR_OPERADOR.bat`: Status badge do feedback agregado
```

**Entregáveis:**
- ✅ `docs/STATUS_ENTREGAS.md`: S2-6 marcado 🟢 COMPLETO
- ✅ `docs/ROADMAP.md`: Oportunidade 21 ✅ CONCLUÍDO
- ✅ `docs/CHANGELOG.md`: Entry v1.2.0 com S2-6
- ✅ `docs/SYNCHRONIZATION.md`: New sync record
- ✅ Validação MONITOR_OPERADOR.bat sem erros

**Prazo:** 27/02 23:59  
**Owner:** Doc Advocate  
**Status:** 🔴 TODO

---

## 📊 Timeline Paralela (Gantt Visual)

```
24/02  │ 25/02  │ 26/02  │ 27/02  │
───────┼────────┼────────┼────────┼
Task 1 │ ▓▓▓▓▓▓│        │        │  Eng Sr: Loop Int
Task 2 │        │ ▓▓▓▓▓▓│        │  ML Expert: Dataset
Task 3 │        │ ▓▓▓▓▓▓│        │  Arquiteto: REST API
Task 4 │ ▓▓▓▓▓▓│        │        │  DevOps: DB Setup
Task 5 │ ▓▓▓▓▓▓│        │        │  Data Eng: Indexes
Task 6 │        │ ▓▓▓▓▓▓│        │  QA: Tests 98%
Task 7 │        │        │ ▓▓▓▓▓▓│  Documentation
Task 8 │        │        │ ▓▓▓▓▓▓│  Governance
```

---

## 🎯 Success Criteria (Squad Level)

- ✅ Todas 8 tasks paralelas entregues no prazo
- ✅ AC cumpridas 100%
- ✅ 20+ testes passando (98% coverage)
- ✅ Código com 100% type hints + docstrings
- ✅ STATUS_ENTREGAS.md S2-6 = 🟢 COMPLETO
- ✅ ROADMAP.md Oportunidade 21 ✅
- ✅ MONITOR_OPERADOR.bat + INICIAR.BAT sem quebras
- ✅ Commit + push com UTF-8 + lint OK

---

## 📋 Governance & Communication

**Daily Standup:** 15:00 BRT (todos participam)
**Async Updates:** Slack channel #s2-6-feedback-squad
**Decision Gate:** Doc Advocate faz call de go/no-go a cada etapa

---

**Status:** 🟡 FORMADA  
**Created:** 2026-02-24T20:40:00Z  
**Target Delivery:** 2026-02-27T18:00:00Z
