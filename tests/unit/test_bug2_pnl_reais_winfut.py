"""
BUG-2: Correcao do calculo de pnl_reais para WINFUT.

Problema diagnosticado:
O campo pnl_reais no historico_fechamentos usava multiplicador incorreto
(100 pontos/contrato) em vez do valor real do mini-indice WINFUT
(R$0,20 por ponto). Resultado: valores 500x maiores que o real.

Exemplo real registrado: pnl_reais: -18.449.000 para trade ~R$-200.

Correcao: VALOR_PONTO_WINFUT = 0.20 (R$ por ponto de mini-indice).

Referencia: docs/BACKLOG.md (BUG-2 / INICIAR_AGENTE_RL_DIRETO.bat)
"""

import pytest
from src.application.motor_decisao_isolado import (
    MotorDecisaoIsolado,
    MotivoFechamento,
    TipoPosicao,
)


# Precos tipicos do WINFUT (mini-indice Ibovespa) em pontos
PRECO_ENTRADA_BUY = 130_000.0   # 130.000 pontos de entrada
PRECO_SAIDA_TP = 130_250.0      # +250 pontos (target)
PRECO_SAIDA_SL = 129_875.0      # -125 pontos (stop loss)
PRECO_ENTRADA_SELL = 130_000.0
PRECO_SAIDA_SELL_TP = 129_750.0  # -250 pontos (SELL ganha quando cai)
PRECO_SAIDA_SELL_SL = 130_125.0  # +125 pontos (SELL perde quando sobe)

# Valor do ponto WINFUT: R$ 0,20 por ponto por contrato
VALOR_PONTO_WINFUT = 0.20


@pytest.fixture
def motor(tmp_path):
    """Motor isolado em diretorio temporario."""
    return MotorDecisaoIsolado(agent_id="teste_bug2", data_dir=tmp_path)


