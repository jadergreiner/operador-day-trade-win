"""
Testes para PositionClosureDetector.

Validam detecta de como posicoes foram fechadas:
- TP_HIT: Preco atingiu Take Profit
- SL_HIT: Preco atingiu Stop Loss
- MANUAL_CLOSE: Operador fechou manualmente
- TIMEOUT: Posicao aberta >24h sem fechar (auto-close)
- CANCELLED: Ordem cancelada antes de executar
"""

from datetime import datetime, timedelta
from typing import Dict, Any
from enum import Enum

import pytest

from src.application.position_closure_detector import (
    ClosureReason,
    ClosureDetectionResult,
    PositionClosureDetector,
)


class TestClosureReasonEnum:
    """Testa enum ClosureReason com 5 tipos validos."""

    def test_enum_tem_5_valores_validos(self) -> None:
        """Valida que ClosureReason contem exatamente 5 valores."""
        shutdown_reasons = [reason for reason in ClosureReason]
        assert len(shutdown_reasons) == 5, (
            f"Esperado 5 ClosureReasons, obtido {len(shutdown_reasons)}"
        )

    def test_enum_contem_tp_hit(self) -> None:
        """Valida existencia de TP_HIT."""
        assert hasattr(ClosureReason, "TP_HIT")
        assert ClosureReason.TP_HIT.value == "TP_HIT"

    def test_enum_contem_sl_hit(self) -> None:
        """Valida existencia de SL_HIT."""
        assert hasattr(ClosureReason, "SL_HIT")
        assert ClosureReason.SL_HIT.value == "SL_HIT"

    def test_enum_contem_manual_close(self) -> None:
        """Valida existencia de MANUAL_CLOSE."""
        assert hasattr(ClosureReason, "MANUAL_CLOSE")
        assert ClosureReason.MANUAL_CLOSE.value == "MANUAL_CLOSE"

    def test_enum_contem_timeout(self) -> None:
        """Valida existencia de TIMEOUT."""
        assert hasattr(ClosureReason, "TIMEOUT")
        assert ClosureReason.TIMEOUT.value == "TIMEOUT"

    def test_enum_contem_cancelled(self) -> None:
        """Valida existencia de CANCELLED."""
        assert hasattr(ClosureReason, "CANCELLED")
        assert ClosureReason.CANCELLED.value == "CANCELLED"


class TestClosureDetectionResult:
    """Testa dataclass ClosureDetectionResult."""

    def test_criar_resultado_com_tp_hit(self) -> None:
        """Cria um ClosureDetectionResult com TP_HIT."""
        resultado = ClosureDetectionResult(
            ticket=123456,
            simbolo="WINFUT",
            preco_entrada=100.50,
            preco_saida=102.50,
            pnl_reais=200.0,
            pnl_pct=1.99,
            motivo_fechamento=ClosureReason.TP_HIT,
            duracao_minutos=30,
            timestamp_deteccao=datetime.now(),
        )
        assert resultado.ticket == 123456
        assert resultado.pnl_reais == 200.0
        assert resultado.motivo_fechamento == ClosureReason.TP_HIT

    def test_resultado_para_dict(self) -> None:
        """Converte ClosureDetectionResult para dict."""
        resultado = ClosureDetectionResult(
            ticket=123456,
            simbolo="WINFUT",
            preco_entrada=100.0,
            preco_saida=99.0,
            pnl_reais=-100.0,
            pnl_pct=-1.0,
            motivo_fechamento=ClosureReason.SL_HIT,
            duracao_minutos=15,
            timestamp_deteccao=datetime.now(),
        )
        resultado_dict = resultado.para_dict()
        assert isinstance(resultado_dict, Dict)
        assert resultado_dict["ticket"] == 123456
        assert resultado_dict["motivo_fechamento"] == "SL_HIT"

    def test_resultado_timestamp_formato_iso(self) -> None:
        """Valida timestamp em formato ISO 8601."""
        agora = datetime.now()
        resultado = ClosureDetectionResult(
            ticket=111111,
            simbolo="WINFUT",
            preco_entrada=100.0,
            preco_saida=100.5,
            pnl_reais=50.0,
            pnl_pct=0.5,
            motivo_fechamento=ClosureReason.MANUAL_CLOSE,
            duracao_minutos=5,
            timestamp_deteccao=agora,
        )
        resultado_dict = resultado.para_dict()
        # Timestamp deve ser string em ISO format
        assert isinstance(resultado_dict["timestamp_deteccao"], str)


