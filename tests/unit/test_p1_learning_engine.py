"""
P1-LEARNING: Testes para CausalLearningEngine (Etapas 1-2)

Framework causal de 7 passos para capturar causação em trades
e extrair regras aprendizadas estruturadas.

Testes cobrem:
- Etapa 1: Signal detection capture (technical + market context)
- Etapa 2: Decision logging (action + confidence + reasoning)
- Persistência em SQLite
- Validação de tipos
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path
import tempfile
import json

from src.application.p1_learning_engine import (
    CausalLearningEngine,
    CausalEpisode,
    SignalDetection,
    DecisionRecord,
)


class TestSignalDetection:
    """Testes para captura de signal detection (Etapa 1)."""

    def test_criar_signal_detection_valido(self) -> None:
        """Deve criar registro de signal detection."""
        detection = SignalDetection(
            timestamp=datetime.now(),
            technical_factors={
                "indicator": "RSI",
                "value": 72.0,
                "threshold": 70.0,
            },
            market_conditions={
                "trend": "UPTREND",
                "volatility": 1.2,
                "volume_ratio": 1.5,
            },
            context_score=0.85,
        )

        assert detection.technical_factors["indicator"] == "RSI"
        assert detection.market_conditions["trend"] == "UPTREND"
        assert detection.context_score == 0.85

    def test_signal_detection_para_dict(self) -> None:
        """Deve converter SignalDetection para dicionário."""
        detection = SignalDetection(
            timestamp=datetime(2026, 3, 16, 10, 30, 0),
            technical_factors={"rsi": 72.0},
            market_conditions={"trend": "UPTREND"},
            context_score=0.85,
        )

        data = detection.para_dict()
        assert data["technical_factors"]["rsi"] == 72.0
        assert isinstance(data["timestamp"], str)

    def test_signal_detection_com_score_baixo(self) -> None:
        """Deve permitir signal detection com contexto fraco."""
        detection = SignalDetection(
            timestamp=datetime.now(),
            technical_factors={"rsi": 72.0},
            market_conditions={"trend": "SIDEWAYS"},
            context_score=0.35,  # Contexto fraco
        )

        assert detection.context_score == 0.35


class TestDecisionRecord:
    """Testes para decision logging (Etapa 2)."""

    def test_criar_decision_record_valido(self) -> None:
        """Deve criar registro de decisão."""
        decision = DecisionRecord(
            timestamp=datetime.now(),
            action="ENTER",
            confidence=0.68,
            reasoning="RSI overbought + strong uptrend confirmation",
            threshold_values={"rsi_threshold": 70, "volume_ratio_min": 1.3},
        )

        assert decision.action == "ENTER"
        assert decision.confidence == 0.68

    def test_decision_record_para_dict(self) -> None:
        """Deve converter DecisionRecord para dicionário."""
        decision = DecisionRecord(
            timestamp=datetime(2026, 3, 16, 10, 30, 15),
            action="HOLD",
            confidence=0.45,
            reasoning="Not enough confluence",
            threshold_values={"min_confluence": 3},
        )

        data = decision.para_dict()
        assert data["action"] == "HOLD"
        assert isinstance(data["timestamp"], str)

    def test_decision_record_diferentes_acoes(self) -> None:
        """Deve aceitar diferentes tipos de ações."""
        for action in ["ENTER", "HOLD", "EXIT"]:
            decision = DecisionRecord(
                timestamp=datetime.now(),
                action=action,
                confidence=0.60,
                reasoning="Test",
                threshold_values={},
            )
            assert decision.action == action


class TestCausalEpisode:
    """Testes para dataclass CausalEpisode."""

    def test_criar_causal_episode(self) -> None:
        """Deve criar episódio causal."""
        detection = SignalDetection(
            timestamp=datetime.now(),
            technical_factors={"rsi": 72.0},
            market_conditions={"trend": "UPTREND"},
            context_score=0.85,
        )

        decision = DecisionRecord(
            timestamp=datetime.now(),
            action="ENTER",
            confidence=0.68,
            reasoning="Valid signal",
            threshold_values={"rsi_threshold": 70},
        )

        episode = CausalEpisode(
            episode_id="EP_20260316_100015",
            trade_id="TRD_20260316_100015",
            signal_detection=detection,
            decision_record=decision,
        )

        assert episode.episode_id == "EP_20260316_100015"
        assert episode.signal_detection.context_score == 0.85


class TestCausalLearningEngine:
    """Testes para CausalLearningEngine."""

    @pytest.fixture
    def engine(self, tmp_path: Path) -> CausalLearningEngine:
        """Cria engine para testes."""
        engine = CausalLearningEngine(
            db_path=tmp_path / "test_causal.db"
        )
        return engine

    def test_initializar_engine(self, engine: CausalLearningEngine) -> None:
        """Deve inicializar engine corretamente."""
        assert engine.db_path.exists()
        # Verificar que tabela foi criada
        import sqlite3

        conn = sqlite3.connect(str(engine.db_path))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='causal_learning_episodes'"
        )
        result = cursor.fetchone()
        conn.close()
        assert result is not None

    def test_registrar_signal_detection(
        self, engine: CausalLearningEngine
    ) -> None:
        """Deve registrar signal detection (Etapa 1)."""
        episode_id = "EP_20260316_100015"
        technical = {"rsi": 72.0, "indicator": "RSI"}
        market = {"trend": "UPTREND", "volatility": 1.2}

        episode = engine.registrar_signal_detection(
            episode_id=episode_id,
            technical_factors=technical,
            market_conditions=market,
            context_score=0.85,
        )

        assert episode.episode_id == episode_id
        assert episode.signal_detection is not None
        assert episode.signal_detection.technical_factors["rsi"] == 72.0

    def test_registrar_decision(
        self, engine: CausalLearningEngine
    ) -> None:
        """Deve registrar decisão (Etapa 2)."""
        episode_id = "EP_20260316_100015"

        # Primeiro registrar signal detection
        engine.registrar_signal_detection(
            episode_id=episode_id,
            technical_factors={"rsi": 72.0},
            market_conditions={"trend": "UPTREND"},
            context_score=0.85,
        )

        # Depois registrar decision
        episode = engine.registrar_decision(
            episode_id=episode_id,
            action="ENTER",
            confidence=0.68,
            reasoning="Valid RSI overbought",
            threshold_values={"rsi_threshold": 70},
        )

        assert episode.decision_record is not None
        assert episode.decision_record.action == "ENTER"

    def test_listar_episodes(self, engine: CausalLearningEngine) -> None:
        """Deve listar todos os episódios registrados."""
        # Registrar 3 episódios
        for i in range(3):
            episode_id = f"EP_20260316_10001{i}"
            engine.registrar_signal_detection(
                episode_id=episode_id,
                technical_factors={"rsi": 70.0 + i},
                market_conditions={"trend": "UPTREND"},
                context_score=0.80 + (0.05 * i),
            )

        episodes = engine.listar_episodes()
        assert len(episodes) == 3

    def test_obter_episode_por_id(self, engine: CausalLearningEngine) -> None:
        """Deve obter episódio por ID."""
        episode_id = "EP_20260316_100015"

        # Registrar episódio
        engine.registrar_signal_detection(
            episode_id=episode_id,
            technical_factors={"rsi": 72.0},
            market_conditions={"trend": "UPTREND"},
            context_score=0.85,
        )

        # Recuperar
        episode = engine.obter_episode(episode_id)
        assert episode is not None
        assert episode.episode_id == episode_id

    def test_obter_episode_nao_existente(
        self, engine: CausalLearningEngine
    ) -> None:
        """Deve retornar None para episódio inexistente."""
        episode = engine.obter_episode("EP_NAO_EXISTE")
        assert episode is None

    def test_persistencia_multiplos_campos(
        self, engine: CausalLearningEngine
    ) -> None:
        """Deve persistir todos os campos de signal + decision."""
        episode_id = "EP_20260316_100015"
        trade_id = "TRD_20260316_100015"

        technical = {
            "indicator": "RSI",
            "value": 72.5,
            "threshold": 70.0,
            "period": 14,
        }
        market = {
            "trend": "UPTREND",
            "volatility": 1.25,
            "volume_ratio": 1.6,
            "support_level": 12500,
        }

        # Registrar signal
        episode = engine.registrar_signal_detection(
            episode_id=episode_id,
            trade_id=trade_id,
            technical_factors=technical,
            market_conditions=market,
            context_score=0.87,
        )

        # Registrar decision
        episode = engine.registrar_decision(
            episode_id=episode_id,
            action="ENTER",
            confidence=0.72,
            reasoning="Strong confluence of signals",
            threshold_values={
                "min_confluence": 3,
                "rsi_threshold": 70,
                "volume_min": 1.3,
            },
        )

        # Recuperar e validar
        retrieved = engine.obter_episode(episode_id)
        assert retrieved is not None
        assert retrieved.signal_detection.technical_factors["value"] == 72.5
        assert retrieved.decision_record.confidence == 0.72

    def test_tipos_retorno_corretos(
        self, engine: CausalLearningEngine
    ) -> None:
        """Deve retornar tipos corretos em todos os métodos."""
        episode_id = "EP_20260316_100015"

        # Registrar
        episode = engine.registrar_signal_detection(
            episode_id=episode_id,
            technical_factors={"rsi": 72.0},
            market_conditions={"trend": "UPTREND"},
            context_score=0.85,
        )
        assert isinstance(episode, CausalEpisode)

        # Listar
        episodes = engine.listar_episodes()
        assert isinstance(episodes, list)
        assert all(isinstance(e, CausalEpisode) for e in episodes)

        # Obter
        retrieved = engine.obter_episode(episode_id)
        assert isinstance(retrieved, CausalEpisode) or retrieved is None

    def test_sequencia_completa_etapas_1_2(
        self, engine: CausalLearningEngine
    ) -> None:
        """Deve executar sequência completa Etapas 1-2."""
        episode_id = "EP_20260316_100020"
        trade_id = "TRD_20260316_100020"

        # Etapa 1: Signal Detection
        detection_episode = engine.registrar_signal_detection(
            episode_id=episode_id,
            trade_id=trade_id,
            technical_factors={
                "atr": 45.2,
                "bollinger_upper": 12625.5,
                "rsi": 68.3,
            },
            market_conditions={
                "regime": "UPTREND",
                "volume_profile": "BULLISH",
                "volatility_level": "NORMAL",
            },
            context_score=0.88,
        )

        assert detection_episode.signal_detection is not None
        assert detection_episode.decision_record is None

        # Etapa 2: Decision
        decision_episode = engine.registrar_decision(
            episode_id=episode_id,
            action="ENTER",
            confidence=0.75,
            reasoning="Strong bounce pattern + confluence",
            threshold_values={
                "min_confluence": 3,
                "min_context_score": 0.80,
            },
        )

        assert decision_episode.decision_record is not None
        assert decision_episode.signal_detection is not None

        # Validar estado final
        final = engine.obter_episode(episode_id)
        assert final.signal_detection.context_score == 0.88
        assert final.decision_record.action == "ENTER"
