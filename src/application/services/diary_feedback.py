"""
Serviço de Feedback do Diário para RL.

Persiste as análises críticas do diário no SQLite para que o agente
possa ler e usar como sinal adicional de aprendizado por reforço.

Ciclo de feedback:
  1. Diário analisa episódios/rewards do agente (RLPerformanceReader)
  2. Gera análise crítica profunda (analyze_agent_coherence)
  3. Persiste feedback nesta tabela
  4. Agente lê feedback mais recente a cada N ciclos
  5. Agente ajusta comportamento (thresholds, filtros) baseado no feedback

Campos do feedback:
  - nota_agente: 0-10 (nota geral da performance)
  - alertas_criticos: lista de alertas graves
  - incoerencias: contradições entre sinal macro e ação do agente
  - filtros_bloqueantes: filtros que estão impedindo operações
  - parametros_questionados: parâmetros que podem estar incorretos
  - custo_oportunidade_pts: pontos que poderiam ter sido capturados
  - sugestoes: sugestões concretas de ajuste
  - threshold_sugerido_buy: threshold de compra sugerido pelo diário
  - threshold_sugerido_sell: threshold de venda sugerido pelo diário
  - smc_bypass_recomendado: se o diário recomenda bypass do SMC
  - trend_following_recomendado: se deveria ativar modo trend following
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from typing import Optional


@dataclass
class DiaryFeedback:
    """Feedback do diário para o agente RL."""

    # Identificação
    date: str = ""                              # YYYY-MM-DD
    timestamp: str = ""                         # ISO timestamp
    source: str = "diary_rl_performance"        # Qual thread gerou

    # Nota geral
    nota_agente: int = 10                       # 0-10

    # Análise qualitativa (JSON serializado)
    alertas_criticos: list[str] = field(default_factory=list)
    incoerencias: list[str] = field(default_factory=list)
    filtros_bloqueantes: list[str] = field(default_factory=list)
    parametros_questionados: list[str] = field(default_factory=list)
    sugestoes: list[str] = field(default_factory=list)

    # Métricas quantitativas
    custo_oportunidade_pts: float = 0.0         # Pts deixados na mesa
    eficiencia_pct: float = 0.0                 # 0-100
    hold_pct: float = 0.0                       # % do tempo em HOLD
    win_rate_pct: float = 0.0                   # Win rate no momento
    market_range_pts: float = 0.0               # Range do mercado
    n_opportunities: int = 0                    # Oportunidades detectadas
    n_episodes: int = 0                         # Episódios processados

    # Sinais de AJUSTE para o agente (RL feedback direto)
    threshold_sugerido_buy: int = 5             # Score mínimo para BUY
    threshold_sugerido_sell: int = -5           # Score mínimo para SELL
    smc_bypass_recomendado: bool = False         # Bypass SMC em tendência?
    trend_following_recomendado: bool = False    # Ativar trend following?
    max_adx_para_trend: float = 25.0            # ADX acima = tendência
    confianca_minima_sugerida: float = 60.0     # Confiança mínima

    # Análise crítica de regiões (nível Head)
    regioes_fortes: list[str] = field(default_factory=list)      # Regiões com score >= 3
    regioes_armadilhas: list[str] = field(default_factory=list)  # Regiões contra-indicadas
    veredicto_regioes: str = ""                  # Veredicto geral das regiões

    # Análise crítica do direcional macro (nível Head)
    direcional_vieses: list[str] = field(default_factory=list)      # Viéses detectados
    direcional_contradicoes: list[str] = field(default_factory=list) # Contradições entre categorias
    direcional_questionamentos: list[str] = field(default_factory=list)  # Questionamentos abertos
    veredicto_direcional: str = ""               # Veredicto geral do direcional
    confianca_direcional_ajustada: float = 0.0   # Confiança recalculada pelo diary

    # Macro Scenario Guardian (monitoramento contínuo)
    guardian_kill_switch: bool = False            # Kill switch — pausar trading
    guardian_kill_reason: str = ""               # Motivo do kill switch
    guardian_reduced_exposure: bool = False       # Exposição reduzida
    guardian_confidence_penalty: float = 0.0      # Penalidade de confiança (0-30)
    guardian_bias_override: str = ""              # Override direcional ("", "NEUTRO", "CONTRA")
    guardian_scenario_changes: int = 0            # Mudanças de cenário no dia
    guardian_alertas: list[str] = field(default_factory=list)  # Alertas macro ativos

    # Contexto do mercado no momento da análise
    macro_signal_dominante: str = ""            # COMPRA, VENDA, NEUTRO
    smc_equilibrium_dominante: str = ""         # PREMIUM, DISCOUNT, NEUTRO
    adx_medio: float = 0.0                      # ADX médio
    micro_score_medio: float = 0.0              # Micro score médio

    # Estado
    active: bool = True                         # Feedback ativo?

    def to_dict(self) -> dict:
        """Converte para dicionário serializável."""
        d = asdict(self)
        # Serializar listas como JSON strings
        for key in ("alertas_criticos", "incoerencias", "filtros_bloqueantes",
                     "parametros_questionados", "sugestoes",
                     "regioes_fortes", "regioes_armadilhas",
                     "direcional_vieses", "direcional_contradicoes",
                     "direcional_questionamentos",
                     "guardian_alertas"):
            if isinstance(d[key], list):
                d[key] = json.dumps(d[key], ensure_ascii=False)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> DiaryFeedback:
        """Cria a partir de dicionário do SQLite."""
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {}
        for k, v in data.items():
            if k not in valid_fields:
                continue
            # Deserializar JSON strings para listas
            if k in ("alertas_criticos", "incoerencias", "filtros_bloqueantes",
                      "parametros_questionados", "sugestoes",
                      "regioes_fortes", "regioes_armadilhas",
                      "direcional_vieses", "direcional_contradicoes",
                      "direcional_questionamentos",
                      "guardian_alertas"):
                if isinstance(v, str):
                    try:
                        filtered[k] = json.loads(v)
                    except (json.JSONDecodeError, TypeError):
                        filtered[k] = [v] if v else []
                else:
                    filtered[k] = v if v else []
            else:
                filtered[k] = v
        return cls(**filtered)


# ────────────────────────────────────────────────────────────────
# Persistência SQLite
# ────────────────────────────────────────────────────────────────

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS diary_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'diary_rl_performance',

    -- Avaliação
    nota_agente INTEGER NOT NULL DEFAULT 10,

    -- Análise qualitativa (JSON)
    alertas_criticos TEXT DEFAULT '[]',
    incoerencias TEXT DEFAULT '[]',
    filtros_bloqueantes TEXT DEFAULT '[]',
    parametros_questionados TEXT DEFAULT '[]',
    sugestoes TEXT DEFAULT '[]',

    -- Métricas quantitativas
    custo_oportunidade_pts REAL DEFAULT 0,
    eficiencia_pct REAL DEFAULT 0,
    hold_pct REAL DEFAULT 0,
    win_rate_pct REAL DEFAULT 0,
    market_range_pts REAL DEFAULT 0,
    n_opportunities INTEGER DEFAULT 0,
    n_episodes INTEGER DEFAULT 0,

    -- Sinais de ajuste para o agente (RL feedback)
    threshold_sugerido_buy INTEGER DEFAULT 5,
    threshold_sugerido_sell INTEGER DEFAULT -5,
    smc_bypass_recomendado INTEGER DEFAULT 0,
    trend_following_recomendado INTEGER DEFAULT 0,
    max_adx_para_trend REAL DEFAULT 25.0,
    confianca_minima_sugerida REAL DEFAULT 60.0,

    -- Análise crítica de regiões
    regioes_fortes TEXT DEFAULT '[]',
    regioes_armadilhas TEXT DEFAULT '[]',
    veredicto_regioes TEXT DEFAULT '',

    -- Análise crítica do direcional macro
    direcional_vieses TEXT DEFAULT '[]',
    direcional_contradicoes TEXT DEFAULT '[]',
    direcional_questionamentos TEXT DEFAULT '[]',
    veredicto_direcional TEXT DEFAULT '',
    confianca_direcional_ajustada REAL DEFAULT 0,

    -- Macro Scenario Guardian
    guardian_kill_switch INTEGER DEFAULT 0,
    guardian_kill_reason TEXT DEFAULT '',
    guardian_reduced_exposure INTEGER DEFAULT 0,
    guardian_confidence_penalty REAL DEFAULT 0,
    guardian_bias_override TEXT DEFAULT '',
    guardian_scenario_changes INTEGER DEFAULT 0,
    guardian_alertas TEXT DEFAULT '[]',

    -- Contexto de mercado
    macro_signal_dominante TEXT DEFAULT '',
    smc_equilibrium_dominante TEXT DEFAULT '',
    adx_medio REAL DEFAULT 0,
    micro_score_medio REAL DEFAULT 0,

    -- Estado
    active INTEGER DEFAULT 1,

    -- Índices
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_diary_feedback_date ON diary_feedback(date);
CREATE INDEX IF NOT EXISTS ix_diary_feedback_active ON diary_feedback(active, date);
"""


