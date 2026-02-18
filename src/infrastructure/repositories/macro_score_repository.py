"""Repository para persistencia do macro score."""

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from src.infrastructure.database.schema import (
    MacroScoreDecisionModel,
    MacroScoreFeedbackModel,
    MacroScoreItemModel,
)


class IMacroScoreRepository(ABC):
    """Interface do repositorio de macro score."""

    @abstractmethod
    def save_item_scores(
        self, session_id: str, items: list[dict]
    ) -> None:
        """Persiste scores individuais de cada item."""
        pass

    @abstractmethod
    def save_decision(self, decision: dict) -> None:
        """Persiste a decisao final do macro score."""
        pass

    @abstractmethod
    def save_feedback(self, feedback: dict) -> None:
        """Persiste feedback de aprendizado por reforco."""
        pass

    @abstractmethod
    def get_recent_decisions(self, limit: int = 10) -> list[dict]:
        """Retorna as decisoes mais recentes."""
        pass

    @abstractmethod
    def get_item_accuracy(
        self, item_number: int, limit: int = 50
    ) -> Optional[float]:
        """Calcula acuracia historica de um item."""
        pass

    @abstractmethod
    def get_pending_feedback(
        self, evaluation_minutes: int
    ) -> list[dict]:
        """Retorna decisoes pendentes de avaliacao de feedback."""
        pass


class SqliteMacroScoreRepository(IMacroScoreRepository):
    """Implementacao SQLite do repositorio de macro score."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def save_item_scores(
        self, session_id: str, items: list[dict]
    ) -> None:
        """Persiste scores individuais."""
        for item in items:
            model = MacroScoreItemModel(
                session_id=session_id,
                timestamp=item["timestamp"],
                item_number=item["item_number"],
                symbol=item["symbol"],
                resolved_symbol=item.get("resolved_symbol"),
                category=item["category"],
                correlation=item["correlation"],
                opening_price=item.get("opening_price"),
                current_price=item.get("current_price"),
                score=item["score"],
                weight=item["weight"],
                weighted_score=item["weighted_score"],
                status=item["status"],
                detail=item.get("detail"),
            )
            self.session.add(model)

        self.session.commit()

    def save_decision(self, decision: dict) -> None:
        """Persiste decisao final."""
        model = MacroScoreDecisionModel(
            session_id=decision["session_id"],
            timestamp=decision["timestamp"],
            total_items=decision["total_items"],
            items_available=decision["items_available"],
            items_unavailable=decision["items_unavailable"],
            score_bullish=decision["score_bullish"],
            score_bearish=decision["score_bearish"],
            score_neutral=decision["score_neutral"],
            score_final=decision["score_final"],
            signal=decision["signal"],
            confidence=decision.get("confidence"),
            win_price_at_decision=decision.get("win_price_at_decision"),
            summary=decision.get("summary"),
        )
        self.session.add(model)
        self.session.commit()

    def save_feedback(self, feedback: dict) -> None:
        """Persiste feedback de aprendizado."""
        model = MacroScoreFeedbackModel(
            session_id=feedback["session_id"],
            timestamp_decision=feedback["timestamp_decision"],
            signal_at_decision=feedback["signal_at_decision"],
            score_at_decision=feedback["score_at_decision"],
            win_price_at_decision=feedback["win_price_at_decision"],
            evaluation_minutes=feedback["evaluation_minutes"],
            win_price_at_evaluation=feedback.get("win_price_at_evaluation"),
            actual_direction=feedback.get("actual_direction"),
            decision_correct=feedback.get("decision_correct"),
            price_change_points=feedback.get("price_change_points"),
            evaluated_at=feedback.get("evaluated_at"),
        )
        self.session.add(model)
        self.session.commit()

    def get_recent_decisions(self, limit: int = 10) -> list[dict]:
        """Retorna decisoes recentes."""
        models = (
            self.session.query(MacroScoreDecisionModel)
            .order_by(MacroScoreDecisionModel.timestamp.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "session_id": m.session_id,
                "timestamp": m.timestamp,
                "total_items": m.total_items,
                "items_available": m.items_available,
                "score_final": m.score_final,
                "signal": m.signal,
                "confidence": m.confidence,
                "win_price_at_decision": m.win_price_at_decision,
            }
            for m in models
        ]

    def get_item_accuracy(
        self, item_number: int, limit: int = 50
    ) -> Optional[float]:
        """Calcula acuracia de um item baseado no feedback historico.

        Junta items com feedback para verificar se o score do item
        acompanhou a direcao real do WIN.
        """
        # Buscar items recentes com seus session_ids
        item_models = (
            self.session.query(MacroScoreItemModel)
            .filter(MacroScoreItemModel.item_number == item_number)
            .order_by(MacroScoreItemModel.timestamp.desc())
            .limit(limit)
            .all()
        )

        if not item_models:
            return None

        correct = 0
        total = 0

        for item_model in item_models:
            # Buscar feedback correspondente
            feedback = (
                self.session.query(MacroScoreFeedbackModel)
                .filter(
                    MacroScoreFeedbackModel.session_id == item_model.session_id,
                    MacroScoreFeedbackModel.decision_correct.isnot(None),
                )
                .first()
            )

            if feedback is None:
                continue

            total += 1
            # O item contribuiu na direcao correta?
            item_score = item_model.score
            actual_dir = feedback.actual_direction

            if item_score > 0 and actual_dir == "UP":
                correct += 1
            elif item_score < 0 and actual_dir == "DOWN":
                correct += 1
            elif item_score == 0:
                # Neutro nao conta como erro nem acerto
                total -= 1

        if total == 0:
            return None

        return correct / total

    def get_pending_feedback(
        self, evaluation_minutes: int
    ) -> list[dict]:
        """Retorna decisoes que precisam ser avaliadas."""
        # Buscar feedbacks criados mas ainda nao avaliados
        models = (
            self.session.query(MacroScoreFeedbackModel)
            .filter(
                MacroScoreFeedbackModel.evaluation_minutes == evaluation_minutes,
                MacroScoreFeedbackModel.evaluated_at.is_(None),
            )
            .all()
        )

        return [
            {
                "id": m.id,
                "session_id": m.session_id,
                "timestamp_decision": m.timestamp_decision,
                "signal_at_decision": m.signal_at_decision,
                "score_at_decision": m.score_at_decision,
                "win_price_at_decision": m.win_price_at_decision,
                "evaluation_minutes": m.evaluation_minutes,
            }
            for m in models
        ]

    def update_feedback_evaluation(
        self,
        feedback_id: int,
        win_price_at_evaluation: Decimal,
        actual_direction: str,
        decision_correct: bool,
        price_change_points: Decimal,
    ) -> None:
        """Atualiza um registro de feedback com o resultado real."""
        model = (
            self.session.query(MacroScoreFeedbackModel)
            .filter(MacroScoreFeedbackModel.id == feedback_id)
            .first()
        )

        if model:
            model.win_price_at_evaluation = win_price_at_evaluation
            model.actual_direction = actual_direction
            model.decision_correct = 1 if decision_correct else 0
            model.price_change_points = price_change_points
            model.evaluated_at = datetime.now()
            self.session.commit()
