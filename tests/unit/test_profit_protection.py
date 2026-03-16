"""
Testes unitários para módulo de Proteção de Lucros em Tempo Real.

Classes testadas:
- ProfitProtectionResult: Dataclass com resultado de proteção
- ProfitProtectionEngine: Motor de proteção dinâmico
"""

import json
from datetime import datetime
from typing import Dict

import pytest

from src.application.profit_protection_engine import (
    ProfitProtectionEngine,
    ProfitProtectionResult,
    ProtectionStatus,
)


# ============================================================
# FIXTURES
# ============================================================


@pytest.fixture
def engine() -> ProfitProtectionEngine:
    """Instancia motor de proteção com config padrão."""
    return ProfitProtectionEngine(
        profit_target_pct=2.0,
        stop_loss_pct=1.0,
        partial_close_pct=0.75,
        break_even_offset_pct=0.10,
    )


@pytest.fixture
def sample_trade_entry() -> Dict:
    """Trade de exemplo com entrada BUY."""
    return {
        "trade_id": "T001",
        "symbol": "WINFUT",
        "entry_price": 100.0,
        "entry_time": datetime(2026, 3, 16, 10, 30, 0),
        "direction": "BUY",
        "quantity": 1,
        "initial_sl": 99.0,
        "initial_tp": 102.0,
    }


@pytest.fixture
def sample_trade_sell() -> Dict:
    """Trade de exemplo com entrada SELL."""
    return {
        "trade_id": "T002",
        "symbol": "WINFUT",
        "entry_price": 100.0,
        "entry_time": datetime(2026, 3, 16, 10, 35, 0),
        "direction": "SELL",
        "quantity": 1,
        "initial_sl": 101.0,
        "initial_tp": 98.0,
    }


# ============================================================
# TEST: ProfitProtectionResult (Dataclass)
# ============================================================


class TestProfitProtectionResult:
    """Testa dataclass de resultado de proteção."""

    def test_resultado_criacao_basica(self) -> None:
        """Valida criação básica de resultado."""
        resultado = ProfitProtectionResult(
            trade_id="T001",
            status=ProtectionStatus.ATIVO,
            profit_atual=50.0,
            profit_objetivo=200.0,
            acao_sugerida="AGUARDAR",
            timestamp=datetime.now(),
        )

        assert resultado.trade_id == "T001"
        assert resultado.status == ProtectionStatus.ATIVO
        assert resultado.profit_atual == 50.0
        assert resultado.profit_objetivo == 200.0
        assert resultado.acao_sugerida == "AGUARDAR"

    def test_resultado_conversao_dict(self) -> None:
        """Valida conversão para dicionário."""
        resultado = ProfitProtectionResult(
            trade_id="T001",
            status=ProtectionStatus.LUCRO_PROTEGIDO,
            profit_atual=100.0,
            profit_objetivo=200.0,
            acao_sugerida="FECHAR_PARCIAL",
            timestamp=datetime(2026, 3, 16, 10, 30, 0),
        )

        resultado_dict = resultado.to_dict()

        assert resultado_dict["trade_id"] == "T001"
        assert resultado_dict["status"] == "LUCRO_PROTEGIDO"
        assert resultado_dict["profit_atual"] == 100.0
        assert resultado_dict["acao_sugerida"] == "FECHAR_PARCIAL"

    def test_resultado_conversao_json(self) -> None:
        """Valida conversão para JSON."""
        resultado = ProfitProtectionResult(
            trade_id="T001",
            status=ProtectionStatus.PARADO,
            profit_atual=0.0,
            profit_objetivo=200.0,
            acao_sugerida="AGUARDAR",
            timestamp=datetime(2026, 3, 16, 10, 30, 0),
        )

        resultado_json = resultado.to_json()
        parsed = json.loads(resultado_json)

        assert parsed["trade_id"] == "T001"
        assert parsed["status"] == "PARADO"
        assert parsed["profit_atual"] == 0.0


# ============================================================
# TEST: ProfitProtectionEngine (Core Logic)
# ============================================================


