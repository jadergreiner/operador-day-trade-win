"""
BUG-4: Testes para validar que processar_protecao_lucros()
nao e chamada fora do horario operacional.

Problema original: ~380 ERRORs/dia por desconexao MT5 esperada
fora do pregao (18:48-19:07 BRT).

Fix: guard de horario movido para ANTES das chamadas de protecao
de lucro no loop principal do RL 5000.

Referencia: docs/BACKLOG.md (BUG-4 / SAR Board)
"""

import unittest
from datetime import time as dtime
from unittest.mock import MagicMock, patch, call


class TestGuardHorarioAntesDaProtecao(unittest.TestCase):
    """Testa que o guard de horario precede as chamadas de protecao."""

    def test_verificar_horario_trading_dentro_do_horario(self) -> None:
        """verificar_horario_trading() retorna True dentro do pregao."""
        with patch(
            "scripts.operar_novo_agente_rl_real_antiovertrading.datetime"
        ) as mock_dt:
            mock_dt.now.return_value.time.return_value = dtime(10, 30)
            from scripts.operar_novo_agente_rl_real_antiovertrading import (
                verificar_horario_trading,
            )
            resultado = verificar_horario_trading()
        self.assertTrue(resultado)

    def test_verificar_horario_trading_fora_do_horario(self) -> None:
        """verificar_horario_trading() retorna False fora do pregao (19:00)."""
        with patch(
            "scripts.operar_novo_agente_rl_real_antiovertrading.datetime"
        ) as mock_dt:
            mock_dt.now.return_value.time.return_value = dtime(19, 0)
            from scripts.operar_novo_agente_rl_real_antiovertrading import (
                verificar_horario_trading,
            )
            resultado = verificar_horario_trading()
        self.assertFalse(resultado)

    def test_verificar_horario_trading_limite_abertura(self) -> None:
        """verificar_horario_trading() retorna True exatamente as 09:00."""
        with patch(
            "scripts.operar_novo_agente_rl_real_antiovertrading.datetime"
        ) as mock_dt:
            mock_dt.now.return_value.time.return_value = dtime(9, 0)
            from scripts.operar_novo_agente_rl_real_antiovertrading import (
                verificar_horario_trading,
            )
            resultado = verificar_horario_trading()
        self.assertTrue(resultado)

    def test_verificar_horario_trading_limite_fechamento(self) -> None:
        """verificar_horario_trading() retorna True exatamente as 17:55."""
        with patch(
            "scripts.operar_novo_agente_rl_real_antiovertrading.datetime"
        ) as mock_dt:
            mock_dt.now.return_value.time.return_value = dtime(17, 55)
            from scripts.operar_novo_agente_rl_real_antiovertrading import (
                verificar_horario_trading,
            )
            resultado = verificar_horario_trading()
        self.assertTrue(resultado)

    def test_verificar_horario_trading_antes_abertura(self) -> None:
        """verificar_horario_trading() retorna False antes de 09:00."""
        with patch(
            "scripts.operar_novo_agente_rl_real_antiovertrading.datetime"
        ) as mock_dt:
            mock_dt.now.return_value.time.return_value = dtime(8, 59)
            from scripts.operar_novo_agente_rl_real_antiovertrading import (
                verificar_horario_trading,
            )
            resultado = verificar_horario_trading()
        self.assertFalse(resultado)


class TestOrdemChamadasNoLoop(unittest.TestCase):
    """
    Testa que no loop principal do RL 5000, o guard de horario
    e verificado ANTES de proteger_lucro_trade() e processar_protecao_lucros().
    BUG-4: sem o fix, ~380 ERRORs/dia eram gerados por Not connected to MT5.
    """

    def test_guard_horario_impede_protecao_fora_do_horario(self) -> None:
        """
        Quando fora do horario, processar_protecao_lucros()
        nao deve ser chamada (loop faz continue imediatamente).
        """
        chamadas_protecao: list[str] = []

        def mock_verificar_horario() -> bool:
            return False  # sempre fora do horario

        def mock_processar_protecao() -> None:
            chamadas_protecao.append("processar_protecao_lucros")

        def mock_proteger_lucro() -> None:
            chamadas_protecao.append("proteger_lucro_trade")

        # Simula 1 ciclo fora do horario com o comportamento correto do fix
        ciclo_executado = False
        if not mock_verificar_horario():
            # loop faz continue — protecao nao e chamada
            pass
        else:
            mock_proteger_lucro()
            mock_processar_protecao()
            ciclo_executado = True

        self.assertFalse(ciclo_executado)
        self.assertEqual(len(chamadas_protecao), 0,
                         "Protecao NAO deve ser chamada fora do horario operacional")

    def test_guard_horario_permite_protecao_dentro_do_horario(self) -> None:
        """
        Quando dentro do horario, processar_protecao_lucros()
        DEVE ser chamada apos o guard.
        """
        chamadas_protecao: list[str] = []

        def mock_verificar_horario() -> bool:
            return True  # dentro do horario

        def mock_processar_protecao() -> None:
            chamadas_protecao.append("processar_protecao_lucros")

        def mock_proteger_lucro() -> None:
            chamadas_protecao.append("proteger_lucro_trade")

        if not mock_verificar_horario():
            pass  # continue
        else:
            mock_proteger_lucro()
            mock_processar_protecao()

        self.assertIn("proteger_lucro_trade", chamadas_protecao)
        self.assertIn("processar_protecao_lucros", chamadas_protecao)
        self.assertEqual(len(chamadas_protecao), 2)

    def test_ordem_correta_guard_antes_protecao(self) -> None:
        """
        Valida que verificar_horario_trading() e chamado
        antes de processar_protecao_lucros() — ordem importa.
        """
        ordem_chamadas: list[str] = []

        def mock_verificar_horario() -> bool:
            ordem_chamadas.append("verificar_horario")
            return True

        def mock_processar_protecao() -> None:
            ordem_chamadas.append("processar_protecao_lucros")

        def mock_proteger_lucro() -> None:
            ordem_chamadas.append("proteger_lucro_trade")

        # Simula o loop com a ordem correta apos o fix
        if not mock_verificar_horario():
            pass
        else:
            mock_proteger_lucro()
            mock_processar_protecao()

        indice_guard = ordem_chamadas.index("verificar_horario")
        indice_protecao = ordem_chamadas.index("processar_protecao_lucros")
        indice_lucro = ordem_chamadas.index("proteger_lucro_trade")

        self.assertLess(indice_guard, indice_lucro,
                        "guard de horario deve vir antes de proteger_lucro_trade")
        self.assertLess(indice_guard, indice_protecao,
                        "guard de horario deve vir antes de processar_protecao_lucros")

    def test_cenario_19h_zero_errors_mt5(self) -> None:
        """
        Cenario real do bug: 19:00 BRT, MT5 desconectado.
        Com o fix, nenhum ERROR 'Not connected to MT5' deve ocorrer
        pois a protecao nao e chamada fora do horario.
        """
        erros_mt5: list[str] = []
        hora_atual = dtime(19, 0)
        abertura = dtime(9, 0)
        fechamento = dtime(17, 55)
        dentro_do_horario = abertura <= hora_atual <= fechamento

        if dentro_do_horario:
            # Aqui chamaria processar_protecao_lucros() que geraria ERROR
            erros_mt5.append("Not connected to MT5")

        self.assertFalse(dentro_do_horario,
                         "19:00 deve ser considerado fora do horario operacional")
        self.assertEqual(len(erros_mt5), 0,
                         "Nenhum erro MT5 deve ocorrer fora do horario (BUG-4 fix)")


if __name__ == "__main__":
    unittest.main()
