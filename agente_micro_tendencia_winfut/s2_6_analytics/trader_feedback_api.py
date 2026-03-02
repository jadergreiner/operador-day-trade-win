"""
Trader Feedback API - S2-6

API para comunicacao bidirecional com o trader:
- Aprovacao/rejeicao de sinais
- Feedback em tempo real
- Parametros de override
- Status sistema
"""

import asyncio
import json
from datetime import datetime
from typing import Callable, Dict, Optional, Any, Set
from dataclasses import asdict

from .config import AnalyticsConfig
from .models import Signal, TraderFeedback, InterventionType


class TraderFeedbackAPI:
    """API para feedback e intervencao do trader"""

    def __init__(self, config: Optional[AnalyticsConfig] = None) -> None:
        """
        Inicializa a API de feedback

        Args:
            config: Configuracao do modulo
        """
        self.config = config or AnalyticsConfig()
        self.clients: Set[str] = set()  # Traders conectados
        self.pending_signals: Dict[str, Signal] = {}  # Sinais aguardando aprovacao
        self.callbacks: Dict[str, Callable] = {}  # Callbacks para eventos

    def register_callback(
        self,
        event_name: str,
        callback: Callable,
    ) -> None:
        """
        Registra callback para um evento

        Args:
            event_name: Nome do evento (signal_approved, signal_rejected, etc)
            callback: Funcao callback
        """
        self.callbacks[event_name] = callback

    async def trigger_callback(
        self,
        event_name: str,
        data: Dict[str, Any],
    ) -> None:
        """
        Dispara um callback registrado

        Args:
            event_name: Nome do evento
            data: Dados do evento
        """
        if event_name in self.callbacks:
            callback = self.callbacks[event_name]
            if asyncio.iscoroutinefunction(callback):
                await callback(data)
            else:
                callback(data)

    def submit_signal_for_approval(
        self,
        signal: Signal,
        timeout_seconds: Optional[float] = None,
    ) -> None:
        """
        Submete um sinal para aprovacao do trader

        Args:
            signal: Sinal a ser aprovado
            timeout_seconds: Timeout para decisao (None = nao expira)
        """
        self.pending_signals[signal.signal_id] = signal

        # Callback para notificar traders conectados
        asyncio.create_task(
            self.trigger_callback(
                "signal_submitted",
                {
                    "signal_id": signal.signal_id,
                    "direction": signal.direction,
                    "confidence": signal.confidence_score,
                    "smc_confluence": signal.smc_confluence_score,
                    "entry_price": signal.entry_price,
                    "stop_loss": signal.stop_loss,
                    "take_profit": signal.take_profit,
                    "timestamp": signal.timestamp.isoformat(),
                },
            )
        )

        # Configurar timeout se especificado
        if timeout_seconds:
            asyncio.create_task(
                self._signal_timeout(signal.signal_id, timeout_seconds)
            )

    async def approve_signal(
        self,
        signal_id: str,
        trader_id: str,
    ) -> bool:
        """
        Trader aprova um sinal

        Args:
            signal_id: ID do sinal
            trader_id: ID do trader que aprovou

        Returns:
            True se aprovacao foi registrada
        """
        if signal_id not in self.pending_signals:
            return False

        signal = self.pending_signals.pop(signal_id)
        signal.status = signal.status.APPROVED
        signal.approved_by = trader_id
        signal.approval_timestamp = datetime.now()

        await self.trigger_callback(
            "signal_approved",
            {
                "signal_id": signal_id,
                "trader_id": trader_id,
                "approval_timestamp": signal.approval_timestamp.isoformat(),
            },
        )

        return True

    async def reject_signal(
        self,
        signal_id: str,
        trader_id: str,
        reason: str = "",
    ) -> bool:
        """
        Trader rejeita um sinal

        Args:
            signal_id: ID do sinal
            trader_id: ID do trader que rejeitou
            reason: Motivo da rejeicao

        Returns:
            True se rejeicao foi registrada
        """
        if signal_id not in self.pending_signals:
            return False

        signal = self.pending_signals.pop(signal_id)
        signal.status = signal.status.REJECTED

        await self.trigger_callback(
            "signal_rejected",
            {
                "signal_id": signal_id,
                "trader_id": trader_id,
                "reason": reason,
                "rejection_timestamp": datetime.now().isoformat(),
            },
        )

        return True

    async def submit_feedback(
        self,
        signal_id: str,
        trader_id: str,
        feedback_type: str,
        rating: int,
        comment: str,
        suggestions: Optional[Dict[str, Any]] = None,
    ) -> TraderFeedback:
        """
        Trader submete feedback sobre um sinal

        Args:
            signal_id: ID do sinal
            trader_id: ID do trader
            feedback_type: Tipo de feedback
            rating: Rating (1-5)
            comment: Comentario
            suggestions: Sugestoes (opcional)

        Returns:
            TraderFeedback registrado
        """
        feedback = TraderFeedback(
            feedback_id=f"feedback_{signal_id}_{int(datetime.now().timestamp())}",
            timestamp=datetime.now(),
            trader_id=trader_id,
            signal_id=signal_id,
            feedback_type=feedback_type,
            rating=rating,
            comment=comment,
            suggestions=suggestions or {},
        )

        await self.trigger_callback(
            "feedback_submitted",
            asdict(feedback),
        )

        return feedback

    async def _signal_timeout(self, signal_id: str, timeout_seconds: float) -> None:
        """
        Timeout para decisao do trader sobre sinal

        Args:
            signal_id: ID do sinal
            timeout_seconds: Segundos de timeout
        """
        await asyncio.sleep(timeout_seconds)

        if signal_id in self.pending_signals:
            signal = self.pending_signals.pop(signal_id)

            # Auto-reject se timeout
            await self.trigger_callback(
                "signal_timeout",
                {
                    "signal_id": signal_id,
                    "action": "auto_rejected",
                    "timeout_seconds": timeout_seconds,
                },
            )

    def get_pending_signals(self) -> Dict[str, Signal]:
        """
        Obtem todos sinais pendentes de aprovacao

        Returns:
            Dicionario de sinais pendentes
        """
        return self.pending_signals.copy()

    def get_pending_count(self) -> int:
        """
        Obtem quantidade de sinais pendentes

        Returns:
            Quantidade de sinais aguardando aprovacao
        """
        return len(self.pending_signals)

    def register_trader(self, trader_id: str) -> None:
        """
        Registra trader conectado

        Args:
            trader_id: ID do trader
        """
        self.clients.add(trader_id)

    def unregister_trader(self, trader_id: str) -> None:
        """
        Desregistra trader desconectado

        Args:
            trader_id: ID do trader
        """
        self.clients.discard(trader_id)

    def get_connected_traders(self) -> Set[str]:
        """
        Obtem lista de traders conectados

        Returns:
            Set com IDs dos traders conectados
        """
        return self.clients.copy()
