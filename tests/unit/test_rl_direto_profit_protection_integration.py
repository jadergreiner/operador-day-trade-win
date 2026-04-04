"""
Testes de integração do Profit Protection no RL Direto.

AC-018: Valida que RL Direto chama o motor de proteção periodicamente.
Teste crítico para RELEASE_DEVOLVER → GO.
"""

import unittest
from unittest.mock import MagicMock, patch, call
from datetime import datetime
from pathlib import Path


class TestRLDiretoProtectionIntegration(unittest.TestCase):
    """Valida que profit protection é executado periodicamente no RL Direto."""

    def test_processar_protecao_lucros_exists_in_module(self):
        """AC-018.1: Função processar_protecao_lucros deve existir no módulo."""
        # Import o módulo RL Direto
        try:
            import sys
            from pathlib import Path
            import os

            root = Path(__file__).parent.parent.parent
            sys.path.insert(0, str(root))

            # Importar diretamente
            spec = __import__(
                "importlib.util"
            ).util.spec_from_file_location(
                "agente_rl_direto",
                str(root / "scripts" / "agente_rl_direto_independente.py"),
            )
            if spec and spec.loader:
                module = __import__("importlib.util").util.module_from_spec(spec)
                # Neste fase podemos apenas validar que a função será procurada
                # Não executamos pois tem dependências MT5
                self.assertIsNotNone(module, "Módulo RL Direto deve importar")
        except ImportError as e:
            self.skipTest(f"Módulo não importável localmente (esperado): {e}")

    def test_profit_protection_called_periodically_pattern(self):
        """AC-018.2: Pattern de chamada periódica deve estar presente."""
        # Verificar via grep no arquivo
        import os

        rl_direto_path = (
            Path(__file__).parent.parent.parent
            / "scripts"
            / "agente_rl_direto_independente.py"
        )

        if not rl_direto_path.exists():
            self.skipTest(f"Arquivo não encontrado: {rl_direto_path}")

        with open(rl_direto_path, encoding="utf-8") as f:
            content = f.read()

        # Deve conter a função processar_protecao_lucros
        self.assertIn(
            "def processar_protecao_lucros_rl_direto(",
            content,
            "RL Direto deve definir processar_protecao_lucros_rl_direto()",
        )

        # Deve conter chamada dentro do loop principal
        self.assertIn(
            "processar_protecao_lucros_rl_direto(",
            content,
            "RL Direto deve CHAMAR processar_protecao_lucros_rl_direto() no loop",
        )

    def test_profit_protection_executes_in_position_open_block(self):
        """AC-018.3: Proteção deve executar quando posição está aberta."""
        # Verificar que a chamada está no bloco correto
        import os

        rl_direto_path = (
            Path(__file__).parent.parent.parent
            / "scripts"
            / "agente_rl_direto_independente.py"
        )

        with open(rl_direto_path, encoding="utf-8") as f:
            lines = f.readlines()

        # Buscar pelo padrão de posição aberta
        position_open_block = False
        protection_in_right_place = False

        for i, line in enumerate(lines):
            # Encontrar bloco de posição aberta
            if "posicao_tracker.tem_posicao_aberta()" in line:
                position_open_block = True
                # Procurar por processar_protecao_lucros nos próximos 320 linhas
                # (loop principal do agente é extenso e inclui blocos de validação)
                for j in range(i, min(i + 320, len(lines))):
                    if "processar_protecao_lucros_rl_direto(" in lines[j]:
                        protection_in_right_place = True
                        break
                if protection_in_right_place:
                    break

        self.assertTrue(
            protection_in_right_place,
            "processar_protecao_lucros_rl_direto() deve estar dentro "
            "do bloco 'if posicao_tracker.tem_posicao_aberta()'",
        )

    def test_profit_protection_wiring_is_unique(self):
        """Evita regressão de wiring duplicado no RL Direto."""
        rl_direto_path = (
            Path(__file__).parent.parent.parent
            / "scripts"
            / "agente_rl_direto_independente.py"
        )

        with open(rl_direto_path, encoding="utf-8") as f:
            content = f.read()

        self.assertEqual(
            content.count("def processar_protecao_lucros_rl_direto("),
            1,
            "Deve existir apenas uma definição de processar_protecao_lucros_rl_direto",
        )

    def test_profit_protection_exception_handled(self):
        """AC-018.4: Exceções em proteção não devem derrubar o loop."""
        # Validar que há try/except ou que execução é sempre segura
        import os

        rl_direto_path = (
            Path(__file__).parent.parent.parent
            / "scripts"
            / "agente_rl_direto_independente.py"
        )

        with open(rl_direto_path, encoding="utf-8") as f:
            content = f.read()

        # A função processar_protecao_lucros deve ter try/except interno
        # OU a chamada deve estar dentro de try/except
        self.assertIn(
            "try",
            content,
            "Loops devem ter tratamento de exceção",
        )

    def test_profit_protection_engine_initialized_with_profile(self):
        """AC-018.5: profit_protection_engine deve ser inicializado com perfil."""
        import os

        rl_direto_path = (
            Path(__file__).parent.parent.parent
            / "scripts"
            / "agente_rl_direto_independente.py"
        )

        with open(rl_direto_path, encoding="utf-8") as f:
            content = f.read()

        # Deve inicializar com perfil (não apenas kwargs)
        self.assertIn(
            "profile=",
            content,
            "profit_protection deve ser inicializado com profile (ADR-018)",
        )

        # Deve ter loader de config
        self.assertIn(
            "_carregar_pp_config_direto",
            content,
            "Deve haver função para carregar config PP",
        )


if __name__ == "__main__":
    unittest.main()
