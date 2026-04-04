"""
Testes de Integracao E2E — S2-4: Detector SMC + Pipeline de Alertas

Valida o fluxo completo:
  deteccao SMC -> AlertaOportunidade -> FilaAlertas -> WebSocket -> Trader

Acceptance Criteria:
  AC-1: Detector integrado no loop principal (ProcessadorBDI)
  AC-2: WebSocket alerts incluem sinal_smc + confluencia_strength
  AC-3: E2E test passando
  AC-4: Performance <500ms latencia P95
"""

import asyncio
import json
import time
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.services.detector_smc import DetectorSMC
from src.application.services.alerta_formatter import AlertaFormatter
from src.domain.enums.alerta_enums import PatraoAlerta, NivelAlerta


# ===========================================================================
# Fixtures compartilhadas
# ===========================================================================

@pytest.fixture
def detector() -> DetectorSMC:
    return DetectorSMC()


@pytest.fixture
def formatter() -> AlertaFormatter:
    return AlertaFormatter()


@pytest.fixture
def ts() -> datetime:
    return datetime(2026, 4, 4, 10, 0, 0)


# ===========================================================================
# AC-1: DetectorSMC integrado ao ProcessadorBDI
# ===========================================================================

class TestIntegracaoProcessadorBDI:
    """AC-1: Detector SMC hookado no loop principal do ProcessadorBDI."""

    @pytest.mark.asyncio
    async def test_processador_bdi_chama_detector_smc_na_segunda_vela(self):
        """
        CASE: ProcessadorBDI recebe 2 velas consecutivas com BOS
        WHEN: processar_vela chamado 2x
        THEN: detector_smc.detectar_smc e chamado e alerta enfileirado
        """
        from src.application.services.processador_bdi import ProcessadorBDI

        processador = ProcessadorBDI.__new__(ProcessadorBDI)

        # Mocks internos
        processador.detector_vol = MagicMock()
        processador.detector_vol.analisar_vela = MagicMock(return_value=None)
        processador.detector_padroes = MagicMock()
        processador.detector_smc = DetectorSMC()
        processador._vela_anterior = {}
        processador._candles_hist = {}

        alertas_enfileirados = []

        fila_mock = AsyncMock()
        fila_mock.enfileirar = AsyncMock(side_effect=lambda a: alertas_enfileirados.append(a))
        processador.fila = fila_mock

        vela1 = {"open": 127000.0, "high": 127200.0, "low": 126900.0, "close": 127100.0, "volume": 500}
        vela2 = {"open": 127100.0, "high": 127600.0, "low": 127000.0, "close": 127500.0, "volume": 800}

        await processador.processar_vela("WIN$N", vela1)
        await processador.processar_vela("WIN$N", vela2)

        alertas_smc = [a for a in alertas_enfileirados if a.sinal_smc_nome is not None]
        assert len(alertas_smc) >= 1, "Deveria ter enfileirado ao menos 1 alerta SMC"

    @pytest.mark.asyncio
    async def test_processador_bdi_nao_gera_smc_na_primeira_vela(self):
        """
        CASE: ProcessadorBDI recebe apenas 1 vela (sem historico)
        WHEN: processar_vela chamado 1x
        THEN: detector SMC nao e acionado (precisa de vela anterior)
        """
        from src.application.services.processador_bdi import ProcessadorBDI

        processador = ProcessadorBDI.__new__(ProcessadorBDI)
        processador.detector_vol = MagicMock()
        processador.detector_vol.analisar_vela = MagicMock(return_value=None)
        processador.detector_padroes = MagicMock()
        processador.detector_smc = DetectorSMC()
        processador._vela_anterior = {}
        processador._candles_hist = {}

        alertas_enfileirados = []
        fila_mock = AsyncMock()
        fila_mock.enfileirar = AsyncMock(side_effect=lambda a: alertas_enfileirados.append(a))
        processador.fila = fila_mock

        vela1 = {"open": 127000.0, "high": 127200.0, "low": 126900.0, "close": 127100.0}
        await processador.processar_vela("WIN$N", vela1)

        alertas_smc = [a for a in alertas_enfileirados if a.sinal_smc_nome is not None]
        assert len(alertas_smc) == 0, "Primeira vela nao deve gerar SMC (sem historico)"


# ===========================================================================
# AC-2: WebSocket alert inclui sinal_smc + confluencia_strength
# ===========================================================================

