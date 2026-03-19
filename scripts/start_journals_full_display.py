"""
Start Journals with Full Display - Diários com Análise RL.

Inicia 3 diários em threads separadas:
  1. Trading Journal — Narrativa macro/micro a cada 5 min
  2. AI Reflection — Auto-avaliação do sistema a cada 10 min
  3. RL Performance Diary — Análise de recompensas RL a cada 15 min
     - Lê episódios e rewards do SQLite (dados reais do agente)
     - Calcula range do mercado (pontos) vs oportunidades detectadas
     - Avalia se o agente acertou ou precisa ser aprimorado
"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import sqlite3
import threading
import time
from decimal import Decimal
from datetime import datetime, timedelta, date
from typing import Any
from config import get_config
from src.application.services.trading_journal import TradingJournalService
from src.application.services.quantum_operator import QuantumOperatorEngine
from src.application.services.ai_reflection_journal import AIReflectionJournalService
from src.domain.value_objects import Symbol
from src.infrastructure.adapters.mt5_adapter import MT5Adapter, TimeFrame
from src.application.services.diary_feedback import (
    DiaryFeedback,
    create_diary_feedback_table,
    save_diary_feedback,
)
from src.application.services.macro_scenario_guardian import (
    GuardianState,
    run_guardian_check,
    format_guardian_display,
    guardian_state_to_feedback_fields,
    GUARDIAN_INTERVAL_SEC,
)
from src.application.diario_order_manager import DiarioOrderManager
from src.application.diarios_watchdog import ThreadWatchdog, ConfiguracaoThread
from src.application.diario_observability_panel import ObservabilidadeDiarios
from src.application.opening_context_runtime import initialize_opening_context_runtime
from src.application.opening_context_report import (
    generate_opening_context_vs_result_report,
)
from src.application.confidence_utils import normalize_confidence
from src.application.retreino_micro_tendencia import GerenciadorRetreino

# ────────────────────────────────────────────────────────────────
# Macro Data Provider (REC2/REC6: dados ao vivo, não hardcoded)
# ────────────────────────────────────────────────────────────────
try:
    from scripts.agente_wdo_winfut.macro_data_provider import (
        get_bcb_selic,
        get_bcb_ipca,
        get_bcb_usd_brl,
        get_fred_dxy,
        get_fred_vix,
    )
    HAS_MACRO_PROVIDER = True
except ImportError:
    HAS_MACRO_PROVIDER = False

# --- Grupo 2: Feedback Validator (AC5.9) ---
try:
    from src.application.ac5_9_feedback_validator import (
        FeedbackValidator,
    )
    AC5_9_DISPONIVEL = True
except ImportError:
    AC5_9_DISPONIVEL = False
    FeedbackValidator = None  # type: ignore[assignment,misc]

# --- Grupo 3: Storytelling / Reflection Runtime (roadmap multiagentes) ---
try:
    from src.application.reflection_question_evolution import ReflectionQuestionEvolution
    HAS_REFLECTION_QUESTION_EVOLUTION = True
except ImportError:
    HAS_REFLECTION_QUESTION_EVOLUTION = False
    ReflectionQuestionEvolution = None  # type: ignore[assignment,misc]

try:
    from src.application.narrative_persistence import NarrativePersistence
    HAS_NARRATIVE_PERSISTENCE = True
except ImportError:
    HAS_NARRATIVE_PERSISTENCE = False
    NarrativePersistence = None  # type: ignore[assignment,misc]

try:
    from src.application.trade_narrative_correlator import TradeNarrativeCorrelator
    HAS_TRADE_NARRATIVE_CORRELATOR = True
except ImportError:
    HAS_TRADE_NARRATIVE_CORRELATOR = False
    TradeNarrativeCorrelator = None  # type: ignore[assignment,misc]

try:
    from src.application.narrative_dataset_exporter import build_dataset, to_json_payload
    HAS_NARRATIVE_DATASET_EXPORTER = True
except ImportError:
    HAS_NARRATIVE_DATASET_EXPORTER = False
    build_dataset = None  # type: ignore[assignment,misc]
    to_json_payload = None  # type: ignore[assignment,misc]

try:
    from src.application.diarios_runtime_mlops_bridge import DiarioRuntimeMlOpsBridge
    HAS_MLOPS_RUNTIME_BRIDGE = True
except ImportError:
    HAS_MLOPS_RUNTIME_BRIDGE = False
    DiarioRuntimeMlOpsBridge = None  # type: ignore[assignment,misc]


NARRATIVE_EXPORT_DIR = Path("outputs")
NARRATIVE_EXPORT_EVERY_N_CYCLES = 3
NARRATIVE_EXPORT_PREFIX = "narrative_dataset_ai_reflection"


def _fetch_live_macro() -> dict:
    """Busca dados macro ao vivo via APIs gratuitas."""
    defaults = {
        "dxy": Decimal("104.3"),
        "vix": Decimal("16.5"),
        "selic": Decimal("10.75"),
        "ipca": Decimal("4.5"),
        "usd_brl": Decimal("5.85"),
    }
    if not HAS_MACRO_PROVIDER:
        return defaults
    try:
        dxy = get_fred_dxy()
        vix = get_fred_vix()
        selic = get_bcb_selic()
        ipca = get_bcb_ipca()
        usd = get_bcb_usd_brl()
        return {
            "dxy": Decimal(str(dxy)) if dxy else defaults["dxy"],
            "vix": Decimal(str(vix)) if vix else defaults["vix"],
            "selic": Decimal(str(selic)) if selic else defaults["selic"],
            "ipca": Decimal(str(ipca)) if ipca else defaults["ipca"],
            "usd_brl": Decimal(str(usd)) if usd else defaults["usd_brl"],
        }
    except Exception:
        return defaults


# ────────────────────────────────────────────────────────────────
# EA ID (Magic Number) reservado para Agente Diários
# Hoje este agente NÃO envia ordens. Se no futuro enviar,
# usar este magic para isolar das demais:
#   RL 5000=234500 | Direto=234600 | Micro Tendência=234700
# ────────────────────────────────────────────────────────────────
MAGIC_NUMBER = 234800


# ────────────────────────────────────────────────────────────────
# DB Path helper
# ────────────────────────────────────────────────────────────────
def _get_db_path() -> str:
    """Retorna path do banco de dados do agente."""
    config = get_config()
    return getattr(config, "db_path", "data/db/trading.db")


def _coerce_datetime(value: Any) -> datetime:
    """Converte timestamps usados no runtime para datetime."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise TypeError("timestamp deve ser datetime ou string ISO")


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    """Converte valores numericos para float sem derrubar o ciclo."""
    try:
        if value is None:
            return fallback
        return float(value)
    except Exception:
        return fallback


def _normalize_confidence_percent(value: Any) -> float:
    """Normaliza confidence para escala 0-1 antes de exibir como percentual."""
    conf = _safe_float(value, 0.0)
    if conf < 0:
        return 0.0
    if conf > 1.0:
        return conf / 100.0
    return conf


def _format_learning_block(db_path: str) -> str:
    """Formata um bloco simples de aprendizado do micro tendencia."""
    try:
        mgr = GerenciadorRetreino(
            db_path=db_path,
            modelos_dir=str(project_root / "data" / "models" / "micro_tendencia"),
        )
        estado = mgr.obter_estado_aprendizado()
        return (
            "============================================================\n"
            "             APRENDIZADO DO MICRO TENDENCIA\n"
            "------------------------------------------------------------\n"
            f"  Episodios do micro         : {estado.episodios_acumulados}\n"
            f"  Recompensas do micro       : {estado.rewards_acumuladas}\n"
            f"  Retreino do micro          : faltam {estado.rewards_ate_proximo_treino}"
            f" / {estado.threshold_rewards} rewards\n"
            f"  Ultimo retreino            : {estado.ultima_versao_treino}\n"
            f"  Data do ultimo retreino    : {estado.ultima_data_treino}\n"
            "============================================================"
        )
    except Exception as exc:
        return f"[APRENDIZADO] indisponivel: {exc}"


