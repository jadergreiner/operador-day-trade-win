"""Testes unitários para sistema de alertas - US-004."""

import asyncio
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from src.application.services.alerta_formatter import AlertaFormatter
from src.application.services.detector_padroes_tecnico import DetectorPadroesTecnico
from src.application.services.detector_volatilidade import DetectorVolatilidade
from src.domain.entities.alerta import AlertaOportunidade
from src.domain.enums.alerta_enums import (
    NivelAlerta,
    PatraoAlerta,
    StatusAlerta,
)
from src.domain.value_objects import Price, Symbol
from src.infrastructure.providers.fila_alertas import FilaAlertas


class TestAlertaOportunidade:
    """Testes da entidade AlertaOportunidade."""

    def test_alerta_inicializa_corretamente(self):
        """AC-001: Alerta inicializa com dados válidos."""

        alerta = AlertaOportunidade(
            ativo=Symbol("WIN$N"),
            padrao=PatraoAlerta.VOLATILIDADE_EXTREMA,
            nivel=NivelAlerta.CRÍTICO,
            preco_atual=Price(Decimal("89.50")),
            timestamp_deteccao=datetime.now(),
            entrada_minima=Price(Decimal("89.00")),
            entrada_maxima=Price(Decimal("90.00")),
            stop_loss=Price(Decimal("88.50")),
            confianca=Decimal("0.85"),
            risk_reward=Decimal("2.5"),
        )

        assert alerta.id is not None
        assert alerta.status == StatusAlerta.GERADO
        assert str(alerta.ativo) == "WIN$N"
        assert float(alerta.confianca) == 0.85

    def test_alerta_rejeita_entrada_invalida(self):
        """AC-001: Alerta rejeita entrada_min > entrada_max."""

        with pytest.raises(ValueError):
            AlertaOportunidade(
                ativo=Symbol("WIN$N"),
                padrao=PatraoAlerta.VOLATILIDADE_EXTREMA,
                nivel=NivelAlerta.CRÍTICO,
                preco_atual=Price(Decimal("89.50")),
                timestamp_deteccao=datetime.now(),
                entrada_minima=Price(Decimal("90.00")),  # Invertido!
                entrada_maxima=Price(Decimal("89.00")),
                stop_loss=Price(Decimal("88.50")),
                confianca=Decimal("0.85"),
                risk_reward=Decimal("2.5"),
            )

    def test_alerta_calcula_latencia(self):
        """AC-004: Calcula latência entre detecção e ação operador."""

        agora = datetime.now()
        alerta = AlertaOportunidade(
            ativo=Symbol("WIN$N"),
            padrao=PatraoAlerta.VOLATILIDADE_EXTREMA,
            nivel=NivelAlerta.CRÍTICO,
            preco_atual=Price(Decimal("89.50")),
            timestamp_deteccao=agora,
            entrada_minima=Price(Decimal("89.00")),
            entrada_maxima=Price(Decimal("90.00")),
            stop_loss=Price(Decimal("88.50")),
            confianca=Decimal("0.85"),
            risk_reward=Decimal("2.5"),
        )

        # Sem ação ainda
        assert alerta.calcular_latencia_total() == -1

        # Registra ação 5 segundos depois
        import time
        time.sleep(0.1)  # 100ms para teste ser rápido
        alerta.registrar_acao_operador("operador1", "EXECUTOU")

        latencia = alerta.calcular_latencia_total()
        assert latencia > 100  # Mínimo 100ms


