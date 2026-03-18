"""
Testes para TradePerformanceTracker - Rastreamento de P&L por Trade.

Este modulo testa a classe TradePerformanceTracker que monitora ganhos e perdas
de cada trade aberto, registrando entrada, saida, percentual e duracao.

Requisitos (AC):
- Rastrear preco entrada + horario de cada trade
- Calcular P&L em R$ e percentual
- Registrar motivo de fechamento (TP, SL, manual, timeout)
- Persistir em JSON por session_id
- Gerar relatorio com estatisticas agregadas
- Type hints 100% (mypy --strict OK)
- Test coverage >= 80%
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

import pytest

from src.application.trade_performance_tracker import (
    TradeClosureReason,
    TradePerformanceResult,
    TradePerformanceTracker,
)


class TestTradePerformanceDataClasses:
    """Testes para dataclasses e enums."""

    def test_criar_trade_performance_result(self) -> None:
        """Criar resultado de performance de trade com todos campos."""
        resultado: TradePerformanceResult = TradePerformanceResult(
            ticket=123456,
            simbolo="WINFUT",
            direcao="BUY",
            preco_entrada=100.50,
            horario_entrada=datetime(2026, 3, 16, 10, 30, 45),
            preco_saida=102.00,
            horario_saida=datetime(2026, 3, 16, 10, 35, 20),
            pnl_reais=75.00,
            percentual_pnl=1.49,
            motivo_fechamento=TradeClosureReason.TP_HIT,
            duracao_minutos=4,
        )

        assert resultado.ticket == 123456
        assert resultado.simbolo == "WINFUT"
        assert resultado.direcao == "BUY"
        assert resultado.preco_entrada == 100.50
        assert resultado.pnl_reais == 75.00
        assert resultado.percentual_pnl == 1.49
        assert resultado.motivo_fechamento == TradeClosureReason.TP_HIT
        assert resultado.duracao_minutos == 4

    def test_trade_performance_result_para_dict(self) -> None:
        """Converter resultado para dicionario (para JSON serialization)."""
        resultado: TradePerformanceResult = TradePerformanceResult(
            ticket=123456,
            simbolo="WINFUT",
            direcao="SELL",
            preco_entrada=100.50,
            horario_entrada=datetime(2026, 3, 16, 10, 30, 45),
            preco_saida=98.50,
            horario_saida=datetime(2026, 3, 16, 10, 45, 20),
            pnl_reais=100.00,
            percentual_pnl=1.99,
            motivo_fechamento=TradeClosureReason.TP_HIT,
            duracao_minutos=14,
        )

        resultado_dict: Dict[str, Any] = resultado.para_dict()

        assert resultado_dict["ticket"] == 123456
        assert resultado_dict["simbolo"] == "WINFUT"
        assert resultado_dict["direcao"] == "SELL"
        assert resultado_dict["preco_entrada"] == 100.50
        assert resultado_dict["pnl_reais"] == 100.00
        assert "horario_entrada" in resultado_dict
        assert "horario_saida" in resultado_dict

    def test_trade_closure_reason_enum(self) -> None:
        """Validar enum de motivos de fechamento."""
        assert TradeClosureReason.TP_HIT.value == "TP_HIT"
        assert TradeClosureReason.SL_HIT.value == "SL_HIT"
        assert TradeClosureReason.MANUAL_CLOSE.value == "MANUAL_CLOSE"
        assert TradeClosureReason.TIMEOUT.value == "TIMEOUT"
        assert TradeClosureReason.CANCELLED.value == "CANCELLED"


class TestTradePerformanceTracker:
    """Testes para classe TradePerformanceTracker."""

    @pytest.fixture
    def temp_dir(self) -> Path:
        """Criar diretorio temporario para testes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def tracker(self, temp_dir: Path) -> TradePerformanceTracker:
        """Criar tracker com session_id.")."""
        return TradePerformanceTracker(
            session_id="test_session_001",
            output_dir=temp_dir,
        )

    def test_inicializar_tracker(
        self, tracker: TradePerformanceTracker
    ) -> None:
        """Inicializar tracker com session_id e output_dir."""
        assert tracker.session_id == "test_session_001"
        assert tracker.trades == []
        assert tracker.lotes_gravados == 0

    def test_registrar_trade_simples(
        self, tracker: TradePerformanceTracker
    ) -> None:
        """Registrar um trade simples com TP hit (precos WINFUT em pontos)."""
        # WINFUT tipico: precos na faixa de 100000+ pontos
        # Ganho de 500 pontos * R$0,20 = R$100,00
        entrada = datetime(2026, 3, 16, 10, 30, 45)
        saida = datetime(2026, 3, 16, 10, 35, 20)

        resultado: TradePerformanceResult = tracker.registrar_trade(
            ticket=123456,
            simbolo="WINFUT",
            direcao="BUY",
            preco_entrada=100000.0,
            horario_entrada=entrada,
            preco_saida=100500.0,
            horario_saida=saida,
            motivo_fechamento=TradeClosureReason.TP_HIT,
        )

        assert resultado.ticket == 123456
        # 500 pts * R$0,20/ponto = R$100,00
        assert resultado.pnl_reais == pytest.approx(100.00, abs=0.01)
        assert resultado.percentual_pnl == pytest.approx(0.5, abs=0.01)
        assert resultado.duracao_minutos == 4
        assert len(tracker.trades) == 1

    def test_registrar_trade_com_perda(
        self, tracker: TradePerformanceTracker
    ) -> None:
        """Registrar trade que resulta em perda (SL hit)."""
        # Perda de 300 pontos * R$0,20 = -R$60,00
        entrada = datetime(2026, 3, 16, 11, 0, 0)
        saida = datetime(2026, 3, 16, 11, 5, 0)

        resultado: TradePerformanceResult = tracker.registrar_trade(
            ticket=789012,
            simbolo="WINFUT",
            direcao="BUY",
            preco_entrada=100000.0,
            horario_entrada=entrada,
            preco_saida=99700.0,
            horario_saida=saida,
            motivo_fechamento=TradeClosureReason.SL_HIT,
        )

        # -300 pts * R$0,20/ponto = -R$60,00
        assert resultado.pnl_reais == pytest.approx(-60.00, abs=0.01)
        assert resultado.percentual_pnl == pytest.approx(-0.3, abs=0.01)
        assert resultado.motivo_fechamento == TradeClosureReason.SL_HIT

    def test_registrar_multiplos_trades(
        self, tracker: TradePerformanceTracker
    ) -> None:
        """Registrar multiplos trades sequenciais."""
        base_time = datetime(2026, 3, 16, 9, 30, 0)

        # Trade 1: Ganho
        tracker.registrar_trade(
            ticket=1,
            simbolo="WINFUT",
            direcao="BUY",
            preco_entrada=100.0,
            horario_entrada=base_time,
            preco_saida=102.0,
            horario_saida=base_time + timedelta(minutes=5),
            motivo_fechamento=TradeClosureReason.TP_HIT,
        )

        # Trade 2: Perda
        tracker.registrar_trade(
            ticket=2,
            simbolo="WINFUT",
            direcao="SELL",
            preco_entrada=101.0,
            horario_entrada=base_time + timedelta(minutes=6),
            preco_saida=101.5,
            horario_saida=base_time + timedelta(minutes=11),
            motivo_fechamento=TradeClosureReason.SL_HIT,
        )

        # Trade 3: Manual close
        tracker.registrar_trade(
            ticket=3,
            simbolo="WINFUT",
            direcao="BUY",
            preco_entrada=100.5,
            horario_entrada=base_time + timedelta(minutes=12),
            preco_saida=100.75,
            horario_saida=base_time + timedelta(minutes=17),
            motivo_fechamento=TradeClosureReason.MANUAL_CLOSE,
        )

        assert len(tracker.trades) == 3

    def test_calcular_estatisticas(
        self, tracker: TradePerformanceTracker
    ) -> None:
        """Calcular estatisticas agregadas de trades."""
        base_time = datetime(2026, 3, 16, 9, 30, 0)

        # Track 3 trades: 2 ganhos + 1 perda
        tracker.registrar_trade(
            ticket=1,
            simbolo="WINFUT",
            direcao="BUY",
            preco_entrada=100.0,
            horario_entrada=base_time,
            preco_saida=101.0,
            horario_saida=base_time + timedelta(minutes=5),
            motivo_fechamento=TradeClosureReason.TP_HIT,
        )

        tracker.registrar_trade(
            ticket=2,
            simbolo="WINFUT",
            direcao="BUY",
            preco_entrada=100.0,
            horario_entrada=base_time + timedelta(minutes=6),
            preco_saida=98.0,
            horario_saida=base_time + timedelta(minutes=11),
            motivo_fechamento=TradeClosureReason.SL_HIT,
        )

        tracker.registrar_trade(
            ticket=3,
            simbolo="WINFUT",
            direcao="BUY",
            preco_entrada=100.0,
            horario_entrada=base_time + timedelta(minutes=12),
            preco_saida=102.0,
            horario_saida=base_time + timedelta(minutes=17),
            motivo_fechamento=TradeClosureReason.TP_HIT,
        )

        stats: Dict[str, Any] = tracker.calcular_estatisticas()

        assert stats["total_trades"] == 3
        assert stats["total_ganhos"] == 2
        assert stats["total_perdas"] == 1
        assert stats["win_rate"] == pytest.approx(66.67, abs=1.0)
        assert stats["pnl_total_reais"] > 0.0

    def test_gravar_json(self, tracker: TradePerformanceTracker) -> None:
        """Gravar trades em arquivo JSON."""
        base_time = datetime(2026, 3, 16, 9, 30, 0)

        tracker.registrar_trade(
            ticket=123,
            simbolo="WINFUT",
            direcao="BUY",
            preco_entrada=100.0,
            horario_entrada=base_time,
            preco_saida=101.0,
            horario_saida=base_time + timedelta(minutes=5),
            motivo_fechamento=TradeClosureReason.TP_HIT,
        )

        arquivo_saida: Path = tracker.gravar_json()

        assert arquivo_saida.exists()
        assert arquivo_saida.name.startswith("agente_performance_test_session_001")
        assert arquivo_saida.suffix == ".json"

        # Validar conteudo JSON
        with open(arquivo_saida) as f:
            dados: Dict[str, Any] = json.load(f)

        assert "metadata" in dados
        assert "session_id" in dados["metadata"]
        assert "trades" in dados
        assert len(dados["trades"]) == 1
        assert dados["trades"][0]["ticket"] == 123

    def test_format_timestamp_iso(
        self, tracker: TradePerformanceTracker
    ) -> None:
        """Validar formatacao de timestamp em ISO 8601."""
        resultado: TradePerformanceResult = tracker.registrar_trade(
            ticket=999,
            simbolo="WINFUT",
            direcao="BUY",
            preco_entrada=100.0,
            horario_entrada=datetime(2026, 3, 16, 10, 30, 45),
            preco_saida=101.0,
            horario_saida=datetime(2026, 3, 16, 10, 35, 20),
            motivo_fechamento=TradeClosureReason.TP_HIT,
        )

        resultado_dict: Dict[str, Any] = resultado.para_dict()
        timestamp_str: str = resultado_dict["horario_entrada"]

        # Validar formato ISO (YYYY-MM-DDTHH:MM:SS)
        assert "2026-03-16" in timestamp_str
        assert "10:30:45" in timestamp_str or "10:30" in timestamp_str

    def test_validar_pnl_percentual_buy(
        self, tracker: TradePerformanceTracker
    ) -> None:
        """Validar calculo de percentual P&L para ordem BUY com WINFUT."""
        # 1000 pontos de ganho = R$0,20 * 1000 = R$200
        resultado: TradePerformanceResult = tracker.registrar_trade(
            ticket=100,
            simbolo="WINFUT",
            direcao="BUY",
            preco_entrada=100000.0,
            horario_entrada=datetime(2026, 3, 16, 10, 0, 0),
            preco_saida=101000.0,
            horario_saida=datetime(2026, 3, 16, 10, 5, 0),
            motivo_fechamento=TradeClosureReason.TP_HIT,
        )

        # Ganho: (101000 - 100000) / 100000 * 100 = 1.0%
        assert resultado.percentual_pnl == pytest.approx(1.0, abs=0.01)
        # PnL WINFUT: 1000 pts * R$0,20/ponto = R$200,00
        assert resultado.pnl_reais == pytest.approx(200.0, abs=0.01)

    def test_validar_pnl_percentual_sell(
        self, tracker: TradePerformanceTracker
    ) -> None:
        """Validar calculo de percentual P&L para ordem SELL com WINFUT."""
        # 500 pontos de ganho SELL = R$0,20 * 500 = R$100
        resultado: TradePerformanceResult = tracker.registrar_trade(
            ticket=101,
            simbolo="WINFUT",
            direcao="SELL",
            preco_entrada=100000.0,
            horario_entrada=datetime(2026, 3, 16, 10, 0, 0),
            preco_saida=99500.0,
            horario_saida=datetime(2026, 3, 16, 10, 5, 0),
            motivo_fechamento=TradeClosureReason.TP_HIT,
        )

        # Ganho SELL: (100000 - 99500) / 100000 * 100 = 0.5%
        assert resultado.percentual_pnl == pytest.approx(0.5, abs=0.01)
        # PnL WINFUT: 500 pts * R$0,20/ponto = R$100,00
        assert resultado.pnl_reais == pytest.approx(100.0, abs=0.01)


