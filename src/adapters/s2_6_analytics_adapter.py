#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
S2-6 Analytics Adapter
Integra Analytics de Intervenção Manual ao Operador Auto-Trade.

Sincroniza cada trade/decisão/resultado com API REST S2-6.
"""

import requests
import logging
from typing import Optional, Dict
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TradeEvent:
    """Evento de trade para registrar no Analytics"""
    symbol: str
    action: str  # OVERRIDE, PAUSE, CANCEL, EXECUTE
    trader_decision: str  # Descrição da decisão
    p_and_l: float = 0.0
    result: Optional[str] = None  # WIN, LOSS, PARTIAL
    timestamp: Optional[str] = None
    intervention_id: Optional[int] = None


class AnalyticsAdapter:
    """
    Adapter para S2-6 Analytics REST API.

    Registra intervenções manuais e automáticas em tempo real.
    Integração com `/api/intervention/log` e `/api/intervention/{id}/result`.
    """

    def __init__(self, api_url: str = "http://localhost:8000"):
        """
        Args:
            api_url: URL base da API S2-6 (default: production)
        """
        self.api_url = api_url
        self.session = requests.Session()
        self.timeout = 5.0
        self.enabled = self._check_api_available()

        if self.enabled:
            logger.info(f"[S2-6] Analytics adapter inicializado: {api_url}")
        else:
            logger.warning(f"[S2-6] Analytics API indisponível: {api_url}")

    def _check_api_available(self) -> bool:
        """Verifica se API de Analytics está disponível"""
        try:
            resp = self.session.get(
                f"{self.api_url}/health",
                timeout=2.0
            )
            return resp.status_code == 200
        except Exception as e:
            logger.debug(f"[S2-6] Health check falhou: {e}")
            return False

    def log_intervention(self, event: TradeEvent) -> Optional[int]:
        """
        Registra uma intervenção manual (trade/override).

        Args:
            event: TradeEvent com detalhes da intervenção

        Returns:
            intervention_id se sucesso, None se erro
        """
        if not self.enabled:
            logger.warning("[S2-6] Analytics desabilitado, skip log_intervention")
            return None

        try:
            payload = {
                "symbol": event.symbol,
                "action": event.action,
                "trader_decision": event.trader_decision,
                "p_and_l": event.p_and_l,
            }

            resp = self.session.post(
                f"{self.api_url}/api/intervention/log",
                json=payload,
                timeout=self.timeout
            )

            if resp.status_code in [200, 201]:
                data = resp.json()
                intervention_id = data.get("intervention_id") or data.get("id")
                logger.info(f"[S2-6] Intervencao registrada: id={intervention_id}, {event.symbol} {event.action}")
                return intervention_id
            else:
                logger.error(f"[S2-6] POST /api/intervention/log failed: {resp.status_code}")
                return None

        except requests.Timeout:
            logger.error("[S2-6] Timeout ao registrar intervencao (retry na proxima)")
            return None
        except Exception as e:
            logger.error(f"[S2-6] Erro ao log_intervention: {e}")
            return None

    def update_result(self, intervention_id: int, result: str, p_and_l: float) -> bool:
        """
        Atualiza resultado da intervenção (WIN/LOSS/PARTIAL).

        Args:
            intervention_id: ID da intervencao registrada
            result: WIN, LOSS, PARTIAL
            p_and_l: P&L final da operacao

        Returns:
            True se sucesso, False se erro
        """
        if not self.enabled:
            logger.warning("[S2-6] Analytics desabilitado, skip update_result")
            return False

        if not intervention_id:
            logger.warning("[S2-6] intervention_id vazio, skip update_result")
            return False

        try:
            payload = {
                "result": result,
                "p_and_l": p_and_l,
            }

            resp = self.session.post(
                f"{self.api_url}/api/intervention/{intervention_id}/result",
                json=payload,
                timeout=self.timeout
            )

            if resp.status_code in [200, 201]:
                logger.info(f"[S2-6] Resultado registrado: id={intervention_id}, result={result}, p_and_l={p_and_l}")
                return True
            else:
                logger.error(f"[S2-6] POST /api/intervention/{{id}}/result failed: {resp.status_code}")
                return False

        except requests.Timeout:
            logger.warning("[S2-6] Timeout ao atualizar resultado (retry na proxima)")
            return False
        except Exception as e:
            logger.error(f"[S2-6] Erro ao update_result: {e}")
            return False

    def get_stats(self, symbol: Optional[str] = None) -> Optional[Dict]:
        """
        Obtém estatísticas de intervencoes.

        Args:
            symbol: Opcional, filtro por simbolo

        Returns:
            Dict com stats ou None se erro
        """
        if not self.enabled:
            return None

        try:
            params = {}
            if symbol:
                params["symbol"] = symbol

            resp = self.session.get(
                f"{self.api_url}/api/analytics/stats",
                params=params,
                timeout=self.timeout
            )

            if resp.status_code == 200:
                return resp.json()
            else:
                logger.warning(f"[S2-6] GET /api/analytics/stats failed: {resp.status_code}")
                return None

        except Exception as e:
            logger.debug(f"[S2-6] Erro ao get_stats: {e}")
            return None

    def get_dashboard(self) -> Optional[Dict]:
        """
        Obtém dashboard de intervencoes (breakdown por ação).

        Returns:
            Dict com dashboard ou None se erro
        """
        if not self.enabled:
            return None

        try:
            resp = self.session.get(
                f"{self.api_url}/api/analytics/dashboard",
                timeout=self.timeout
            )

            if resp.status_code == 200:
                return resp.json()
            else:
                logger.warning(f"[S2-6] GET /api/analytics/dashboard failed: {resp.status_code}")
                return None

        except Exception as e:
            logger.debug(f"[S2-6] Erro ao get_dashboard: {e}")
            return None


# Singleton global
_analytics: Optional[AnalyticsAdapter] = None


def get_analytics_adapter(api_url: str = "http://localhost:8000") -> AnalyticsAdapter:
    """
    Obtém ou cria instância global do adapter.

    Args:
        api_url: URL base da API S2-6

    Returns:
        AnalyticsAdapter pronto para usar
    """
    global _analytics
    if _analytics is None:
        _analytics = AnalyticsAdapter(api_url)
    return _analytics


def reset_analytics_adapter():
    """Reset do adapter (para testes)"""
    global _analytics
    _analytics = None
