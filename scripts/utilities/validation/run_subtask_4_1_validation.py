"""
Operador Quantum - Subtask 4.1 Validation Script

Versão: 1.0.0
Data: 02 de Março de 2026
Propósito: Quick validation script para testar ConnectionManager (AC-1, AC-2)
e MessageHandler (AC-5) sem necessidade de pytest framework

Uso:
    python scripts/utilities/validation/run_subtask_4_1_validation.py

Exemplo:
    python scripts/utilities/validation/run_subtask_4_1_validation.py

Entrada:
    - Requer: src/application/websocket_server_ati1.py (ConnectionManager, MessageHandler)
    - Mock objects via unittest.mock

Saída:
    - STDOUT: Logs estruturados com status de cada teste
    - Exemplo: ✅ Test 1: CONNECT passed
    - Exit code: 0 (sucesso) ou 1 (falha)

Dependências (pip install):
    - loguru
    - asyncio (built-in)
    - unittest.mock (built-in)

Dependências (internas):
    - src/application/websocket_server_ati1.py

Configuração:
    - Nenhuma. Script auto-configurável com loguru

Saída esperada:
    ✅ Sucesso: 9 testes PASSED, SUBTASK 4.1 STATUS: COMPLETE
    ❌ Erro: 1+ testes FAILED, SUBTASK 4.1 STATUS: NEEDS FIXES

Troubleshooting:
    - Erro de import: Verificar se src/ tem websocket_server_ati1.py
    - Erro de async: Python 3.7+ requerido
    - Erro de loguru: pip install loguru

Versionamento:
    - v1.0.0 (02/03/2026): Versão inicial (movido de raiz)
    
Localização no repositório:
    - scripts/utilities/validation/run_subtask_4_1_validation.py
    
Referência em Backlog:
    - INTEGRATION-ENG-002: WebSocket Server (PRIORITY 4)
    - Subtask 4.1: Validação ConnectionManager
"""

import asyncio
import sys
from unittest.mock import AsyncMock
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stderr, format="<level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>")


async def test_connection_manager():
    """
    Test ConnectionManager class
    AC-1: Connection persistence
    AC-2: P95 latency tracking
    """

    # Import
    try:
        from src.application.websocket_server_ati1 import ConnectionManager
        logger.info("✅ Successfully imported ConnectionManager")
    except ImportError as e:
        logger.error(f"❌ Failed to import: {e}")
        return False

    # Initialize
    manager = ConnectionManager()
    logger.info("✅ ConnectionManager initialized")

    # Test 1: Connect
    try:
        ws1 = AsyncMock()
        await manager.connect(ws1, "TRADER_001")

        assert "TRADER_001" in manager.active_connections
        assert ws1 in manager.active_connections["TRADER_001"]
        logger.info("✅ Test 1: CONNECT passed")
    except Exception as e:
        logger.error(f"❌ Test 1 FAILED: {e}")
        return False

    # Test 2: Connection time (for AC-2 latency)
    try:
        import time
        current_time = time.time()

        assert ws1 in manager.connection_times
        connection_time = manager.connection_times[ws1]

        # Should be recent (within 1 second)
        assert abs(current_time - connection_time) < 1.0
        logger.info("✅ Test 2: CONNECTION TIME passed")
    except Exception as e:
        logger.error(f"❌ Test 2 FAILED: {e}")
        return False

    # Test 3: Multiple connections per trader
    try:
        ws2 = AsyncMock()
        ws3 = AsyncMock()

        await manager.connect(ws2, "TRADER_001")
        await manager.connect(ws3, "TRADER_001")

        assert len(manager.active_connections["TRADER_001"]) == 3
        logger.info("✅ Test 3: MULTIPLE CONNECTIONS passed")
    except Exception as e:
        logger.error(f"❌ Test 3 FAILED: {e}")
        return False

    # Test 4: Broadcast message
    try:
        message = {
            "type": "order",
            "trader_id": "TRADER_001",
            "data": "test_broadcast"
        }

        await manager.broadcast(message, trader_id="TRADER_001")

        # All 3 connections should receive
        assert ws1.send_json.call_count >= 1
        assert ws2.send_json.call_count >= 1
        assert ws3.send_json.call_count >= 1
        logger.info("✅ Test 4: BROADCAST passed")
    except Exception as e:
        logger.error(f"❌ Test 4 FAILED: {e}")
        return False

    # Test 5: Disconnect
    try:
        await manager.disconnect(ws1, "TRADER_001")

        assert ws1 not in manager.active_connections["TRADER_001"]
        assert len(manager.active_connections["TRADER_001"]) == 2
        logger.info("✅ Test 5: DISCONNECT passed")
    except Exception as e:
        logger.error(f"❌ Test 5 FAILED: {e}")
        return False

    # Test 6: Clean disconnect (remove trader when empty)
    try:
        await manager.disconnect(ws2, "TRADER_001")
        await manager.disconnect(ws3, "TRADER_001")

        assert "TRADER_001" not in manager.active_connections
        logger.info("✅ Test 6: TRAIL DISCONNECT passed")
    except Exception as e:
        logger.error(f"❌ Test 6 FAILED: {e}")
        return False

    # Test 7: Max connections per trader
    try:
        from src.application.websocket_server_ati1 import MAX_CONNECTIONS_PER_TRADER

        # Create max connections
        connections = []
        for i in range(MAX_CONNECTIONS_PER_TRADER):
            ws = AsyncMock()
            await manager.connect(ws, "TRADER_MAX")
            connections.append(ws)

        # Try one more - should fail
        ws_extra = AsyncMock()
        try:
            await manager.connect(ws_extra, "TRADER_MAX")
            logger.error("❌ Test 7: Should have rejected extra connection")
            return False
        except RuntimeError as e:
            assert "Max connections" in str(e)
            logger.info("✅ Test 7: MAX CONNECTIONS protection passed")
    except Exception as e:
        logger.error(f"❌ Test 7 FAILED: {e}")
        return False

    return True


