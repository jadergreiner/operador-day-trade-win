#!/usr/bin/env python3
"""
Test Runner para WebSocket Server - INTEGRATION-ENG-002

Executa testes com PYTHONPATH correto.
"""

import sys
import os
from pathlib import Path

# Setup path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))
os.environ["PYTHONPATH"] = str(repo_root)

# Agora importar pytest
import pytest

if __name__ == "__main__":
    print("=" * 80)
    print("🧪 TESTE: WebSocket Server Integration (INTEGRATION-ENG-002)")
    print("=" * 80)

    # Executar testes
    exit_code = pytest.main([
        "tests/test_websocket_server_integration.py",
        "-v",
        "--tb=short",
        "-x",  # Parar no primeiro erro
    ])

    sys.exit(exit_code)