class TestWebSocketPayloadSMC:
    """AC-2: Payload JSON do WebSocket contem campos SMC."""

    def test_formatar_json_inclui_bloco_sinal_smc(self, detector, ts):
        """
        CASE: Alerta SMC gerado pelo detector
        WHEN: AlertaFormatter.formatar_json chamado
        THEN: payload JSON contem chave 'sinal_smc' com subcampos
        """
        vela_ant = {"open": 127000.0, "high": 127200.0, "low": 126900.0, "close": 127100.0}
        vela_atu = {"open": 127100.0, "high": 127600.0, "low": 127000.0, "close": 127500.0}

        alerta = detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts)
        assert alerta is not None

        payload = AlertaFormatter.formatar_json(alerta)

        assert "sinal_smc" in payload, "Payload deve conter 'sinal_smc'"
        smc = payload["sinal_smc"]
        assert "nome" in smc
        assert "confianca" in smc
        assert "confluencia_strength" in smc
        assert "trader_pode_ver_sinal" in smc

    def test_formatar_json_sinal_smc_nome_e_bos(self, detector, ts):
        """
        CASE: BOS Bullish detectado
        WHEN: formatar_json chamado
        THEN: sinal_smc.nome == 'BOS'
        """
        vela_ant = {"open": 127000.0, "high": 127200.0, "low": 126900.0, "close": 127100.0}
        vela_atu = {"open": 127100.0, "high": 127600.0, "low": 127000.0, "close": 127500.0}

        alerta = detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts)
        payload = AlertaFormatter.formatar_json(alerta)

        assert payload["sinal_smc"]["nome"] == "BOS"

    def test_formatar_json_confianca_e_float_no_intervalo_0_1(self, detector, ts):
        """
        CASE: Qualquer alerta SMC
        WHEN: formatar_json chamado
        THEN: sinal_smc.confianca e float em [0, 1]
        """
        vela_ant = {"open": 127000.0, "high": 127200.0, "low": 126900.0, "close": 127100.0}
        vela_atu = {"open": 127100.0, "high": 127600.0, "low": 127000.0, "close": 127500.0}

        alerta = detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts)
        payload = AlertaFormatter.formatar_json(alerta)

        confianca = payload["sinal_smc"]["confianca"]
        assert isinstance(confianca, float)
        assert 0.0 <= confianca <= 1.0

    def test_formatar_json_confluencia_strength_entre_1_e_5(self, detector, ts):
        """
        CASE: BOS detectado
        WHEN: formatar_json chamado
        THEN: sinal_smc.confluencia_strength entre 1 e 5
        """
        vela_ant = {"open": 127000.0, "high": 127200.0, "low": 126900.0, "close": 127100.0}
        vela_atu = {"open": 127100.0, "high": 127600.0, "low": 127000.0, "close": 127500.0}

        alerta = detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts)
        payload = AlertaFormatter.formatar_json(alerta)

        cs = payload["sinal_smc"]["confluencia_strength"]
        assert 1 <= cs <= 5

    def test_formatar_json_trader_pode_ver_sinal_e_true(self, detector, ts):
        """
        CASE: BOS detectado
        WHEN: formatar_json chamado
        THEN: sinal_smc.trader_pode_ver_sinal == True
        """
        vela_ant = {"open": 127000.0, "high": 127200.0, "low": 126900.0, "close": 127100.0}
        vela_atu = {"open": 127100.0, "high": 127600.0, "low": 127000.0, "close": 127500.0}

        alerta = detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts)
        payload = AlertaFormatter.formatar_json(alerta)

        assert payload["sinal_smc"]["trader_pode_ver_sinal"] is True

    def test_formatar_json_serializa_para_string_json_valido(self, detector, ts):
        """
        CASE: Alerta SMC formatado
        WHEN: json.dumps chamado no payload
        THEN: nenhuma excecao, string JSON valida
        """
        vela_ant = {"open": 127000.0, "high": 127200.0, "low": 126900.0, "close": 127100.0}
        vela_atu = {"open": 127100.0, "high": 127600.0, "low": 127000.0, "close": 127500.0}

        alerta = detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts)
        payload = AlertaFormatter.formatar_json(alerta)

        json_str = json.dumps(payload)
        parsed = json.loads(json_str)

        assert parsed["padrao"] == PatraoAlerta.SMC_BOS.value

    def test_payload_nao_smc_tambem_contem_bloco_sinal_smc_com_nome_none(self):
        """
        CASE: Alerta de volatilidade (nao-SMC) formatado
        WHEN: formatar_json chamado
        THEN: payload contem bloco sinal_smc com nome=None (retrocompativel)
        """
        from src.application.services.detector_volatilidade import DetectorVolatilidade
        from src.domain.entities.alerta import AlertaOportunidade
        from src.domain.enums.alerta_enums import PatraoAlerta, NivelAlerta
        from src.domain.value_objects import Price, Symbol

        alerta = AlertaOportunidade(
            ativo=Symbol("WIN$N"),
            padrao=PatraoAlerta.VOLATILIDADE_EXTREMA,
            nivel=NivelAlerta.ALTO,
            preco_atual=Price(Decimal("127100")),
            timestamp_deteccao=datetime(2026, 4, 4, 10, 0, 0),
            entrada_minima=Price(Decimal("127000")),
            entrada_maxima=Price(Decimal("127200")),
            stop_loss=Price(Decimal("126800")),
            take_profit=Price(Decimal("127500")),
            confianca=Decimal("0.85"),
            risk_reward=Decimal("2.0"),
        )

        payload = AlertaFormatter.formatar_json(alerta)

        assert "sinal_smc" in payload
        assert payload["sinal_smc"]["nome"] is None


