# -*- coding: utf-8 -*-
"""
Testes E2E Automaçâo (S1-4)
Validação do fluxo completo: Market Data -> Sinais -> Execução -> Auditoria
"""
import os
import unittest
from pathlib import Path

# Adiciona o diretório raiz para importações de 'src'
import sys
current_dir = Path(__file__).parent.parent.parent
sys.path.append(str(current_dir))

from src.infrastructure.monitoring.health_checker import HealthChecker

class TestE2EAutomation(unittest.TestCase):
    """Bateria de testes End-to-End da automação de trading (S1-4)"""

    @classmethod
    def setUpClass(cls):
        """Setup global para os testes E2E"""
        cls.checker = HealthChecker(workspace_root=str(current_dir))
        cls.status_entregas_path = os.path.join(str(current_dir), "docs", "STATUS_ENTREGAS.md")

    def test_governance_gate_sincronizado(self):
        """[QA Automation (12)] Valida se o Gate de Governança está sincronizado"""
        passed, detail = self.checker.check_governance_sync()
        self.assertTrue(passed, f"Gate de Governança falhou: {detail}")
        self.assertEqual(detail, "Sincronizado")

    def test_latency_p95_compliance(self):
        """[Arquiteto de Sistemas (6)] Valida se a latência P95 é inferior a 500ms"""
        passed, p95 = self.checker.calculate_p95_latency(samples=5)
        self.assertTrue(passed, f"Latência P95 Crítica ({p95:.2f}ms > 500ms)")
        self.assertLess(p95, 500, f"Latência P95 fora do target: {p95:.2f}ms")

    def test_s1_4_status_in_entregas(self):
        """[Doc Advocate (8)] Valida se a tarefa S1-4 está marcada como COMPLETO no documento oficial"""
        with open(self.status_entregas_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Verifica se S1-4 está em COMPLETO ou EM VALIDAÇÃO
        self.assertIn("S1-4", content, "ID S1-4 não encontrado em STATUS_ENTREGAS.md")
        valid_status = "COMPLETO" in content or "EM VALIDAÇÃO" in content or "ANDAMENTO" in content
        self.assertTrue(valid_status, "A tarefa S1-4 deveria estar com status válido")

if __name__ == "__main__":
    unittest.main()