class TestBug2PnlWinfut:
    """BUG-2: Verificar que pnl_reais usa R$0,20/ponto (nao tamanho_contrato=50)."""

    def test_pnl_buy_winfut_multiplier(self, tmp_path: Path) -> None:
        """BUY: 500 pts ganho deve gerar R$100, nao R$25000."""
        tracker: TradePerformanceTracker = TradePerformanceTracker(
            session_id="bug2_buy", output_dir=tmp_path
        )
        resultado: TradePerformanceResult = tracker.registrar_trade(
            ticket=1,
            simbolo="WINFUT",
            direcao="BUY",
            preco_entrada=100000.0,
            horario_entrada=datetime(2026, 3, 16, 10, 0, 0),
            preco_saida=100500.0,
            horario_saida=datetime(2026, 3, 16, 10, 5, 0),
            motivo_fechamento=TradeClosureReason.TP_HIT,
        )
        # 500 pts * R$0,20/ponto = R$100,00 (range valido: R$10 a R$300)
        assert resultado.pnl_reais == pytest.approx(100.0, abs=0.01)
        assert 10.0 <= resultado.pnl_reais <= 300.0

    def test_pnl_sell_winfut_multiplier(self, tmp_path: Path) -> None:
        """SELL: 300 pts ganho deve gerar R$60, nao R$15000."""
        tracker: TradePerformanceTracker = TradePerformanceTracker(
            session_id="bug2_sell", output_dir=tmp_path
        )
        resultado: TradePerformanceResult = tracker.registrar_trade(
            ticket=2,
            simbolo="WINFUT",
            direcao="SELL",
            preco_entrada=100000.0,
            horario_entrada=datetime(2026, 3, 16, 10, 0, 0),
            preco_saida=99700.0,
            horario_saida=datetime(2026, 3, 16, 10, 5, 0),
            motivo_fechamento=TradeClosureReason.TP_HIT,
        )
        # 300 pts * R$0,20/ponto = R$60,00 (range valido: R$10 a R$300)
        assert resultado.pnl_reais == pytest.approx(60.0, abs=0.01)
        assert 10.0 <= resultado.pnl_reais <= 300.0

    def test_pnl_nao_usa_tamanho_50(self, tmp_path: Path) -> None:
        """Garantir que multiplicador errado (50) nao esta em uso."""
        tracker: TradePerformanceTracker = TradePerformanceTracker(
            session_id="bug2_check", output_dir=tmp_path
        )
        resultado: TradePerformanceResult = tracker.registrar_trade(
            ticket=3,
            simbolo="WINFUT",
            direcao="BUY",
            preco_entrada=100000.0,
            horario_entrada=datetime(2026, 3, 16, 10, 0, 0),
            preco_saida=100100.0,
            horario_saida=datetime(2026, 3, 16, 10, 5, 0),
            motivo_fechamento=TradeClosureReason.TP_HIT,
        )
        # 100 pts: correto = R$20; errado seria R$5000 (100 * 50)
        assert resultado.pnl_reais == pytest.approx(20.0, abs=0.01)
        assert resultado.pnl_reais < 100.0  # nunca deve ser 5000


