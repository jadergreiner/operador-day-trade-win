<!-- pyml disable md013 -->
<!-- pyml disable md040 -->

# S2-6 — Analytics de Intervenção Manual

**ID:** S2-6  
**Task:** Analytics de Intervenção Manual  
**Estado:** 🔴 BACKLOG → 🟡 PRIORIZADO (24/02/2026)  
**Owner:** Doc Advocate + Squad Multidisciplinar  
**Timeline:** 24/02 - 27/02 (4 dias)  
**Impacto Esperado:** +1-2% win rate via feedback trader-IA  
**Criticidade:** 🟠 MÉDIA (não bloqueia operações, melhora treinamento)

---

## 📋 Objetivo

Implementar um sistema de coleta de feedback estruturado quando o operador humano
encerra uma posição manualmente, alimentando o ciclo de aprendizado contínuo da IA.
Permitir que o trader comunique rapidamente o motivo da intervenção (código
numérico) e que o sistema persista esse feedback para retrainamento incremental.

---

## 🎯 Critérios de Aceitação

| # | AC | Status |
|:---:|:---|:---:|
| 1 | Menu de feedback embutido em `agente_micro_tendencia_winfut.py` | ⏳ TODO |
| 2 | 8 códigos de intervenção pré-definidos (1-Técnica, 2-Risco, ...) | ⏳ TODO |
| 3 | Persistência de feedback em `analytics_intervencao_manual.db` | ⏳ TODO |
| 4 | Registro estruturado com: timestamp, operação, código, contexto | ⏳ TODO |
| 5 | Endpoint REST para consulta de histórico (GET /feedback/history) | ⏳ TODO |
| 6 | Análise agregada de categorias de intervenção (gráfico .png) | ⏳ TODO |
| 7 | Integração com dashboard de monitoramento (status badge) | ⏳ TODO |
| 8 | 98% cobertura de testes (unit + integração) | ⏳ TODO |

---

## 🏗️ Arquitetura Proposta