async def test_message_handler():
    """
    Test MessageHandler class
    AC-5: Message validation
    """

    try:
        from src.application.websocket_server_ati1 import MessageHandler
        logger.info("✅ Successfully imported MessageHandler")
    except ImportError as e:
        logger.error(f"❌ Failed to import MessageHandler: {e}")
        return False

    # Test 1: Valid message
    try:
        valid_msg = {"type": "order", "trader_id": "TRADER_001"}
        assert MessageHandler.validate_message(valid_msg) is True
        logger.info("✅ Test 8: VALID MESSAGE passed")
    except Exception as e:
        logger.error(f"❌ Test 8 FAILED: {e}")
        return False

    # Test 2: Invalid message (missing type)
    try:
        invalid_msg = {"trader_id": "TRADER_001"}
        assert MessageHandler.validate_message(invalid_msg) is False
        logger.info("✅ Test 9: INVALID MESSAGE detection passed")
    except Exception as e:
        logger.error(f"❌ Test 9 FAILED: {e}")
        return False

    return True


async def main():
    """Run all validation tests"""

    logger.info("=" * 60)
    logger.info("PRIORITY 4: Subtask 4.1 - Validation Suite")
    logger.info("=" * 60)
    logger.info("")

    # ConnectionManager tests
    logger.info("🔧 Testing ConnectionManager...")
    result1 = await test_connection_manager()

    # MessageHandler tests
    logger.info("")
    logger.info("🔧 Testing MessageHandler...")
    result2 = await test_message_handler()

    # Summary
    logger.info("")
    logger.info("=" * 60)

    if result1 and result2:
        logger.info("✅✅✅ ALL TESTS PASSED!")
        logger.info("")
        logger.info("SUBTASK 4.1 STATUS: COMPLETE ✅")
        logger.info("Ready to proceed to Subtask 4.2")
        logger.info("=" * 60)
        return 0
    else:
        logger.error("❌ SOME TESTS FAILED")
        logger.error("")
        logger.error("SUBTASK 4.1 STATUS: NEEDS FIXES")
        logger.info("=" * 60)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