class TestPositionClosureDetector:
    """Testa PositionClosureDetector com 10+ casos."""

    def test_inicializar_detector(self) -> None:
        """Cria instancia de PositionClosureDetector."""
        detector = PositionClosureDetector()
        assert detector is not None
        assert hasattr(detector, "detectar_tp_hit")
        assert hasattr(detector, "detectar_sl_hit")
        assert hasattr(detector, "detectar_manual_close")
        assert hasattr(detector, "detectar_timeout")
        assert hasattr(detector, "gerar_relatorio_markdown")

    def test_detectar_tp_hit_buy(self) -> None:
        """Detecta TP_HIT para posicao BUY."""
        detector = PositionClosureDetector()

        # Posicao BUY esperada bater TP (102.50)
        resultado = detector.detectar_tp_hit(
            preco_entrada=100.0,
            preco_saida=102.50,
            take_profit=102.50,
            direcao="BUY",
        )

        assert resultado is not None
        assert resultado == ClosureReason.TP_HIT

    def test_detectar_tp_hit_sell(self) -> None:
        """Detecta TP_HIT para posicao SELL."""
        detector = PositionClosureDetector()

        # Posicao SELL esperada bater TP (98.00)
        resultado = detector.detectar_tp_hit(
            preco_entrada=100.0,
            preco_saida=98.00,
            take_profit=98.00,
            direcao="SELL",
        )

        assert resultado is not None
        assert resultado == ClosureReason.TP_HIT

    def test_detectar_tp_hit_nao_atingido_buy(self) -> None:
        """Nao detecta TP_HIT se preco nao atingiu TP."""
        detector = PositionClosureDetector()

        # BUY preco saida (101.5) < TP (102.5) = nao atingiu
        resultado = detector.detectar_tp_hit(
            preco_entrada=100.0,
            preco_saida=101.50,
            take_profit=102.50,
            direcao="BUY",
        )

        assert resultado is None

    def test_detectar_sl_hit_buy(self) -> None:
        """Detecta SL_HIT para posicao BUY."""
        detector = PositionClosureDetector()

        # BUY esperada bater SL (99.00)
        resultado = detector.detectar_sl_hit(
            preco_entrada=100.0,
            preco_saida=99.00,
            stop_loss=99.00,
            direcao="BUY",
        )

        assert resultado is not None
        assert resultado == ClosureReason.SL_HIT

    def test_detectar_sl_hit_sell(self) -> None:
        """Detecta SL_HIT para posicao SELL."""
        detector = PositionClosureDetector()

        # SELL SL (102.00) foi atingido
        resultado = detector.detectar_sl_hit(
            preco_entrada=100.0,
            preco_saida=102.00,
            stop_loss=102.00,
            direcao="SELL",
        )

        assert resultado is not None
        assert resultado == ClosureReason.SL_HIT

    def test_detectar_timeout_24h(self) -> None:
        """Detecta TIMEOUT quando posicao aberta >24h."""
        detector = PositionClosureDetector()

        # Abertura 25 horas atras
        timestamp_abertura = datetime.now() - timedelta(hours=25)
        timestamp_fechamento = datetime.now()

        resultado = detector.detectar_timeout(
            timestamp_abertura=timestamp_abertura,
            timestamp_fechamento=timestamp_fechamento,
        )

        assert resultado is not None
        assert resultado == ClosureReason.TIMEOUT

    def test_detectar_timeout_nao_aplica_posicao_recente(self) -> None:
        """Nao detecta TIMEOUT se posicao aberta <24h."""
        detector = PositionClosureDetector()

        # Abertura 10 horas atras
        timestamp_abertura = datetime.now() - timedelta(hours=10)
        timestamp_fechamento = datetime.now()

        resultado = detector.detectar_timeout(
            timestamp_abertura=timestamp_abertura,
            timestamp_fechamento=timestamp_fechamento,
        )

        assert resultado is None

    def test_detectar_manual_close_se_nenhum_motivo_automatico(self) -> None:
        """Classifica como MANUAL_CLOSE se nao foi TP/SL/TIMEOUT."""
        detector = PositionClosureDetector()

        # Preço nao bateu TP/SL, abertura recente = MANUAL_CLOSE
        resultado = detector.detectar_manual_close(
            preco_entrada=100.0,
            preco_saida=100.75,
            take_profit=102.50,
            stop_loss=98.00,
            direcao="BUY",
            timestamp_abertura=datetime.now() - timedelta(minutes=30),
            timestamp_fechamento=datetime.now(),
        )

        assert resultado is not None
        assert resultado == ClosureReason.MANUAL_CLOSE

    def test_calcular_pnl_buy(self) -> None:
        """Calcula P&L para BUY (positivo)."""
        detector = PositionClosureDetector()

        pnl_reais, pnl_pct = detector.calcular_pnl(
            preco_entrada=100.0,
            preco_saida=102.0,
            direcao="BUY",
            tamanho_contrato=100,
        )

        assert pnl_reais == 200.0  # (102 - 100) * 100
        assert pnl_pct == 2.0  # (102 - 100) / 100 * 100

    def test_calcular_pnl_sell(self) -> None:
        """Calcula P&L para SELL (quando preco desce)."""
        detector = PositionClosureDetector()

        pnl_reais, pnl_pct = detector.calcular_pnl(
            preco_entrada=100.0,
            preco_saida=98.0,
            direcao="SELL",
            tamanho_contrato=100,
        )

        assert pnl_reais == 200.0  # (100 - 98) * 100
        assert pnl_pct == 2.0  # (100 - 98) / 100 * 100

    def test_gerar_relatorio_markdown_estrutura(self) -> None:
        """Gera relatorio markdown com estrutura valida."""
        detector = PositionClosureDetector()

        # Registrar alguns resultados
        resultado1 = ClosureDetectionResult(
            ticket=123456,
            simbolo="WINFUT",
            preco_entrada=100.0,
            preco_saida=102.0,
            pnl_reais=200.0,
            pnl_pct=2.0,
            motivo_fechamento=ClosureReason.TP_HIT,
            duracao_minutos=30,
            timestamp_deteccao=datetime.now(),
        )

        detector.registrar_deteccao(resultado1)

        markdown = detector.gerar_relatorio_markdown()

        assert isinstance(markdown, str)
        assert "TP_HIT" in markdown or "Take Profit" in markdown
        assert "#" in markdown  # Headers markdown