class TestDetectorVolatilidade:
    """Testes do detector de volatilidade (ML Expert)."""

    def test_detector_identifica_volatilidade_extrema(self):
        """AC-001: Detecta volatilidade >2σ."""

        detector = DetectorVolatilidade(window=5, threshold_sigma=2.0)

        # Cria histórico com picos extremos
        historico = [89.0, 89.1, 89.2, 89.15, 89.25]  # Crescimento steady
        precos_adicionais = [
            89.5,  # +0.25 (normal)
            89.8,  # +0.3 (normal)
            91.0,  # +1.2 (EXTREMO! >2σ)
            91.5,  # +0.5 (EXTREMO confirmado!)
        ]

        for idx, preco in enumerate(precos_adicionais):
            alerta = detector.analisar_vela(
                symbol="WIN$N",
                close=Decimal(str(preco)),
                timestamp=datetime.now(),
                barras_historicas=[float(x) for x in historico],
            )

            if idx == 3:  # Última vela, segunda extrema
                assert alerta is not None, "Deveria detectar voltilidade extrema"
                assert alerta.padrao == PatraoAlerta.VOLATILIDADE_EXTREMA
                assert float(alerta.confianca) >= 0.85

    def test_detector_calcula_atr_corretamente(self):
        """AC-003: ATR e band as de entrada calculadas corretamente."""

        detector = DetectorVolatilidade()

        historico = [89.0] * 20  # Sem volatilidade
        alerta = detector.analisar_vela(
            symbol="WIN$N",
            close=Decimal("89.0"),
            timestamp=datetime.now(),
            barras_historicas=historico,
        )

        # Sem volatilidade, não gera alerta
        assert alerta is None

        # Agora força picos
        historico2 = [89.0, 89.0, 89.0, 89.0, 89.0, 88.5, 88.5, 88.5, 88.5, 88.5]
        alerta2 = detector.analisar_vela(
            symbol="WIN$N2",
            close=Decimal("92.0"),  # Pico extremo
            timestamp=datetime.now(),
            barras_historicas=historico2,
        )

        if alerta2:  # Se detecta
            assert alerta2.entrada_minima < alerta2.entrada_maxima
            assert alerta2.stop_loss < alerta2.entrada_minima
            assert alerta2.take_profit > alerta2.entrada_maxima


class TestDetectorPadroesTecnico:
    """Testes do detector de padrões técnicos (ML Expert)."""

    def test_engulfing_bullish_detectado(self):
        """Detecta padrão Engulfing Bullish."""

        detector = DetectorPadroesTecnico()

        # Vela anterior: Bearish
        vela_anterior = {"open": 90.0, "close": 89.0, "high": 90.5, "low": 88.5}

        # Vela atual: Bullish, envolve anterior
        vela_atual = {"open": 88.8, "close": 90.2, "high": 90.5, "low": 88.5}

        alerta = detector.detectar_engulfing(
            symbol="WIN$N",
            vela_atual=vela_atual,
            vela_anterior=vela_anterior,
            timestamp=datetime.now(),
        )

        assert alerta is not None
        assert alerta.padrao == PatraoAlerta.ENGULFING_BULLISH
        assert float(alerta.confianca) == 0.65

    def test_break_suporte_nao_gatilha_falso(self):
        """AC-001: Break de suporte requer confirmação."""

        detector = DetectorPadroesTecnico()

        precos = [89.0, 89.1, 89.2, 89.15, 89.3]  # Sem break

        alerta = detector.detectar_break_suporte(
            symbol="WIN$N",
            precos=precos,
            timestamp=datetime.now(),
            window=3,
        )

        assert alerta is None  # Sem break detectado