def create_diary_feedback_table(db_path: str) -> None:
    """Cria a tabela diary_feedback se não existir."""
    try:
        conn = sqlite3.connect(db_path)
        conn.executescript(_CREATE_TABLE_SQL)
        # Migrar tabelas existentes — adicionar colunas novas se não existem
        _alter_table_migrations = [
            ("regioes_fortes", "TEXT DEFAULT '[]'"),
            ("regioes_armadilhas", "TEXT DEFAULT '[]'"),
            ("veredicto_regioes", "TEXT DEFAULT ''"),
            ("direcional_vieses", "TEXT DEFAULT '[]'"),
            ("direcional_contradicoes", "TEXT DEFAULT '[]'"),
            ("direcional_questionamentos", "TEXT DEFAULT '[]'"),
            ("veredicto_direcional", "TEXT DEFAULT ''"),
            ("confianca_direcional_ajustada", "REAL DEFAULT 0"),
            ("guardian_kill_switch", "INTEGER DEFAULT 0"),
            ("guardian_kill_reason", "TEXT DEFAULT ''"),
            ("guardian_reduced_exposure", "INTEGER DEFAULT 0"),
            ("guardian_confidence_penalty", "REAL DEFAULT 0"),
            ("guardian_bias_override", "TEXT DEFAULT ''"),
            ("guardian_scenario_changes", "INTEGER DEFAULT 0"),
            ("guardian_alertas", "TEXT DEFAULT '[]'"),
        ]
        cursor = conn.cursor()
        for col_name, col_def in _alter_table_migrations:
            try:
                cursor.execute(f"ALTER TABLE diary_feedback ADD COLUMN {col_name} {col_def}")
            except Exception:
                pass  # Coluna já existe
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[AVISO] Erro ao criar tabela diary_feedback: {e}")