class TestTradePerformanceTrackerIntegration:
    """Testes de integracao ou cenarios complexos."""

    def test_rastreamento_sessao_completa(
        self, tmp_path: Path
    ) -> None:
        """Simular sessao completa com multiplos trades e gravacao."""
        tracker: TradePerformanceTracker = TradePerformanceTracker(
            session_id="integration_test_001",
            output_dir=tmp_path,
        )

        base_time: datetime = datetime(2026, 3, 16, 9, 30, 0)

        # Simular 5 trades em sequencia
        trades_data: list = [
            # Trade 1: TP hit, ganho 2%
            (
                1,
                "WINFUT",
                "BUY",
                100.0,
                102.0,
                0,
                10,
                TradeClosureReason.TP_HIT,
            ),
            # Trade 2: SL hit, perda 1%
            (
                2,
                "WINFUT",
                "BUY",
                100.0,
                99.0,
                11,
                5,
                TradeClosureReason.SL_HIT,
            ),
            # Trade 3: Manual close, ganho 1.5%
            (
                3,
                "WINFUT",
                "SELL",
                100.0,
                98.5,
                17,
                8,
                TradeClosureReason.MANUAL_CLOSE,
            ),
            # Trade 4: TP hit, ganho 1%
            (
                4,
                "WINFUT",
                "BUY",
                100.0,
                101.0,
                26,
                5,
                TradeClosureReason.TP_HIT,
            ),
            # Trade 5: Timeout, sem ganho
            (
                5,
                "WINFUT",
                "BUY",
                100.0,
                100.0,
                32,
                15,
                TradeClosureReason.TIMEOUT,
            ),
        ]

        for (
            ticket,
            simbolo,
            direcao,
            entrada,
            saida,
            minuto_inicio,
            duracao,
            motivo,
        ) in trades_data:
            tracker.registrar_trade(
                ticket=ticket,
                simbolo=simbolo,
                direcao=direcao,
                preco_entrada=entrada,
                horario_entrada=base_time + timedelta(minutes=minuto_inicio),
                preco_saida=saida,
                horario_saida=base_time
                + timedelta(minutes=minuto_inicio + duracao),
                motivo_fechamento=motivo,
            )

        # Validar agregacoes
        stats: Dict[str, Any] = tracker.calcular_estatisticas()
        assert stats["total_trades"] == 5
        assert stats["total_ganhos"] == 3  # Trades 1, 3, 4
        assert stats["total_perdas"] == 1  # Trade 2
        assert stats["total_breakeven"] == 1  # Trade 5

        # Gravar JSON e validar
        arquivo: Path = tracker.gravar_json()
        assert arquivo.exists()

        with open(arquivo) as f:
            dados: Dict[str, Any] = json.load(f)

        assert len(dados["trades"]) == 5
        assert dados["metadata"]["total_trades"] == 5