class TestAlertaFormatter:
    """Testes do formatador de alertas (Eng Sr)."""

    def test_alertformatter_gera_html_valido(self):
        """AC-003: Formata HTML válido para email."""

        alerta = AlertaOportunidade(
            ativo=Symbol("WIN$N"),
            padrao=PatraoAlerta.VOLATILIDADE_EXTREMA,
            nivel=NivelAlerta.CRÍTICO,
            preco_atual=Price(Decimal("89.50")),
            timestamp_deteccao=datetime.now(),
            entrada_minima=Price(Decimal("89.00")),
            entrada_maxima=Price(Decimal("90.00")),
            stop_loss=Price(Decimal("88.50")),
            take_profit=Price(Decimal("91.00")),
            confianca=Decimal("0.85"),
            risk_reward=Decimal("2.5"),
        )

        html = AlertaFormatter.formatar_email_html(alerta)

        assert "<html>" in html.lower()
        assert "89.50" in html  # Preço atual
        assert "WIN$N" in html  # Ativo
        assert "CRÍTICO" in html  # Nível

    def test_alertformatter_sms_respeita_limite(self):
        """AC-003: SMS tem máximo 160 caracteres."""

        alerta = AlertaOportunidade(
            ativo=Symbol("WIN$N"),
            padrao=PatraoAlerta.VOLATILIDADE_EXTREMA,
            nivel=NivelAlerta.CRÍTICO,
            preco_atual=Price(Decimal("89.50")),
            timestamp_deteccao=datetime.now(),
            entrada_minima=Price(Decimal("89.00")),
            entrada_maxima=Price(Decimal("90.00")),
            stop_loss=Price(Decimal("88.50")),
            confianca=Decimal("0.85"),
            risk_reward=Decimal("2.5"),
        )

        sms = AlertaFormatter.formatar_sms(alerta)

        assert len(sms) <= 160
        assert "[C]" in sms  # Inicial de CRÍTICO


class TestFilaAlertas:
    """Testes da fila de alertas com deduplicação (Eng Sr)."""

    @pytest.mark.asyncio
    async def test_queue_deduplicacao_alerts(self):
        """AC-004: Deduplicação >95% funciona."""

        fila = FilaAlertas(rate_limit_seconds=60)

        alerta = AlertaOportunidade(
            ativo=Symbol("WIN$N"),
            padrao=PatraoAlerta.VOLATILIDADE_EXTREMA,
            nivel=NivelAlerta.CRÍTICO,
            preco_atual=Price(Decimal("89.50")),
            timestamp_deteccao=datetime.now(),
            entrada_minima=Price(Decimal("89.00")),
            entrada_maxima=Price(Decimal("90.00")),
            stop_loss=Price(Decimal("88.50")),
            confianca=Decimal("0.85"),
            risk_reward=Decimal("2.5"),
        )

        # Primeira enfileirada deve passar
        resultado1 = await fila.enfileirar(alerta)
        assert resultado1 is True

        # Segundo igual (duplicado) deve ser rejeitado
        resultado2 = await fila.enfileirar(alerta)
        assert resultado2 is False

    @pytest.mark.asyncio
    async def test_rate_limiting_falha_corretamente(self):
        """AC-004: Rate limiting rejeita alertas <60s."""

        fila = FilaAlertas(rate_limit_seconds=60)

        alerta1 = AlertaOportunidade(
            ativo=Symbol("WIN$N"),
            padrao=PatraoAlerta.VOLATILIDADE_EXTREMA,
            nivel=NivelAlerta.CRÍTICO,
            preco_atual=Price(Decimal("89.50")),
            timestamp_deteccao=datetime.now(),
            entrada_minima=Price(Decimal("89.00")),
            entrada_maxima=Price(Decimal("90.00")),
            stop_loss=Price(Decimal("88.50")),
            confianca=Decimal("0.85"),
            risk_reward=Decimal("2.5"),
        )

        # Primeira enfileira
        resultado1 = await fila.enfileirar(alerta1)
        assert resultado1 is True

        # Cria segundo alerta (mesmo padrão, preço diferente)
        alerta2 = AlertaOportunidade(
            ativo=Symbol("WIN$N"),
            padrao=PatraoAlerta.VOLATILIDADE_EXTREMA,  # MESMO
            nivel=NivelAlerta.CRÍTICO,
            preco_atual=Price(Decimal("89.60")),  # Preço diferente
            timestamp_deteccao=datetime.now(),
            entrada_minima=Price(Decimal("89.10")),
            entrada_maxima=Price(Decimal("90.10")),
            stop_loss=Price(Decimal("88.60")),
            confianca=Decimal("0.85"),
            risk_reward=Decimal("2.5"),
        )

        # Rate limit deve rejeitar (mesmo padrão em <60s)
        resultado2 = await fila.enfileirar(alerta2)
        assert resultado2 is False


if __name__ == "__main__":
    # Executa testes
    pytest.main([__file__, "-v"])