def save_diary_feedback(db_path: str, feedback: DiaryFeedback) -> int:
    """Persiste feedback do diário no SQLite.

    Retorna o ID do registro inserido.
    """
    create_diary_feedback_table(db_path)

    d = feedback.to_dict()

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO diary_feedback (
                date, timestamp, source,
                nota_agente,
                alertas_criticos, incoerencias, filtros_bloqueantes,
                parametros_questionados, sugestoes,
                custo_oportunidade_pts, eficiencia_pct,
                hold_pct, win_rate_pct, market_range_pts,
                n_opportunities, n_episodes,
                threshold_sugerido_buy, threshold_sugerido_sell,
                smc_bypass_recomendado, trend_following_recomendado,
                max_adx_para_trend, confianca_minima_sugerida,
                regioes_fortes, regioes_armadilhas, veredicto_regioes,
                direcional_vieses, direcional_contradicoes,
                direcional_questionamentos, veredicto_direcional,
                confianca_direcional_ajustada,
                guardian_kill_switch, guardian_kill_reason,
                guardian_reduced_exposure, guardian_confidence_penalty,
                guardian_bias_override, guardian_scenario_changes,
                guardian_alertas,
                macro_signal_dominante, smc_equilibrium_dominante,
                adx_medio, micro_score_medio,
                active
            ) VALUES (
                ?, ?, ?,
                ?,
                ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?,
                ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?,
                ?, ?,
                ?, ?,
                ?
            )
        """, (
            d["date"], d["timestamp"], d["source"],
            d["nota_agente"],
            d["alertas_criticos"], d["incoerencias"], d["filtros_bloqueantes"],
            d["parametros_questionados"], d["sugestoes"],
            d["custo_oportunidade_pts"], d["eficiencia_pct"],
            d["hold_pct"], d["win_rate_pct"], d["market_range_pts"],
            d["n_opportunities"], d["n_episodes"],
            d["threshold_sugerido_buy"], d["threshold_sugerido_sell"],
            1 if d["smc_bypass_recomendado"] else 0,
            1 if d["trend_following_recomendado"] else 0,
            d["max_adx_para_trend"], d["confianca_minima_sugerida"],
            d["regioes_fortes"], d["regioes_armadilhas"], d["veredicto_regioes"],
            d["direcional_vieses"], d["direcional_contradicoes"],
            d["direcional_questionamentos"], d["veredicto_direcional"],
            d["confianca_direcional_ajustada"],
            1 if d["guardian_kill_switch"] else 0,
            d["guardian_kill_reason"],
            1 if d["guardian_reduced_exposure"] else 0,
            d["guardian_confidence_penalty"],
            d["guardian_bias_override"],
            d["guardian_scenario_changes"],
            d["guardian_alertas"],
            d["macro_signal_dominante"], d["smc_equilibrium_dominante"],
            d["adx_medio"], d["micro_score_medio"],
            1 if d["active"] else 0,
        ))

        feedback_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return feedback_id or 0

    except Exception as e:
        print(f"[ERRO] Falha ao salvar diary_feedback: {e}")
        return 0


def load_latest_feedback(db_path: str, today_only: bool = True) -> Optional[DiaryFeedback]:
    """Carrega o feedback mais recente do diário.

    Args:
        db_path: Caminho do banco SQLite
        today_only: Se True, busca apenas feedback de hoje

    Returns:
        DiaryFeedback mais recente ou None
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if today_only:
            today = date.today().isoformat()
            cursor.execute("""
                SELECT * FROM diary_feedback
                WHERE date = ? AND active = 1
                ORDER BY id DESC
                LIMIT 1
            """, (today,))
        else:
            cursor.execute("""
                SELECT * FROM diary_feedback
                WHERE active = 1
                ORDER BY id DESC
                LIMIT 1
            """)

        row = cursor.fetchone()
        conn.close()

        if row:
            return DiaryFeedback.from_dict(dict(row))
        return None

    except Exception:
        return None


