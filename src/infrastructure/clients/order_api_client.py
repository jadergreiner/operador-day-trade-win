#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLIENT REST PARA P0-1 API (Orders REST Gateway)

Abstrai a comunicação HTTP com a API REST P0-1, permitindo que
agentes usem ordenação via fila/auditoria sem chamar MT5 direto.

Funciona como proxy entre agente e API.
"""

import logging
import requests
from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class APIOrderResponse:
    """Resposta estruturada da API REST."""
    order_id: str
    symbol: str
    order_type: str
    volume: float
    status: str
    created_at: str
    audit_trail: list = None
    success: bool = True
    error: Optional[str] = None


class OrderAPIClient:
    """
    Cliente HTTP para P0-1 REST API.

    Responsabilidades:
    - Converter ExecutionOrder em CreateOrderRequest
    - Chamar POST /api/v1/orders
    - Interpretar resposta JSON
    - Implementar retry logic (3x com exponential backoff)
    - Logar todas as chamadas para auditoria

    Uso:
    ```python
    client = OrderAPIClient(api_url="http://localhost:8888")
    response = client.create_order(
        symbol="WIN",
        order_type="BUY",
        volume=1.0,
        entry_price=98500.0,
        stop_loss=98400.0,
        take_profit=98600.0,
        ml_score=0.78
    )
    if response.success:
        print(f"Ordem criada: {response.order_id}")
    ```
    """

    def __init__(
        self,
        api_url: str = "http://localhost:8888",
        timeout: int = 5,
        max_retries: int = 3
    ):
        """
        Inicializa cliente REST.

        Args:
            api_url: Base URL da API (ex: http://localhost:8888)
            timeout: Timeout de conexão em segundos
            max_retries: Número máximo de tentativas
        """
        self.api_url = api_url
        self.base_path = "/api/v1"
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update(
            {"Content-Type": "application/json", "User-Agent": "OrderAPIClient/1.0"}
        )

    def health_check(self) -> bool:
        """
        Verifica se API está OK.

        Returns:
            True se API respondeu com 200 OK
        """
        try:
            url = f"{self.api_url}/health"
            response = self.session.get(url, timeout=2)
            is_healthy = response.status_code == 200
            if is_healthy:
                logger.debug(f"✅ API Health: OK ({self.api_url}/health)")
            else:
                logger.warning(f"⚠️  API Health: Status {response.status_code}")
            return is_healthy
        except requests.RequestException as e:
            logger.error(f"❌ API Health check falhou: {str(e)[:60]}")
            return False

    def create_order(
        self,
        symbol: str,
        order_type: str,
        volume: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        ml_score: float,
        detector_spike: float = 0.0,
    ) -> APIOrderResponse:
        """
        Cria ordem via API REST P0-1.

        Fluxo:
        1. Valida parâmetros
        2. Monta payload JSON
        3. POST /api/v1/orders com retry logic
        4. Interpreta resposta
        5. Loga auditoria

        Args:
            symbol: Símbolo (ex: "WIN", "WINFUT")
            order_type: "BUY" ou "SELL"
            volume: Quantidade de contratos
            entry_price: Preço de entrada
            stop_loss: Stop loss
            take_profit: Take profit
            ml_score: Score ML 0.0-1.0
            detector_spike: Score spike 0.0-1.0

        Returns:
            APIOrderResponse com status sucesso/erro
        """
        # Validação
        if order_type not in ["BUY", "SELL"]:
            logger.error(f"❌ order_type inválido: {order_type}")
            return APIOrderResponse(
                order_id="ERROR",
                symbol=symbol,
                order_type=order_type,
                volume=volume,
                status="REJECTED",
                created_at=datetime.now().isoformat(),
                success=False,
                error=f"order_type deve ser BUY ou SELL, recebido: {order_type}"
            )

        if volume <= 0:
            return APIOrderResponse(
                order_id="ERROR",
                symbol=symbol,
                order_type=order_type,
                volume=volume,
                status="REJECTED",
                created_at=datetime.now().isoformat(),
                success=False,
                error=f"volume deve ser > 0, recebido: {volume}"
            )

        # Monta payload
        payload = {
            "symbol": symbol,
            "order_type": order_type,
            "volume": volume,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "ml_score": ml_score,
            "detector_spike": detector_spike,
        }

        # Retry logic (3x com backoff exponencial)
        url = f"{self.api_url}{self.base_path}/orders"
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(
                    f"[{symbol}] POST /api/v1/orders "
                    f"(tentativa {attempt}/{self.max_retries})"
                )

                response = self.session.post(
                    url,
                    json=payload,
                    timeout=self.timeout
                )

                # ✅ Sucesso (200 OK)
                if response.status_code == 200:
                    data = response.json()
                    result = APIOrderResponse(
                        order_id=data.get("order_id", "UNKNOWN"),
                        symbol=data.get("symbol", symbol),
                        order_type=data.get("order_type", order_type),
                        volume=data.get("volume", volume),
                        status=data.get("status", "ENQUEUED"),
                        created_at=data.get("created_at", datetime.now().isoformat()),
                        audit_trail=data.get("audit_trail", []),
                        success=True,
                        error=None
                    )
                    logger.info(
                        f"✅ Ordem criada via API: {result.order_id} "
                        f"({symbol} {order_type} {volume})"
                    )
                    return result

                # ❌ Erro 4xx/5xx
                else:
                    error_msg = response.text[:100]
                    logger.warning(
                        f"⚠️  Resposta API status {response.status_code}: "
                        f"{error_msg}"
                    )
                    last_error = f"HTTP {response.status_code}: {error_msg}"

                    # Não faz retry em 400 (erro de validação)
                    if response.status_code == 400:
                        break

            except requests.Timeout:
                last_error = f"Timeout (tentativa {attempt}/{self.max_retries})"
                logger.warning(f"⚠️  {last_error}")

            except requests.RequestException as e:
                last_error = str(e)[:100]
                logger.warning(
                    f"⚠️  Erro conexão (tentativa {attempt}/{self.max_retries}): "
                    f"{last_error}"
                )

            # Wait antes de retry (1s, 2s, 4s)
            if attempt < self.max_retries:
                wait_time = 2 ** (attempt - 1)
                logger.debug(f"  ⏳ Aguardando {wait_time}s antes de retry...")
                import time
                time.sleep(wait_time)

        # ❌ Falha após todos os retries
        logger.error(
            f"❌ Ordem rejeitada após {self.max_retries} tentativas. "
            f"Erro: {last_error}"
        )
        return APIOrderResponse(
            order_id="ERROR",
            symbol=symbol,
            order_type=order_type,
            volume=volume,
            status="REJECTED",
            created_at=datetime.now().isoformat(),
            success=False,
            error=f"Falha após {self.max_retries} tentativas: {last_error}"
        )

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém status de uma ordem.

        Args:
            order_id: ID da ordem

        Returns:
            Dict com dados da ordem ou None se erro
        """
        try:
            url = f"{self.api_url}{self.base_path}/orders/{order_id}"
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"⚠️  GET /orders/{order_id} retornou {response.status_code}")
                return None
        except requests.RequestException as e:
            logger.error(f"❌ Erro ao obter ordem {order_id}: {str(e)[:60]}")
            return None

    def list_orders(self, limit: int = 100) -> Optional[Dict[str, Any]]:
        """
        Lista todas as ordens.

        Args:
            limit: Número máximo de ordens a retornar

        Returns:
            Dict com lista de ordens ou None se erro
        """
        try:
            url = f"{self.api_url}{self.base_path}/orders?limit={limit}"
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"⚠️  GET /orders retornou {response.status_code}")
                return None
        except requests.RequestException as e:
            logger.error(f"❌ Erro ao listar ordens: {str(e)[:60]}")
            return None

    def close(self):
        """Fecha session HTTP."""
        self.session.close()
