"""
P1-LEARNING: Framework Causal de 7 Passos - Engine (Etapas 1-2)

Framework para capturar causação em trades ao invés de simples correlação.

Etapa 1: Signal Detection
  - Detectar sinal (indicador técnico que dispara)
  - Capturar contexto de mercado (trend, volatilidade, volume)
  - Calcular context_score (confiança do contexto)

Etapa 2: Decision Recording
  - Registrar decisão tomada (ENTER, HOLD, EXIT)
  - Confiança da decisão
  - Rationale (por que decidiu)
  - Threshold values (parâmetros usados)

Próximas etapas (Etapa 3-7):
  - Monitoring: Rastreamento da posição
  - Closure: Resultado final
  - L1 Analysis: Decisão funcionou?
  - L2 Analysis: Causação ou spurious?
  - Learning: Gerar regra causal

Exemplo:
    engine = CausalLearningEngine(db_path="data/db/causal.db")

    # Etapa 1: Signal Detection
    episode = engine.registrar_signal_detection(
        episode_id="EP_20260316_100015",
        trade_id="TRD_20260316_100015",
        technical_factors={"rsi": 72.0, "indicator": "RSI"},
        market_conditions={"trend": "UPTREND", "volatility": 1.2},
        context_score=0.85
    )

    # Etapa 2: Decision Recording
    episode = engine.registrar_decision(
        episode_id="EP_20260316_100015",
        action="ENTER",
        confidence=0.68,
        reasoning="RSI overbought + uptrend",
        threshold_values={"rsi_threshold": 70}
    )
"""

import sqlite3
import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


# ============================================================================
# DATACLASSES
# ============================================================================


