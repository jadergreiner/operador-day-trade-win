#!/usr/bin/env python3
"""
Launcher para o servidor WebSocket de Alertas Automaticos.

Configura o PYTHONPATH corretamente e inicia o uvicorn na porta
definida pela variavel de ambiente PORT (padrao: 8767).

Uso:
    python scripts/start_websocket_server.py
    PORT=8767 python scripts/start_websocket_server.py
"""

import os
import sys
from pathlib import Path

# Garantir que o root do projeto esteja no sys.path
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import uvicorn  # noqa: E402

from src.interfaces.websocket_server import app  # noqa: E402

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 8767))
    uvicorn.run(app, host="0.0.0.0", port=porta, log_level="info")
