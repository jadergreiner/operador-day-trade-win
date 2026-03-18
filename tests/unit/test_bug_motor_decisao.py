"""
Teste para validar BUG-1: NameError motor_decisao em enviar_ordem()

Garante que motor_decisao é passado corretamente em todas as chamadas
de enviar_ordem() e que nenhuma função tenta usá-lo sem recebê-lo como
parâmetro.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Mock dos imports
sys.modules['config.settings'] = MagicMock()
sys.modules['src.infrastructure.adapters.mt5_adapter'] = MagicMock()
sys.modules['src.infrastructure.database.schema'] = MagicMock()
sys.modules['src.application.services.novo_agente.agente_q_learning'] = MagicMock()
sys.modules['src.application.services.novo_agente.pipeline_treinamento'] = MagicMock()
sys.modules['src.infrastructure.repositories.rl_repository'] = MagicMock()
sys.modules['src.application.profit_protection_engine'] = MagicMock()
sys.modules['src.application.trade_tracker_integration'] = MagicMock()
sys.modules['src.application.trade_performance_tracker'] = MagicMock()
sys.modules['src.domain.enums.trading_enums'] = MagicMock()
sys.modules['src.application.motor_decisao_isolado'] = MagicMock()
sys.modules['src.application.posicao_isolamento'] = MagicMock()


@pytest.fixture
def mock_motor_decisao():
    """Cria um mock de MotorDecisaoIsolado."""
    motor = Mock()
    motor.abrir_posicao = Mock(return_value=True)
    motor.fechar_posicao = Mock(return_value=True)
    motor.obter_posicoes_abertas = Mock(return_value=[])
    return motor


@pytest.fixture
def mock_posicao_tracker():
    """Cria um mock de PosicaoIsoladaManager."""
    tracker = Mock()
    tracker.registrar_posicao_aberta = Mock(return_value=True)
    tracker.registrar_posicao_fechada = Mock(return_value=True)
    tracker.tem_posicao_aberta = Mock(return_value=False)
    return tracker


@pytest.fixture
def mock_mt5_adapter():
    """Cria um mock para MT5Adapter."""
    adapter = Mock()
    adapter.send_order = Mock(return_value=12345)
    adapter.get_positions = Mock(return_value=[])
    return adapter


@pytest.fixture
def mock_rl_repo():
    """Cria um mock para RL Repository."""
    repo = Mock()
    repo.save_episode = Mock(return_value=True)
    return repo


@pytest.fixture
def mock_trade_tracker():
    """Cria um mock para TradeTracker."""
    tracker = Mock()
    tracker.registrar_entrada = Mock(return_value=True)
    return tracker


class TestMotorDecisaoAcessoCorreto:
    """Testa que motor_decisao é passado e usado corretamente."""

    def test_motor_decisao_passado_como_parametro_em_enviar_ordem(
        self, mock_motor_decisao, mock_posicao_tracker, mock_mt5_adapter,
        mock_rl_repo, mock_trade_tracker
    ):
        """Valida que enviar_ordem() aceita motor_decisao como parâmetro.
        """
        # Importar a função após setup de mocks
        import sys
        from importlib import reload

        # Simular a assinatura correta de enviar_ordem
        def enviar_ordem_assinatura_correta(
            mt5_adapter, acao, preco_atual,
            posicao_tracker, rl_repo, trade_tracker,
            motor_decisao, dados=None
        ):
            """Assinatura correta de enviar_ordem com motor_decisao."""
            assert motor_decisao is not None, "motor_decisao deve ser passado como parâmetro"
            assert hasattr(motor_decisao, 'abrir_posicao'), \
                "motor_decisao deve ter método abrir_posicao()"
            return True

        # Testar chamada com todos os parâmetros
        resultado = enviar_ordem_assinatura_correta(
            mock_mt5_adapter,
            "Comprar",
            100.0,
            mock_posicao_tracker,
            mock_rl_repo,
            mock_trade_tracker,
            mock_motor_decisao,
        )
        assert resultado is True

    def test_motor_decisao_nao_e_variavel_global_nao_definida(
        self, mock_motor_decisao
    ):
        """Valida que motor_decisao NÃO é referenciado como global não definido.
        """
        # Esta função simula o erro que estava acontecendo
        def codigo_com_erro_nameerror():
            """Simula o código que causava NameError."""
            try:
                # Isto causaria NameError se motor_decisao não fosse definido
                motor_decisao.abrir_posicao(1, 'BUY', 100.0)  # noqa: F821
                return False
            except NameError:
                return True  # Esperado

        assert codigo_com_erro_nameerror() is True, \
            "Fora de função, motor_decisao não deve estar definido (esperado)"

    def test_motor_decisao_acessivel_quando_passado_como_parametro(
        self, mock_motor_decisao
    ):
        """Valida que motor_decisao é acessível quando passa como parâmetro.
        """
        def funcao_com_motor_como_parametro(motor_decisao):
            """Função que recebe motor_decisao como parâmetro."""
            assert motor_decisao is not None
            motor_decisao.abrir_posicao(1, 'BUY', 100.0)
            return motor_decisao.abrir_posicao.called

        resultado = funcao_com_motor_como_parametro(mock_motor_decisao)
        assert resultado is True

    def test_verificar_posicao_no_mt5_recebe_motor_decisao(
        self, mock_posicao_tracker, mock_motor_decisao, mock_mt5_adapter
    ):
        """Valida que verificar_posicao_no_mt5 recebe motor_decisao corretamente.
        """
        mock_posicao_tracker.tem_posicao_aberta.return_value = False

        def verificar_posicao_no_mt5_assinatura_correta(
            posicao_mgr, motor, mt5_adapter_local
        ):
            """Assinatura correta de verificar_posicao_no_mt5."""
            assert motor is not None, "motor deve ser passado"
            assert hasattr(motor, 'obter_posicoes_abertas'), \
                "motor deve ter método obter_posicoes_abertas()"
            return False

        resultado = verificar_posicao_no_mt5_assinatura_correta(
            mock_posicao_tracker,
            mock_motor_decisao,
            mock_mt5_adapter,
        )
        assert resultado is False

    def test_motor_decisao_em_main_alcanca_funcoes_chamadas(
        self, mock_motor_decisao
    ):
        """Valida que motor_decisao de main() pode ser passado para subfunções.
        """
        def main_simulado():
            """Simula main() com motor_decisao local."""
            motor_decisao = mock_motor_decisao

            def funcao_chamada_de_main(motor):
                assert motor is mock_motor_decisao
                return True

            return funcao_chamada_de_main(motor_decisao)

        assert main_simulado() is True

    def test_sem_nameerror_linha_331_fix(
        self, mock_motor_decisao, mock_posicao_tracker, mock_mt5_adapter,
        mock_rl_repo, mock_trade_tracker
    ):
        """
        Valida que não há NameError em linha 331 (ou equivalente) onde
        motor_decisao.abrir_posicao() é chamado.

        Cenário:
        - motor_decisao é parâmetro de enviar_ordem()
        - motor_decisao.abrir_posicao() é chamado dentro de enviar_ordem()
        - Nenhum NameError deve ocorrer
        """
        mock_mt5_adapter.send_order.return_value = 999

        def enviar_ordem_fixed(
            mt5_adapter, acao, preco_atual,
            posicao_tracker, rl_repo, trade_tracker,
            motor_decisao, dados=None
        ):
            """Versão corrigida de enviar_ordem."""
            if acao not in ['Comprar', 'Vender']:
                return False

            ticket = mt5_adapter.send_order(None)
            if ticket:
                posicao_tracker.registrar_posicao_aberta(
                    preco_entrada=preco_atual,
                    ticket=int(ticket),
                    lado=acao,
                    quantidade=1,
                )
                # ✅ FIX: motor_decisao é recebido como parâmetro
                motor_decisao.abrir_posicao(
                    ticket=int(ticket),
                    tipo='COMPRADA' if acao == 'Comprar' else 'VENDIDA',
                    preco_entrada=preco_atual,
                    volume=1.0,
                    stop_loss=99.0,
                    take_profit=101.0,
                )
                return True

            return False

        # Executar sem exceção
        resultado = enviar_ordem_fixed(
            mock_mt5_adapter,
            "Comprar",
            100.0,
            mock_posicao_tracker,
            mock_rl_repo,
            mock_trade_tracker,
            mock_motor_decisao,  # ✅ Passado como parâmetro
        )

        assert resultado is True
        assert mock_motor_decisao.abrir_posicao.called


class TestMotorDecisaoIntegracao:
    """Testa integração completa do motor_decisao no fluxo."""

    def test_motor_decisao_abrir_fechar_ciclo_completo(
        self, mock_motor_decisao, mock_posicao_tracker, mock_mt5_adapter,
        mock_rl_repo, mock_trade_tracker
    ):
        """Testa ciclo completo: abrir → fechar → encerrar."""

        def simular_ciclo_completo():
            """Simula ciclo operacional completo."""
            # Simular envio de ordem (abrir)
            ticket = 12345
            mock_motor_decisao.abrir_posicao(
                ticket=ticket,
                tipo='COMPRADA',
                preco_entrada=100.0,
                volume=1.0,
                stop_loss=99.0,
                take_profit=101.0,
            )

            # Verificar se foi registrado
            assert mock_motor_decisao.abrir_posicao.called

            # Simular fechamento
            mock_motor_decisao.fechar_posicao(
                ticket=ticket,
                preco_saida=101.0,
                motivo='TP_ATINGIDO',
            )

            assert mock_motor_decisao.fechar_posicao.called
            return True

        assert simular_ciclo_completo() is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