class TestPnlReaisCalculo:
    """Testes unitarios de calculo de pnl_reais para WINFUT."""

    def test_pnl_buy_ganho_250_pontos_1_contrato(self, motor):
        """
        BUY: entrada 130.000, saida 130.250 (+250 pontos), 1 contrato.
        pnl_reais esperado = 250 * 1 * 0.20 = R$ 50,00.
        """
        motor.abrir_posicao(
            ticket=101,
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=PRECO_ENTRADA_BUY,
            volume=1.0,
            stop_loss=129_875.0,
            take_profit=PRECO_SAIDA_TP,
        )
        historico = motor.fechar_posicao(
            ticket=101,
            preco_saida=PRECO_SAIDA_TP,
            motivo=MotivoFechamento.TP_ATINGIDO,
        )
        assert historico is not None
        pnl_esperado = 250.0 * 1.0 * VALOR_PONTO_WINFUT  # R$ 50,00
        assert abs(historico.pnl_reais - pnl_esperado) < 0.01, (
            f"Esperado R${pnl_esperado:.2f}, obtido R${historico.pnl_reais:.2f}"
        )

    def test_pnl_buy_perda_125_pontos_1_contrato(self, motor):
        """
        BUY: entrada 130.000, saida 129.875 (-125 pontos), 1 contrato.
        pnl_reais esperado = -125 * 1 * 0.20 = R$ -25,00.
        """
        motor.abrir_posicao(
            ticket=102,
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=PRECO_ENTRADA_BUY,
            volume=1.0,
            stop_loss=PRECO_SAIDA_SL,
            take_profit=PRECO_SAIDA_TP,
        )
        historico = motor.fechar_posicao(
            ticket=102,
            preco_saida=PRECO_SAIDA_SL,
            motivo=MotivoFechamento.SL_ATINGIDO,
        )
        assert historico is not None
        pnl_esperado = -125.0 * 1.0 * VALOR_PONTO_WINFUT  # R$ -25,00
        assert abs(historico.pnl_reais - pnl_esperado) < 0.01, (
            f"Esperado R${pnl_esperado:.2f}, obtido R${historico.pnl_reais:.2f}"
        )

    def test_pnl_sell_ganho_250_pontos_1_contrato(self, motor):
        """
        SELL: entrada 130.000, saida 129.750 (-250 pontos), 1 contrato.
        pnl_reais esperado = 250 * 1 * 0.20 = R$ 50,00.
        """
        motor.abrir_posicao(
            ticket=103,
            tipo=TipoPosicao.VENDIDA,
            preco_entrada=PRECO_ENTRADA_SELL,
            volume=1.0,
            stop_loss=130_125.0,
            take_profit=PRECO_SAIDA_SELL_TP,
        )
        historico = motor.fechar_posicao(
            ticket=103,
            preco_saida=PRECO_SAIDA_SELL_TP,
            motivo=MotivoFechamento.TP_ATINGIDO,
        )
        assert historico is not None
        pnl_esperado = 250.0 * 1.0 * VALOR_PONTO_WINFUT  # R$ 50,00
        assert abs(historico.pnl_reais - pnl_esperado) < 0.01, (
            f"Esperado R${pnl_esperado:.2f}, obtido R${historico.pnl_reais:.2f}"
        )

    def test_pnl_sell_perda_125_pontos_1_contrato(self, motor):
        """
        SELL: entrada 130.000, saida 130.125 (+125 pontos), 1 contrato.
        pnl_reais esperado = -125 * 1 * 0.20 = R$ -25,00.
        """
        motor.abrir_posicao(
            ticket=104,
            tipo=TipoPosicao.VENDIDA,
            preco_entrada=PRECO_ENTRADA_SELL,
            volume=1.0,
            stop_loss=PRECO_SAIDA_SELL_SL,
            take_profit=PRECO_SAIDA_SELL_TP,
        )
        historico = motor.fechar_posicao(
            ticket=104,
            preco_saida=PRECO_SAIDA_SELL_SL,
            motivo=MotivoFechamento.SL_ATINGIDO,
        )
        assert historico is not None
        pnl_esperado = -125.0 * 1.0 * VALOR_PONTO_WINFUT  # R$ -25,00
        assert abs(historico.pnl_reais - pnl_esperado) < 0.01, (
            f"Esperado R${pnl_esperado:.2f}, obtido R${historico.pnl_reais:.2f}"
        )

    def test_pnl_buy_2_contratos(self, motor):
        """
        BUY: entrada 130.000, saida 130.250, 2 contratos.
        pnl_reais esperado = 250 * 2 * 0.20 = R$ 100,00.
        """
        motor.abrir_posicao(
            ticket=105,
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=PRECO_ENTRADA_BUY,
            volume=2.0,
            stop_loss=129_875.0,
            take_profit=PRECO_SAIDA_TP,
        )
        historico = motor.fechar_posicao(
            ticket=105,
            preco_saida=PRECO_SAIDA_TP,
            motivo=MotivoFechamento.TP_ATINGIDO,
        )
        assert historico is not None
        pnl_esperado = 250.0 * 2.0 * VALOR_PONTO_WINFUT  # R$ 100,00
        assert abs(historico.pnl_reais - pnl_esperado) < 0.01

    def test_pnl_range_realista_nunca_excede_300_reais_1_contrato(self, motor):
        """
        Para WINFUT com 1 contrato, diferenca de 500 pontos (range largo) = R$100.
        Garante que resultado NUNCA fica na casa dos milhoes.
        """
        motor.abrir_posicao(
            ticket=106,
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=130_000.0,
            volume=1.0,
            stop_loss=129_500.0,
            take_profit=130_500.0,
        )
        historico = motor.fechar_posicao(
            ticket=106,
            preco_saida=130_500.0,
            motivo=MotivoFechamento.TP_ATINGIDO,
        )
        assert historico is not None
        # 500 pontos * 1 contrato * R$0,20 = R$100 (nunca R$50.000!)
        assert historico.pnl_reais < 300.0, (
            f"pnl_reais muito alto ({historico.pnl_reais:.2f}) — "
            f"possivel uso de multiplicador errado (100 em vez de 0.20)"
        )
        assert historico.pnl_reais > 0.0

    def test_pnl_cenario_real_historico_negativo_range_correto(self, motor):
        """
        Replica o cenario real que gerou pnl_reais: -18.449.000.
        Com preco_entrada=182590, preco_saida=130000 (diferenca ~52590 pts).
        Com correcao: -52590 * 1 * 0.20 = R$-10.518 (nao R$-18.449.000).
        """
        motor.abrir_posicao(
            ticket=107,
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=182_590.0,
            volume=1.0,
            stop_loss=182_340.0,
            take_profit=183_090.0,
        )
        historico = motor.fechar_posicao(
            ticket=107,
            preco_saida=182_340.0,
            motivo=MotivoFechamento.SL_ATINGIDO,
        )
        assert historico is not None
        # SL = 250 pontos de diferenca = R$50 de perda
        pnl_esperado = -250.0 * 1.0 * VALOR_PONTO_WINFUT  # R$ -50,00
        assert abs(historico.pnl_reais - pnl_esperado) < 0.01, (
            f"Esperado R${pnl_esperado:.2f}, obtido R${historico.pnl_reais:.2f}. "
            f"Valor na casa dos milhoes indica multiplicador incorreto."
        )

    def test_atualizar_pnl_posicao_aberta_usa_valor_ponto_correto(self, motor):
        """
        Testa que atualizar_posicao() tambem usa VALOR_PONTO_WINFUT = 0.20.
        """
        motor.abrir_posicao(
            ticket=108,
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=130_000.0,
            volume=1.0,
            stop_loss=129_750.0,
            take_profit=130_250.0,
        )
        motor.atualizar_posicao(108, 130_100.0)
        posicao = motor.obter_posicao(108)
        assert posicao is not None
        # +100 pontos * 1 contrato * R$0,20 = R$20,00
        pnl_esperado = 100.0 * 1.0 * VALOR_PONTO_WINFUT
        assert abs((posicao.pnl_reais or 0.0) - pnl_esperado) < 0.01, (
            f"Esperado R${pnl_esperado:.2f}, obtido R${posicao.pnl_reais:.2f}"
        )

    def test_pnl_pct_independente_do_valor_ponto(self, motor):
        """
        pnl_pct e percentual puro (sem valor_ponto) e deve permanecer correto.
        BUY: entrada 130.000, saida 130.260 = +0.20% exato.
        """
        motor.abrir_posicao(
            ticket=109,
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=130_000.0,
            volume=1.0,
            stop_loss=129_750.0,
            take_profit=130_260.0,
        )
        historico = motor.fechar_posicao(
            ticket=109,
            preco_saida=130_260.0,
            motivo=MotivoFechamento.TP_ATINGIDO,
        )
        assert historico is not None
        pct_esperado = (260.0 / 130_000.0) * 100.0  # ~0.20%
        assert abs(historico.pnl_pct - pct_esperado) < 0.001
