#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MT5ADAPTER PROXY - Encaminha chamadas à API REST P0-1

Wrapper que substitui MT5Adapter.send_order() para usar a API REST
P0-1 ao invés de chamar MT5 direto, mantendo a mesma interface.

Funciona como middleware transparente entre agente e MT5 real.

Uso:
    adapter = MT5AdapterProxy(mt5_adapter_original, api_client)
    ticket = adapter.send_order(order)  # Usa API REST internamente!
"""

import logging
from typing import Optional, Tuple
from decimal import Decimal
from src.infrastructure.clients.order_api_client import OrderAPIClient

logger = logging.getLogger(__name__)


class MT5AdapterProxy:
    """
    Proxy que redirecionam chamadas send_order() para API REST P0-1.

    Mantém compatibilidade total com MT5Adapter original:
    - Mesma interface pública
    - Converte ExecutionOrder para CreateOrderRequest
    - Retorna ticket string (mesmo que API)
    - Falhas degradam graciosamente

    Arquitetura:
    agente.send_order(order)
         ↓
    MT5AdapterProxy.send_order(order)
         ↓
    OrderAPIClient.create_order(...)
         ↓
    POST /api/v1/orders
         ↓
    FastAPI → ExecutionOrder.enqueue_order()
         ↓
    SQLite api_orders + api_audit_log
    """

    def __init__(
        self,
        original_adapter,
        api_client: OrderAPIClient = None,
        use_api_rest: bool = True,
        fallback_to_mt5: bool = True
    ):
        """
        Inicializa proxy.

        Args:
            original_adapter: MT5Adapter original para fallback
            api_client: OrderAPIClient (cria novo se None)
            use_api_rest: Se False, usa MT5 direto (bypass proxy)
            fallback_to_mt5: Se True e API falha, usa MT5 como fallback
        """
        self.original_adapter = original_adapter
        self.api_client = api_client or OrderAPIClient()
        self.use_api_rest = use_api_rest
        self.fallback_to_mt5 = fallback_to_mt5
        self.call_count = 0
        self.api_success_count = 0
        self.fallback_count = 0

    def send_order(self, order) -> Optional[str]:
        """
        Envia ordem usando API REST P0-1 (com fallback optional para MT5).

        Fluxo:
        1. Se use_api_rest=False → usa MT5 direto (bypass proxy)
        2. Se use_api_rest=True:
           a. verifica health API
           b. POST /api/v1/orders com retry logic
           c. Se sucesso → retorna order_id
           d. Se falha e fallback_to_mt5=True → usa MT5 como fallback
           e. Se falha e fallback_to_mt5=False → retorna None

        Args:
            order: Order/ExecutionOrder object com atributos:
                - symbol: str
                - side: OrderSide enum (BUY/SELL)
                - quantity: Quantity object
                - price: Price object (entry)
                - stop_loss: Price object
                - take_profit: Price object
                - order_type: OrderType enum

        Returns:
            ticket: str (order_id) ou None se falha
        """
        self.call_count += 1

        # ─────────────────────────────────────────────────────────────
        # CASO 1: Bypass proxy (usa MT5 direto)
        # ─────────────────────────────────────────────────────────────
        if not self.use_api_rest:
            logger.info(
                f"[{order.symbol}] Usando MT5 direto "
                f"(use_api_rest=False, bypass proxy)"
            )
            return self.original_adapter.send_order(order)

        # ─────────────────────────────────────────────────────────────
        # CASO 2: Usar API REST P0-1
        # ─────────────────────────────────────────────────────────────
        logger.info(
            f"[{order.symbol}] Enviando via API REST P0-1... "
            f"(chamada #{self.call_count})"
        )

        try:
            # Converte Order domain para parâmetros API
            symbol = str(order.symbol)
            order_type = "BUY" if str(order.side).upper() == "BUY" else "SELL"
            volume = float(order.quantity)
            entry_price = float(order.price)
            stop_loss = float(order.stop_loss)
            take_profit = float(order.take_profit)

            # ML score e detector (values padrão se não disponível)
            ml_score = getattr(order, 'ml_score', 0.5)
            detector_spike = getattr(order, 'detector_spike', 0.0)

            # Chama API REST com retry automático
            api_response = self.api_client.create_order(
                symbol=symbol,
                order_type=order_type,
                volume=volume,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                ml_score=ml_score,
                detector_spike=detector_spike
            )

            # ✅ Sucesso na API
            if api_response.success:
                self.api_success_count += 1
                logger.info(
                    f"✅ Ordem enviada via API: {api_response.order_id} "
                    f"(status: {api_response.status})"
                )
                return api_response.order_id  # Retorna order_id como ticket

            # ❌ Falha na API
            else:
                logger.warning(
                    f"⚠️  API retornou erro: {api_response.error}"
                )

                # Fallback para MT5 se configurado
                if self.fallback_to_mt5:
                    logger.info(
                        f"🔄 Fallback para MT5 (fallback_to_mt5=True)..."
                    )
                    self.fallback_count += 1
                    return self.original_adapter.send_order(order)
                else:
                    logger.error(
                        f"❌ Falha em API e fallback desabilitado. "
                        f"Ordem rejeitada."
                    )
                    return None

        except Exception as e:
            logger.error(
                f"❌ Erro ao enviar via API: {str(e)[:80]}. "
                f"Fallback: {self.fallback_to_mt5}"
            )

            if self.fallback_to_mt5:
                logger.info("🔄 Usando MT5 como fallback após erro...")
                self.fallback_count += 1
                return self.original_adapter.send_order(order)
            else:
                return None

    def resolve_open_position_ticket(self, symbol: str, side) -> Optional[str]:
        """
        Delega ao adapter original.
        Não há equivalente em API REST, então usa MT5.
        """
        return self.original_adapter.resolve_open_position_ticket(symbol, side)

    def get_position_details(self, symbol: str, side) -> Optional[dict]:
        """Delega ao adapter original."""
        return self.original_adapter.get_position_details(symbol, side)

    def close_position(self, symbol: str, ticket: str, volume: float) -> bool:
        """Delega ao adapter original."""
        return self.original_adapter.close_position(symbol, ticket, volume)

    def get_stats(self) -> dict:
        """Retorna estatísticas do proxy."""
        return {
            "total_calls": self.call_count,
            "api_success": self.api_success_count,
            "fallback_mt5": self.fallback_count,
            "api_success_rate": (
                self.api_success_count / self.call_count * 100
                if self.call_count > 0 else 0
            )
        }

    # Delega outros métodos ao adapter original
    def __getattr__(self, name):
        """Delega atributos ao adapter original para compatibilidade."""
        return getattr(self.original_adapter, name)