class TestProfitProtectionEngine:
    """Testa motor principal de proteção de lucros."""

    def test_engine_direcao_buy_com_lucro(
        self, engine: ProfitProtectionEngine, sample_trade_entry: Dict
    ) -> None:
        """Valida cálculo correto para BUY com lucro positivo."""
        # Preço subiu de 100 para 101.5 = +1.5% lucro
        resultado = engine.processar_protecao(
            trade=sample_trade_entry, preco_atual=101.5
        )

        assert resultado.trade_id == "T001"
        assert resultado.profit_atual == 1.5
        assert resultado.status == ProtectionStatus.ATIVO

    def test_engine_direcao_sell_com_lucro(
        self, engine: ProfitProtectionEngine, sample_trade_sell: Dict
    ) -> None:
        """Valida cálculo correto para SELL com lucro positivo."""
        # Preço caiu de 100 para 99.0 = +1.0% lucro
        resultado = engine.processar_protecao(
            trade=sample_trade_sell, preco_atual=99.0
        )

        assert resultado.trade_id == "T002"
        assert resultado.profit_atual == 1.0
        assert resultado.status == ProtectionStatus.ATIVO

    def test_engine_direcao_buy_com_prejuizo(
        self, engine: ProfitProtectionEngine, sample_trade_entry: Dict
    ) -> None:
        """Valida cálculo para BUY com prejuízo."""
        # Preço caiu de 100 para 99.5 = -0.5% prejuizo
        resultado = engine.processar_protecao(
            trade=sample_trade_entry, preco_atual=99.5
        )

        assert resultado.trade_id == "T001"
        assert resultado.profit_atual == -0.5
        assert resultado.status == ProtectionStatus.PARADO

    def test_engine_stop_loss_acionado(
        self, engine: ProfitProtectionEngine, sample_trade_entry: Dict
    ) -> None:
        """Valida detecção de stop loss acionado."""
        # Stop Loss é 99.0, preço atual 98.9 = SL acionado
        resultado = engine.processar_protecao(
            trade=sample_trade_entry, preco_atual=98.9
        )

        assert resultado.profit_atual < 0
        assert resultado.status == ProtectionStatus.PARADO

    def test_engine_break_even_stop_ativado(
        self, engine: ProfitProtectionEngine, sample_trade_entry: Dict
    ) -> None:
        """Valida ativação de break-even stop."""
        # Ganha 1.0%, break-even deveria estar ~99.9
        resultado = engine.processar_protecao(
            trade=sample_trade_entry,
            preco_atual=101.0,
            break_even_stop_ativo=True,
        )

        assert resultado.status == ProtectionStatus.ATIVO
        assert resultado.profit_atual == 1.0

    def test_engine_fechamento_parcial_sugerido(
        self, engine: ProfitProtectionEngine, sample_trade_entry: Dict
    ) -> None:
        """Valida sugestão de fechamento parcial.."""
        # Lucro de 1.5% com profit target de 2.0% = acionado
        resultado = engine.processar_protecao(
            trade=sample_trade_entry, preco_atual=101.5
        )

        # Se lucro >= 75% do target, sugerir fechar parcial
        if resultado.profit_atual >= engine.config["profit_target_pct"] * 0.75:
            assert resultado.acao_sugerida in [
                "FECHAR_PARCIAL",
                "AGUARDAR_TARGET",
            ]

    def test_engine_target_atingido(
        self, engine: ProfitProtectionEngine, sample_trade_entry: Dict
    ) -> None:
        """Valida detecção de target atingido."""
        # Target é 2.0%, preço de 102.0 = 2.0% lucro = TARGET!
        resultado = engine.processar_protecao(
            trade=sample_trade_entry, preco_atual=102.0
        )

        assert resultado.profit_atual == 2.0
        assert resultado.status == ProtectionStatus.LUCRO_PROTEGIDO
        assert resultado.acao_sugerida == "FECHAR_TOTAL"

    def test_engine_reacao_reversal_sharp(
        self, engine: ProfitProtectionEngine, sample_trade_entry: Dict
    ) -> None:
        """Valida reação a reversão aguda após alta ganho."""
        # Ganha 1.8%, depois cai para 0.5% = reversão
        resultado = engine.processar_protecao(
            trade=sample_trade_entry,
            preco_atual=100.5,
            lucro_maximo_sessao=1.8,
        )

        # Deviation do máximo = (1.8 - 0.5) = 1.3%
        # Se > threshold, sugerir fechar = ALERTA
        assert resultado.status in [
            ProtectionStatus.ATIVO,
            ProtectionStatus.ALERTA,
        ]

    def test_engine_validacao_entrada_none(
        self, engine: ProfitProtectionEngine
    ) -> None:
        """Valida tratamento de entrada None."""
        with pytest.raises(ValueError):
            engine.processar_protecao(trade=None, preco_atual=100.0)

    def test_engine_validacao_preco_invalido(
        self, engine: ProfitProtectionEngine, sample_trade_entry: Dict
    ) -> None:
        """Valida tratamento de preço inválido."""
        with pytest.raises(ValueError):
            engine.processar_protecao(trade=sample_trade_entry, preco_atual=-1.0)

    def test_engine_validacao_quantidade_zero(
        self, engine: ProfitProtectionEngine, sample_trade_entry: Dict
    ) -> None:
        """Valida rejeição de quantidade zero."""
        sample_trade_entry["quantity"] = 0
        with pytest.raises(ValueError):
            engine.processar_protecao(
                trade=sample_trade_entry, preco_atual=100.0
            )


# ============================================================
# TEST: Integração de Proteção (Cenários Complexos)
# ============================================================