```
┌─────────────────────────────────────────────────────────────┐
│           TRADER FEEDBACK COLLECTION LAYER                   │
│         (Loop Principal + Menu de Intervenção)               │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│           FEEDBACK PROCESSING & VALIDATION                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  • Validação de código (1-8)                          │  │
│  │  • Captura de contexto (score, volatilidade, etc)     │  │
│  │  • Timestamp sincronizado                             │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│           PERSISTENCE LAYER (SQLite)                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Table: intervencoes_manuais                          │  │
│  │    - id_intervencao (PK)                              │  │
│  │    - timestamp                                        │  │
│  │    - codigo_intervencao (1-8)                         │  │
│  │    - descricao_codigo                                 │  │
│  │    - contexto_json (score, volatilidade, etc)         │  │
│  │    - resultado_operacao (win/loss/closed)             │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│           ANALYTICS ENGINE                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  • Agregação por categoria                            │  │
│  │  • Detecção de padrões (ex: "Código 2 sempre perde") │  │
│  │  • Geração de insights                                │  │
│  │  • Export em JSON + visualização PNG                  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Categorias de Intervenção (Códigos 1-8)

| Código | Descrição | Rationale |
|:---:|:---|:---|
| **1** | Falha Técnica | MT5 lag, reconexão, ordem não executada |
| **2** | Risco Externo | Notícia importante, evento econômico inesperado |
| **3** | Lucro Satisfatório | Trader encerrou por meta de ganho diária |
| **4** | Stop Hit + Reentrada | Trader quer tentar novamente com novo score |
| **5** | Volatilidade Extrema | Mercado muito nervoso, parou por preservação |
| **6** | Falta de Confiança IA | Trader viu o sinal mas não confiou no score |
| **7** | Pausa Operacional | Trader vai sair, parou o robô temporariamente |
| **8** | Outro / Livre | Descrição customizada do trader |

---

## 🔧 Implementação Técnica

### 1. Estrutura de Banco de Dados

```sql
CREATE TABLE intervencoes_manuais (
  id_intervencao INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp TEXT NOT NULL,
  codigo_intervencao INTEGER CHECK (codigo_intervencao BETWEEN 1 AND 8),
  descricao_codigo TEXT,
  contexto_json TEXT,  -- {
                       --   "score": 0.85,
                       --   "volatilidade": 1.2,
                       --   "win_rate_sesao": 0.62,
                       --   "p_and_l_sesao": 456.78
                       -- }
  resultado_operacao TEXT,  -- 'win', 'loss', 'closed', 'rl_feedback'
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_timestamp ON intervencoes_manuais(timestamp);
CREATE INDEX idx_codigo ON intervencoes_manuais(codigo_intervencao);
```

### 2. Menu de Feedback (UX Console)

```
╔════════════════════════════════════════════════════╗
║  FEEDBACK DE INTERVENÇÃO MANUAL                    ║
║  Posição Encerrada: WINFUT-2026-02-24 13:45:30    ║
║  Score IA: 0.85 | Resultado: -127.50              ║
╚════════════════════════════════════════════════════╝

Selecione o motivo da intervenção (1-8):
  1. Falha Técnica (MT5 lag, reconexão)
  2. Risco Externo (notícia, evento)
  3. Lucro Satisfatório (meta atingida)
  4. Stop Hit + Reentrada
  5. Volatilidade Extrema
  6. Falta de Confiança na IA
  7. Pausa Operacional
  8. Outro / Livre

Código? > _
```

### 3. Classe Principal: `FeedbackCollector`

```python
class FeedbackCollector:
    """Coletor de feedback de intervenção manual."""
  
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
  
    def _init_db(self):
        """Inicializa tabela intervencoes_manuais."""
        ...
  
    def solicitar_feedback(self, operacao_id: str,
                          contexto: dict) -> FeedbackIntervencaoManual:
        """
        Exibe menu e coleta feedback do trader.
  
        Retorna: FeedbackIntervencaoManual com código e timestamp.
        """
        ...
  
    def registrar_intervencao(self,
                            feedback: FeedbackIntervencaoManual,
                            resultado: str) -> int:
        """
        Persiste feedback em intervencoes_manuais.
  
        Retorna: id_intervencao (PK).
        """
        ...
  
    def obter_historico(self,
                       filtro_data: Tuple[str, str]) ->
                       List[FeedbackIntervencaoManual]:
        """Retorna histórico de intervenções com filtro de data."""
        ...
  
    def gerar_relatorio_agregado(self) -> dict:
        """
        Retorna análise agregada por código com contagem e percentual.
  
        {
          "1": {"count": 45, "percentual": 18.3, "descricao": "Falha Técnica"},
          ...
        }
        """
        ...
```

### 4. Dataclass: `FeedbackIntervencaoManual`

```python
@dataclass
class FeedbackIntervencaoManual:
    """Feedback de intervenção manual do trader."""
  
    codigo_intervencao: int  # 1-8
    timestamp: str
    contexto: dict  # {score, volatilidade, ...}
    descricao: str = ""  # Opcional para código 8
    resultado_operacao: str = ""  # win, loss, closed
```

---

## 📈 REST API (Analytics Service)

### Endpoint 1: Registrar Feedback (POST)

```http
POST /api/v1/feedback/registrar
Content-Type: application/json

{
  "codigo": 3,
  "timestamp": "2026-02-24T14:30:00Z",
  "contexto": {
    "score": 0.85,
    "volatilidade": 1.2,
    "win_rate": 0.62
  },
  "descricao": ""  # Vazio se código 1-7, preenchido se 8
}

Response:
{
  "id_intervencao": 42,
  "status": "success",
  "mensagem": "Feedback registrado com sucesso"
}
```

### Endpoint 2: Consultar Histórico (GET)

```http
GET /api/v1/feedback/historico?data_inicio=2026-02-20&data_fim=2026-02-24

Response:
{
  "contador_total": 247,
  "intervencoes": [
    {
      "id": 42,
      "timestamp": "2026-02-24T14:30:00Z",
      "codigo": 3,
      "descricao": "Lucro Satisfatório",
      "contexto": {...}
    }
  ]
}
```

### Endpoint 3: Análise Agregada (GET)

```http
GET /api/v1/feedback/analise?data_inicio=2026-02-20&data_fim=2026-02-24

Response:
{
  "periodo": "2026-02-20 a 2026-02-24",
  "total_intervencoes": 247,
  "por_codigo": {
    "1": {"count": 45, "percentual": 18.2, "desc": "Falha Técnica"},
    "2": {"count": 32, "percentual": 12.9, "desc": "Risco Externo"},
    "3": {"count": 89, "percentual": 36.0, "desc": "Lucro Satisfatório"},
    ...
  },
  "insight_prioritario": "36% das intervenções são por lucro satisfatório"
}
```

---

## 🧪 Testes Unitários (98% Coverage)

### Teste 1: Inicialização BD

```python
def test_feedback_collector_init_database():
    """DADO: Collector sem BD existente.
    QUANDO: Inicializa.
    ENTÃO: Tabela intervencoes_manuais criada."""
    ...
```

### Teste 2: Registrar Intervenção

```python
def test_registrar_intervencao_codigo_valido():
    """DADO: Feedback com código 1-8.
    QUANDO: Registra.
    ENTÃO: ID retornado e persistido no BD."""
    ...

def test_registrar_intervencao_codigo_invalido():
    """DADO: Feedback com código 0 ou 9.
    QUANDO: Tenta registrar.
    ENTÃO: ValidationError levantado."""
    ...
```

### Teste 3: Histórico Filtrado

```python
def test_obter_historico_com_filtro_data():
    """DADO: 10 intervenções em diferentes datas.
    QUANDO: Filtra por intervalo [início, fim].
    ENTÃO: Retorna apenas intervenções no intervalo."""
    ...
```

### Teste 4: Relatório Agregado

```python
def test_gerar_relatorio_agregado():
    """DADO: 100 intervenções (30-codigo1, 25-codigo2, 45-codigo3).
    QUANDO: Gera relatório.
    ENTÃO: Percentuais calculados corretamente."""
    ...
```

---

## 🔗 Integração com Loop Principal

### Em: `scripts/agente_micro_tendencia_winfut.py`

```python
# Loop Principal - Trecho
while True:
    try:
        # Lógica existente (BDI, SMC, ML)
        ordem_executada = executar_ordem_se_sinal_valido(...)
  
        if ordem_executada:
            # NOVO: Aguardar resultado da posição
            resultado = aguardar_resultado_posicao(timeout=3600)
  
            # NOVO: Se trader encerrou manualmente
            if resultado.tipo == "intervencao_manual":
                feedback = feedback_collector.solicitar_feedback(
                    operacao_id=resultado.trade_id,
                    contexto={
                        "score": score_final,
                        "volatilidade": atr_atual,
                        "win_rate": stats.win_rate_sesao
                    }
                )
                feedback_collector.registrar_intervencao(
                    feedback,
                    resultado.outcome
                )
    except Exception as e:
        logger.error(f"Erro no loop: {e}")
        time.sleep(5)
```

---

## 📊 Visualizações Analytics

### 1. Gráfico de Distribuição (PNG)

```
Categorias de Intervenção Manual (24/02)

Lucro Satisfatório     |████████████████ 36.0%  (89 ops)
Falha Técnica          |████████ 18.2%  (45 ops)
Risco Externo          |███████ 12.9%  (32 ops)
Falta de Confiança     |███████ 12.5%  (31 ops)
Stop Hit + Reentrada   |████ 8.1%  (20 ops)
Volatilidade Extrema   |██ 1.6%  (4 ops)
Pausa Operacional      |██ 1.2%  (3 ops)
Outro                  |██ 1.2%  (3 ops)
```

### 2. Dashboard Status Badge

```
🔴 FEEDBACK: 247 intervenções | Código #3 dominante (36%)
              Tendência: ↑ 12% vs semana anterior
```

---

## 📋 Job/Task Paralelas para Squad

| Persona | Task | AC | Prazo |
|:---|:---|:---:|:---:|
| **Eng Sr** | Integração com loop principal | AC1, AC4 | 25/02 |
| **ML Expert** | Pipeline de dataset p/ retrainamento | AC3, AC4 | 26/02 |
| **Data Engineer** | Otimização índices BD + backup | AC3 | 25/02 |
| **QA Automation** | Suite de 20+ testes unitários | AC8 | 26/02 |
| **Arquiteto Sistemas** | REST API analytics service | AC5, AC6 | 26/02 |
| **Infra DevOps** | Deploy SQLite + CI/CD integration | AC3 | 25/02 |
| **Head Documentação** | Docstrings 100% + guia operacional | AC1 | 27/02 |
| **Doc Advocate** | Coordenação + STATUS_ENTREGAS update | — | 27/02 |

---

## ✅ Checklist de Conclusão

- [ ] Especificação revisada por 3+ personas
- [ ] Código escrito com 100% type hints
- [ ] Testes unitários: 98% coverage (PASS)
- [ ] Testes integração: .bat + loop validado
- [ ] Documentação: docstrings + README + guia operacional
- [ ] Lint: pymarkdown + pylint OK
- [ ] STATUS_ENTREGAS.md atualizado (🟢 COMPLETO)
- [ ] ROADMAP.md sincronizado (Oportunidade 21 ✅)
- [ ] Commit assinado e push origin main
- [ ] MONITOR_OPERADOR.bat sem quebras / INICIAR.BAT funcional

---

## 📚 Referências

- [docs/ARCHITECTURE.md](ARCHITECTURE.md): Feedlback Layer integrado
- [docs/STATUS_ENTREGAS.md](STATUS_ENTREGAS.md): Rastreabilidade
- [docs/ROADMAP.md](ROADMAP.md): Oportunidade 21
- [scripts/agente_micro_tendencia_winfut.py](../scripts/agente_micro_tendencia_winfut.py): Loop principal

---

**Estado:** 🟡 PRIORIZADO  
**Criado:** 2026-02-24T20:35:00Z  
**Last Updated:** 2026-02-24T20:35:00Z
