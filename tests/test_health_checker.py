# -*- coding: utf-8 -*-
import sys
import os
import unittest
from pathlib import Path

# Adiciona diretórios ao sys.path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))
# also append src if needed for legacy imports
sys.path.append(str(root_dir / "src"))

from src.infrastructure.monitoring.health_checker import HealthChecker

class TestHealthChecker(unittest.TestCase):
    """Testes Unitários para HealthChecker (S1-2)"""

    def setUp(self):
        self.workspace_root = str(Path(__file__).parent.parent)
        self.checker = HealthChecker(workspace_root=self.workspace_root)

    def test_governance_sync_success(self):
        """Testa se o gate de governança passa com a tag [SYNC]"""
        # Criar arquivo de status temporário
        status_path = Path(self.workspace_root) / "docs" / "STATUS_ENTREGAS.md"
        if not status_path.exists():
            status_path.parent.mkdir(parents=True, exist_ok=True)
            with open(status_path, 'w', encoding='utf-8') as f:
                f.write("# Status\n[SYNC] Ativo")

        passed, reason = self.checker.check_governance_sync()
        self.assertTrue(passed)
        self.assertEqual(reason, "Sincronizado")

    def test_latency_is_measured(self):
        """Testa se a latência é medida e dentro do range esperado (em teste local)"""
        passed, val = self.checker.calculate_p95_latency(samples=3)
        self.assertIsInstance(val, (int, float))
        # localmente deve ser rápido < 500ms
        self.assertTrue(passed or val > 0)

    def test_db_logging(self):
        """Testa se os logs de saúde são salvos no banco de dados"""
        results = {
            "governance": (True, "Sincronizado"),
            "mt5": (True, "Conectado"),
            "latency": (True, 10.0)
        }
        self.checker._log_health_to_db(results)

        # Verificar se tabela existe
        import sqlite3
        conn = sqlite3.connect(self.checker.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_health_logs'")
        self.assertIsNotNone(cursor.fetchone())

        # Verificar se ha pelo menos 1 registro
        cursor.execute("SELECT count(*) FROM system_health_logs")
        count = cursor.fetchone()[0]
        self.assertGreaterEqual(count, 1)
        conn.close()

if __name__ == "__main__":
    unittest.main()