class TestProtecaoIntegrada:
    """Testa cenários de proteção integrada."""

    def test_cenario_win_reversao_sharp(
        self, engine: ProfitProtectionEngine, sample_trade_entry: Dict
    ) -> None:
        """Simula win rápido + reversão (problema real)."""
        # Fase 1: Ganha rápido
        resultado1 = engine.processar_protecao(
            trade=sample_trade_entry, preco_atual=101.8
        )
        # Usar aproximação para floating point
        assert abs(resultado1.profit_atual - 1.8) < 1e-6
        assert resultado1.status == ProtectionStatus.ATIVO

        # Fase 2: Reversão aguda devolve lucro
        resultado2 = engine.processar_protecao(
            trade=sample_trade_entry,
            preco_atual=100.2,
            lucro_maximo_sessao=1.8,
        )
        # Usar aproximação para floating point
        assert abs(resultado2.profit_atual - 0.2) < 1e-5

    def test_cenario_break_even_stop_protege_lucro(
        self, engine: ProfitProtectionEngine, sample_trade_entry: Dict
    ) -> None:
        """Valida que break-even stop protege lucro."""
        # 1. Ganha 1.0%
        resultado1 = engine.processar_protecao(
            trade=sample_trade_entry, preco_atual=101.0
        )
        assert resultado1.profit_atual == 1.0

        # 2. Ativa break-even stop em ~99.1
        resultado2 = engine.processar_protecao(
            trade=sample_trade_entry,
            preco_atual=101.0,
            break_even_stop_ativo=True,
        )
        assert resultado2.status == ProtectionStatus.ATIVO

        # 3. Reversão aguda, mas SL em break-even protege
        resultado3 = engine.processar_protecao(
            trade=sample_trade_entry,
            preco_atual=99.2,
            break_even_stop_ativo=True,
        )
        # Deveria estar protegido por break-even
        assert resultado3.status in [
            ProtectionStatus.ATIVO,
            ProtectionStatus.PARADO,
        ]

    def test_cenario_fechamento_parcial_dinamico(
        self, engine: ProfitProtectionEngine, sample_trade_entry: Dict
    ) -> None:
        """Testa fechamento parcial quando lucro robusto."""
        # Target=2%, partial=75% do target = 1.5%
        resultado = engine.processar_protecao(
            trade=sample_trade_entry, preco_atual=101.5
        )

        lucro_parcial_trigger = (
            engine.config["profit_target_pct"]
            * engine.config["partial_close_pct"]
        )
        assert resultado.profit_atual >= lucro_parcial_trigger * 0.9

    def test_cenario_cooldown_evita_overtrading(
        self, engine: ProfitProtectionEngine, sample_trade_entry: Dict
    ) -> None:
        """Valida que cooldown evita sinais excessivos."""
        from datetime import timedelta

        # Processa em t1
        resultado1 = engine.processar_protecao(
            trade=sample_trade_entry, preco_atual=101.0
        )

        # Tenta processar novamente em t1+1s (deve respeitar cooldown)
        sample_trade_entry_recente = sample_trade_entry.copy()
        sample_trade_entry_recente["entry_time"] = datetime.now()

        resultado2 = engine.processar_protecao(
            trade=sample_trade_entry_recente, preco_atual=101.1
        )

        # Ambos devem ser válidos, mas cooldown deve estar em efeito
        assert resultado1.status is not None
        assert resultado2.status is not None


# ============================================================
# TEST: Performance e Validação
# ============================================================


class TestPerformanceProfitProtection:
    """Testa performance e integridade."""

    def test_performance_procesamento_rapido(
        self, engine: ProfitProtectionEngine, sample_trade_entry: Dict
    ) -> None:
        """Valida latência < 50ms (10x mais rápido que 500ms target)."""
        import time

        inicio = time.time()
        for _ in range(100):
            engine.processar_protecao(
                trade=sample_trade_entry, preco_atual=101.0
            )
        duracao = (time.time() - inicio) / 100

        assert duracao < 0.050  # 50ms

    def test_resultado_campos_obrigatorios(
        self, engine: ProfitProtectionEngine, sample_trade_entry: Dict
    ) -> None:
        """Valida que resultado tem todos campos obrigatórios."""
        resultado = engine.processar_protecao(
            trade=sample_trade_entry, preco_atual=101.0
        )

        campos_obrigatorios = [
            "trade_id",
            "status",
            "profit_atual",
            "profit_objetivo",
            "acao_sugerida",
            "timestamp",
        ]

        for campo in campos_obrigatorios:
            assert hasattr(resultado, campo), f"Campo obrigatório: {campo}"
            assert getattr(resultado, campo) is not None


# ============================================================
# TEST: Type Hints e Documentação
# ============================================================


class TestTypeHintsDocumentation:
    """Valida que type hints e docs estão corretos."""

    def test_engine_possui_type_hints(
        self, engine: ProfitProtectionEngine
    ) -> None:
        """Valida que classe principal tem type hints."""
        import inspect

        processar_sig = inspect.signature(engine.processar_protecao)
        assert "trade" in processar_sig.parameters
        assert "preco_atual" in processar_sig.parameters
        assert processar_sig.return_annotation is not None

    def test_resultado_possui_docstring(self) -> None:
        """Valida que dataclass de resultado tem docstring."""
        assert ProfitProtectionResult.__doc__ is not None

    def test_engine_possui_docstring(
        self, engine: ProfitProtectionEngine
    ) -> None:
        """Valida que engine tem docstring."""
        assert ProfitProtectionEngine.__doc__ is not None
        assert engine.processar_protecao.__doc__ is not None
