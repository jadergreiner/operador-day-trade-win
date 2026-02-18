"""Avaliador de feedback por reforco para o macro score."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

from src.infrastructure.adapters.mt5_adapter import MT5Adapter
from src.infrastructure.repositories.macro_score_repository import (
    IMacroScoreRepository,
)

logger = logging.getLogger(__name__)


class FeedbackEvaluator:
    """Avalia decisoes passadas do macro score contra resultados reais.

    Compara o sinal emitido (COMPRA/VENDA/NEUTRO) com a direcao real
    do WIN apos intervalos de 30min, 1h e 2h.

    Funcionalidades:
    - Avaliar decisoes pendentes
    - Calcular acuracia por item e por categoria
    - Sugerir ajuste de pesos (aprovacao manual)
    """

    def __init__(
        self,
        mt5_adapter: MT5Adapter,
        repository: IMacroScoreRepository,
    ) -> None:
        self._mt5 = mt5_adapter
        self._repository = repository

    def evaluate_pending(self, evaluation_minutes: int = 30) -> int:
        """Avalia todas as decisoes pendentes para um intervalo.

        Args:
            evaluation_minutes: Intervalo de avaliacao (30, 60, 120)

        Returns:
            Quantidade de decisoes avaliadas.
        """
        pending = self._repository.get_pending_feedback(evaluation_minutes)
        evaluated = 0

        for feedback in pending:
            # Verificar se ja passou tempo suficiente
            decision_time = feedback["timestamp_decision"]
            now = datetime.now()
            elapsed_minutes = (now - decision_time).total_seconds() / 60

            if elapsed_minutes < evaluation_minutes:
                continue  # Ainda nao deu tempo

            # Obter preco atual do WIN
            win_price_now = self._get_win_price()
            if win_price_now is None:
                continue

            win_price_decision = Decimal(str(feedback["win_price_at_decision"]))
            price_change = win_price_now - win_price_decision

            # Determinar direcao real
            if price_change > 0:
                actual_direction = "UP"
            elif price_change < 0:
                actual_direction = "DOWN"
            else:
                actual_direction = "FLAT"

            # Verificar se a decisao foi correta
            signal = feedback["signal_at_decision"]
            decision_correct = self._check_correctness(
                signal, actual_direction
            )

            # Atualizar no repositorio
            self._repository.update_feedback_evaluation(
                feedback_id=feedback["id"],
                win_price_at_evaluation=win_price_now,
                actual_direction=actual_direction,
                decision_correct=decision_correct,
                price_change_points=price_change,
            )

            evaluated += 1

            logger.info(
                "Feedback avaliado: sessao=%s | %dmin | sinal=%s | "
                "direcao_real=%s | correto=%s | variacao=%s pts",
                feedback["session_id"][:8],
                evaluation_minutes,
                signal,
                actual_direction,
                decision_correct,
                price_change,
            )

        return evaluated

    def get_item_accuracy(self, item_number: int) -> Optional[float]:
        """Retorna acuracia historica de um item.

        Args:
            item_number: Numero do item (1-85)

        Returns:
            Acuracia (0 a 1) ou None se dados insuficientes.
        """
        return self._repository.get_item_accuracy(item_number)

    def get_accuracy_report(self) -> dict:
        """Gera relatorio de acuracia por item e categoria.

        Returns:
            Dicionario com acuracias agrupadas.
        """
        from src.application.services.macro_score.item_registry import (
            get_item_registry,
        )

        registry = get_item_registry()
        report = {
            "items": [],
            "categories": {},
            "overall": None,
        }

        all_accuracies = []

        for item in registry:
            accuracy = self.get_item_accuracy(item.number)
            item_data = {
                "number": item.number,
                "symbol": item.symbol,
                "name": item.name,
                "category": str(item.category),
                "accuracy": accuracy,
            }
            report["items"].append(item_data)

            if accuracy is not None:
                all_accuracies.append(accuracy)

                # Agrupar por categoria
                cat = str(item.category)
                if cat not in report["categories"]:
                    report["categories"][cat] = []
                report["categories"][cat].append(accuracy)

        # Calcular medias por categoria
        for cat, accuracies in report["categories"].items():
            report["categories"][cat] = (
                sum(accuracies) / len(accuracies) if accuracies else None
            )

        # Acuracia geral
        if all_accuracies:
            report["overall"] = sum(all_accuracies) / len(all_accuracies)

        return report

    def suggest_weight_adjustments(
        self, min_evaluations: int = 20
    ) -> list[dict]:
        """Sugere ajustes de peso baseado na acuracia historica.

        Itens com acuracia consistentemente alta devem ganhar peso.
        Itens com acuracia baixa (ruido) devem perder peso.

        Args:
            min_evaluations: Minimo de avaliacoes para sugerir ajuste.

        Returns:
            Lista de sugestoes de ajuste.
        """
        from src.application.services.macro_score.item_registry import (
            get_item_registry,
        )

        registry = get_item_registry()
        suggestions = []

        for item in registry:
            accuracy = self._repository.get_item_accuracy(
                item.number, limit=min_evaluations
            )
            if accuracy is None:
                continue

            current_weight = float(item.weight)

            if accuracy >= 0.7:
                # Alta acuracia - sugerir aumento
                suggested_weight = min(current_weight * 1.5, 3.0)
                reason = f"Acuracia alta ({accuracy:.0%}) - aumentar peso"
            elif accuracy <= 0.4:
                # Baixa acuracia - sugerir reducao
                suggested_weight = max(current_weight * 0.5, 0.1)
                reason = f"Acuracia baixa ({accuracy:.0%}) - reduzir peso"
            else:
                continue  # Acuracia mediana, manter

            suggestions.append({
                "item_number": item.number,
                "symbol": item.symbol,
                "name": item.name,
                "current_weight": current_weight,
                "suggested_weight": round(suggested_weight, 2),
                "accuracy": round(accuracy, 4),
                "reason": reason,
            })

        return suggestions

    def _check_correctness(
        self, signal: str, actual_direction: str
    ) -> bool:
        """Verifica se o sinal foi correto."""
        if signal == "COMPRA" and actual_direction == "UP":
            return True
        if signal == "VENDA" and actual_direction == "DOWN":
            return True
        if signal == "NEUTRO" and actual_direction == "FLAT":
            return True
        return False

    def _get_win_price(self) -> Optional[Decimal]:
        """Obtem preco atual do WIN."""
        try:
            tick = self._mt5.get_symbol_info_tick("WIN$N")
            if tick:
                return tick.last.value
            return None
        except Exception:
            return None