def load_feedback_history(db_path: str, days: int = 5) -> list[DiaryFeedback]:
    """Carrega histórico de feedback dos últimos N dias.

    Útil para o agente aprender padrões de feedback ao longo do tempo.
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM diary_feedback
            WHERE active = 1
            ORDER BY id DESC
            LIMIT ?
        """, (days * 10,))  # ~10 feedbacks/dia (a cada 15 min por ~2.5h)

        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        return [DiaryFeedback.from_dict(r) for r in rows]

    except Exception:
        return []


def get_feedback_trend(db_path: str) -> dict:
    """Analisa tendência do feedback ao longo dos dias.

    Retorna evolução da nota, hold_pct, oportunidades.
    Útil para verificar se o agente está melhorando.
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Últimos 10 feedbacks
        cursor.execute("""
            SELECT date, nota_agente, hold_pct, n_opportunities,
                   win_rate_pct, eficiencia_pct, market_range_pts
            FROM diary_feedback
            WHERE active = 1
            ORDER BY id DESC
            LIMIT 30
        """)

        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        if not rows:
            return {"trend": "sem_dados", "improving": False}

        notas = [r["nota_agente"] for r in rows]
        holds = [r["hold_pct"] for r in rows]
        opps = [r["n_opportunities"] for r in rows]

        # Compara primeira metade vs segunda metade
        mid = len(notas) // 2
        if mid == 0:
            return {
                "trend": "poucos_dados",
                "improving": False,
                "nota_atual": notas[0],
                "hold_pct_atual": holds[0],
            }

        nota_recente = sum(notas[:mid]) / mid
        nota_anterior = sum(notas[mid:]) / (len(notas) - mid)
        improving = nota_recente > nota_anterior

        return {
            "trend": "melhorando" if improving else "piorando",
            "improving": improving,
            "nota_atual": notas[0],
            "nota_media_recente": nota_recente,
            "nota_media_anterior": nota_anterior,
            "hold_pct_atual": holds[0] if holds else 0,
            "opp_media": sum(opps) / len(opps) if opps else 0,
        }

    except Exception:
        return {"trend": "erro", "improving": False}
