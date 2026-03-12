"""
ATI-1 Broadcast Client
Envia mensagens internas para o WebSocket ATI-1 via endpoint HTTP.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class Ati1BroadcastClient:
    """Cliente HTTP para broadcast no ATI-1 WebSocket Server."""

    def __init__(
        self,
        base_url: str,
        token: Optional[str] = None,
        timeout: float = 2.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def broadcast(self, message: Dict[str, Any], trader_id: Optional[str] = None) -> bool:
        """Envia broadcast para ATI-1 server."""
        url = f"{self.base_url}/api/v1/broadcast"
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["X-Internal-Token"] = self.token

        payload = {"message": message, "trader_id": trader_id}

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            if resp.status_code != 200:
                logger.warning(f"ATI-1 broadcast failed: {resp.status_code} {resp.text[:120]}")
                return False
            return True
        except Exception as e:
            logger.error(f"ATI-1 broadcast error: {e}")
            return False