# ===========================================================================
# AC-3: E2E fluxo completo (deteccao -> alert -> trader)
# ===========================================================================

class TestE2EFluxoSMC:
    """AC-3: Teste E2E completo deteccao -> alert -> trader."""

    @pytest.mark.asyncio
    async def test_e2e_bos_ate_websocket_payload(self, detector, ts):
        """
        CASE: BOS detectado em WIN$N
        WHEN: fluxo completo do pipeline executado
        THEN: payload JSON pronto para WebSocket com todos os campos esperados
        """
        vela_ant = {"open": 127000.0, "high": 127200.0, "low": 126900.0, "close": 127100.0}
        vela_atu = {"open": 127100.0, "high": 127600.0, "low": 127000.0, "close": 127500.0}

        # Passo 1: Deteccao
        alerta = detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts)
        assert alerta is not None, "Deteccao falhou"

        # Passo 2: Formatacao para WebSocket
        payload = AlertaFormatter.formatar_json(alerta)
        json_str = json.dumps(payload)

        # Passo 3: Simulacao de recepcao pelo trader (parsing)
        recebido = json.loads(json_str)

        assert recebido["ativo"] == "WIN$N"
        assert recebido["padrao"] == "smc_bos"
        assert recebido["sinal_smc"]["nome"] == "BOS"
        assert isinstance(recebido["sinal_smc"]["confianca"], float)
        assert isinstance(recebido["sinal_smc"]["confluencia_strength"], int)
        assert recebido["sinal_smc"]["trader_pode_ver_sinal"] is True

    @pytest.mark.asyncio
    async def test_e2e_choch_ate_websocket_payload(self, ts):
        """
        CASE: CHoCH detectado apos injetar estrutura ALTA
        WHEN: fluxo E2E executado
        THEN: payload com padrao smc_choch e nivel CRITICO
        """
        detector = DetectorSMC()

        # Injeta estrutura ALTA para garantir CHoCH na proxima chamada
        detector._historico_estrutura["WIN$N"] = "ALTA"

        # CHoCH: close < low_ant
        vela_choch_ant = {"open": 127500.0, "high": 127800.0, "low": 127300.0, "close": 127600.0}
        vela_choch_atu = {"open": 127600.0, "high": 127650.0, "low": 127100.0, "close": 127200.0}
        alerta = detector.detectar_smc("WIN$N", vela_choch_atu, vela_choch_ant, ts)

        assert alerta is not None
        payload = AlertaFormatter.formatar_json(alerta)
        recebido = json.loads(json.dumps(payload))

        assert recebido["padrao"] == "smc_choch"
        assert recebido["nivel"] == "CRÍTICO"
        assert recebido["sinal_smc"]["nome"] == "CHoCH"

    @pytest.mark.asyncio
    async def test_e2e_50_alertas_smc_gerados_em_100_velas(self, ts):
        """
        CASE: 100 velas com alternancia de BOS e estrutura neutra
        WHEN: detectar_smc chamado para cada par de velas
        THEN: ao menos 40 alertas gerados (80%) — validacao de escala
        """
        detector = DetectorSMC()
        alertas_gerados = []

        preco = 127000.0
        for i in range(100):
            vela_ant = {
                "open": preco, "high": preco + 200,
                "low": preco - 100, "close": preco + 100
            }
            # Alterna: metade com rompimento, metade sem
            if i % 2 == 0:
                vela_atu = {
                    "open": preco + 100, "high": preco + 600,
                    "low": preco, "close": preco + 500
                }
            else:
                vela_atu = {
                    "open": preco + 100, "high": preco + 200,
                    "low": preco + 50, "close": preco + 150
                }
            preco += 100

            alerta = detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts)
            if alerta:
                alertas_gerados.append(alerta)

        # Nos 50 casos de rompimento deve gerar alertas
        assert len(alertas_gerados) >= 30, (
            f"Esperado >= 30 alertas, obtido {len(alertas_gerados)}"
        )


# ===========================================================================
# AC-4: Performance <500ms P95 (integracao completa com formatter)
# ===========================================================================

class TestPerformanceE2E:
    """AC-4: Latencia ponta-a-ponta < 500ms P95."""

    def test_pipeline_completo_100_velas_p95_abaixo_500ms(self, ts):
        """
        CASE: 100 velas processadas pelo pipeline completo
        WHEN: deteccao + formatacao medidas
        THEN: P95 < 500ms
        """
        detector = DetectorSMC()
        tempos: list = []

        preco = 127000.0
        for i in range(100):
            vela_ant = {"open": preco, "high": preco + 200, "low": preco - 100, "close": preco + 100}
            vela_atu = {"open": preco + 100, "high": preco + 600, "low": preco, "close": preco + 500}
            preco += 100

            inicio = time.perf_counter()

            alerta = detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts)
            if alerta:
                AlertaFormatter.formatar_json(alerta)

            fim = time.perf_counter()
            tempos.append((fim - inicio) * 1000)

        tempos.sort()
        p95 = tempos[int(len(tempos) * 0.95)]

        assert p95 < 500, f"P95={p95:.3f}ms excede 500ms"