def _build_runtime_order_history(perf: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrai historico simplificado para o learner de execucao."""
    history: list[dict[str, Any]] = []
    rewards_by_horizon = perf.get("rewards_by_horizon", {})
    if not isinstance(rewards_by_horizon, dict):
        return history

    for horizon_data in rewards_by_horizon.values():
        if not isinstance(horizon_data, dict):
            continue
        entries = horizon_data.get("entries", [])
        if not isinstance(entries, list):
            continue
        for entry in entries[-20:]:
            if not isinstance(entry, dict):
                continue
            pts = _safe_float(entry.get("pts", 0.0), 0.0)
            history.append(
                {
                    "quality_score": 100.0 if _safe_float(entry.get("correct", 0), 0.0) == 1.0 else 40.0,
                    "fill_rate": 1.0,
                    "latency_ms": 120.0,
                    "slippage_points": abs(pts) * 0.02,
                    "status": "FILLED",
                    "outcome": "WIN" if _safe_float(entry.get("correct", 0), 0.0) == 1.0 else "LOSS",
                }
            )
    return history


def _build_runtime_execution_patterns(perf: dict[str, Any]) -> dict[str, Any]:
    """Cria resumo de padroes para o learner de execucao."""
    evaluated = max(1, int(perf.get("n_rewards_evaluated", 0) or 0))
    correct = int(perf.get("correct_count", 0) or 0)
    fill_rate = correct / evaluated
    rejection_rate = 1.0 - fill_rate
    return {
        "summary": {
            "event_count": int(perf.get("n_episodes", 0) or 0),
            "fill_rate": max(0.0, min(1.0, fill_rate)),
            "avg_slippage_points": 0.8,
            "avg_latency_ms": 120.0,
            "rejection_rate": max(0.0, min(1.0, rejection_rate)),
            "failure_reasons": {},
        }
    }


def _build_reflection_question_context(
    reflection: Any,
    decision: Any,
    episodes: list[dict[str, Any]],
    opportunities: list[dict[str, Any]],
    change_10min: float,
) -> dict[str, Any]:
    """Cria o contexto minimo para evolucao das perguntas de reflexao."""
    decision_name = getattr(getattr(decision, "action", None), "value", None)
    confidence = _safe_float(getattr(decision, "confidence", None), 0.0)
    alignment = _safe_float(getattr(decision, "alignment_score", None), 0.0)

    return {
        "high_risk": confidence < 0.60 or abs(change_10min) >= 0.40,
        "emotional_instability": str(getattr(reflection, "mood", "")).upper() in {
            "CONFUSO",
            "FRUSTRADO",
            "CAOTICO",
            "PRESSURE",
            "PRESSIONADO",
        },
        "decision": decision_name or str(getattr(decision, "action", "")),
        "confidence": confidence,
        "alignment": alignment,
        "market_move_10min": change_10min,
        "episode_count": len(episodes),
        "opportunity_count": len(opportunities),
        "mood": getattr(reflection, "mood", None),
    }


def _build_narrative_text(
    reflection: Any,
    question_payloads: list[dict[str, Any]],
    latest_episode: dict[str, Any] | None,
) -> str:
    """Resume a narrativa em texto simples para persistencia e dataset."""
    parts = [
        str(getattr(reflection, "honest_assessment", "")),
        str(getattr(reflection, "what_im_seeing", "")),
        str(getattr(reflection, "data_relevance", "")),
        str(getattr(reflection, "am_i_useful", "")),
        str(getattr(reflection, "my_data_correlation", "")),
    ]
    if latest_episode:
        parts.append(
            "Episodio RL: "
            f"action={latest_episode.get('action')} "
            f"macro_score={latest_episode.get('macro_score_final')} "
            f"regime={latest_episode.get('market_regime')}"
        )
    if question_payloads:
        prompts = " | ".join(item["prompt"] for item in question_payloads)
        parts.append(f"Perguntas evolutivas: {prompts}")
    return "\n".join(part for part in parts if part)


def _build_trade_headline(reflection: Any, latest_episode: dict[str, Any] | None) -> str:
    """Cria um headline curto para a narrativa persistida."""
    if latest_episode:
        action = latest_episode.get("action") or latest_episode.get("side") or "UNKNOWN"
        episode_id = latest_episode.get("episode_id") or latest_episode.get("trade_id") or "NA"
        return f"Trade {episode_id} - {action}"
    return str(getattr(reflection, "one_liner", "Reflexao de mercado"))


class NarrativeRuntimeBridge:
    """Integra question evolution, persistence, correlation e export em runtime."""

    def __init__(
        self,
        export_dir: Path | str = NARRATIVE_EXPORT_DIR,
        export_every_n_cycles: int = NARRATIVE_EXPORT_EVERY_N_CYCLES,
        question_evolution: Any | None = None,
        persistence: Any | None = None,
        correlator: Any | None = None,
    ) -> None:
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.export_every_n_cycles = max(1, int(export_every_n_cycles))
        self.question_evolution = question_evolution
        self.persistence = persistence
        self.correlator = correlator
        self._used_prompts: list[str] = []
        self._cycle_count = 0

        if self.question_evolution is None and HAS_REFLECTION_QUESTION_EVOLUTION:
            self.question_evolution = ReflectionQuestionEvolution()
        if self.persistence is None and HAS_NARRATIVE_PERSISTENCE:
            self.persistence = NarrativePersistence()
        if self.correlator is None and HAS_TRADE_NARRATIVE_CORRELATOR:
            self.correlator = TradeNarrativeCorrelator()

    @property
    def enabled(self) -> bool:
        return self.question_evolution is not None or self.persistence is not None

    def process_cycle(
        self,
        reflection: Any,
        decision: Any,
        episodes: list[dict[str, Any]],
        opportunities: list[dict[str, Any]],
        historical_sessions: list[Any],
    ) -> dict[str, Any]:
        """Processa um ciclo completo de reflexao e exportacao."""
        self._cycle_count += 1
        latest_episode = episodes[-1] if episodes else None
        trade_id = str(
            (latest_episode or {}).get("episode_id")
            or (latest_episode or {}).get("trade_id")
            or getattr(reflection, "entry_id", "reflection")
        )

        question_context = _build_reflection_question_context(
            reflection=reflection,
            decision=decision,
            episodes=episodes,
            opportunities=opportunities,
            change_10min=_safe_float(getattr(reflection, "price_change_last_10min", 0.0)),
        )

        question_payloads: list[dict[str, Any]] = []
        if self.question_evolution is not None:
            try:
                questions = self.question_evolution.evolve_questions(
                    question_context,
                    historical_sessions,
                    used_prompts=self._used_prompts,
                    limit=3,
                )
                question_payloads = [question.to_dict() for question in questions]
                if question_payloads:
                    print("Perguntas evolutivas:")
                    for idx, question in enumerate(question_payloads, start=1):
                        print(
                            f"  {idx}. [{question['level']}/{question['category']}] "
                            f"{question['prompt']}"
                        )
                    self._used_prompts.extend(item["prompt"] for item in question_payloads)
            except Exception as exc:
                print(f"[NARRATIVES] Falha ao gerar perguntas evolutivas: {exc}")

        if self.persistence is not None:
            try:
                reflection_record = self._build_reflection_record(
                    reflection=reflection,
                    trade_id=trade_id,
                    question_payloads=question_payloads,
                    latest_episode=latest_episode,
                    decision=decision,
                    question_context=question_context,
                )
                self.persistence.save_narrative(reflection_record)

                if latest_episode is not None:
                    trade_record = self._build_trade_record(
                        reflection=reflection,
                        latest_episode=latest_episode,
                        trade_id=trade_id,
                        question_context=question_context,
                    )
                    self.persistence.save_narrative(trade_record)
            except Exception as exc:
                print(f"[NARRATIVES] Falha ao persistir narrativas em memoria: {exc}")

        export_path: Path | None = None
        if (
            self.persistence is not None
            and self.correlator is not None
            and HAS_NARRATIVE_DATASET_EXPORTER
            and self._cycle_count % self.export_every_n_cycles == 0
        ):
            try:
                export_path = self.export_dataset(episodes)
                if export_path is not None:
                    print(f"[NARRATIVES] Dataset exportado em {export_path}")
            except Exception as exc:
                print(f"[NARRATIVES] Falha ao exportar dataset: {exc}")

        return {
            "trade_id": trade_id,
            "questions": question_payloads,
            "export_path": str(export_path) if export_path is not None else None,
        }

    def export_dataset(self, episodes: list[dict[str, Any]]) -> Path | None:
        """Exporta o dataset de narrativas para JSON em outputs/."""
        if self.persistence is None or self.correlator is None:
            return None
        records = self.persistence.list_all()
        if not records:
            return None

        correlation = self.correlator.correlate(episodes, records)
        dataset = build_dataset(records)
        dataset["correlation_summary"] = {
            "total_trades": correlation.get("total_trades", 0),
            "total_narratives": correlation.get("total_narratives", 0),
            "correlated_trades": correlation.get("correlated_trades", 0),
            "correlation_rate": correlation.get("correlation_rate", 0.0),
            "direct_matches": correlation.get("direct_matches", 0),
            "temporal_matches": correlation.get("temporal_matches", 0),
        }
        dataset["correlation_features"] = self.correlator.extract_features(
            correlation.get("correlations", [])
        )

        payload = to_json_payload(dataset)
        output_path = self.export_dir / (
            f"{NARRATIVE_EXPORT_PREFIX}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        output_path.write_text(payload, encoding="utf-8")
        return output_path

    def _build_reflection_record(
        self,
        reflection: Any,
        trade_id: str,
        question_payloads: list[dict[str, Any]],
        latest_episode: dict[str, Any] | None,
        decision: Any,
        question_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Serializa a reflexao principal para persistencia narrativa."""
        action_name = getattr(getattr(decision, "action", None), "value", None)
        confidence = _safe_float(getattr(decision, "confidence", None))
        alignment = _safe_float(getattr(decision, "alignment_score", None))
        record_context = {
            "source": "ai_reflection",
            "decision": action_name or str(getattr(decision, "action", "")),
            "confidence": confidence,
            "alignment": alignment,
            "current_price": _safe_float(getattr(reflection, "current_price", 0.0)),
            "price_change_since_open": _safe_float(
                getattr(reflection, "price_change_since_open", 0.0)
            ),
            "price_change_last_10min": _safe_float(
                getattr(reflection, "price_change_last_10min", 0.0)
            ),
            "question_context": dict(question_context),
            "questions": question_payloads,
        }
        if latest_episode is not None:
            record_context["latest_episode"] = {
                "episode_id": latest_episode.get("episode_id"),
                "timestamp": latest_episode.get("timestamp"),
                "action": latest_episode.get("action"),
                "macro_score_final": latest_episode.get("macro_score_final"),
                "market_regime": latest_episode.get("market_regime"),
            }

        return {
            "trade_id": trade_id,
            "timestamp": getattr(reflection, "timestamp"),
            "headline": str(getattr(reflection, "one_liner", "Reflexao de mercado")),
            "narrative": _build_narrative_text(reflection, question_payloads, latest_episode),
            "category": "reflection",
            "session_id": None,
            "outcome": action_name,
            "tags": [
                "ai_reflection",
                f"mood_{str(getattr(reflection, 'mood', 'unknown')).lower()}",
                f"decision_{str(action_name or getattr(decision, 'action', 'unknown')).lower()}",
            ],
            "context": record_context,
        }

    def _build_trade_record(
        self,
        reflection: Any,
        latest_episode: dict[str, Any],
        trade_id: str,
        question_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Serializa o ultimo trade do ciclo como narrativa correlacionavel."""
        raw_timestamp = latest_episode.get("timestamp")
        trade_timestamp = _coerce_datetime(raw_timestamp) if raw_timestamp else getattr(
            reflection,
            "timestamp",
        )
        action = latest_episode.get("action") or latest_episode.get("side") or "UNKNOWN"
        headline = _build_trade_headline(reflection, latest_episode)

        context = {
            "source": "rl_episode",
            "question_context": dict(question_context),
            "episode_id": latest_episode.get("episode_id"),
            "action": action,
            "macro_score_final": latest_episode.get("macro_score_final"),
            "micro_score": latest_episode.get("micro_score"),
            "market_regime": latest_episode.get("market_regime"),
            "session_phase": latest_episode.get("session_phase"),
            "alignment_score": latest_episode.get("alignment_score"),
        }

        return {
            "trade_id": trade_id,
            "timestamp": trade_timestamp,
            "headline": headline,
            "narrative": (
                f"Episodio RL {latest_episode.get('episode_id')} com acao {action}. "
                f"Macro score={latest_episode.get('macro_score_final')} | "
                f"micro score={latest_episode.get('micro_score')} | "
                f"regime={latest_episode.get('market_regime')}"
            ),
            "category": "trade",
            "session_id": None,
            "outcome": str(action),
            "tags": ["trade", "rl_episode"],
            "context": context,
        }


# ────────────────────────────────────────────────────────────────
# RL Performance Reader — Leitura direta do SQLite
# ────────────────────────────────────────────────────────────────

class RLPerformanceReader:
    """Lê e analisa episódios/rewards RL do banco do agente."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_today_episodes(self) -> list[dict]:
        """Retorna todos os episódios RL do dia corrente."""
        today = date.today().isoformat()
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT episode_id, timestamp, source, action,
                       win_price, win_open_price, win_high_of_day, win_low_of_day,
                       macro_score_final, micro_score, micro_trend,
                       alignment_score, overall_confidence,
                       market_regime, session_phase,
                       smc_direction, smc_equilibrium,
                       vwap_position, probability_up, probability_down,
                       macro_bias, technical_bias, sentiment_bias,
                       entry_price, stop_loss, take_profit, risk_reward_ratio,
                       reasoning
                FROM rl_episodes
                WHERE session_date = ? OR date(timestamp) = ?
                ORDER BY timestamp ASC
            """, (today, today))
            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return rows
        except Exception:
            return []

    def get_today_rewards(self) -> list[dict]:
        """Retorna rewards avaliados do dia corrente."""
        today = date.today().isoformat()
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.episode_id, r.horizon_minutes, r.action_at_decision,
                       r.win_price_at_decision, r.win_price_at_evaluation,
                       r.price_change_points, r.price_change_pct,
                       r.reward_direction, r.was_correct,
                       r.reward_normalized, r.reward_continuous,
                       r.max_favorable_points, r.max_adverse_points,
                       r.is_evaluated
                FROM rl_rewards r
                WHERE date(r.timestamp_decision) = ?
                ORDER BY r.timestamp_decision ASC, r.horizon_minutes ASC
            """, (today,))
            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return rows
        except Exception:
            return []

    def get_today_micro_decisions(self) -> list[dict]:
        """Retorna decisões de micro tendência do dia."""
        today = date.today().isoformat()
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, timestamp, macro_score, macro_signal, macro_confidence,
                       micro_score, micro_trend, price_current, price_open,
                       vwap, pivot_pp, smc_direction, smc_equilibrium,
                       adx, rsi, num_opportunities,
                       macro_score_raw, directive_suspended
                FROM micro_trend_decisions
                WHERE date(timestamp) = ?
                ORDER BY timestamp ASC
            """, (today,))
            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return rows
        except Exception:
            return []

    def get_today_opportunities(self) -> list[dict]:
        """Retorna oportunidades detectadas hoje."""
        today = date.today().isoformat()
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT o.direction, o.entry, o.stop_loss, o.take_profit,
                       o.risk_reward, o.confidence, o.reason, o.region,
                       o.timestamp
                FROM micro_trend_opportunities o
                WHERE date(o.timestamp) = ?
                ORDER BY o.timestamp ASC
            """, (today,))
            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return rows
        except Exception:
            return []

    def get_today_regions(self) -> list[dict]:
        """Retorna regiões de interesse mapeadas hoje."""
        today = date.today().isoformat()
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.price, r.label, r.tipo, r.confluences,
                       r.distance_pct, r.timestamp, r.decision_id
                FROM micro_trend_regions r
                WHERE date(r.timestamp) = ?
                ORDER BY r.timestamp ASC
            """, (today,))
            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return rows
        except Exception:
            return []

    def get_today_macro_items(self) -> list[dict]:
        """Retorna items macro do último ciclo do dia (breakdown por categoria)."""
        today = date.today().isoformat()
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            # Pegar o último decision_id do dia
            cursor.execute("""
                SELECT id FROM micro_trend_decisions
                WHERE date(timestamp) = ?
                ORDER BY id DESC LIMIT 1
            """, (today,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return []
            last_id = row["id"]
            # Buscar todos os items desse ciclo
            cursor.execute("""
                SELECT symbol, category, score, price_current, price_open
                FROM micro_trend_items
                WHERE decision_id = ?
                ORDER BY category, item_number
            """, (last_id,))
            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return rows
        except Exception:
            return []

    def get_macro_category_history(self) -> dict:
        """Retorna evolução histórica do score por categoria ao longo do dia.

        Para cada categoria, calcula o score em cada ciclo do dia,
        permitindo detectar viradas, divergências crescentes, etc.
        """
        today = date.today().isoformat()
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT d.id as decision_id, d.timestamp,
                       i.category, i.score, i.symbol
                FROM micro_trend_items i
                JOIN micro_trend_decisions d ON d.id = i.decision_id
                WHERE date(d.timestamp) = ?
                ORDER BY d.timestamp ASC, i.category
            """, (today,))
            rows = cursor.fetchall()
            conn.close()

            # Agrupar por decision_id → categoria → soma de scores
            history = {}  # {category: [(timestamp, score_sum, n_items)]}
            cycle_data = {}  # {decision_id: {category: {score_sum, n_items, timestamp}}}

            for r in rows:
                did = r["decision_id"]
                cat = r["category"]
                if did not in cycle_data:
                    cycle_data[did] = {}
                if cat not in cycle_data[did]:
                    cycle_data[did][cat] = {"score": 0, "n": 0, "ts": r["timestamp"]}
                cycle_data[did][cat]["score"] += r["score"]
                cycle_data[did][cat]["n"] += 1

            for did in sorted(cycle_data.keys()):
                for cat, data in cycle_data[did].items():
                    if cat not in history:
                        history[cat] = []
                    history[cat].append((data["ts"], data["score"], data["n"]))

            return history
        except Exception:
            return {}

    def analyze_directional_critical(self) -> dict:
        """Análise CRÍTICA nível Head sobre o direcional do dia.

        Questiona como advogado do diabo:
        - O score está inflado por uma categoria dominante?
        - Existem contradições entre categorias correlacionadas?
        - A confiança é compatível com o score?
        - Categorias negativas estão sendo ignoradas?
        - O score mudou de direção ao longo do dia?
        - Há divergência entre mercados locais e globais?

        Objetivo: garantir que o direcional não é um viés falso.
        """
        items = self.get_today_macro_items()
        episodes = self.get_today_episodes()
        cat_history = self.get_macro_category_history()

        result = {
            "questionamentos": [],
            "contradicoes": [],
            "vieses_detectados": [],
            "veredicto": "",
            "confianca_ajustada": 0,
            "detalhes_categorias": [],
        }

        if not items:
            result["veredicto"] = "Sem dados de items macro para analisar"
            return result

        # ── 1. BREAKDOWN POR CATEGORIA ──
        categories = {}
        for item in items:
            cat = item["category"]
            if cat not in categories:
                categories[cat] = {"score": 0, "pos": 0, "neg": 0, "n": 0, "symbols": []}
            categories[cat]["score"] += item["score"]
            categories[cat]["n"] += 1
            if item["score"] > 0:
                categories[cat]["pos"] += 1
            elif item["score"] < 0:
                categories[cat]["neg"] += 1
            categories[cat]["symbols"].append((item["symbol"], item["score"]))

        total_score = sum(c["score"] for c in categories.values())
        total_items = sum(c["n"] for c in categories.values())
        positive_cats = [c for c, d in categories.items() if d["score"] > 0]
        negative_cats = [c for c, d in categories.items() if d["score"] < 0]
        neutral_cats = [c for c, d in categories.items() if d["score"] == 0]

        # Macro dados do episódio mais recente
        last_ep = episodes[-1] if episodes else {}
        macro_conf = float(last_ep.get("macro_confidence", 0))

        # ── 2. CONCENTRAÇÃO — score inflado por 1 categoria? ──
        if categories:
            sorted_cats = sorted(categories.items(), key=lambda x: abs(x[1]["score"]), reverse=True)
            top_cat, top_data = sorted_cats[0]
            top_contribution_pct = abs(top_data["score"]) / max(abs(total_score), 1) * 100

            if top_contribution_pct > 40 and len(categories) > 3:
                result["vieses_detectados"].append(
                    f"CONCENTRAÇÃO: '{top_cat}' contribui {top_contribution_pct:.0f}% do score total "
                    f"(+{top_data['score']} de {total_score:+d}). "
                    f"Se essa categoria estiver errada, o direcional inteiro é questionável.")

            # Top 2 dominam?
            if len(sorted_cats) >= 2:
                top2_score = abs(sorted_cats[0][1]["score"]) + abs(sorted_cats[1][1]["score"])
                top2_pct = top2_score / max(abs(total_score), 1) * 100
                if top2_pct > 65:
                    result["vieses_detectados"].append(
                        f"2 categorias ({sorted_cats[0][0]} + {sorted_cats[1][0]}) "
                        f"dominam {top2_pct:.0f}% do score. Diversificação fraca.")

        # ── 3. CONTRADIÇÕES ENTRE CATEGORIAS CORRELACIONADAS ──
        # a) Brasil vs Global
        br_score = categories.get("INDICES_BRASIL", {}).get("score", 0)
        gl_score = categories.get("INDICES_GLOBAIS", {}).get("score", 0)
        if br_score > 5 and gl_score < -2:
            result["contradicoes"].append(
                f"BRASIL vs GLOBAL: Índices Brasil +{br_score} mas Globais {gl_score}. "
                f"Rally brasileiro ISOLADO? Cuidado com correção se globais piorarem.")
        elif br_score < -5 and gl_score > 2:
            result["contradicoes"].append(
                f"BRASIL vs GLOBAL: Índices Brasil {br_score} contra Globais +{gl_score}. "
                f"Problema DOMÉSTICO específico? Pode reverter se global puxar.")

        # b) Dólar vs Ações Brasil (inversamente correlacionados)
        dolar_score = categories.get("DOLAR_CAMBIO", {}).get("score", 0)
        acoes_score = categories.get("ACOES_BRASIL", {}).get("score", 0)
        if dolar_score > 0 and acoes_score > 0:
            result["contradicoes"].append(
                f"CONTRADIÇÃO: Dólar +{dolar_score} E Ações Brasil +{acoes_score}. "
                f"Normalmente inversamente correlacionados. Sinal confuso.")
        if dolar_score < -2 and acoes_score > 3:
            result["questionamentos"].append(
                f"ALINHAMENTO FORTE: Dólar caindo ({dolar_score}) + Ações subindo (+{acoes_score}). "
                f"Fluxo estrangeiro entrando? Confirma tendência de alta.")

        # c) Commodities vs Câmbio
        comm_score = categories.get("COMMODITIES", {}).get("score", 0)
        if comm_score > 3 and dolar_score > 0:
            result["contradicoes"].append(
                f"COMMODITIES vs DÓLAR: Commodities +{comm_score} mas Dólar +{dolar_score}. "
                f"Commodities em alta normalmente pressionam dólar pra baixo no Brasil.")

        # d) Juros vs Ações
        juros_score = categories.get("JUROS_RENDA_FIXA", {}).get("score", 0)
        curva_score = categories.get("CURVA_JUROS", {}).get("score", 0)
        juros_total = juros_score + curva_score
        if juros_total > 3 and acoes_score > 3:
            result["questionamentos"].append(
                f"JUROS E AÇÕES subindo juntos (juros +{juros_total}, ações +{acoes_score}). "
                f"Normal em cenário de queda de juros onde bonds sobem. "
                f"Se for alta de juros futuros, cuidado — equity pode sofrer depois.")

        # e) Cripto vs Risk-on
        cripto_score = categories.get("CRIPTOMOEDAS", {}).get("score", 0)
        if cripto_score < -3 and total_score > 10:
            result["questionamentos"].append(
                f"ATENÇÃO: Cripto em queda ({cripto_score}) com mercado geral bullish (+{total_score}). "
                f"Cripto frequentemente antecipa risk-off. Monitorar reversão global.")
        elif cripto_score > 3 and total_score < -5:
            result["questionamentos"].append(
                f"Cripto subindo (+{cripto_score}) contra mercado geral ({total_score}). "
                f"Pode indicar fuga de capital para ativos alternativos.")

        # f) Volatilidade vs Score
        vol_score = categories.get("VOLATILIDADE", {}).get("score", 0)
        if vol_score < 0 and total_score > 0:
            result["questionamentos"].append(
                f"VIX/Volatilidade negativa ({vol_score}) com score bullish (+{total_score}). "
                f"Normal — volatilidade sobe em mercado de queda. Mas se VIX dispara "
                f"com score ainda positivo, pode ser sinal prévio de reversão.")

        # g) Indicadores técnicos vs Score macro
        tech_score = categories.get("INDICADORES_TECNICOS", {}).get("score", 0)
        if total_score > 10 and tech_score < 0:
            result["contradicoes"].append(
                f"MACRO vs TÉCNICO: Score macro +{total_score} mas indicadores técnicos {tech_score}. "
                f"Fundamentos puxando mas gráfico não confirma ainda — CUIDADO com timing.")
        elif total_score < -10 and tech_score > 0:
            result["contradicoes"].append(
                f"MACRO vs TÉCNICO: Score macro {total_score} mas técnico +{tech_score}. "
                f"Gráfico ainda positivo mas fundamentos deteriorando. Pode ser atraso.")

        # h) Fluxo vs Score
        fluxo_score = categories.get("FLUXO_MICROESTRUTURA", {}).get("score", 0)
        if total_score > 15 and fluxo_score <= 0:
            result["questionamentos"].append(
                f"Score forte (+{total_score}) mas fluxo/microestrutura neutro ({fluxo_score}). "
                f"Preço pode não ter o empurrão necessário para seguir — risco de "
                f"'todos sabem que é COMPRA' mas ninguém está comprando.")

        # ── 4. CONFIANÇA vs SCORE ──
        if total_score > 20 and macro_conf < 0.65:
            result["questionamentos"].append(
                f"Score alto (+{total_score}) mas confiança baixa ({macro_conf*100:.0f}%). "
                f"Muitos itens indisponíveis? Dados parciais podem distorcer o score.")
        elif total_score > 5 and total_score < 15 and macro_conf > 0.80:
            result["questionamentos"].append(
                f"Score modesto (+{total_score}) mas confiança alta ({macro_conf*100:.0f}%). "
                f"Mercado dividido entre categorias — direcional fraco apesar da confiança.")

        # ── 5. MUITAS CATEGORIAS NEGATIVAS ──
        if len(negative_cats) >= len(positive_cats) and total_score > 0:
            result["vieses_detectados"].append(
                f"MAIS categorias negativas ({len(negative_cats)}) que positivas "
                f"({len(positive_cats)}), mas score total positivo (+{total_score}). "
                f"Poucas categorias de peso estão carregando o score inteiro. "
                f"Diversificação FRACA do sinal.")

        # ── 6. EVOLUÇÃO INTRA-DIA ──
        if cat_history:
            # Verificar se o score total mudou de sinal durante o dia
            total_by_cycle = []
            for cat, hist in cat_history.items():
                for ts, score, n in hist:
                    # Acumular por timestamp
                    found = False
                    for entry in total_by_cycle:
                        if entry[0] == ts:
                            entry[1] += score
                            found = True
                            break
                    if not found:
                        total_by_cycle.append([ts, score])

            if len(total_by_cycle) >= 3:
                total_by_cycle.sort()
                scores_cycle = [s for _, s in total_by_cycle]
                first_half = scores_cycle[:len(scores_cycle)//2]
                second_half = scores_cycle[len(scores_cycle)//2:]
                avg_first = sum(first_half) / len(first_half) if first_half else 0
                avg_second = sum(second_half) / len(second_half) if second_half else 0

                if avg_first > 5 and avg_second < avg_first * 0.5:
                    result["questionamentos"].append(
                        f"DETERIORAÇÃO: Score médio caiu de +{avg_first:.0f} "
                        f"(1ª metade) para +{avg_second:.0f} (2ª metade). "
                        f"Momentum do direcional ENFRAQUECENDO.")
                elif avg_first < -5 and avg_second > avg_first * 0.5:
                    result["questionamentos"].append(
                        f"RECUPERAÇÃO: Score melhorando de {avg_first:.0f} para "
                        f"{avg_second:.0f}. Tendência de reversão em andamento.")

                # Categoria que mudou de sinal
                for cat, hist in cat_history.items():
                    if len(hist) >= 3:
                        first_scores = [s for _, s, _ in hist[:len(hist)//2]]
                        last_scores = [s for _, s, _ in hist[len(hist)//2:]]
                        avg_f = sum(first_scores) / len(first_scores) if first_scores else 0
                        avg_l = sum(last_scores) / len(last_scores) if last_scores else 0
                        if avg_f > 2 and avg_l < -1:
                            result["contradicoes"].append(
                                f"VIRADA: '{cat}' mudou de +{avg_f:.0f} para {avg_l:.0f} "
                                f"durante o dia. Categoria virou contra o direcional.")
                        elif avg_f < -2 and avg_l > 1:
                            result["questionamentos"].append(
                                f"VIRADA POSITIVA: '{cat}' saiu de {avg_f:.0f} para "
                                f"+{avg_l:.0f}. Categoria agora apoia o direcional.")

        # ── 7. DETALHES POR CATEGORIA ──
        for cat, data in sorted(categories.items(), key=lambda x: abs(x[1]["score"]), reverse=True):
            pct_of_total = data["score"] / max(abs(total_score), 1) * 100
            # Consenso interno da categoria
            if data["n"] > 3:
                consenso = (data["pos"] - data["neg"]) / data["n"] * 100
            else:
                consenso = 100 if data["score"] != 0 else 0

            alinhado_str = "✓ ALINHADO" if (data["score"] > 0 and total_score > 0) or (data["score"] < 0 and total_score < 0) else "✗ CONTRA"
            if data["score"] == 0:
                alinhado_str = "= NEUTRO"

            result["detalhes_categorias"].append({
                "categoria": cat,
                "score": data["score"],
                "pos": data["pos"],
                "neg": data["neg"],
                "n_items": data["n"],
                "pct_of_total": pct_of_total,
                "consenso_interno": consenso,
                "alinhado": alinhado_str,
            })

        # ── VEREDICTO ──
        n_issues = len(result["contradicoes"]) + len(result["vieses_detectados"])
        n_questions = len(result["questionamentos"])

        if n_issues == 0 and n_questions <= 1:
            result["veredicto"] = (
                f"DIRECIONAL SÓLIDO — Score +{total_score} com {len(positive_cats)} categorias "
                f"positivas, sem contradições significativas. Operar com confiança.")
            result["confianca_ajustada"] = min(90, int(macro_conf * 100) + 5)
        elif n_issues <= 1 and n_questions <= 3:
            result["veredicto"] = (
                f"DIRECIONAL QUESTIONÁVEL — Score +{total_score} com "
                f"{n_issues} contradição(ões) e {n_questions} questão(ões). "
                f"Operar apenas se confirmado por técnico + fluxo.")
            result["confianca_ajustada"] = max(40, int(macro_conf * 100) - 10)
        elif n_issues >= 2:
            result["veredicto"] = (
                f"DIRECIONAL FRACO — Score +{total_score} mas {n_issues} contradições "
                f"entre categorias. O score pode estar INFLADO. "
                f"Reduzir exposição ou aguardar confirmação.")
            result["confianca_ajustada"] = max(30, int(macro_conf * 100) - 20)
        else:
            result["veredicto"] = (
                f"DIRECIONAL INCERTO — {n_questions} questões abertas, "
                f"mercado dividido. Cautela recomendada.")
            result["confianca_ajustada"] = max(35, int(macro_conf * 100) - 15)

        return result

    def analyze_region_behavior(self) -> list[dict]:
        """Analisa se o preço respeitou ou furou cada região mapeada.

        Para cada região única, verifica a história de preços:
         - RESPEITOU: preço chegou ±50 pts e depois reverteu ≥100 pts
         - FUROU: preço cruzou a região e seguiu ≥100 pts além
         - NÃO TESTADO: preço nunca chegou a ±50 pts da região
         - TESTANDO: preço está na zona agora (±50 pts)
        """
        regions_raw = self.get_today_regions()
        decisions = self.get_today_micro_decisions()

        if not regions_raw or not decisions:
            return []

        # Obter histórico de preços com timestamps
        price_history = []
        for d in decisions:
            p = d.get("price_current")
            ts = d.get("timestamp", "")
            if p:
                price_history.append((ts, float(p)))

        if not price_history:
            return []

        # Deduplicar regiões por preço (±30 pts = mesma região)
        unique_regions = []
        seen_prices = []
        DEDUP_TOLERANCE = 30.0

        for reg in regions_raw:
            price = float(reg["price"])
            is_dup = False
            for sp in seen_prices:
                if abs(price - sp) <= DEDUP_TOLERANCE:
                    is_dup = True
                    break
            if not is_dup:
                seen_prices.append(price)
                unique_regions.append(reg)

        # Analisar cada região
        TOUCH_ZONE = 50.0      # pts — considera "chegou na região"
        CONFIRM_MOVE = 100.0   # pts — movimento de confirmação
        results = []

        current_price = price_history[-1][1] if price_history else 0

        for reg in unique_regions:
            reg_price = float(reg["price"])
            tipo = reg.get("tipo", "")
            label = reg.get("label", "")
            confluences = reg.get("confluences", 1)

            # Encontrar momentos em que o preço tocou a região
            touches = []
            for i, (ts, p) in enumerate(price_history):
                if abs(p - reg_price) <= TOUCH_ZONE:
                    touches.append((i, ts, p))

            if not touches:
                status = "NÃO TESTADO"
                detail = "Preço não chegou nesta região"
            else:
                # Pegar o PRIMEIRO toque
                first_touch_idx, first_touch_ts, first_touch_price = touches[0]

                # Verificar o que aconteceu DEPOIS do toque
                prices_after = [p for _, p in price_history[first_touch_idx:]]

                if not prices_after or len(prices_after) < 3:
                    status = "TESTANDO"
                    detail = f"Toque recente em {first_touch_ts[:19]}"
                else:
                    if tipo == "RESISTENCIA":
                        # Resistência: preço subiu até a região
                        max_above = max(prices_after) - reg_price
                        min_after = min(prices_after[1:])
                        pullback = reg_price - min_after

                        if max_above > CONFIRM_MOVE:
                            status = "FUROU ↑"
                            detail = f"Rompeu +{max_above:.0f} pts acima"
                        elif pullback > CONFIRM_MOVE:
                            status = "RESPEITOU ↓"
                            detail = f"Rejeitou, caiu {pullback:.0f} pts"
                        elif abs(current_price - reg_price) <= TOUCH_ZONE:
                            status = "TESTANDO"
                            detail = "Preço na zona agora"
                        else:
                            status = "RESPEITOU ↓"
                            detail = f"Recuou {pullback:.0f} pts"
                    elif tipo == "SUPORTE":
                        # Suporte: preço caiu até a região
                        min_below = reg_price - min(prices_after)
                        max_after = max(prices_after[1:])
                        bounce = max_after - reg_price

                        if min_below > CONFIRM_MOVE:
                            status = "FUROU ↓"
                            detail = f"Rompeu {min_below:.0f} pts abaixo"
                        elif bounce > CONFIRM_MOVE:
                            status = "RESPEITOU ↑"
                            detail = f"Segurou, subiu {bounce:.0f} pts"
                        elif abs(current_price - reg_price) <= TOUCH_ZONE:
                            status = "TESTANDO"
                            detail = "Preço na zona agora"
                        else:
                            status = "RESPEITOU ↑"
                            detail = f"Segurou, subiu {bounce:.0f} pts"
                    else:
                        status = "TOCOU"
                        detail = f"Toque em {first_touch_ts[:19]}"

            results.append({
                "price": reg_price,
                "label": label,
                "tipo": tipo,
                "confluences": confluences,
                "status": status,
                "detail": detail,
                "n_touches": len(touches),
            })

        # Ordenar por preço (maior→menor)
        results.sort(key=lambda x: x["price"], reverse=True)
        return results

    def analyze_performance(self) -> dict:
        """Análise completa de performance RL do dia."""
        episodes = self.get_today_episodes()
        rewards = self.get_today_rewards()
        decisions = self.get_today_micro_decisions()
        opportunities = self.get_today_opportunities()

        # --- Range do mercado ---
        market_high = 0.0
        market_low = float("inf")
        market_open = 0.0
        market_current = 0.0

        for ep in episodes:
            h = float(ep.get("win_high_of_day") or 0)
            l = float(ep.get("win_low_of_day") or 0)
            if h > market_high:
                market_high = h
            if l > 0 and l < market_low:
                market_low = l

        # Fallback para micro decisions se RL não tem dados de high/low
        if market_high == 0 and decisions:
            prices = [float(d["price_current"]) for d in decisions if d.get("price_current")]
            if prices:
                market_high = max(prices)
                market_low = min(prices)

        if episodes:
            market_open = float(episodes[0].get("win_open_price") or episodes[0].get("win_price") or 0)
            market_current = float(episodes[-1].get("win_price") or 0)
        elif decisions:
            market_open = float(decisions[0].get("price_open") or 0)
            market_current = float(decisions[-1].get("price_current") or 0)

        market_range_pts = market_high - market_low if market_low < float("inf") else 0

        # --- Rewards avaliados ---
        evaluated = [r for r in rewards if r.get("is_evaluated") == 1]
        pending = [r for r in rewards if r.get("is_evaluated") == 0]

        correct = sum(1 for r in evaluated if r.get("was_correct") == 1)
        incorrect = sum(1 for r in evaluated if r.get("was_correct") == 0)
        total_eval = len(evaluated)
        win_rate = (correct / total_eval * 100) if total_eval > 0 else 0.0

        # Reward médio por horizonte
        rewards_by_horizon = {}
        for r in evaluated:
            h = r["horizon_minutes"]
            if h not in rewards_by_horizon:
                rewards_by_horizon[h] = {"total": 0, "correct": 0, "pts": [], "normalized": []}
            rewards_by_horizon[h]["total"] += 1
            if r.get("was_correct") == 1:
                rewards_by_horizon[h]["correct"] += 1
            if r.get("price_change_points") is not None:
                rewards_by_horizon[h]["pts"].append(float(r["price_change_points"]))
            if r.get("reward_normalized") is not None:
                rewards_by_horizon[h]["normalized"].append(float(r["reward_normalized"]))

        # --- Ações tomadas ---
        actions = {}
        for ep in episodes:
            a = ep.get("action", "UNKNOWN")
            actions[a] = actions.get(a, 0) + 1

        # --- Oportunidades ---
        opp_buy = sum(1 for o in opportunities if o.get("direction") == "BUY")
        opp_sell = sum(1 for o in opportunities if o.get("direction") == "SELL")

        # --- Diagnóstico do agente ---
        diagnostico = self._diagnosticar(
            market_range_pts=market_range_pts,
            n_episodes=len(episodes),
            n_decisions=len(decisions),
            n_opportunities=len(opportunities),
            win_rate=win_rate,
            total_eval=total_eval,
            actions=actions,
        )

        return {
            "timestamp": datetime.now().isoformat(),
            "date": date.today().isoformat(),
            # Mercado
            "market_open": market_open,
            "market_current": market_current,
            "market_high": market_high,
            "market_low": market_low if market_low < float("inf") else 0,
            "market_range_pts": market_range_pts,
            "market_change_pts": market_current - market_open if market_open > 0 else 0,
            # Episódios RL
            "n_episodes": len(episodes),
            "n_rewards_evaluated": total_eval,
            "n_rewards_pending": len(pending),
            "win_rate_pct": win_rate,
            "correct_count": correct,
            "incorrect_count": incorrect,
            "rewards_by_horizon": rewards_by_horizon,
            # Micro decisões
            "n_micro_decisions": len(decisions),
            "n_opportunities": len(opportunities),
            "opp_buy": opp_buy,
            "opp_sell": opp_sell,
            # Ações
            "actions_distribution": actions,
            # Diagnóstico
            "diagnostico": diagnostico,
        }

    def analyze_agent_coherence(self) -> dict:
        """Análise PROFUNDA de coerência do agente — cruza dados para encontrar problemas.

        Faz o que o Head Global faria:
        - Cruza macro_signal vs ações do agente
        - Analisa se SMC está bloqueando tudo
        - Verifica se ADX justifica thresholds atuais
        - Calcula custo de oportunidade (pts deixados na mesa)
        - Questiona parâmetros e configurações
        - Sugere mudanças concretas
        """
        episodes = self.get_today_episodes()
        decisions = self.get_today_micro_decisions()
        opportunities = self.get_today_opportunities()
        rewards = self.get_today_rewards()

        result = {
            "alertas_criticos": [],
            "incoerencias": [],
            "filtros_bloqueantes": [],
            "parametros_questionados": [],
            "custo_oportunidade": {},
            "sugestoes": [],
            "nota_agente": 10,  # Começa com 10, desconta por problema
        }

        # BUG-DIARIOS-02: Calcular pts_capturados via rewards avaliados (BUY/SELL corretos)
        _pts_capturados = 0.0
        for r in rewards:
            acao = r.get("action_at_decision", "")
            if acao in ("BUY", "SELL") and r.get("is_evaluated") == 1 and r.get("was_correct") == 1:
                pts = float(r.get("price_change_points") or 0)
                if pts > 0:
                    _pts_capturados += pts

        if not episodes and not decisions:
            result["alertas_criticos"].append(
                "Nenhum dado do agente hoje. Não é possível analisar."
            )
            result["nota_agente"] = 0
            return result

        # ── 1. COERÊNCIA MACRO SIGNAL vs AÇÃO ──
        macro_signals = {}
        agent_actions = {}
        for ep in episodes:
            sig = ep.get("macro_bias", "UNKNOWN")
            macro_signals[sig] = macro_signals.get(sig, 0) + 1
            act = ep.get("action", "UNKNOWN")
            agent_actions[act] = agent_actions.get(act, 0) + 1

        total_ep = len(episodes)
        if total_ep > 0:
            # Qual o sinal macro dominante?
            dominant_signal = max(macro_signals, key=macro_signals.get) if macro_signals else "UNKNOWN"
            dominant_signal_pct = macro_signals.get(dominant_signal, 0) / total_ep * 100

            # Qual a ação dominante do agente?
            dominant_action = max(agent_actions, key=agent_actions.get) if agent_actions else "UNKNOWN"
            dominant_action_pct = agent_actions.get(dominant_action, 0) / total_ep * 100

            # CONTRADIÇÃO: Macro diz COMPRA mas agente fica HOLD
            compra_signals = macro_signals.get("BULLISH", 0) + macro_signals.get("COMPRA", 0)
            venda_signals = macro_signals.get("BEARISH", 0) + macro_signals.get("VENDA", 0)
            holds = agent_actions.get("HOLD", 0)
            buys = agent_actions.get("BUY", 0)
            sells = agent_actions.get("SELL", 0)

            compra_pct = compra_signals / total_ep * 100 if total_ep else 0
            hold_pct = holds / total_ep * 100 if total_ep else 0

            if compra_pct > 70 and hold_pct > 80:
                result["incoerencias"].append(
                    f"🔴 CONTRADIÇÃO GRAVE: Macro sinalizou COMPRA {compra_pct:.0f}% do tempo, "
                    f"mas agente ficou HOLD {hold_pct:.0f}%. "
                    f"O agente está IGNORANDO o próprio sinal macro! "
                    f"Filtros downstream (SMC, threshold, confiança) estão vetando a decisão."
                )
                result["nota_agente"] -= 3

            if venda_signals > total_ep * 0.7 and hold_pct > 80:
                result["incoerencias"].append(
                    f"🔴 CONTRADIÇÃO: Macro sinalizou VENDA {venda_signals/total_ep*100:.0f}% "
                    f"mas agente ficou HOLD {hold_pct:.0f}%. Mesma paralisia."
                )
                result["nota_agente"] -= 3

        # ── 2. ANÁLISE DE FILTROS BLOQUEANTES (SMC) ──
        smc_equilibrium = {}
        smc_direction = {}
        for ep in episodes:
            eq = ep.get("smc_equilibrium", "UNKNOWN")
            smc_equilibrium[eq] = smc_equilibrium.get(eq, 0) + 1
            sd = ep.get("smc_direction", "UNKNOWN")
            smc_direction[sd] = smc_direction.get(sd, 0) + 1

        if total_ep > 0:
            premium_count = smc_equilibrium.get("PREMIUM", 0)
            discount_count = smc_equilibrium.get("DISCOUNT", 0)
            premium_pct = premium_count / total_ep * 100

            if premium_pct > 80 and buys < total_ep * 0.1:
                result["filtros_bloqueantes"].append(
                    f"🔒 SMC PREMIUM BLOQUEOU COMPRAS: Equilíbrio SMC ficou PREMIUM "
                    f"{premium_pct:.0f}% do tempo. Se o filtro SMC veta BUY em PREMIUM, "
                    f"NENHUMA compra é possível! "
                    f"Em tendência de alta forte, PREMIUM é NORMAL. "
                    f"O filtro deveria ser relaxado para scores altos."
                )
                result["nota_agente"] -= 2

            discount_pct = discount_count / total_ep * 100
            if discount_pct > 80 and sells < total_ep * 0.1:
                result["filtros_bloqueantes"].append(
                    f"🔒 SMC DISCOUNT BLOQUEOU VENDAS: Equilíbrio SMC ficou DISCOUNT "
                    f"{discount_pct:.0f}% do tempo, vetando SELL. "
                    f"Em tendência de baixa, DISCOUNT é normal."
                )
                result["nota_agente"] -= 2

        # ── 3. ANÁLISE ADX vs THRESHOLDS ──
        adx_values = []
        for d in decisions:
            adx = d.get("adx")
            if adx is not None:
                adx_values.append(float(adx))

        if adx_values:
            avg_adx = sum(adx_values) / len(adx_values)
            max_adx = max(adx_values)
            last_adx = adx_values[-1]

            if avg_adx > 25 and len(opportunities) == 0:
                result["parametros_questionados"].append(
                    f"📏 ADX médio = {avg_adx:.1f} (último: {last_adx:.1f}, máx: {max_adx:.1f}). "
                    f"ADX>25 indica TENDÊNCIA FORTE, mas 0 oportunidades foram geradas. "
                    f"QUESTÃO: Os thresholds de score (±5) estão altos demais para um "
                    f"mercado tendencial? Com ADX>25, thresholds adaptativos de ±3 seriam "
                    f"mais apropriados."
                )

            if max_adx > 40 and len(opportunities) == 0:
                result["parametros_questionados"].append(
                    f"🔥 ADX chegou a {max_adx:.1f} — tendência EXTREMAMENTE forte. "
                    f"O agente deveria ter ativado modo 'trend following' agressivo, "
                    f"reduzindo filtros e priorizando momentum. 0 oportunidades é INACEITÁVEL."
                )
                result["nota_agente"] -= 1

        # ── 4. ANÁLISE RSI ──
        rsi_values = []
        for d in decisions:
            rsi = d.get("rsi")
            if rsi is not None:
                rsi_values.append(float(rsi))

        if rsi_values:
            avg_rsi = sum(rsi_values) / len(rsi_values)
            max_rsi = max(rsi_values)

            if avg_rsi > 60 and max_rsi < 80 and compra_pct > 70 and hold_pct > 80:
                result["parametros_questionados"].append(
                    f"📊 RSI médio = {avg_rsi:.1f} (máx {max_rsi:.1f}). "
                    f"RSI entre 60-80 em tendência de alta é NORMAL, não sobrecomprado. "
                    f"Se o agente está usando RSI>70 como filtro de bloqueio, está "
                    f"incorreto para tendências fortes."
                )

        # ── 5. MICRO SCORE vs TENDÊNCIA REAL ──
        micro_scores = []
        micro_trends = {}
        for d in decisions:
            ms = d.get("micro_score")
            if ms is not None:
                micro_scores.append(float(ms))
            mt = d.get("micro_trend", "UNKNOWN")
            micro_trends[mt] = micro_trends.get(mt, 0) + 1

        if micro_scores and decisions:
            avg_micro = sum(micro_scores) / len(micro_scores)
            last_micro = micro_scores[-1]

            # Preço subindo mas micro score negativo
            prices = [float(d["price_current"]) for d in decisions if d.get("price_current")]
            if len(prices) >= 10:
                price_change = prices[-1] - prices[0]
                if price_change > 500 and avg_micro < 0:
                    result["incoerencias"].append(
                        f"🔴 MICRO SCORE INVERTIDO: Preço subiu {price_change:.0f} pts "
                        f"mas micro_score médio = {avg_micro:.1f}. "
                        f"A classificação micro está ERRADA — está chamando "
                        f"pullbacks saudáveis de 'reversão'. Em tendência forte, "
                        f"micro score deveria ser positivo."
                    )
                    result["nota_agente"] -= 1

                if price_change < -500 and avg_micro > 0:
                    result["incoerencias"].append(
                        f"🔴 MICRO SCORE INVERTIDO: Preço caiu {abs(price_change):.0f} pts "
                        f"mas micro_score médio = {avg_micro:.1f}. "
                        f"Classificação micro incoerente com o mercado."
                    )
                    result["nota_agente"] -= 1

            # Tendências detectadas
            reversao_pct = micro_trends.get("REVERSÃO", 0) / len(decisions) * 100 if decisions else 0
            if reversao_pct > 50 and len(prices) >= 10 and abs(prices[-1] - prices[0]) > 500:
                result["incoerencias"].append(
                    f"🔴 FALSA REVERSÃO: {reversao_pct:.0f}% das decisões classificaram "
                    f"como REVERSÃO, mas o mercado moveu {prices[-1]-prices[0]:+.0f} pts. "
                    f"O classificador de micro tendência está confundindo PULLBACKS "
                    f"normais com reversões. Precisa considerar ADX na classificação."
                )

        # ── 6. CUSTO DE OPORTUNIDADE ──
        if decisions:
            prices = [float(d["price_current"]) for d in decisions if d.get("price_current")]
            if len(prices) >= 5:
                price_range = max(prices) - min(prices)
                price_direction = prices[-1] - prices[0]

                # Quantos pontos um trader que seguisse a tendência capturaria?
                # Estimativa conservadora: 40% do range em tendência clara
                if abs(price_direction) > price_range * 0.5:  # Tendência unidirecional
                    capturable = abs(price_direction) * 0.4
                    n_ops = len(opportunities)
                    # BUG-DIARIOS-02: eficiencia_pct calculada sempre (nao apenas n_ops==0)
                    eficiencia = (
                        min(_pts_capturados / capturable * 100, 100.0)
                        if capturable > 0 else 0.0
                    )
                    result["custo_oportunidade"] = {
                        "range_total": price_range,
                        "direcao_pts": price_direction,
                        "capturable_estimado": capturable,
                        "oportunidades_detectadas": n_ops,
                        "pts_capturados": _pts_capturados,
                        "eficiencia_pct": eficiencia,
                    }
                    if n_ops == 0:
                        result["alertas_criticos"].append(
                            f"💰 CUSTO DE OPORTUNIDADE: Mercado moveu {price_direction:+.0f} pts "
                            f"(range {price_range:.0f} pts). Estimativa conservadora de captura: "
                            f"{capturable:.0f} pts. O agente capturou: {_pts_capturados:.0f} pts. "
                            f"EFICIÊNCIA: {eficiencia:.0f}%."
                        )
                        result["nota_agente"] -= 2
                    elif eficiencia < 30 and n_ops > 0:
                        result["alertas_criticos"].append(
                            f"📉 BAIXA EFICIENCIA: Agente capturou {_pts_capturados:.0f} pts "
                            f"de {capturable:.0f} pts capturaveis ({eficiencia:.0f}%). "
                            f"{n_ops} oportunidades detectadas mas aproveitamento baixo."
                        )

        # ── 7. MACRO SCORE ABSOLUTO vs AÇÃO ──
        macro_scores = []
        for ep in episodes:
            ms = ep.get("macro_score_final")
            if ms is not None:
                macro_scores.append(float(ms))

        if macro_scores:
            avg_macro = sum(macro_scores) / len(macro_scores)
            max_macro = max(macro_scores)
            last_macro = macro_scores[-1] if macro_scores else 0

            if avg_macro > 30 and hold_pct > 80:
                result["parametros_questionados"].append(
                    f"📊 Macro Score médio = {avg_macro:.0f} (último: {last_macro:.0f}, "
                    f"máx: {max_macro:.0f}). Score >30 indica VIÉS COMPRADOR claro, "
                    f"mas agente ficou HOLD {hold_pct:.0f}%. "
                    f"Se macro_score > 30, por que o micro_score não consegue chegar a +5?"
                )

            if max_macro >= 50 and len(opportunities) == 0:
                result["alertas_criticos"].append(
                    f"🔴 Macro Score chegou a {max_macro:.0f} (indicação FORTE de compra) "
                    f"e ZERO oportunidades. Os filtros downstream estão anulando "
                    f"completamente a análise macro."
                )

        # ── 8. VWAP POSITION ──
        vwap_positions = {}
        for ep in episodes:
            vp = ep.get("vwap_position", "UNKNOWN")
            vwap_positions[vp] = vwap_positions.get(vp, 0) + 1

        if total_ep > 0:
            above_vwap = vwap_positions.get("ABOVE_2S", 0) + vwap_positions.get("ABOVE_1S", 0)
            above_pct = above_vwap / total_ep * 100

            if above_pct > 70 and premium_pct > 80:
                result["filtros_bloqueantes"].append(
                    f"🔒 VWAP ACIMA {above_pct:.0f}% + SMC PREMIUM {premium_pct:.0f}% = "
                    f"Duplo bloqueio. Em tendência de alta isso é NORMAL. "
                    f"Os filtros foram desenhados para mercado lateral, não tendencial."
                )

            # Sugestão se VWAP above
            if above_pct > 60 and avg_adx > 25 if adx_values else False:
                result["sugestoes"].append(
                    f"Quando VWAP ABOVE + ADX>{avg_adx:.0f}, o agente deveria "
                    f"entrar em modo 'trend following': comprar pullbacks até "
                    f"VWAP+1σ ao invés de esperar DISCOUNT."
                )

        # ── 9. SUGESTÕES CONCRETAS ──
        if len(opportunities) == 0 and total_ep > 20:
            result["sugestoes"].append(
                "EMERGENCIAL: 0 oportunidades com agente ativo. Verificar: "
                "1) threshold de score (muito alto?), "
                "2) filtro SMC (bloqueando em tendência?), "
                "3) min_confidence (muito exigente?), "
                "4) min R:R (impossível em mercado esticado?)."
            )

        if hold_pct > 85:
            result["sugestoes"].append(
                f"HOLD em {hold_pct:.0f}% indica PARALISIA. O agente precisa de "
                f"mecanismos de 'forçar' ação quando a oportunidade é clara: "
                f"macro forte + ADX alto + preço em zona de compra."
            )

        if premium_pct > 80 and compra_pct > 70:
            result["sugestoes"].append(
                "SMC PREMIUM não deveria vetar BUY em tendência forte (ADX>25). "
                "Implementar bypass: se macro_score >= 8 E ADX > 25, "
                "permitir BUY mesmo em PREMIUM (comprar pullback)."
            )

        # Nota mínima 0
        result["nota_agente"] = max(0, result["nota_agente"])

        return result

    def evaluate_feedback_effectiveness(self) -> dict:
        """Avalia se o feedback ANTERIOR melhorou o agente.

        Compara janelas de tempo: ANTES vs DEPOIS do último feedback.
        Isso fecha o loop de RL — o diário aprende se suas sugestões funcionam.

        Returns:
            dict com comparação antes/depois e se houve melhoria.
        """
        from src.application.services.diary_feedback import load_feedback_history

        feedbacks = load_feedback_history(self.db_path, days=1)
        if len(feedbacks) < 2:
            return {"has_comparison": False, "reason": "Poucos feedbacks para comparar"}

        # Feedback mais recente (o que vamos avaliar se melhorou)
        current = feedbacks[0]
        previous = feedbacks[1]

        # Pegar timestamp do feedback anterior para separar episódios
        prev_ts = previous.timestamp

        episodes = self.get_today_episodes()
        decisions = self.get_today_micro_decisions()

        if not episodes or len(episodes) < 10:
            return {"has_comparison": False, "reason": "Poucos episódios para comparar"}

        # Separar episódios ANTES e DEPOIS do feedback anterior
        before = []
        after = []
        for ep in episodes:
            ep_ts = ep.get("timestamp", "")
            if ep_ts < prev_ts:
                before.append(ep)
            else:
                after.append(ep)

        if len(before) < 5 or len(after) < 5:
            return {"has_comparison": False, "reason": f"Janelas muito pequenas (antes={len(before)}, depois={len(after)})"}

        # Métricas ANTES
        before_holds = sum(1 for e in before if e.get("action") == "HOLD")
        before_hold_pct = before_holds / len(before) * 100
        before_buys = sum(1 for e in before if e.get("action") == "BUY")
        before_sells = sum(1 for e in before if e.get("action") == "SELL")

        # Métricas DEPOIS
        after_holds = sum(1 for e in after if e.get("action") == "HOLD")
        after_hold_pct = after_holds / len(after) * 100
        after_buys = sum(1 for e in after if e.get("action") == "BUY")
        after_sells = sum(1 for e in after if e.get("action") == "SELL")

        # Oportunidades antes/depois
        opportunities = self.get_today_opportunities()
        opps_before = sum(1 for o in opportunities if o.get("timestamp", "") < prev_ts)
        opps_after = sum(1 for o in opportunities if o.get("timestamp", "") >= prev_ts)

        # Rewards antes/depois
        rewards = self.get_today_rewards()
        r_before = [r for r in rewards if r.get("is_evaluated") == 1]
        # Não temos timestamp direto nos rewards, usar contagem geral
        total_correct = sum(1 for r in r_before if r.get("was_correct") == 1)
        total_eval = len(r_before)
        current_wr = total_correct / total_eval * 100 if total_eval > 0 else 0

        # Avaliar se melhorou
        hold_melhorou = after_hold_pct < before_hold_pct if previous.hold_pct > 80 else True
        opps_melhorou = opps_after > opps_before
        diversificou = (after_buys + after_sells) > (before_buys + before_sells)

        score_melhoria = 0
        detalhes = []

        if hold_melhorou and before_hold_pct > 80:
            score_melhoria += 2
            detalhes.append(f"✓ HOLD reduziu: {before_hold_pct:.0f}% → {after_hold_pct:.0f}%")
        elif not hold_melhorou and before_hold_pct > 80:
            score_melhoria -= 1
            detalhes.append(f"✗ HOLD não reduziu: {before_hold_pct:.0f}% → {after_hold_pct:.0f}%")

        if opps_melhorou:
            score_melhoria += 2
            detalhes.append(f"✓ Oportunidades: {opps_before} → {opps_after}")
        elif opps_before == 0 and opps_after == 0:
            score_melhoria -= 1
            detalhes.append(f"✗ Ainda 0 oportunidades antes e depois")

        if diversificou:
            score_melhoria += 1
            detalhes.append(f"✓ Mais ações: BUY {before_buys}→{after_buys}, SELL {before_sells}→{after_sells}")

        # Contexto
        return {
            "has_comparison": True,
            "feedback_avaliado_id": getattr(previous, 'id', '?'),
            "nota_anterior": previous.nota_agente,
            "nota_atual": current.nota_agente,
            "sugestoes_anteriores": previous.sugestoes[:2] if previous.sugestoes else [],
            "threshold_anterior": f"{previous.threshold_sugerido_buy}/{previous.threshold_sugerido_sell}",
            "smc_bypass_anterior": previous.smc_bypass_recomendado,
            # Antes vs Depois
            "before": {
                "episodios": len(before),
                "hold_pct": before_hold_pct,
                "buys": before_buys,
                "sells": before_sells,
                "opportunidades": opps_before,
            },
            "after": {
                "episodios": len(after),
                "hold_pct": after_hold_pct,
                "buys": after_buys,
                "sells": after_sells,
                "opportunities": opps_after,
            },
            "win_rate_atual": current_wr,
            # Avaliação
            "score_melhoria": score_melhoria,  # positivo = melhorou
            "melhorou": score_melhoria > 0,
            "detalhes": detalhes,
            "veredicto": (
                "FEEDBACK EFICAZ — sugestões melhoraram o agente" if score_melhoria >= 2
                else "FEEDBACK PARCIAL — melhoria limitada" if score_melhoria > 0
                else "FEEDBACK INEFICAZ — sem melhoria ou piora" if score_melhoria == 0
                else "FEEDBACK CONTRAPRODUCENTE — agente piorou"
            ),
        }

    def analyze_regions_critical(self) -> dict:
        """Análise CRÍTICA nível Head Global sobre regiões de interesse.

        Para cada região, avalia como ADVOGADO DO DIABO:
        - FAZ sentido operar neste nível? Por que SIM / Por que NÃO?
        - Volume confirma ou contradiz?
        - Confluência é real ou artificial (mesmo indicador repetido)?
        - Qual o risco de ser um nível falso?
        - O preço já testou e furou? Ou respeitou?

        Objetivo: NÃO perder oportunidades reais, mas NÃO sugerir viés equivocado.
        """
        regions_raw = self.get_today_regions()
        region_behavior = self.analyze_region_behavior()
        decisions = self.get_today_micro_decisions()
        episodes = self.get_today_episodes()

        result = {
            "regioes_analisadas": [],
            "veredicto_geral": "",
            "alertas": [],
            "oportunidades_reais": [],
            "armadilhas_possiveis": [],
        }

        if not regions_raw or not decisions:
            result["veredicto_geral"] = "Sem dados de regiões ou decisões para analisar"
            return result

        # Contexto de mercado
        prices = [float(d["price_current"]) for d in decisions if d.get("price_current")]
        if not prices:
            result["veredicto_geral"] = "Sem histórico de preços"
            return result

        current_price = prices[-1]
        market_high = max(prices)
        market_low = min(prices)
        market_range = market_high - market_low
        price_open = prices[0]
        price_direction = current_price - price_open  # + = alta, - = baixa
        direction_label = "ALTA" if price_direction > 0 else "BAIXA" if price_direction < 0 else "FLAT"

        # ADX médio (força da tendência)
        adx_values = [float(d["adx"]) for d in decisions if d.get("adx")]
        avg_adx = sum(adx_values) / len(adx_values) if adx_values else 0
        trend_strong = avg_adx > 25

        # Macro dominante
        macro_signals = {}
        for ep in episodes:
            sig = ep.get("macro_bias", "UNKNOWN")
            macro_signals[sig] = macro_signals.get(sig, 0) + 1
        macro_dom = max(macro_signals, key=macro_signals.get) if macro_signals else "UNKNOWN"

        # SMC dominante
        smc_eq = {}
        for ep in episodes:
            eq = ep.get("smc_equilibrium", "UNKNOWN")
            smc_eq[eq] = smc_eq.get(eq, 0) + 1
        smc_dom = max(smc_eq, key=smc_eq.get) if smc_eq else "UNKNOWN"

        # Indexar comportamento por preço
        behavior_map = {}
        for b in region_behavior:
            behavior_map[round(b["price"])] = b

        # Deduplicar regiões mais recentes (últimas 2h de dados)
        recent_regions = {}
        for reg in reversed(regions_raw):
            price_key = round(float(reg["price"]) / 50) * 50  # Agrupa ±25 pts
            if price_key not in recent_regions:
                recent_regions[price_key] = reg

        # Analisar cada região única
        for price_key, reg in sorted(recent_regions.items(), key=lambda x: x[0], reverse=True):
            reg_price = float(reg["price"])
            label = reg.get("label", "?")
            tipo = reg.get("tipo", "?")
            conf = int(reg.get("confluences", 1))
            distance = reg_price - current_price
            distance_pct = distance / current_price * 100

            # Pular regiões muito distantes (> 1.5%)
            if abs(distance_pct) > 1.5:
                continue

            analysis = {
                "price": reg_price,
                "label": label,
                "tipo": tipo,
                "confluences": conf,
                "distance_pts": distance,
                "distance_pct": distance_pct,
                "favoravel": False,
                "argumentos_pro": [],
                "argumentos_contra": [],
                "volume_confirma": None,
                "comportamento": None,
                "veredicto": "",
                "confianca_nivel": 0,  # 0-10
            }

            # ── COMPORTAMENTO HISTÓRICO ──
            reg_key = round(reg_price)
            beh = behavior_map.get(reg_key)
            if beh:
                analysis["comportamento"] = beh["status"]
                n_touches = beh.get("n_touches", 0)
                if "RESPEITOU" in beh["status"]:
                    analysis["argumentos_pro"].append(
                        f"Preço JÁ RESPEITOU este nível ({beh['detail']})")
                    analysis["confianca_nivel"] += 3
                elif "FUROU" in beh["status"]:
                    analysis["argumentos_contra"].append(
                        f"Preço JÁ FUROU este nível ({beh['detail']}) — região INVALIDADA")
                    analysis["confianca_nivel"] -= 3
                elif "TESTANDO" in beh["status"]:
                    analysis["argumentos_pro"].append("Preço TESTANDO agora — decisão iminente")
                    analysis["confianca_nivel"] += 1
                if n_touches >= 3:
                    analysis["argumentos_contra"].append(
                        f"Tocou {n_touches}x — região DESGASTADA, próximo toque pode furar")
                    analysis["confianca_nivel"] -= 1

            # ── CONFLUÊNCIA REAL vs ARTIFICIAL ──
            if conf >= 4:
                analysis["argumentos_pro"].append(
                    f"Confluência alta ({conf}★) — múltiplos indicadores independentes convergem")
                analysis["confianca_nivel"] += 2
            elif conf >= 2:
                analysis["confianca_nivel"] += 1
            if conf == 1:
                analysis["argumentos_contra"].append(
                    "Confluência baixa (1★) — nível FRACO, apenas 1 indicador")
                analysis["confianca_nivel"] -= 1

            # Verificar se a confluência é real (fontes diversas) ou artificial
            label_lower = label.lower()
            has_vwap = "vwap" in label_lower
            has_pivot = "pivô" in label_lower or "pivot" in label_lower
            has_ob = "ob " in label_lower or "order block" in label_lower
            has_fvg = "fvg" in label_lower
            has_topo = "topo" in label_lower
            has_fundo = "fundo" in label_lower
            source_count = sum([has_vwap, has_pivot, has_ob, has_fvg, has_topo, has_fundo])
            if conf >= 3 and source_count <= 1:
                analysis["argumentos_contra"].append(
                    f"Confluência pode ser ARTIFICIAL — label indica apenas 1 tipo ({label})")

            # ── ANÁLISE CONTEXTUAL POR TIPO ──

            # RESISTÊNCIA — faz sentido VENDER aqui?
            if tipo == "RESISTENCIA":
                if price_direction > 0 and trend_strong:
                    analysis["argumentos_contra"].append(
                        f"Mercado em ALTA FORTE (ADX {avg_adx:.0f}, +{price_direction:.0f} pts). "
                        f"Resistências tendem a ser ROMPIDAS em tendência forte.")
                    analysis["confianca_nivel"] -= 2
                if macro_dom in ("BULLISH", "COMPRA"):
                    analysis["argumentos_contra"].append(
                        f"Macro BULLISH — vender em resistência contra a maré é PERIGOSO.")
                    analysis["confianca_nivel"] -= 1
                if smc_dom == "PREMIUM" and avg_adx > 30:
                    analysis["argumentos_contra"].append(
                        "SMC PREMIUM + ADX>30 = tendência de alta FORTE. "
                        "PREMIUM é relativo — em rally, o topo antigo vira piso.")
                    analysis["confianca_nivel"] -= 1
                if distance > 0 and distance < market_range * 0.15:
                    analysis["argumentos_pro"].append(
                        f"Resistência PRÓXIMA ({distance:.0f} pts) — "
                        f"bom para TAKE PROFIT parcial, não necessariamente venda.")
                    analysis["confianca_nivel"] += 1

                # Em contra-tendência, resistência é mais confiável como referência
                if price_direction < -100 and avg_adx < 20:
                    analysis["argumentos_pro"].append(
                        "Mercado sem tendência clara — resistência tem mais chance de segurar.")
                    analysis["confianca_nivel"] += 2

            # SUPORTE — faz sentido COMPRAR aqui?
            elif tipo == "SUPORTE":
                if price_direction < 0 and trend_strong:
                    analysis["argumentos_contra"].append(
                        f"Mercado em BAIXA FORTE (ADX {avg_adx:.0f}, {price_direction:.0f} pts). "
                        f"Suportes tendem a ser ROMPIDOS em queda forte.")
                    analysis["confianca_nivel"] -= 2
                if macro_dom in ("BEARISH", "VENDA"):
                    analysis["argumentos_contra"].append(
                        f"Macro BEARISH — comprar em suporte contra a tendência é PERIGOSO.")
                    analysis["confianca_nivel"] -= 1
                if distance < 0 and abs(distance) < market_range * 0.15:
                    analysis["argumentos_pro"].append(
                        f"Suporte PRÓXIMO ({abs(distance):.0f} pts) — "
                        f"bom para STOP LOSS referência ou entry em pullback.")
                    analysis["confianca_nivel"] += 1
                if macro_dom in ("BULLISH", "COMPRA") and abs(distance_pct) < 0.3:
                    analysis["argumentos_pro"].append(
                        "Macro BULLISH + suporte próximo = zona ideal para BUY em pullback.")
                    analysis["confianca_nivel"] += 3

                # Suporte forte em mercado lateral
                if abs(price_direction) < 100 and avg_adx < 20:
                    analysis["argumentos_pro"].append(
                        "Mercado LATERAL — suporte tem alta chance de segurar para bounce.")
                    analysis["confianca_nivel"] += 2

            # ── VOLUME ──
            # Verificar se o volume no nível é significativo
            vol_strength = 0
            for d in decisions[-20:]:  # Últimas 20 decisões
                d_price = float(d.get("price_current", 0))
                if abs(d_price - reg_price) < 50:  # Preço perto do nível
                    # TODO: precisaria do volume do tick, mas podemos inferir do contexto
                    vol_strength += 1

            if vol_strength >= 5:
                analysis["volume_confirma"] = True
                analysis["argumentos_pro"].append(
                    f"Preço teve {vol_strength} interações nesta zona — volume CONFIRMA interesse.")
                analysis["confianca_nivel"] += 1
            elif vol_strength == 0:
                analysis["volume_confirma"] = False
                analysis["argumentos_contra"].append(
                    "Preço não negociou nesta zona — nível TEÓRICO, sem confirmação de volume.")

            # ── ADVOGADO DO DIABO: ARMADILHAS ──
            # Trap: suporte falso em queda forte
            if tipo == "SUPORTE" and price_direction < -200 and avg_adx > 30:
                analysis["argumentos_contra"].append(
                    "⚠ POSSÍVEL ARMADILHA: suporte em queda forte (>200 pts) com ADX>30 "
                    "pode ser 'dead cat bounce'. Confirmar com volume + reversão clara.")

            # Trap: resistência falsa em alta forte
            if tipo == "RESISTENCIA" and price_direction > 200 and avg_adx > 30:
                analysis["argumentos_contra"].append(
                    "⚠ POSSÍVEL ARMADILHA: resistência em alta forte (>200 pts) com ADX>30 "
                    "provavelmente será rompida. NÃO vender short aqui.")

            # ── VEREDICTO ──
            pros = len(analysis["argumentos_pro"])
            cons = len(analysis["argumentos_contra"])
            score = analysis["confianca_nivel"]

            if score >= 5:
                analysis["veredicto"] = "FORTE — operar com confiança"
                analysis["favoravel"] = True
            elif score >= 2:
                analysis["veredicto"] = "MODERADO — operar com cautela, confirmar volume"
                analysis["favoravel"] = True
            elif score >= 0:
                analysis["veredicto"] = "FRACO — apenas como referência de TP/SL, não entry"
                analysis["favoravel"] = False
            else:
                analysis["veredicto"] = "CONTRA-INDICADO — nível provavelmente será furado"
                analysis["favoravel"] = False

            # Classificar como oportunidade real ou armadilha
            if analysis["favoravel"] and score >= 3:
                result["oportunidades_reais"].append(
                    f"{label} @ {reg_price:.0f} ({tipo}) — {analysis['veredicto']} "
                    f"(score {score})")
            elif score < 0:
                result["armadilhas_possiveis"].append(
                    f"{label} @ {reg_price:.0f} ({tipo}) — {analysis['veredicto']} "
                    f"(score {score}): {analysis['argumentos_contra'][0] if analysis['argumentos_contra'] else 'risco elevado'}")

            result["regioes_analisadas"].append(analysis)

        # ── VEREDICTO GERAL ──
        n_regioes = len(result["regioes_analisadas"])
        n_fortes = sum(1 for r in result["regioes_analisadas"] if r["confianca_nivel"] >= 3)
        n_fracas = sum(1 for r in result["regioes_analisadas"] if r["confianca_nivel"] < 0)

        if n_fortes > 0 and n_fracas == 0:
            result["veredicto_geral"] = (
                f"MERCADO BEM MAPEADO — {n_fortes}/{n_regioes} regiões fortes. "
                f"Contexto: {direction_label}, ADX {avg_adx:.0f}, Macro {macro_dom}.")
        elif n_fortes > 0 and n_fracas > 0:
            result["veredicto_geral"] = (
                f"MISTO — {n_fortes} regiões confiáveis, {n_fracas} duvidosas. "
                f"Operar apenas nos níveis FORTES. "
                f"Contexto: {direction_label}, ADX {avg_adx:.0f}.")
        elif n_fracas >= n_regioes * 0.7:
            result["veredicto_geral"] = (
                f"CUIDADO — {n_fracas}/{n_regioes} regiões fracas ou contra-indicadas. "
                f"Mercado em {direction_label} forte, níveis podem ser rompidos. "
                f"Priorizar TREND FOLLOWING sobre FADE.")
        else:
            result["veredicto_geral"] = (
                f"NEUTRO — {n_regioes} regiões mapeadas, nenhuma excepcionalmente forte. "
                f"Operar com cautela e confirmação.")

        # Alertas específicos
        if n_fracas > n_fortes and n_regioes > 2:
            result["alertas"].append(
                "MAIS regiões fracas que fortes — o mapeamento pode estar "
                "gerando falsa sensação de segurança.")
        if market_range > 500 and n_regioes < 3:
            result["alertas"].append(
                f"Range grande ({market_range:.0f} pts) mas poucas regiões ({n_regioes}). "
                f"O agente pode estar cego em zonas importantes.")
        if trend_strong and all(r.get("tipo") == "RESISTENCIA" for r in result["regioes_analisadas"] if r.get("distance_pts", 0) > 0):
            suportes_proximos = [r for r in result["regioes_analisadas"]
                                 if r["tipo"] == "SUPORTE" and abs(r.get("distance_pct", 1)) < 0.5]
            if suportes_proximos and macro_dom in ("BULLISH", "COMPRA"):
                result["alertas"].append(
                    f"OPORTUNIDADE: Suportes próximos em mercado BULLISH com ADX {avg_adx:.0f}. "
                    f"Considerar BUY em pullback até suporte ao invés de esperar DISCOUNT.")

        return result

    def _diagnosticar(
        self,
        market_range_pts: float,
        n_episodes: int,
        n_decisions: int,
        n_opportunities: int,
        win_rate: float,
        total_eval: int,
        actions: dict,
    ) -> list[str]:
        """Gera diagnósticos/reflexões sobre a performance (nível 1 — rápido)."""
        diags = []

        # Range vs Oportunidades
        if market_range_pts > 500 and n_opportunities == 0:
            diags.append(
                f"⚠ CRÍTICO: Mercado moveu {market_range_pts:.0f} pts "
                f"mas o agente não detectou NENHUMA oportunidade. "
                f"Possível insensibilidade nos filtros ou thresholds muito restritivos."
            )
        elif market_range_pts > 300 and n_opportunities == 0:
            diags.append(
                f"⚠ ALERTA: Range de {market_range_pts:.0f} pts sem oportunidades. "
                f"O agente pode estar conservador demais."
            )
        elif market_range_pts < 100 and n_opportunities == 0:
            diags.append(
                f"✓ Range estreito ({market_range_pts:.0f} pts) — "
                f"correto não operar em mercado sem direcionalidade."
            )
        elif n_opportunities > 0:
            pts_por_opp = market_range_pts / n_opportunities if n_opportunities else 0
            diags.append(
                f"📊 {n_opportunities} oportunidade(s) em range de {market_range_pts:.0f} pts "
                f"({pts_por_opp:.0f} pts/opp)."
            )

        # Win Rate
        if total_eval >= 5:
            if win_rate >= 60:
                diags.append(f"✓ Win rate {win_rate:.1f}% — agente acertando bem.")
            elif win_rate >= 40:
                diags.append(f"⚡ Win rate {win_rate:.1f}% — margem para melhoria.")
            else:
                diags.append(
                    f"⚠ Win rate {win_rate:.1f}% — agente abaixo do aceitável. "
                    f"Revisar lógica de scoring e thresholds."
                )
        elif total_eval > 0:
            diags.append(f"📋 Poucos rewards avaliados ({total_eval}). Aguardar mais dados.")

        # Distribuição de ações
        holds = actions.get("HOLD", 0)
        buys = actions.get("BUY", 0)
        sells = actions.get("SELL", 0)
        total_actions = holds + buys + sells
        if total_actions > 0:
            hold_pct = holds / total_actions * 100
            if hold_pct > 90:
                diags.append(
                    f"⚠ Agente ficou em HOLD {hold_pct:.0f}% do tempo. "
                    f"Pode estar paralisado ou sem confiança."
                )
            elif hold_pct > 70:
                diags.append(
                    f"⚡ HOLD dominante ({hold_pct:.0f}%). "
                    f"Verificar se mercado justifica tanta cautela."
                )

        # Dados insuficientes
        if n_episodes == 0 and n_decisions == 0:
            diags.append(
                "ℹ Nenhum episódio RL ou decisão micro encontrados hoje. "
                "O agente pode não ter sido executado ainda."
            )

        if not diags:
            diags.append("✓ Sem anomalias detectadas na performance do dia.")

        return diags


# ────────────────────────────────────────────────────────────────
# Price Tracker
# ────────────────────────────────────────────────────────────────

class PriceTracker:
    """Track price history."""
    def __init__(self):
        self.prices = []

    def add_price(self, price: Decimal):
        self.prices.append((datetime.now(), price))

    def get_price_10min_ago(self) -> Decimal:
        if not self.prices:
            return Decimal("0")
        return self.prices[0][1] if self.prices else self.prices[-1][1]


# ────────────────────────────────────────────────────────────────
# Painel de observabilidade global (ROADMAP-DIARIOS-01)
# Instancia global para ser usada pelas threads de diarios.
# Reinicializada em main() com limite configuravel.
# ────────────────────────────────────────────────────────────────
_painel_obs: ObservabilidadeDiarios = ObservabilidadeDiarios(
    limite_inatividade_min=20,
    report_dir=project_root / "outputs" / "analysis",
)


# ────────────────────────────────────────────────────────────────
# Thread 1: Trading Journal (narrativa macro)
# ────────────────────────────────────────────────────────────────

def run_trading_journal():
    """Run trading journal in separate thread."""

    config = get_config()
    symbol = Symbol(config.trading_symbol)

    mt5 = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
        terminal_exe_path=r"C:\Program Files\Clear Investimentos MT5 Terminal\terminal64.exe",
    )

    if not mt5.connect():
        print("[TRADING JOURNAL] Erro ao conectar MT5")
        return

    operator = QuantumOperatorEngine()
    journal = TradingJournalService()
    count = 0

    try:
        while True:
            count += 1
            now = datetime.now()

            print("\n" + "=" * 80)
            print(f"TRADING JOURNAL - ENTRADA #{count} - {now.strftime('%H:%M:%S')}")
            print("=" * 80)

            candles = mt5.get_candles(symbol, TimeFrame.M15, count=100)
            if not candles:
                print("[ERRO] Falha ao obter dados")
                time.sleep(900)
                continue

            opening_candle = candles[0]
            current_candle = candles[-1]
            opening_price = opening_candle.open.value
            current_price = current_candle.close.value
            high = max(c.high.value for c in candles)
            low = min(c.low.value for c in candles)

            # Dados macro ao vivo (não hardcoded)
            macro = _fetch_live_macro()

            # Analyze
            decision = operator.analyze_and_decide(
                symbol=symbol,
                candles=candles,
                dollar_index=macro["dxy"],
                vix=macro["vix"],
                selic=macro["selic"],
                ipca=macro["ipca"],
                usd_brl=macro["usd_brl"],
                embi_spread=250,
            )

            # Create narrative
            decision_data = {
                "action": decision.action,
                "confidence": decision.confidence,
                "primary_reason": decision.primary_reason,
                "macro_bias": decision.macro_bias,
                "fundamental_bias": decision.fundamental_bias,
                "sentiment_bias": decision.sentiment_bias,
                "technical_bias": decision.technical_bias,
                "alignment_score": decision.alignment_score,
                "supporting_factors": decision.supporting_factors,
                "market_regime": decision.market_regime,
            }

            narrative = journal.create_narrative(
                symbol=symbol,
                current_price=current_price,
                opening_price=opening_price,
                high=high,
                low=low,
                decision_data=decision_data,
            )

            entry = journal.save_entry(narrative, decision_data)

            # Display FULL narrative
            print()
            print("MANCHETE:")
            print(f"  {narrative.headline}")
            print()
            print(f"SENTIMENTO: {narrative.market_feeling}")
            print()
            print("-" * 80)
            print("NARRATIVA:")
            print("-" * 80)
            print(narrative.detailed_narrative)
            print()
            print("-" * 80)
            print("CONTEXTO:")
            print(f"  Macro: {decision_data['macro_bias']} | Fundamentos: {decision_data['fundamental_bias']}")
            print(f"  Sentimento: {decision_data['sentiment_bias']} | Tecnica: {decision_data['technical_bias']}")
            print(f"  Alinhamento: {normalize_confidence(entry.alignment_score):.0%}")
            print()
            print(f"DECISAO: {narrative.decision.value} ({normalize_confidence(narrative.confidence):.0%})")
            print(f"Entry ID: {entry.entry_id}")
            print()

            # Wait 5 minutes
            time.sleep(300)

    except Exception as e:
        print(f"[TRADING JOURNAL] Erro: {e}")
    finally:
        mt5.disconnect()


# ────────────────────────────────────────────────────────────────
# Thread 2: AI Reflection
# ────────────────────────────────────────────────────────────────

def run_ai_reflection():
    """Run AI reflection in separate thread — COM análise cruzada do agente."""

    config = get_config()
    symbol = Symbol(config.trading_symbol)

    mt5 = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
        terminal_exe_path=r"C:\Program Files\Clear Investimentos MT5 Terminal\terminal64.exe",
    )

    if not mt5.connect():
        print("[AI REFLECTION] Erro ao conectar MT5")
        return

    operator = QuantumOperatorEngine()
    journal = AIReflectionJournalService()
    price_tracker = PriceTracker()
    narrative_bridge = NarrativeRuntimeBridge()

    # RL Reader para cruzar dados com o agente
    db_path = _get_db_path()
    rl_reader = RLPerformanceReader(db_path)

    # Get opening price
    candles = mt5.get_candles(symbol, TimeFrame.M15, count=100)
    opening_price = candles[0].open.value if candles else Decimal("0")

    count = 0

    try:
        while True:
            count += 1
            now = datetime.now()

            print("\n" + "=" * 80)
            print(f"AI REFLECTION - REFLEXAO #{count} - {now.strftime('%H:%M:%S')}")
            print("=" * 80)

            candles = mt5.get_candles(symbol, TimeFrame.M15, count=100)
            if not candles:
                print("[ERRO] Falha ao obter dados")
                time.sleep(600)
                continue

            current_candle = candles[-1]
            current_price = current_candle.close.value
            price_10min_ago = price_tracker.get_price_10min_ago()
            price_tracker.add_price(current_price)

            episodes = rl_reader.get_today_episodes()
            opportunities = rl_reader.get_today_opportunities()
            historical_sessions = journal.get_today_entries()

            # Dados macro ao vivo
            macro = _fetch_live_macro()

            # Analyze
            decision = operator.analyze_and_decide(
                symbol=symbol,
                candles=candles,
                dollar_index=macro["dxy"],
                vix=macro["vix"],
                selic=macro["selic"],
                ipca=macro["ipca"],
                usd_brl=macro["usd_brl"],
                embi_spread=250,
            )

            change_10min = ((current_price - price_10min_ago) / price_10min_ago * 100) if price_10min_ago > 0 else 0

            # Create reflection
            reflection = journal.generate_reflection(
                current_price=current_price,
                opening_price=opening_price,
                price_10min_ago=price_10min_ago,
                my_decision=decision.action,
                my_confidence=decision.confidence,
                my_alignment=decision.alignment_score,
                macro_moved=False,
                sentiment_changed=abs(change_10min) > 0.3,
                technical_triggered=decision.recommended_entry is not None,
                human_last_action="observando",
            )

            entry = journal.save_entry(reflection)

            # Display reflection
            print()
            print(f"Humor: {reflection.mood}")
            print(f"Frase: {reflection.one_liner}")
            print()
            print("-" * 80)
            print("AVALIACAO HONESTA:")
            print(reflection.honest_assessment)
            print()
            print("RELEVANCIA DOS DADOS:")
            print(reflection.data_relevance)
            print()
            print("SOU UTIL?")
            print(reflection.am_i_useful)
            print()
            print("CORRELACAO:")
            print(reflection.my_data_correlation)
            print()

            if narrative_bridge.enabled:
                narrative_bridge.process_cycle(
                    reflection=reflection,
                    decision=decision,
                    episodes=episodes,
                    opportunities=opportunities,
                    historical_sessions=historical_sessions,
                )

            # ═══════════════════════════════════════════════════════════════
            # NOVO: ANÁLISE CRUZADA — IA questiona o agente
            # ═══════════════════════════════════════════════════════════════
            print("=" * 80)
            print("🔍 ANÁLISE CRUZADA: IA vs AGENTE MICRO TENDÊNCIA")
            print("=" * 80)
            decisions_micro = rl_reader.get_today_micro_decisions()

            if episodes:
                # Comparar decisão da IA com decisão do agente
                last_ep = episodes[-1]
                agent_action = last_ep.get("action", "?")
                agent_macro_score = last_ep.get("macro_score_final", "?")
                agent_smc = last_ep.get("smc_equilibrium", "?")
                ai_decision = decision.action.value

                total_holds = sum(1 for e in episodes if e.get("action") == "HOLD")
                total_episodes = len(episodes)
                hold_pct = total_holds / total_episodes * 100 if total_episodes else 0

                print()
                print(f"  IA diz: {ai_decision} (conf: {normalize_confidence(decision.confidence):.0%})")
                print(f"  Agente diz: {agent_action} (macro_score: {agent_macro_score}, SMC: {agent_smc})")
                print(f"  Oportunidades hoje: {len(opportunities)}")
                print(f"  Ações: HOLD {total_holds}/{total_episodes} ({hold_pct:.0f}%)")

                # QUESTIONAMENTOS DA IA AO AGENTE
                print()
                print("  ┌─────────────────────────────────────────────────────────┐")
                print("  │  QUESTIONAMENTOS DA IA AO AGENTE                       │")
                print("  └─────────────────────────────────────────────────────────┘")

                has_questions = False

                # 1. IA diz BUY/SELL mas agente fica HOLD
                if ai_decision != "HOLD" and agent_action == "HOLD":
                    print(f"  ❓ Eu (IA) estou vendo {ai_decision} com {normalize_confidence(decision.confidence):.0%} de confiança,")
                    print(f"     mas o agente micro está em HOLD. POR QUÊ?")
                    if agent_smc == "PREMIUM" and ai_decision == "BUY":
                        print(f"     → CAUSA PROVÁVEL: Filtro SMC está em PREMIUM, vetando BUY.")
                        print(f"       QUESTÃO: Se o macro score é {agent_macro_score} e eu")
                        print(f"       recomendo {ai_decision}, o SMC deveria ser relaxado?")
                    has_questions = True

                # 2. Muitos HOLDs em mercado tendencial
                if hold_pct > 80 and decisions_micro:
                    prices = [float(d["price_current"]) for d in decisions_micro if d.get("price_current")]
                    if len(prices) >= 5:
                        move = prices[-1] - prices[0]
                        if abs(move) > 300:
                            print(f"  ❓ Mercado moveu {move:+.0f} pts mas agente ficou HOLD {hold_pct:.0f}%.")
                            print(f"     QUESTÃO AO HUMANO: Os parâmetros estão corretos?")
                            print(f"     Os thresholds (±5) podem estar altos demais.")
                            has_questions = True

                # 3. Zero oportunidades
                if len(opportunities) == 0 and total_episodes > 10:
                    print(f"  ❓ {total_episodes} ciclos de análise, 0 oportunidades geradas.")
                    print(f"     QUESTÃO: Qual filtro está bloqueando?")
                    # Investigar
                    smc_premium = sum(1 for e in episodes if e.get("smc_equilibrium") == "PREMIUM")
                    compra_macro = sum(1 for e in episodes if e.get("macro_bias") in ("BULLISH", "COMPRA"))
                    if smc_premium > total_episodes * 0.7:
                        print(f"     → SMC PREMIUM em {smc_premium/total_episodes*100:.0f}% é o bloqueio principal.")
                    if compra_macro > total_episodes * 0.7:
                        print(f"     → Macro diz COMPRA {compra_macro/total_episodes*100:.0f}%! CONTRADIÇÃO com HOLD.")
                    has_questions = True

                # 4. Win rate baixa
                rewards = rl_reader.get_today_rewards()
                evaluated = [r for r in rewards if r.get("is_evaluated") == 1]
                if len(evaluated) >= 10:
                    correct = sum(1 for r in evaluated if r.get("was_correct") == 1)
                    wr = correct / len(evaluated) * 100
                    if wr < 30:
                        print(f"  ❓ Win rate = {wr:.1f}%. O sistema de recompensas está")
                        print(f"     penalizando HOLD injustamente ou o agente está realmente errado?")
                        has_questions = True

                # 5. Verificar ADX alto sem ação
                if decisions_micro:
                    recent_adx = [float(d["adx"]) for d in decisions_micro[-10:] if d.get("adx")]
                    if recent_adx and max(recent_adx) > 40 and len(opportunities) == 0:
                        print(f"  ❓ ADX nos últimos ciclos: {max(recent_adx):.0f}.")
                        print(f"     Tendência FORTE detectada sem nenhuma ação do agente.")
                        print(f"     QUESTÃO: O agente deveria ter modo 'trend following'?")
                        has_questions = True

                if not has_questions:
                    print("  ✓ Nenhuma inconsistência detectada entre IA e agente neste ciclo.")

            else:
                print()
                print("  ℹ Sem dados do agente micro tendência para cruzar.")
                print("    O agente pode não ter sido iniciado.")

            print()

            # Wait 10 minutes
            time.sleep(600)

    except Exception as e:
        print(f"[AI REFLECTION] Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        mt5.disconnect()


# ────────────────────────────────────────────────────────────────
# Thread 3: RL Performance Diary (NOVO)
# ────────────────────────────────────────────────────────────────

def run_rl_performance_diary():
    """Diário de performance RL — lê rewards do SQLite e reflete."""

    db_path = _get_db_path()
    reader = RLPerformanceReader(db_path)
    mlops_runtime_bridge = DiarioRuntimeMlOpsBridge() if HAS_MLOPS_RUNTIME_BRIDGE else None
    count = 0

    try:
        while True:
            count += 1
            now = datetime.now()

            print("\n" + "▓" * 80)
            print(f"  RL PERFORMANCE DIARY - RELATÓRIO #{count} - {now.strftime('%H:%M:%S')}")
            print("▓" * 80)

            perf = reader.analyze_performance()

            # ── Cabeçalho do Mercado ──
            print()
            print("  ╔══════════════════════════════════════════════════════════════╗")
            print(f"  ║  RANGE DO MERCADO HOJE                                     ║")
            print("  ╠══════════════════════════════════════════════════════════════╣")
            print(f"  ║  Abertura: {perf['market_open']:>10.0f}    Atual: {perf['market_current']:>10.0f}          ║")
            print(f"  ║  Máxima:   {perf['market_high']:>10.0f}    Mínima: {perf['market_low']:>10.0f}          ║")
            print(f"  ║  Range:    {perf['market_range_pts']:>10.0f} pts   Var: {perf['market_change_pts']:>+10.0f} pts      ║")
            print("  ╚══════════════════════════════════════════════════════════════╝")

            # ── Episódios RL ──
            print()
            print(f"  📊 EPISÓDIOS RL:     {perf['n_episodes']}")
            print(f"  📊 DECISÕES MICRO:   {perf['n_micro_decisions']}")
            print(f"  📊 OPORTUNIDADES:    {perf['n_opportunities']} (BUY: {perf['opp_buy']} | SELL: {perf['opp_sell']})")

            # ── Distribuição de Ações ──
            if perf["actions_distribution"]:
                print()
                print("  AÇÕES DO AGENTE:")
                for action, count_a in sorted(perf["actions_distribution"].items()):
                    bar = "█" * min(count_a, 50)
                    print(f"    {action:>6}: {count_a:>4}  {bar}")

            # ── Rewards por horizonte ──
            if perf["rewards_by_horizon"]:
                print()
                print("  ┌─────────────────────────────────────────────────────────┐")
                print("  │  RECOMPENSAS RL POR HORIZONTE                          │")
                print("  ├──────────┬────────┬──────────┬──────────┬──────────────┤")
                print("  │ Horizonte│ Total  │ Corretos │ Win Rate │ Pts Médios   │")
                print("  ├──────────┼────────┼──────────┼──────────┼──────────────┤")
                for h in sorted(perf["rewards_by_horizon"].keys()):
                    data = perf["rewards_by_horizon"][h]
                    total = data["total"]
                    correct = data["correct"]
                    wr = (correct / total * 100) if total > 0 else 0
                    avg_pts = sum(data["pts"]) / len(data["pts"]) if data["pts"] else 0
                    icon = "✓" if wr >= 50 else "✗"
                    print(f"  │  {h:>4} min│  {total:>4}  │    {correct:>4}  │  {wr:>5.1f}%  │  {avg_pts:>+8.1f} {icon}  │")
                print("  └──────────┴────────┴──────────┴──────────┴──────────────┘")

            # ── Performance global ──
            print()
            print(f"  WIN RATE GLOBAL: {perf['win_rate_pct']:.1f}%  "
                  f"({perf['correct_count']} ✓ / {perf['incorrect_count']} ✗ "
                  f"de {perf['n_rewards_evaluated']} avaliados, "
                  f"{perf['n_rewards_pending']} pendentes)")

            # ── Comportamento das Regiões ──
            region_behavior = reader.analyze_region_behavior()
            if region_behavior:
                print()
                print("  ┌─────────────────────────────────────────────────────────────┐")
                print("  │  COMPORTAMENTO DAS REGIÕES — Respeitou ou Furou?           │")
                print("  ├──────────┬──────────────────────────┬───────────────────────┤")
                print("  │  Preço   │ Região                   │ Status                │")
                print("  ├──────────┼──────────────────────────┼───────────────────────┤")

                # Stats
                n_respeitou = 0
                n_furou = 0
                n_testado = 0

                for rb in region_behavior:
                    price = rb["price"]
                    label = (rb["label"] or "")[:24]
                    status = rb["status"]
                    detail = (rb["detail"] or "")[:21]
                    touches = rb["n_touches"]
                    conf = rb["confluences"]

                    # Ícones
                    if "RESPEITOU" in status:
                        icon = "🛡️"
                        n_respeitou += 1
                        n_testado += 1
                    elif "FUROU" in status:
                        icon = "💥"
                        n_furou += 1
                        n_testado += 1
                    elif status == "TESTANDO":
                        icon = "⚡"
                        n_testado += 1
                    else:
                        icon = "  "

                    stars = "★" * min(conf, 5) + "☆" * max(0, 5 - conf)
                    print(f"  │ {price:>8.0f} │ {label:<24} │ {icon} {status:<10} {detail:<10}│")

                print("  └──────────┴──────────────────────────┴───────────────────────┘")

                # Resumo
                total_regions = len(region_behavior)
                if n_testado > 0:
                    taxa_respeito = n_respeitou / n_testado * 100
                    print(f"  📐 {total_regions} regiões mapeadas | {n_testado} testadas | "
                          f"{n_respeitou} respeitaram ({taxa_respeito:.0f}%) | {n_furou} furaram")
                    if taxa_respeito >= 70:
                        print("  ✓ Regiões com alta taxa de respeito — mapeamento confiável.")
                    elif taxa_respeito >= 40:
                        print("  ⚡ Regiões com eficácia moderada — filtrar por confluência.")
                    else:
                        print("  ⚠ Maioria das regiões foi furada — revisar critérios de mapeamento.")
                else:
                    print(f"  📐 {total_regions} regiões mapeadas | Nenhuma testada pelo preço ainda.")

            # ── Diagnóstico ──
            print()
            print("  ┌─────────────────────────────────────────────────────────────┐")
            print("  │  DIAGNÓSTICO E REFLEXÃO                                    │")
            print("  └─────────────────────────────────────────────────────────────┘")
            for d in perf["diagnostico"]:
                print(f"    {d}")

            # ══════════════════════════════════════════════════════════════
            # ANÁLISE CRÍTICA PROFUNDA — O que o Head Global veria
            # ══════════════════════════════════════════════════════════════
            coherence = reader.analyze_agent_coherence()

            has_critical = (
                coherence["alertas_criticos"]
                or coherence["incoerencias"]
                or coherence["filtros_bloqueantes"]
                or coherence["parametros_questionados"]
            )

            if has_critical:
                print()
                print("  ╔══════════════════════════════════════════════════════════════╗")
                print("  ║  🔍 ANÁLISE CRÍTICA — INTELIGÊNCIA DO DIÁRIO               ║")
                print(f"  ║  NOTA DO AGENTE: {coherence['nota_agente']}/10"
                      f"{'':>{44-len(str(coherence['nota_agente']))}}║")
                print("  ╚══════════════════════════════════════════════════════════════╝")

                if coherence["alertas_criticos"]:
                    print()
                    print("  🚨 ALERTAS CRÍTICOS:")
                    for a in coherence["alertas_criticos"]:
                        # Quebrar texto longo em linhas
                        words = a.split()
                        line = "    "
                        for w in words:
                            if len(line) + len(w) + 1 > 78:
                                print(line)
                                line = "    " + w
                            else:
                                line += " " + w if line.strip() else "    " + w
                        if line.strip():
                            print(line)
                        print()

                if coherence["incoerencias"]:
                    print("  🔴 INCOERÊNCIAS DETECTADAS:")
                    for inc in coherence["incoerencias"]:
                        words = inc.split()
                        line = "    "
                        for w in words:
                            if len(line) + len(w) + 1 > 78:
                                print(line)
                                line = "    " + w
                            else:
                                line += " " + w if line.strip() else "    " + w
                        if line.strip():
                            print(line)
                        print()

                if coherence["filtros_bloqueantes"]:
                    print("  🔒 FILTROS QUE ESTÃO BLOQUEANDO O AGENTE:")
                    for f in coherence["filtros_bloqueantes"]:
                        words = f.split()
                        line = "    "
                        for w in words:
                            if len(line) + len(w) + 1 > 78:
                                print(line)
                                line = "    " + w
                            else:
                                line += " " + w if line.strip() else "    " + w
                        if line.strip():
                            print(line)
                        print()

                if coherence["parametros_questionados"]:
                    print("  📏 PARÂMETROS QUESTIONADOS:")
                    for p in coherence["parametros_questionados"]:
                        words = p.split()
                        line = "    "
                        for w in words:
                            if len(line) + len(w) + 1 > 78:
                                print(line)
                                line = "    " + w
                            else:
                                line += " " + w if line.strip() else "    " + w
                        if line.strip():
                            print(line)
                        print()

                if coherence["custo_oportunidade"]:
                    co = coherence["custo_oportunidade"]
                    print("  💰 CUSTO DE OPORTUNIDADE:")
                    print(f"    Range: {co['range_total']:.0f} pts | Direção: {co['direcao_pts']:+.0f} pts")
                    print(f"    Capturável (estimado): {co['capturable_estimado']:.0f} pts")
                    print(f"    Capturado pelo agente: {co['pts_capturados']:.0f} pts")
                    print(f"    Eficiência: {co['eficiencia_pct']:.0f}%")
                    print()

                if coherence["sugestoes"]:
                    print("  💡 SUGESTÕES CONCRETAS:")
                    for i, s in enumerate(coherence["sugestoes"], 1):
                        words = s.split()
                        line = f"    {i}. "
                        for w in words:
                            if len(line) + len(w) + 1 > 78:
                                print(line)
                                line = "       " + w
                            else:
                                line += " " + w if len(line) > 7 else w
                        if line.strip():
                            print(line)
                        print()
            else:
                print()
                print("  ✓ Análise crítica: sem incoerências detectadas.")

            # ── EFETIVIDADE DO FEEDBACK ANTERIOR ──
            try:
                effectiveness = reader.evaluate_feedback_effectiveness()
                if effectiveness.get("has_comparison"):
                    eff = effectiveness
                    verd = eff["veredicto"]
                    if "EFICAZ" in verd and "INEFICAZ" not in verd:
                        verd_icon = "✅"
                    elif "PARCIAL" in verd:
                        verd_icon = "🟡"
                    elif "CONTRAPRODUCENTE" in verd:
                        verd_icon = "🔴"
                    else:
                        verd_icon = "⚠"

                    print()
                    print(f"  {verd_icon} EFETIVIDADE DO FEEDBACK ANTERIOR:")
                    print(f"    Veredicto: {verd}")
                    print(f"    Score melhoria: {eff['score_melhoria']:+d}")
                    print(f"    Nota: {eff['nota_anterior']}/10 → {eff['nota_atual']}/10")
                    print(f"    Threshold anterior: {eff['threshold_anterior']}")
                    print(f"    SMC bypass anterior: {'SIM' if eff['smc_bypass_anterior'] else 'NÃO'}")
                    b = eff["before"]
                    a = eff["after"]
                    print(f"    ANTES  ({b['episodios']} eps): HOLD {b['hold_pct']:.0f}% | "
                          f"BUY {b['buys']} | SELL {b['sells']} | Opps {b['opportunidades']}")
                    print(f"    DEPOIS ({a['episodios']} eps): HOLD {a['hold_pct']:.0f}% | "
                          f"BUY {a['buys']} | SELL {a['sells']} | Opps {a['opportunities']}")
                    for d in eff.get("detalhes", []):
                        print(f"    {d}")
                    print()
                else:
                    reason = effectiveness.get("reason", "N/A")
                    print(f"\n  ℹ Efetividade: {reason}\n")
            except Exception as eff_err:
                print(f"  ⚠ Erro ao avaliar efetividade: {eff_err}")

            # ── ANÁLISE CRÍTICA DO DIRECIONAL MACRO (nível Head) ──
            dir_analysis = None
            try:
                dir_analysis = reader.analyze_directional_critical()
                veredicto = dir_analysis.get("veredicto", "")
                if veredicto and veredicto != "Sem dados de items macro para analisar":
                    print()
                    print("  📊 ANÁLISE CRÍTICA DO DIRECIONAL (ADVOGADO DO DIABO):")
                    print(f"  Veredicto: {veredicto}")
                    conf_adj = dir_analysis.get("confianca_ajustada", 0)
                    if conf_adj > 0:
                        print(f"  Confiança ajustada: {conf_adj}%")
                    print()

                    # Tabela por categoria
                    det_cats = dir_analysis.get("detalhes_categorias", [])
                    if det_cats:
                        print("    CATEGORIA                    SCORE  ITENS  +/-    %TOTAL  STATUS")
                        print("    " + "─" * 72)
                        for dc in det_cats:
                            cat_name = dc["categoria"][:30]
                            sc = dc["score"]
                            ni = dc["n_items"]
                            pos = dc["pos"]
                            neg = dc["neg"]
                            pct = dc["pct_of_total"]
                            ali = dc["alinhado"]
                            print(f"    {cat_name:<30} {sc:>+4d}   {ni:>2d}   "
                                  f"{pos}↑{neg}↓  {pct:>5.0f}%  {ali}")
                        print()

                    # Vieses detectados
                    for vies in dir_analysis.get("vieses_detectados", []):
                        words = vies.split()
                        line = "    🔴 VIÉS: "
                        for w in words:
                            if len(line) + len(w) + 1 > 78:
                                print(line)
                                line = "             " + w
                            else:
                                line += " " + w if len(line) > 12 else w
                        if line.strip():
                            print(line)
                    if dir_analysis.get("vieses_detectados"):
                        print()

                    # Contradições
                    for contr in dir_analysis.get("contradicoes", []):
                        words = contr.split()
                        line = "    ⚡ "
                        for w in words:
                            if len(line) + len(w) + 1 > 78:
                                print(line)
                                line = "       " + w
                            else:
                                line += " " + w if len(line) > 6 else w
                        if line.strip():
                            print(line)
                    if dir_analysis.get("contradicoes"):
                        print()

                    # Questionamentos
                    for quest in dir_analysis.get("questionamentos", []):
                        words = quest.split()
                        line = "    ❓ "
                        for w in words:
                            if len(line) + len(w) + 1 > 78:
                                print(line)
                                line = "       " + w
                            else:
                                line += " " + w if len(line) > 6 else w
                        if line.strip():
                            print(line)
                    if dir_analysis.get("questionamentos"):
                        print()
            except Exception as dir_err:
                print(f"  ⚠ Erro na análise crítica direcional: {dir_err}")

            # ── ANÁLISE CRÍTICA DE REGIÕES (nível Head) ──
            try:
                reg_analysis = reader.analyze_regions_critical()
                regioes = reg_analysis.get("regioes_analisadas", [])
                if regioes:
                    print()
                    print("  🎯 ANÁLISE CRÍTICA DE REGIÕES (ADVOGADO DO DIABO):")
                    print(f"  Veredicto geral: {reg_analysis['veredicto_geral']}")
                    print()

                    for r in regioes:
                        dist = r["distance_pts"]
                        icon = "🔴" if r["tipo"] == "RESISTENCIA" else "🟢"
                        score = r["confianca_nivel"]
                        score_bar = ("█" * max(0, min(10, score + 3))) + ("░" * max(0, 10 - max(0, score + 3)))
                        beh_txt = f" [{r['comportamento']}]" if r.get("comportamento") else ""

                        print(f"    {icon} {r['label'][:28]:<28} @ {r['price']:.0f} "
                              f"({dist:+.0f} pts) {'★' * min(5, r['confluences'])}")
                        print(f"       Confiança: [{score_bar}] {score:+d}"
                              f"  → {r['veredicto']}{beh_txt}")

                        if r["argumentos_pro"]:
                            for arg in r["argumentos_pro"][:2]:
                                words = arg.split()
                                line = "       ✓ "
                                for w in words:
                                    if len(line) + len(w) + 1 > 78:
                                        print(line)
                                        line = "         " + w
                                    else:
                                        line += " " + w if len(line) > 9 else w
                                if line.strip():
                                    print(line)

                        if r["argumentos_contra"]:
                            for arg in r["argumentos_contra"][:2]:
                                words = arg.split()
                                line = "       ✗ "
                                for w in words:
                                    if len(line) + len(w) + 1 > 78:
                                        print(line)
                                        line = "         " + w
                                    else:
                                        line += " " + w if len(line) > 9 else w
                                if line.strip():
                                    print(line)

                        vol_txt = ("Volume CONFIRMA" if r["volume_confirma"]
                                   else "Volume NÃO confirma" if r["volume_confirma"] is False
                                   else "Volume: sem dados")
                        print(f"       📊 {vol_txt}")
                        print()

                    # Oportunidades reais vs armadilhas
                    if reg_analysis["oportunidades_reais"]:
                        print("  ✅ OPORTUNIDADES REAIS IDENTIFICADAS:")
                        for opp in reg_analysis["oportunidades_reais"]:
                            print(f"    → {opp}")
                        print()

                    if reg_analysis["armadilhas_possiveis"]:
                        print("  ⚠ POSSÍVEIS ARMADILHAS:")
                        for trap in reg_analysis["armadilhas_possiveis"]:
                            words = trap.split()
                            line = "    → "
                            for w in words:
                                if len(line) + len(w) + 1 > 78:
                                    print(line)
                                    line = "      " + w
                                else:
                                    line += " " + w if len(line) > 6 else w
                            if line.strip():
                                print(line)
                        print()

                    if reg_analysis["alertas"]:
                        for al in reg_analysis["alertas"]:
                            words = al.split()
                            line = "  🔔 "
                            for w in words:
                                if len(line) + len(w) + 1 > 78:
                                    print(line)
                                    line = "     " + w
                                else:
                                    line += " " + w if len(line) > 5 else w
                            if line.strip():
                                print(line)
                        print()
            except Exception as reg_err:
                print(f"  ⚠ Erro na análise crítica de regiões: {reg_err}")

            # ── Oportunidades detalhadas (últimas 5) ──
            opps = reader.get_today_opportunities()
            if opps:
                print()
                print("  ÚLTIMAS OPORTUNIDADES DETECTADAS:")
                for o in opps[-5:]:
                    ts = o.get("timestamp", "")[:19]
                    direction = o.get("direction", "?")
                    entry = float(o.get("entry") or 0)
                    sl = float(o.get("stop_loss") or 0)
                    tp = float(o.get("take_profit") or 0)
                    rr = float(o.get("risk_reward") or 0)
                    conf = _normalize_confidence_percent(o.get("confidence"))
                    reason = (o.get("reason") or "")[:40]
                    icon = "🟢" if direction == "BUY" else "🔴"
                    print(f"    {icon} {ts} | {direction:>4} @ {entry:.0f} "
                          f"| SL {sl:.0f} | TP {tp:.0f} | R:R {rr:.1f} "
                          f"| Conf {conf:.0%} | {reason}")

            # ══════════════════════════════════════════════════════════════
            # PERSISTIR FEEDBACK NO SQLITE — para RL do agente
            # ══════════════════════════════════════════════════════════════
            try:
                # Extrair contexto do mercado para o feedback
                episodes = reader.get_today_episodes()
                decisions = reader.get_today_micro_decisions()

                # Sinal macro dominante
                macro_signals = {}
                for ep in episodes:
                    sig = ep.get("macro_bias", "UNKNOWN")
                    macro_signals[sig] = macro_signals.get(sig, 0) + 1
                macro_dom = max(macro_signals, key=macro_signals.get) if macro_signals else ""

                # SMC dominante
                smc_eq = {}
                for ep in episodes:
                    eq = ep.get("smc_equilibrium", "UNKNOWN")
                    smc_eq[eq] = smc_eq.get(eq, 0) + 1
                smc_dom = max(smc_eq, key=smc_eq.get) if smc_eq else ""

                # ADX médio e micro score médio
                adx_vals = [float(d["adx"]) for d in decisions if d.get("adx")]
                adx_med = sum(adx_vals) / len(adx_vals) if adx_vals else 0
                micro_vals = [float(d["micro_score"]) for d in decisions if d.get("micro_score") is not None]
                micro_med = sum(micro_vals) / len(micro_vals) if micro_vals else 0

                # Calcular thresholds sugeridos baseado em ADX
                suggested_buy = 3 if adx_med > 25 else 5
                suggested_sell = -3 if adx_med > 25 else -5

                # SMC bypass recomendado?
                total_ep = len(episodes)
                premium_count = smc_eq.get("PREMIUM", 0)
                premium_pct = premium_count / total_ep * 100 if total_ep else 0
                compra_count = macro_signals.get("BULLISH", 0) + macro_signals.get("COMPRA", 0)
                compra_pct = compra_count / total_ep * 100 if total_ep else 0
                smc_bypass = premium_pct > 80 and compra_pct > 70

                # Trend following?
                trend_follow = adx_med > 30 and perf["n_opportunities"] == 0

                # ── EVOLUÇÃO ACUMULATIVA INTRA-SESSÃO ──
                # Ajustar thresholds baseado na efetividade do feedback anterior
                try:
                    eff_check = reader.evaluate_feedback_effectiveness()
                    if eff_check.get("has_comparison"):
                        score_m = eff_check["score_melhoria"]
                        prev_buy_th = int(eff_check["threshold_anterior"].split("/")[0])
                        prev_sell_th = int(eff_check["threshold_anterior"].split("/")[1])

                        if score_m >= 2:
                            # EFICAZ — manter ou ser mais agressivo
                            if suggested_buy > 2:
                                suggested_buy = max(prev_buy_th - 1, 2)
                                suggested_sell = min(prev_sell_th + 1, -2)
                                print(f"  📈 Evolução: feedback EFICAZ → thresholds mais agressivos "
                                      f"{prev_buy_th}/{prev_sell_th} → {suggested_buy}/{suggested_sell}")
                        elif score_m <= -1:
                            # CONTRAPRODUCENTE — recuar para default
                            suggested_buy = 5
                            suggested_sell = -5
                            smc_bypass = False
                            print(f"  📉 Evolução: feedback CONTRAPRODUCENTE → revertendo para "
                                  f"defaults 5/-5, SMC bypass OFF")
                        elif score_m == 0:
                            # INEFICAZ — manter sugestão mas ativar bypass se não ativo
                            if not smc_bypass and premium_pct > 60:
                                smc_bypass = True
                                print(f"  🔄 Evolução: feedback INEFICAZ → ativando SMC bypass "
                                      f"(premium {premium_pct:.0f}%)")
                            if not trend_follow and adx_med > 25:
                                trend_follow = True
                                print(f"  🔄 Evolução: feedback INEFICAZ → ativando trend follow "
                                      f"(ADX {adx_med:.0f})")
                except Exception as evo_err:
                    print(f"  ⚠ Erro na evolução acumulativa: {evo_err}")

                # ── Acoplamento runtime Storytelling + ML Ops ──
                mlops_payload: dict[str, Any] | None = None
                try:
                    if mlops_runtime_bridge is not None:
                        guardian_snapshot = get_guardian_state()
                        mlops_payload = mlops_runtime_bridge.process_cycle(
                            {
                                "perf": perf,
                                "coherence": coherence,
                                "dir_analysis": dir_analysis or {},
                                "guardian_state": guardian_snapshot,
                                "order_history": _build_runtime_order_history(perf),
                                "execution_patterns": _build_runtime_execution_patterns(perf),
                            }
                        )
                        summary = mlops_payload.get("summary", {})
                        regime = summary.get("regime", "RANGING")
                        kill_status = "ATIVO" if summary.get("kill_switch_active") else "OFF"
                        exec_mode = summary.get("execution_mode", "BALANCED")
                        retrain = "SIM" if summary.get("retraining_triggered") else "NAO"
                        print(
                            "  🤖 MLOps runtime: "
                            f"regime={regime} | kill_switch={kill_status} | "
                            f"exec_mode={exec_mode} | retrain={retrain}"
                        )

                        exec_rec = mlops_payload.get("execution_recommendation", {})
                        mode = str(exec_rec.get("mode", "BALANCED")).upper()
                        if mode == "CONSERVATIVE":
                            suggested_buy = max(suggested_buy, 6)
                            suggested_sell = min(suggested_sell, -6)
                            trend_follow = False
                        elif mode == "AGGRESSIVE":
                            suggested_buy = max(2, suggested_buy - 1)
                            suggested_sell = min(-2, suggested_sell + 1)
                            trend_follow = True
                except Exception as mlops_err:
                    print(f"  ⚠ Erro no acoplamento runtime MLOps: {mlops_err}")

                # Custo de oportunidade
                co = coherence.get("custo_oportunidade", {})

                # Análise crítica de regiões (nível Head)
                reg_fortes_list = []
                reg_armadilhas_list = []
                veredicto_reg = ""
                try:
                    reg_crit = reader.analyze_regions_critical()
                    reg_fortes_list = reg_crit.get("oportunidades_reais", [])
                    reg_armadilhas_list = reg_crit.get("armadilhas_possiveis", [])
                    veredicto_reg = reg_crit.get("veredicto_geral", "")
                except Exception:
                    pass

                # Análise crítica do direcional macro (nível Head)
                dir_vieses_list = []
                dir_contradicoes_list = []
                dir_questionamentos_list = []
                veredicto_dir = ""
                confianca_dir_adj = 0.0
                try:
                    if dir_analysis:
                        dir_vieses_list = dir_analysis.get("vieses_detectados", [])
                        dir_contradicoes_list = dir_analysis.get("contradicoes", [])
                        dir_questionamentos_list = dir_analysis.get("questionamentos", [])
                        veredicto_dir = dir_analysis.get("veredicto", "")
                        confianca_dir_adj = float(dir_analysis.get("confianca_ajustada", 0))
                except Exception:
                    pass

                sugestoes_feedback = list(coherence.get("sugestoes", []))
                confianca_minima_sugerida = 60.0
                if mlops_payload is not None:
                    summary = mlops_payload.get("summary", {})
                    if summary.get("kill_switch_active"):
                        confianca_minima_sugerida = 75.0
                    elif summary.get("regime") == "HIGH_VOLATILITY":
                        confianca_minima_sugerida = 65.0
                    elif summary.get("regime") in {"TRENDING_UP", "TRENDING_DOWN"}:
                        confianca_minima_sugerida = 55.0
                    mensagem = summary.get("message")
                    if mensagem:
                        sugestoes_feedback.append(f"MLOps runtime: {mensagem}")

                feedback = DiaryFeedback(
                    date=date.today().isoformat(),
                    timestamp=now.isoformat(),
                    source="diary_rl_performance",
                    nota_agente=coherence["nota_agente"],
                    alertas_criticos=coherence["alertas_criticos"],
                    incoerencias=coherence["incoerencias"],
                    filtros_bloqueantes=coherence["filtros_bloqueantes"],
                    parametros_questionados=coherence["parametros_questionados"],
                    sugestoes=sugestoes_feedback,
                    custo_oportunidade_pts=co.get("capturable_estimado", 0),
                    eficiencia_pct=co.get("eficiencia_pct", 0),
                    hold_pct=perf["actions_distribution"].get("HOLD", 0) / max(perf["n_episodes"], 1) * 100,
                    win_rate_pct=perf["win_rate_pct"],
                    market_range_pts=perf["market_range_pts"],
                    n_opportunities=perf["n_opportunities"],
                    n_episodes=perf["n_episodes"],
                    threshold_sugerido_buy=suggested_buy,
                    threshold_sugerido_sell=suggested_sell,
                    smc_bypass_recomendado=smc_bypass,
                    trend_following_recomendado=trend_follow,
                    max_adx_para_trend=25.0,
                    confianca_minima_sugerida=confianca_minima_sugerida,
                    regioes_fortes=reg_fortes_list,
                    regioes_armadilhas=reg_armadilhas_list,
                    veredicto_regioes=veredicto_reg,
                    direcional_vieses=dir_vieses_list,
                    direcional_contradicoes=dir_contradicoes_list,
                    direcional_questionamentos=dir_questionamentos_list,
                    veredicto_direcional=veredicto_dir,
                    confianca_direcional_ajustada=confianca_dir_adj,
                    macro_signal_dominante=macro_dom,
                    smc_equilibrium_dominante=smc_dom,
                    adx_medio=adx_med,
                    micro_score_medio=micro_med,
                    active=True,
                )

                # ── Integrar estado do Guardian Macro ──
                try:
                    gs = get_guardian_state()
                    gf = guardian_state_to_feedback_fields(gs)
                    feedback.guardian_kill_switch = gf["guardian_kill_switch"]
                    feedback.guardian_kill_reason = gf["guardian_kill_reason"]
                    feedback.guardian_reduced_exposure = gf["guardian_reduced_exposure"]
                    feedback.guardian_confidence_penalty = gf["guardian_confidence_penalty"]
                    feedback.guardian_bias_override = gf["guardian_bias_override"]
                    feedback.guardian_scenario_changes = gf["guardian_scenario_changes"]
                    feedback.guardian_alertas = gf["guardian_alertas"]
                except Exception:
                    pass  # Guardian pode não ter rodado ainda

                fb_id = save_diary_feedback(db_path, feedback)
                if fb_id:
                    print(f"  💾 Feedback salvo no SQLite (ID={fb_id}, nota={coherence['nota_agente']}/10)")
                    print(f"     → Agente pode ler: threshold={suggested_buy}/{suggested_sell}, "
                          f"SMC_bypass={'SIM' if smc_bypass else 'NÃO'}, "
                          f"trend_follow={'SIM' if trend_follow else 'NÃO'}")
                    _painel_obs.registrar_gravacao("DIARIOS")
                else:
                    print("  ⚠ Falha ao salvar feedback no SQLite")
            except Exception as fb_err:
                print(f"  ⚠ Erro ao persistir feedback: {fb_err}")

            # AC5.9: Validação de saúde do feedback (Grupo 2)
            if AC5_9_DISPONIVEL and FeedbackValidator:
                try:
                    _fv = FeedbackValidator()
                    # Converte dados RL em formato de trades/feedback
                    _trades = [
                        {
                            "trade_id": str(i),
                            "outcome": (
                                "WIN" if h.get("correct") else "LOSS"
                            ),
                            "pnl": float(h.get("pts", 0)),
                        }
                        for i, h in enumerate(
                            perf.get("rewards_by_horizon", {})
                            .get(5, {}).get("entries", [])
                        )
                    ] if perf.get("rewards_by_horizon") else []
                    if _trades:
                        _report = _fv.validate_feedback_health(
                            trades=_trades, feedback=_trades,
                        )
                        _icon = {
                            "HEALTHY": "🟢",
                            "WARNING": "🟡",
                            "CRITICAL": "🔴",
                        }.get(_report.overall_status, "⚪")
                        print(
                            f"  {_icon} AC5.9 Feedback:"
                            f" {_report.overall_status}"
                            f" | Qualidade:"
                            f" {_report.data_quality_score:.0%}"
                        )
                except Exception as e:
                    print(f"  ⚠ AC5.9: {e}")

            print()
            print("  " + "─" * 60)
            print(f"  Próximo relatório em 15 min... ({now.strftime('%H:%M')})")
            print()

            # Wait 15 minutes
            time.sleep(900)

    except Exception as e:
        print(f"[RL DIARY] Erro: {e}")
        import traceback
        traceback.print_exc()


# ────────────────────────────────────────────────────────────────
# Thread 4 — Macro Scenario Guardian (a cada 2 min)
# ────────────────────────────────────────────────────────────────

# Estado compartilhado do guardian (acessível pelo Thread 3 para feedback)
_guardian_state = GuardianState()
_guardian_lock = threading.Lock()
_opening_context_runtime = None


def get_guardian_state() -> GuardianState:
    """Retorna cópia thread-safe do estado do guardian."""
    with _guardian_lock:
        return _guardian_state


def run_macro_guardian():
    """Thread 4 — Macro Scenario Guardian.

    Monitora cenário macro em alta frequência (2 min):
      - Agressão no dólar (USD/BRL via AwesomeAPI)
      - Shock S&P500 (via dados do agente no SQLite)
      - Reversão/move extremo no WIN
      - Mudança brusca de score macro
      - Divergências perigosas (dólar × índice × sinal)
      - Calendário econômico (COPOM, FOMC, NFP, CPI)
      - Índice Fear & Greed

    Persiste alertas que o agente lê via diary_feedback.
    """
    global _guardian_state

    db_path = _get_db_path()
    print("\n[MACRO GUARDIAN] 🛡️  Iniciando monitor de cenário...")
    print(f"[MACRO GUARDIAN] Intervalo: {GUARDIAN_INTERVAL_SEC}s | DB: {db_path}")

    # Aguardar um pouco para os outros threads estabilizarem
    time.sleep(10)

    try:
        while True:
            now = datetime.now()

            # Verificar se estamos no horário de pregão (8:55-18:10)
            hora = now.hour * 100 + now.minute
            if hora < 855 or hora > 1810:
                time.sleep(60)
                continue

            try:
                with _guardian_lock:
                    new_alerts = run_guardian_check(_guardian_state, db_path)

                # Exibir se houve alertas novos ou a cada 5 checks
                if new_alerts or _guardian_state.n_checks % 5 == 0:
                    display = format_guardian_display(_guardian_state, new_alerts)
                    print(display)

                # Se houve alertas CRITICAL, salvar feedback imediatamente
                critical_alerts = [a for a in new_alerts if a.severity == "CRITICAL"]
                if critical_alerts:
                    try:
                        guardian_fields = guardian_state_to_feedback_fields(_guardian_state)

                        # Criar um feedback parcial do guardian
                        feedback = DiaryFeedback(
                            date=date.today().isoformat(),
                            timestamp=now.isoformat(),
                            source="macro_guardian",
                            nota_agente=10,  # Guardian não avalia nota
                            guardian_kill_switch=guardian_fields["guardian_kill_switch"],
                            guardian_kill_reason=guardian_fields["guardian_kill_reason"],
                            guardian_reduced_exposure=guardian_fields["guardian_reduced_exposure"],
                            guardian_confidence_penalty=guardian_fields["guardian_confidence_penalty"],
                            guardian_bias_override=guardian_fields["guardian_bias_override"],
                            guardian_scenario_changes=guardian_fields["guardian_scenario_changes"],
                            guardian_alertas=guardian_fields["guardian_alertas"],
                            active=True,
                        )

                        fb_id = save_diary_feedback(db_path, feedback)
                        if fb_id:
                            print(f"  🛡️ Guardian: feedback URGENTE salvo (ID={fb_id})")
                            if _guardian_state.active_kill_switch:
                                print(f"  🚨 KILL SWITCH ATIVO — agente deve pausar!")
                            _painel_obs.registrar_gravacao("DIARIOS")
                    except Exception as fb_err:
                        print(f"  ⚠ Guardian: erro ao salvar feedback: {fb_err}")

            except Exception as check_err:
                logger_name = "macro_guardian"
                print(f"  [{logger_name}] Erro no check: {check_err}")

            time.sleep(GUARDIAN_INTERVAL_SEC)

    except Exception as e:
        print(f"[MACRO GUARDIAN] Erro fatal: {e}")
        import traceback
        traceback.print_exc()


# ────────────────────────────────────────────────────────────────
# Thread 5 — Diario Order Manager (execucao de ordens, a cada 30s)
# ────────────────────────────────────────────────────────────────

# Intervalo do ciclo de execucao em segundos
EXECUCAO_INTERVAL_SEC = 30


def run_diario_order_manager():
    """Thread 5 — executa o DiarioOrderManager a cada 30s.

    Consolida sinais do QuantumOperatorEngine, Guardian e oportunidades
    micro, depois decide se abre/monitora/fecha posicao.
    Compartilha o GuardianState com a Thread 4 via get_guardian_state().
    """
    config = get_config()
    symbol = Symbol(config.trading_symbol)

    mt5 = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
        terminal_exe_path=r"C:\Program Files\Clear Investimentos MT5 Terminal\terminal64.exe",
    )

    if not mt5.connect():
        print("[DIARIO EXECUCAO] Erro ao conectar MT5")
        return

    db_path = _get_db_path()
    session_id = f"diarios_{int(time.time())}"
    operator = QuantumOperatorEngine()
    rl_reader = RLPerformanceReader(db_path)

    # Injetar rl_reader para evitar import circular (DiarioOrderManager
    # nao precisa reimportar o script que ja esta rodando)
    opening_context = None
    if _opening_context_runtime is not None:
        opening_context = _opening_context_runtime.features
    manager = DiarioOrderManager(
        mt5,
        db_path,
        session_id,
        rl_reader=rl_reader,
        opening_context=opening_context,
    )

    print(f"\n[DIARIO EXECUCAO] Iniciado | session={session_id} | magic=234800")
    print(f"[DIARIO EXECUCAO] Ciclo: {EXECUCAO_INTERVAL_SEC}s | "
          f"Confianca minima: 60% | SL/TP: por ATR | Autonomo")

    # Aguardar os outros threads estabilizarem
    time.sleep(15)

    try:
        while True:
            agora = datetime.now()

            try:
                # ── Obter candles e decisao macro ──
                candles = mt5.get_candles(symbol, TimeFrame.M15, count=100)
                if not candles:
                    print(f"[DIARIO EXECUCAO] {agora.strftime('%H:%M:%S')} "
                          "Sem candles, aguardando...")
                    time.sleep(EXECUCAO_INTERVAL_SEC)
                    continue

                macro = _fetch_live_macro()
                decisao_macro = operator.analyze_and_decide(
                    symbol=symbol,
                    candles=candles,
                    dollar_index=macro["dxy"],
                    vix=macro["vix"],
                    selic=macro["selic"],
                    ipca=macro["ipca"],
                    usd_brl=macro["usd_brl"],
                    embi_spread=250,
                )

                # ── Obter estado do Guardian (compartilhado com Thread 4) ──
                guardian_state = get_guardian_state()

                # ── Analise critica do direcional macro ──
                dir_analysis: dict | None = None
                try:
                    dir_analysis = rl_reader.analyze_directional_critical()
                except Exception:
                    pass

                # ── Executar ciclo do motor (autonomo) ──
                resultado = manager.ciclo(decisao_macro, candles, guardian_state, dir_analysis)

                # ── Display do ciclo ──
                sinal = resultado.get("sinal")
                acao = resultado.get("acao", "?")
                detalhe = resultado.get("detalhe", "")
                pos_aberta = resultado.get("posicao_aberta", False)

                icone = {
                    "ORDEM_ENVIADA": "🟢",
                    "MONITORANDO": "📊",
                    "FECHAMENTO_REVERSAO": "🔴",
                    "FECHAMENTO_GUARDIAN": "🛡️",
                    "POSICAO_FECHADA_MT5": "✅",
                    "BLOQUEADO": "⏸️",
                    "NENHUMA": "─",
                    "ERRO_ORDEM": "⚠️",
                }.get(acao, "?")

                print(f"\n[DIARIO EXECUCAO] {agora.strftime('%H:%M:%S')} "
                      f"{icone} {acao}")

                if sinal:
                    print(f"  dir={sinal.direcao} conf={normalize_confidence(sinal.confianca):.0%} "
                          f"align={normalize_confidence(sinal.alinhamento):.0%} "
                          f"ATR={sinal.atr:.0f} mom={sinal.momentum:+.0f} "
                          f"guardian={'OK' if sinal.guardian_ok else 'KILL'} "
                          f"wr_propria={sinal.win_rate_propria:.0f}% "
                          f"ep={sinal.n_episodios_proprios}")
                    if sinal.leitura:
                        L = sinal.leitura
                        print(f"  leitura: {L.fase_sessao} | {L.qualidade_movimento} | "
                              f"corr={L.correlacao_estado} | arm={L.risco_armadilha} | "
                              f"ajuste={L.ajuste_confianca:+.2f}")
                        print(f"  \"{L.resumo}\"")

                if detalhe:
                    print(f"  {detalhe}")

                if not pos_aberta and sinal and not sinal.pode_operar and sinal.motivo_bloqueio:
                    print(f"  Bloqueio: {sinal.motivo_bloqueio}")

            except Exception as ciclo_err:
                print(f"[DIARIO EXECUCAO] Erro no ciclo: {ciclo_err}")
                import traceback
                traceback.print_exc()

            time.sleep(EXECUCAO_INTERVAL_SEC)

    except Exception as e:
        print(f"[DIARIO EXECUCAO] Erro fatal: {e}")
        import traceback
        traceback.print_exc()
    finally:
        mt5.disconnect()


# ────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────

def main():
    """Main entry point."""
    global _opening_context_runtime

    print("=" * 80)
    print("DIÁRIOS AUTOMÁTICOS — COM ANÁLISE RL + GUARDIAN MACRO")
    print("=" * 80)
    print()
    print("Iniciando 5 diários em paralelo...")
    print()
    print("  1. Trading Storytelling    — a cada 5 minutos (narrativa macro)")
    print("  2. AI Reflection           — a cada 10 minutos (auto-avaliação)")
    print("  3. RL Performance Diary    — a cada 15 minutos (rewards + diagnóstico)")
    print("  4. Macro Scenario Guardian — a cada 2 minutos (monitor de cenário)")
    print("  5. Diario Order Manager    — a cada 30 segundos (execucao de ordens)")
    print()
    print(f"  DB: {_get_db_path()}")
    print(f"  Macro Provider: {'LIVE' if HAS_MACRO_PROVIDER else 'FALLBACK (hardcoded)'}")
    print(f"  Magic Number (Diarios): 234800")
    print()
    _opening_context_runtime = initialize_opening_context_runtime(
        db_path=_get_db_path(),
        agent_name="diarios",
        source="start_journals_full_display",
        session_id=f"diarios_{int(time.time())}",
        mode="THREADS",
        printer=print,
        operational_context_dir=os.getenv("OPENING_CONTEXT_DIR") or None,
    )
    if _opening_context_runtime.prompt_abertura_agentes:
        print("Prompt de abertura disponível para os diários:")
        print(f"  {_opening_context_runtime.prompt_abertura_agentes}")
        print()
    print("Pressione Ctrl+C para parar")
    print()

    # Painel de observabilidade dos diarios (ROADMAP-DIARIOS-01)
    # Reinicializa instancia global para uso pelas threads
    global _painel_obs
    _painel_obs = ObservabilidadeDiarios(
        limite_inatividade_min=20,
        report_dir=project_root / "outputs" / "analysis",
    )

    # Watchdog monitora e reinicia threads mortas automaticamente
    watchdog = ThreadWatchdog(intervalo_verificacao_seg=30.0)

    watchdog.registrar_thread(ConfiguracaoThread(
        nome="TradingJournal",
        funcao_alvo=run_trading_journal,
        intervalo_reinicio_seg=10,
        max_reinicios=20,
    ))
    watchdog.registrar_thread(ConfiguracaoThread(
        nome="AIReflection",
        funcao_alvo=run_ai_reflection,
        intervalo_reinicio_seg=10,
        max_reinicios=20,
    ))
    watchdog.registrar_thread(ConfiguracaoThread(
        nome="RLDiary",
        funcao_alvo=run_rl_performance_diary,
        intervalo_reinicio_seg=10,
        max_reinicios=20,
    ))
    watchdog.registrar_thread(ConfiguracaoThread(
        nome="MacroGuardian",
        funcao_alvo=run_macro_guardian,
        intervalo_reinicio_seg=10,
        max_reinicios=20,
    ))
    watchdog.registrar_thread(ConfiguracaoThread(
        nome="DiarioExecucao",
        funcao_alvo=run_diario_order_manager,
        intervalo_reinicio_seg=10,
        max_reinicios=20,
    ))

    watchdog.iniciar()

    print("[OK] 5 diários rodando com watchdog ativo!")
    print()

    try:
        while True:
            time.sleep(60)
            relatorio = watchdog.gerar_relatorio_saude()
            mortas = relatorio["total_mortas"]
            paradas = relatorio["total_paradas"]
            if mortas > 0 or paradas > 0:
                print(
                    f"[WATCHDOG] Status: {relatorio['total_rodando']} rodando, "
                    f"{mortas} mortas, {paradas} paradas permanentes."
                )
            # Exibe painel de observabilidade (ROADMAP-DIARIOS-01)
            print(_painel_obs.exibir_painel_terminal())
            try:
                print(_format_learning_block(_get_db_path()))
            except Exception as exc:
                print(f"[APRENDIZADO] erro ao montar bloco: {exc}")
    except KeyboardInterrupt:
        print("\n\nDiários interrompidos pelo usuário.")
    finally:
        watchdog.parar()
        try:
            relatorio = generate_opening_context_vs_result_report(
                db_path=_get_db_path(),
                output_dir=project_root / "outputs" / "analysis",
                outputs_root=project_root / "outputs",
            )
            print(
                "[PRE-ABERTURA] Relatorio contexto x resultado gerado: "
                f"{relatorio.markdown_path}"
            )
        except Exception as exc:
            print(f"[PRE-ABERTURA] Falha ao gerar relatorio final: {exc}")


if __name__ == "__main__":
    main()