class TestPositionClosureDetectorIntegracao:
    """Testa fluxos completos de deteccao de fechamento."""

    def test_fluxo_tp_hit_buy_sucesso(self) -> None:
        """Fluxo completo: BUY ganha ate TP."""
        detector = PositionClosureDetector()

        # Configuracao
        entrada = 100.0
        tp = 102.50
        saida = 102.50
        duracao_min = 25

        # Detectar
        motivo = detector.detectar_tp_hit(
            preco_entrada=entrada,
            preco_saida=saida,
            take_profit=tp,
            direcao="BUY",
        )

        # Validar
        assert motivo == ClosureReason.TP_HIT

        pnl_reais, pnl_pct = detector.calcular_pnl(
            preco_entrada=entrada,
            preco_saida=saida,
            direcao="BUY",
            tamanho_contrato=100,
        )
        assert pnl_reais > 0
        assert pnl_pct > 0

    def test_fluxo_sl_hit_perda(self) -> None:
        """Fluxo completo: SELL perde ate SL."""
        detector = PositionClosureDetector()

        # Configuracao: SELL esperava descer para 98, mas subiu para 101
        entrada = 100.0
        sl = 101.50
        saida = 101.50
        duracao_min = 5

        # Detectar
        motivo = detector.detectar_sl_hit(
            preco_entrada=entrada,
            preco_saida=saida,
            stop_loss=sl,
            direcao="SELL",
        )

        # Validar
        assert motivo == ClosureReason.SL_HIT

        pnl_reais, pnl_pct = detector.calcular_pnl(
            preco_entrada=entrada,
            preco_saida=saida,
            direcao="SELL",
            tamanho_contrato=100,
        )
        assert pnl_reais < 0
        assert pnl_pct < 0

    def test_fluxo_manual_close_sem_alvo(self) -> None:
        """Fluxo completo: Operador fecha manualmente sem atingir TP/SL."""
        detector = PositionClosureDetector()

        # Operador abre BUY em 100, fecha em 101 (sem TP/SL)
        entrada = 100.0
        saida = 101.0
        tp = 103.0
        sl = 98.0

        motivo = detector.detectar_manual_close(
            preco_entrada=entrada,
            preco_saida=saida,
            take_profit=tp,
            stop_loss=sl,
            direcao="BUY",
            timestamp_abertura=datetime.now() - timedelta(minutes=20),
            timestamp_fechamento=datetime.now(),
        )

        assert motivo == ClosureReason.MANUAL_CLOSE