@dataclass
class SignalDetection:
    """Etapa 1: Detecção de sinal com contexto de mercado."""

    timestamp: datetime
    technical_factors: Dict[str, Any]
    market_conditions: Dict[str, Any]
    context_score: float

    def para_dict(self) -> Dict[str, Any]:
        """Converte para dicionário para persistência."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "technical_factors": self.technical_factors,
            "market_conditions": self.market_conditions,
            "context_score": self.context_score,
        }


@dataclass
class DecisionRecord:
    """Etapa 2: Registro de decisão tomada."""

    timestamp: datetime
    action: str  # ENTER, HOLD, EXIT
    confidence: float
    reasoning: str
    threshold_values: Dict[str, Any]

    def para_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "action": self.action,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "threshold_values": self.threshold_values,
        }


@dataclass
class CausalEpisode:
    """Episódio causal completo (7 etapas)."""

    episode_id: str
    trade_id: Optional[str]
    signal_detection: Optional[SignalDetection] = None
    decision_record: Optional[DecisionRecord] = None
    # Etapas 3-7 virão em updates sequenciais
    created_at: datetime = field(default_factory=datetime.now)

    def para_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            "episode_id": self.episode_id,
            "trade_id": self.trade_id,
            "signal_detection": (
                self.signal_detection.para_dict()
                if self.signal_detection
                else None
            ),
            "decision_record": (
                self.decision_record.para_dict()
                if self.decision_record
                else None
            ),
            "created_at": self.created_at.isoformat(),
        }


# ============================================================================
# CAUSAL LEARNING ENGINE
# ============================================================================


class CausalLearningEngine:
    """Engine para capturar e analisar causação em trades.

    Responsabilidades (Etapas 1-7):
    - Etapa 1: Registrar signal detection
    - Etapa 2: Registrar decision
    - Etapa 3: Registrar monitoring (próximo)
    - Etapa 4: Registrar closure (próximo)
    - Etapa 5: L1 Analysis - correctness
    - Etapa 6: L2 Analysis - causation
    - Etapa 7: Generate learning rule

    Atributos:
        db_path: Caminho do banco SQLite
        episodes: Cache em memória de episódios

    Exemplo:
        engine = CausalLearningEngine()
        episode = engine.registrar_signal_detection(...)
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """Inicializa engine.

        Args:
            db_path: Caminho do banco (default: data/db/causal.db)
        """
        if db_path is None:
            self.db_path = Path("data/db/causal_learning.db")
        else:
            self.db_path = Path(db_path) if not isinstance(db_path, Path) else db_path
        
        # Garantir que pasta pai existe
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Cache em memória
        self.episodes: Dict[str, CausalEpisode] = {}

        # Inicializar banco
        self._criar_tabelas()

    # ========================================================================
    # INICIALIZAÇÃO DO BANCO
    # ========================================================================

    def _criar_tabelas(self) -> None:
        """Cria tabelas necessárias no SQLite."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Tabela principal de episódios causais
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS causal_learning_episodes (
                episode_id TEXT PRIMARY KEY,
                trade_id TEXT,

                -- Etapa 1: Signal Detection
                signal_timestamp TIMESTAMP,
                signal_technical_factors TEXT,
                signal_market_conditions TEXT,
                signal_context_score REAL,

                -- Etapa 2: Decision
                decision_timestamp TIMESTAMP,
                decision_action TEXT,
                decision_confidence REAL,
                decision_reasoning TEXT,
                decision_threshold_values TEXT,

                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
            """
        )

        conn.commit()
        conn.close()

    # ========================================================================
    # ETAPA 1: SIGNAL DETECTION
    # ========================================================================

    def registrar_signal_detection(
        self,
        episode_id: str,
        technical_factors: Dict[str, Any],
        market_conditions: Dict[str, Any],
        context_score: float,
        trade_id: Optional[str] = None,
    ) -> CausalEpisode:
        """Registra detecção de sinal (Etapa 1).

        Args:
            episode_id: ID único do episódio
            technical_factors: Indicadores técnicos (RSI, BBands, etc)
            market_conditions: Contexto de mercado (trend, volatilidade)
            context_score: Score de confiança do contexto (0.0-1.0)
            trade_id: ID do trade associado (opcional)

        Returns:
            CausalEpisode com signal detection registrado
        """
        timestamp = datetime.now()

        signal_detection = SignalDetection(
            timestamp=timestamp,
            technical_factors=technical_factors,
            market_conditions=market_conditions,
            context_score=context_score,
        )

        # Criar episódio
        episode = CausalEpisode(
            episode_id=episode_id,
            trade_id=trade_id,
            signal_detection=signal_detection,
        )

        # Persistir em banco
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO causal_learning_episodes (
                episode_id, trade_id,
                signal_timestamp, signal_technical_factors,
                signal_market_conditions, signal_context_score
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                episode_id,
                trade_id,
                timestamp.isoformat(),
                json.dumps(technical_factors),
                json.dumps(market_conditions),
                context_score,
            ),
        )

        conn.commit()
        conn.close()

        # Cache
        self.episodes[episode_id] = episode

        return episode

    # ========================================================================
    # ETAPA 2: DECISION RECORDING
    # ========================================================================

    def registrar_decision(
        self,
        episode_id: str,
        action: str,
        confidence: float,
        reasoning: str,
        threshold_values: Dict[str, Any],
    ) -> CausalEpisode:
        """Registra decisão tomada (Etapa 2).

        Args:
            episode_id: ID do episódio
            action: Ação tomada (ENTER, HOLD, EXIT)
            confidence: Confiança na decisão (0.0-1.0)
            reasoning: Rationale da decisão
            threshold_values: Parâmetros usados na decisão

        Returns:
            CausalEpisode atualizado com decision record
        """
        timestamp = datetime.now()

        decision_record = DecisionRecord(
            timestamp=timestamp,
            action=action,
            confidence=confidence,
            reasoning=reasoning,
            threshold_values=threshold_values,
        )

        # Obter episódio existente ou criar novo
        if episode_id in self.episodes:
            episode: CausalEpisode = self.episodes[episode_id]
        else:
            # Carregar do banco se existir
            loaded_episode = self._carregar_do_banco(episode_id)
            if loaded_episode is None:
                raise ValueError(f"Episode {episode_id} não encontrado")
            episode = loaded_episode

        episode.decision_record = decision_record

        # Persistir em banco
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE causal_learning_episodes SET
                decision_timestamp = ?,
                decision_action = ?,
                decision_confidence = ?,
                decision_reasoning = ?,
                decision_threshold_values = ?,
                updated_at = ?
            WHERE episode_id = ?
            """,
            (
                timestamp.isoformat(),
                action,
                confidence,
                reasoning,
                json.dumps(threshold_values),
                timestamp.isoformat(),
                episode_id,
            ),
        )

        conn.commit()
        conn.close()

        # Atualizar cache
        self.episodes[episode_id] = episode

        return episode

    # ========================================================================
    # CONSULTAS E RECUPERAÇÃO
    # ========================================================================

    def listar_episodes(self) -> List[CausalEpisode]:
        """Lista todos os episódios registrados.

        Returns:
            Lista de CausalEpisode
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            "SELECT episode_id FROM causal_learning_episodes "
            "ORDER BY created_at DESC"
        )
        rows = cursor.fetchall()
        conn.close()

        episodes = []
        for (episode_id,) in rows:
            episode = self._carregar_do_banco(episode_id)
            if episode:
                episodes.append(episode)

        return episodes

    def obter_episode(self, episode_id: str) -> Optional[CausalEpisode]:
        """Obtém episódio por ID.

        Args:
            episode_id: ID do episódio

        Returns:
            CausalEpisode ou None se não encontrado
        """
        # Verificar cache primeiro
        if episode_id in self.episodes:
            return self.episodes[episode_id]

        # Carregar do banco
        return self._carregar_do_banco(episode_id)

    def _carregar_do_banco(
        self, episode_id: str
    ) -> Optional[CausalEpisode]:
        """Carrega episódio do banco SQLite.

        Args:
            episode_id: ID do episódio

        Returns:
            CausalEpisode ou None
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT episode_id, trade_id,
                   signal_timestamp, signal_technical_factors,
                   signal_market_conditions, signal_context_score,
                   decision_timestamp, decision_action,
                   decision_confidence, decision_reasoning,
                   decision_threshold_values
            FROM causal_learning_episodes
            WHERE episode_id = ?
            """,
            (episode_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        (
            ep_id,
            trade_id,
            sig_ts,
            sig_tech,
            sig_market,
            sig_score,
            dec_ts,
            dec_action,
            dec_conf,
            dec_reason,
            dec_thresh,
        ) = row

        # Construir signal detection
        signal_detection = None
        if sig_ts:
            signal_detection = SignalDetection(
                timestamp=datetime.fromisoformat(sig_ts),
                technical_factors=json.loads(sig_tech) if sig_tech else {},
                market_conditions=json.loads(sig_market) if sig_market else {},
                context_score=sig_score or 0.0,
            )

        # Construir decision record
        decision_record = None
        if dec_ts:
            decision_record = DecisionRecord(
                timestamp=datetime.fromisoformat(dec_ts),
                action=dec_action or "",
                confidence=dec_conf or 0.0,
                reasoning=dec_reason or "",
                threshold_values=(
                    json.loads(dec_thresh) if dec_thresh else {}
                ),
            )

        # Construir episódio
        episode = CausalEpisode(
            episode_id=ep_id,
            trade_id=trade_id,
            signal_detection=signal_detection,
            decision_record=decision_record,
        )

        # Cache
        self.episodes[episode_id] = episode

        return episode

    # ========================================================================
    # ESTATÍSTICAS
    # ========================================================================

    def contar_episodios(self) -> int:
        """Conta total de episódios registrados.

        Returns:
            Número de episódios
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM causal_learning_episodes")
        result = cursor.fetchone()
        conn.close()

        if result is None:
            return 0
        count: int = result[0]
        return count

    def contar_com_decision(self) -> int:
        """Conta episódios que tem decision registrado.

        Returns:
            Número com decision_action não nulo
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM causal_learning_episodes "
            "WHERE decision_action IS NOT NULL"
        )
        result = cursor.fetchone()
        conn.close()

        if result is None:
            return 0
        count: int = result[0]
        return count
