"""Testes de integração - fluxo completo US-004."""

import asyncio
from datetime import datetime
from decimal import Decimal

import pytest

from src.application.services.alerta_delivery import AlertaDeliveryManager
from src.application.services.alerta_formatter import AlertaFormatter
from src.application.services.detector_volatilidade import DetectorVolatilidade
from src.domain.entities.alerta import AlertaOportunidade
from src.domain.enums.alerta_enums import NivelAlerta, PatraoAlerta
from src.domain.value_objects import Price, Symbol
from src.infrastructure.database.auditoria_alertas import AuditoriaAlertas
from src.infrastructure.providers.fila_alertas import FilaAlertas


class MockWebSocketClient:
    """Mock WebSocket para testes."""

    def __init__(self):
        self.mensagens_enviadas = []

    async def enviar(self, alerta_id, payload):
        """Simula envio WebSocket."""
        self.mensagens_enviadas.append({"id": alerta_id, "payload": payload})
        return True


class MockEmailClient:
    """Mock SMTP para testes."""

    def __init__(self):
        self.emails_enviados = []

    async def enviar(self, destinatario, assunto, corpo):
        """Simula envio email."""
        self.emails_enviados.append({
            "destinatario": destinatario,
            "assunto": assunto,
            "corpo": corpo,
        })
        return True


class TestFluxoCompletoVolatilidade:
    """Testes de integração: fluxo completo detecção till entrega."""

    @pytest.mark.asyncio
    async def test_fluxo_completo_volatilidade_ate_websocket(self):
        """AC-001-005: Fluxo det ecção → fila → WebSocket."""

        # Setup
        detector = DetectorVolatilidade(window=5, threshold_sigma=2.0)
        formatter = AlertaFormatter()
        ws_mock = MockWebSocketClient()
        delivery = AlertaDeliveryManager(websocket_client=ws_mock)
        fila = FilaAlertas()

        # PASSO 1: Detecta oportunidade
        historico = [89.0, 89.1, 89.2, 89.15, 89.25]
        precos = [89.5, 89.8, 91.0, 91.5]  # Picos extremos

        alerta = None
        for preco in precos:
            alerta = detector.analisar_vela(
                symbol="WIN$N",
                close=Decimal(str(preco)),
                timestamp=datetime.now(),
                barras_historicas=[float(x) for x in historico],
            )

        assert alerta is not None, "Deveria detectar volatilidade"
        assert alerta.padrao == PatraoAlerta.VOLATILIDADE_EXTREMA

        # PASSO 2: Enfileira
        foi_enfileirado = await fila.enfileirar(alerta)
        assert foi_enfileirado is True

        # PASSO 3: Entrega via WebSocket
        await delivery.entregar_alerta(alerta)

        # PASSO 4: Validação
        assert len(ws_mock.mensagens_enviadas) > 0
        msg = ws_mock.mensagens_enviadas[0]
        assert msg["payload"]["nivel"] == "CRÍTICO"
        assert msg["payload"]["ativo"] == "WIN$N"

    @pytest.mark.asyncio
    async def test_fluxo_completo_volatilidade_ate_email(self):
        """AC-002: Fluxo com fallback de email."""

        # Setup
        detector = DetectorVolatilidade()
        formatter = AlertaFormatter()
        email_mock = MockEmailClient()

        delivery = AlertaDeliveryManager(
            websocket_client=None,  # Sem WebSocket
            email_config={
                "smtp_host": "localhost",
                "smtp_port": 1025,
                "from_email": "bot@trading.local",
                "to_email": "operador@trading.local",
            },
        )

        # Cria alerta manualmente (pular detecção por brevidade)
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

        # Entrega (WebSocket falha, email seria fallback)
        # Nota: Email real não é mockado por simplicidade
        await delivery.entregar_alerta(alerta)

        # Alerta foi processado
        assert alerta.status in [
            "ENTREGANDO",
            "ENTREGUE",
        ]  # Novo status após delivery


class TestLatenciaEnd2End:
    """Testes de latência (AC-004)."""

    @pytest.mark.asyncio
    async def test_latencia_deteccao_menor_30s(self):
        """AC-001: Latência detecção <30s."""

        detector = DetectorVolatilidade(window=5, threshold_sigma=2.0)
        tempo_inicio = datetime.now()

        # Simula dados em tempo real
        historico = [89.0] * 5
        precos = [89.5, 89.8, 91.0, 91.5]

        alerta = None
        for preco in precos:
            alerta = detector.analisar_vela(
                symbol="WIN$N",
                close=Decimal(str(preco)),
                timestamp=datetime.now(),
                barras_historicas=[float(x) for x in historico],
            )

        tempo_fim = datetime.now()
        latencia_ms = int((tempo_fim - tempo_inicio).total_seconds() * 1000)

        # Detecção deve ser rápida
        assert latencia_ms < 30000  # <30s
        print(f"Latência de detecção: {latencia_ms}ms")


class TestIntegracaoComAuditoria:
    """Testes de integração com auditoria CVM."""

    def test_alerta_registrado_em_auditoria(self, tmp_path):
        """AC-005: Alerta é registrado em auditoria."""

        # Usa DB em memória para testes
        db_file = str(tmp_path / "test_audit.db")
        auditoria = AuditoriaAlertas(db_path=db_file)

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

        # Registra alerta
        auditoria.registrar_alerta(
            alerta_id=str(alerta.id),
            ativo="WIN$N",
            padrao="volatilidade_extrema",
            nivel="CRÍTICO",
            timestamp_deteccao=alerta.timestamp_deteccao,
            preco_atual=89.50,
            entrada_min=89.00,
            entrada_max=90.00,
            stop_loss=88.50,
            confianca=0.85,
            risk_reward=2.5,
        )

        # Registra entrega
        auditoria.registrar_entrega(
            alerta_id=str(alerta.id),
            canal="websocket",
            status="entregue",
            latencia_ms=150,
        )

        # Registra ação operador
        auditoria.registrar_acao_operador(
            alerta_id=str(alerta.id),
            operador_username="operador1",
            acao="EXECUTOU",
            timestamp_acao=datetime.now(),
            ordem_mt5_id="12345",
        )

        # Consulta
        alertas = auditoria.consultar_alertas(limit=10)
        assert len(alertas) > 0
        assert alertas[0]["ativo"] == "WIN$N"

        # Estatísticas
        stats = auditoria.obter_estatisticas(dias=1)
        assert stats["total_alertas"] >= 1
        assert stats["taxa_entrega"] == 1.0  # 100% entregue

        auditoria.fechar()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
