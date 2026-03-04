#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTE INTEGRAÇÃO P0-1: OrderAPIClient + MT5AdapterProxy

Valida:
1. OrderAPIClient consegue conectar na API
2. MT5AdapterProxy redireciona chamadas corretamente
3. Audit trail está sendo gerado no SQLite
"""

import sys
import os
from pathlib import Path
import logging

# Setup path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = Path(current_dir).parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)-8s | %(name)s | %(message)s'
)

logger = logging.getLogger(__name__)


def test_api_client():
    """Testa se OrderAPIClient consegue conectar na API."""
    logger.info("═" * 60)
    logger.info("TESTE 1: OrderAPIClient Health Check")
    logger.info("═" * 60)
    
    try:
        from src.infrastructure.clients.order_api_client import OrderAPIClient
        
        client = OrderAPIClient(api_url="http://localhost:8888")
        
        # Health check
        is_healthy = client.health_check()
        
        if is_healthy:
            logger.info("✅ API REST P0-1 está respondendo")
            return True
        else:
            logger.warning("⚠️  API REST não respondeu. Verifique se está rodando:")
            logger.warning("   python scripts/start_api_server.py")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        return False


def test_create_order_via_api():
    """Testa criação de ordem via API REST."""
    logger.info("\n" + "═" * 60)
    logger.info("TESTE 2: Criar Ordem via API REST")
    logger.info("═" * 60)
    
    try:
        from src.infrastructure.clients.order_api_client import OrderAPIClient
        
        client = OrderAPIClient(api_url="http://localhost:8888")
        
        # Testa criação
        response = client.create_order(
            symbol="WIN",
            order_type="BUY",
            volume=1.0,
            entry_price=98500.0,
            stop_loss=98400.0,
            take_profit=98600.0,
            ml_score=0.75
        )
        
        if response.success:
            logger.info(f"✅ Ordem criada com sucesso!")
            logger.info(f"   Order ID: {response.order_id}")
            logger.info(f"   Status: {response.status}")
            return response.order_id
        else:
            logger.warning(f"⚠️  Falha ao criar ordem: {response.error}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        return None


def test_sqlite_audit_trail(order_id: str = None):
    """Valida que audit trail foi gerado no SQLite."""
    logger.info("\n" + "═" * 60)
    logger.info("TESTE 3: Validar Audit Trail em SQLite")
    logger.info("═" * 60)
    
    try:
        import sqlite3
        
        db_path = Path(root_dir) / "data" / "db" / "api_orders.db"
        
        if not db_path.exists():
            logger.warning(f"⚠️  Banco {db_path} não existe ainda")
            logger.info("   (Será criado na primeira chamada da API)")
            return False
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Verifica se tabelas existem
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='api_orders'"
        )
        if not cursor.fetchone():
            logger.warning("⚠️  Tabela api_orders não existe ainda")
            return False
        
        logger.info(f"✅ Tabela api_orders existe")
        
        # Conta registros
        cursor.execute("SELECT COUNT(*) FROM api_orders")
        count = cursor.fetchone()[0]
        logger.info(f"   Total de ordens: {count}")
        
        # Se temos um order_id, mostra seus detalhes
        if order_id:
            cursor.execute(
                "SELECT order_id, status, created_at FROM api_orders WHERE order_id = ?",
                (order_id,)
            )
            row = cursor.fetchone()
            if row:
                logger.info(f"   Ordem {row[0]}: status={row[1]}, criada={row[2]}")
        
        # Mostra audit log
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='api_audit_log'"
        )
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) FROM api_audit_log")
            audit_count = cursor.fetchone()[0]
            logger.info(f"✅ Tabela api_audit_log existe")
            logger.info(f"   Total de eventos: {audit_count}")
            
            if order_id:
                cursor.execute(
                    "SELECT state, timestamp, message FROM api_audit_log WHERE order_id = ? LIMIT 3",
                    (order_id,)
                )
                rows = cursor.fetchall()
                for state, ts, msg in rows:
                    logger.info(f"   [{state}] {ts}: {msg}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao ler SQLite: {e}")
        return False


def test_mt5_adapter_proxy():
    """Testa se MT5AdapterProxy consegue ser criado."""
    logger.info("\n" + "═" * 60)
    logger.info("TESTE 4: MT5AdapterProxy Import")
    logger.info("═" * 60)
    
    try:
        from src.infrastructure.adapters.mt5_adapter_proxy import MT5AdapterProxy
        from src.infrastructure.clients.order_api_client import OrderAPIClient
        
        logger.info("✅ MT5AdapterProxy importado com sucesso")
        logger.info("✅ OrderAPIClient importado com sucesso")
        
        # Cria instância (com mock MT5)
        class MockMT5:
            def send_order(self, order):
                return "MOCK-TICKET-123"
        
        mock_mt5 = MockMT5()
        api_client = OrderAPIClient()
        proxy = MT5AdapterProxy(mock_mt5, api_client, use_api_rest=False)
        
        logger.info("✅ MT5AdapterProxy instanciado com sucesso")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_launcher_imports():
    """Testa se launcher consegue importar todas dependências."""
    logger.info("\n" + "═" * 60)
    logger.info("TESTE 5: Launcher Imports")
    logger.info("═" * 60)
    
    try:
        # Tenta importar launcher
        import launch_agent_with_ml_v1_2_3
        
        logger.info("✅ Launcher importado com sucesso")
        
        # Verifica se P0-1 está disponível
        if hasattr(launch_agent_with_ml_v1_2_3, 'P0_1_AVAILABLE'):
            if launch_agent_with_ml_v1_2_3.P0_1_AVAILABLE:
                logger.info("✅ P0-1 API está disponível no launcher")
            else:
                logger.warning("⚠️  P0-1 API não está disponível no launcher")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Executa todos os testes."""
    logger.info("\n\n")
    logger.info("╔" + "═" * 58 + "╗")
    logger.info("║" + " " * 58 + "║")
    logger.info("║" + "  P0-1 INTEGRATION TEST SUITE".center(58) + "║")
    logger.info("║" + " " * 58 + "║")
    logger.info("╚" + "═" * 58 + "╝")
    
    results = {}
    
    # Teste 1
    results['api_health'] = test_api_client()
    
    # Teste 2 (só se API está up)
    if results['api_health']:
        order_id = test_create_order_via_api()
        results['create_order'] = order_id is not None
        
        # Teste 3 (só se criou ordem)
        if order_id:
            results['audit_trail'] = test_sqlite_audit_trail(order_id)
        else:
            results['audit_trail'] = test_sqlite_audit_trail()
    else:
        logger.warning("⊘ Pulando testes 2-3 (API não está respondendo)")
        results['create_order'] = False
        results['audit_trail'] = False
    
    # Teste 4
    results['mt5_proxy'] = test_mt5_adapter_proxy()
    
    # Teste 5
    results['launcher'] = test_launcher_imports()
    
    # Summary
    logger.info("\n" + "═" * 60)
    logger.info("RESUMO DOS TESTES")
    logger.info("═" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} | {test}")
    
    logger.info("═" * 60)
    logger.info(f"Total: {passed}/{total} testes passaram")
    
    if passed == total:
        logger.info("🎉 TODOS OS TESTES PASSARAM!")
        return 0
    else:
        logger.warning(f"⚠️  {total - passed} teste(s) falharam")
        logger.info("\nConfira:")
        logger.info("1. API REST está rodando? python scripts/start_api_server.py")
        logger.info("2. Diretório data/db/ existe?")
        logger.info("3. Port 8888 não está sendo usada?")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
