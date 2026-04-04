"""
Testes Unitarios — DetectorSMC (S2-4)

Cobre:
- AC-1: Detector integrado ao processador
- AC-2: WebSocket alerts incluem sinal SMC + confianca
- AC-3: fluxo de deteccao completo (BOS / CHoCH / FVG)
- AC-4: performance validada (<500ms P95)

Convencoes:
- CASE/WHEN/THEN em portugues
- Sem dependencias externas (mocks)
- Fixtures reutilizaveis
"""

import time
from datetime import datetime
from decimal import Decimal

import pytest

from src.application.services.detector_smc import DetectorSMC, CONFIANCA_MINIMA_SMC
from src.domain.enums.alerta_enums import PatraoAlerta, NivelAlerta


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def detector() -> DetectorSMC:
    """Instancia limpa do DetectorSMC para cada teste."""
    return DetectorSMC()


@pytest.fixture
def ts() -> datetime:
    return datetime(2026, 4, 4, 10, 0, 0)


@pytest.fixture
def vela_bullish() -> dict:
    return {"open": 127000.0, "high": 127500.0, "low": 126900.0, "close": 127400.0, "volume": 1000}


@pytest.fixture
def vela_bearish() -> dict:
    return {"open": 127400.0, "high": 127450.0, "low": 126800.0, "close": 126900.0, "volume": 800}


@pytest.fixture
def vela_neutro() -> dict:
    return {"open": 127200.0, "high": 127300.0, "low": 127100.0, "close": 127200.0, "volume": 500}


# ===========================================================================
# Testes de BOS (Break of Structure)
# ===========================================================================

class TestBOS:
    """Suite para deteccao de BOS."""

    def test_bos_bullish_detectado_quando_close_supera_high_anterior(self, detector, ts):
        """
        CASE: Close atual rompe acima do high anterior
        WHEN: detectar_smc chamado com vela de rompimento de topo
        THEN: AlertaOportunidade com padrao SMC_BOS e sinal_nome='BOS'
        """
        vela_ant = {"open": 127000.0, "high": 127300.0, "low": 126900.0, "close": 127100.0}
        vela_atu = {"open": 127100.0, "high": 127600.0, "low": 127000.0, "close": 127500.0}

        alerta = detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts)

        assert alerta is not None, "Deveria gerar alerta de BOS Bullish"
        assert alerta.padrao == PatraoAlerta.SMC_BOS
        assert alerta.sinal_smc_nome == "BOS"
        assert alerta.nivel == NivelAlerta.ALTO

    def test_bos_bearish_detectado_quando_close_rompe_low_anterior(self, detector, ts):
        """
        CASE: Close atual rompe abaixo do low anterior
        WHEN: detectar_smc chamado com vela de rompimento de fundo
        THEN: AlertaOportunidade com padrao SMC_BOS nivel ALTO
        """
        vela_ant = {"open": 127200.0, "high": 127400.0, "low": 127000.0, "close": 127100.0}
        vela_atu = {"open": 127100.0, "high": 127200.0, "low": 126800.0, "close": 126900.0}

        alerta = detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts)

        assert alerta is not None
        assert alerta.padrao == PatraoAlerta.SMC_BOS
        assert alerta.sinal_smc_nome == "BOS"

    def test_bos_nao_detectado_quando_close_dentro_da_vela_anterior(self, detector, ts, vela_neutro):
        """
        CASE: Close dentro da faixa high/low da vela anterior
        WHEN: detectar_smc chamado
        THEN: Nenhum alerta gerado
        """
        vela_ant = {"open": 127000.0, "high": 127500.0, "low": 126500.0, "close": 127200.0}
        vela_atu = {"open": 127200.0, "high": 127400.0, "low": 127100.0, "close": 127300.0}

        alerta = detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts)

        assert alerta is None, "Nao deveria gerar alerta sem rompimento"

    def test_bos_confianca_igual_a_0_70(self, detector, ts):
        """
        CASE: BOS Bullish detectado
        WHEN: verificar confianca
        THEN: confianca deve ser 0.70 (conforme spec)
        """
        vela_ant = {"open": 127000.0, "high": 127200.0, "low": 126900.0, "close": 127100.0}
        vela_atu = {"open": 127100.0, "high": 127600.0, "low": 127000.0, "close": 127500.0}

        alerta = detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts)

        assert alerta is not None
        assert alerta.confianca == Decimal("0.70")
        assert alerta.sinal_smc_confianca == Decimal("0.70")

    def test_bos_atualiza_historico_estrutura_para_alta(self, detector, ts):
        """
        CASE: BOS Bullish detectado
        WHEN: verificar historico interno do detector
        THEN: estrutura do ativo deve ser 'ALTA'
        """
        vela_ant = {"open": 127000.0, "high": 127200.0, "low": 126900.0, "close": 127100.0}
        vela_atu = {"open": 127100.0, "high": 127600.0, "low": 127000.0, "close": 127500.0}

        detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts)

        assert detector._historico_estrutura.get("WIN$N") == "ALTA"


# ===========================================================================
# Testes de CHoCH (Change of Character)
# ===========================================================================

class TestCHoCH:
    """Suite para deteccao de CHoCH."""

    def test_choch_bearish_quando_estrutura_alta_rompe_low(self, detector, ts):
        """
        CASE: Estrutura anterior era ALTA e close rompe low anterior
        WHEN: detectar_smc chamado apos BOS Bullish estabelecer estrutura ALTA
        THEN: AlertaOportunidade com padrao SMC_CHOCH nivel CRITICO
        """
        # Injeta estrutura ALTA diretamente (evita execucao do BOS neste teste)
        detector._historico_estrutura["WIN$N"] = "ALTA"

        # vela_choch: close < low_anterior -> CHoCH Bearish
        # close=127200, low_ant=127300 -> 127200 < 127300 -> CHoCH
        # Mas precisamos que close < low_ant e close >= low_ant NAO seja verdade para BOS
        # BOS Bearish: close < low_ant -> MESMA condicao
        # Como CHoCH tem prioridade, vai retornar CHoCH
        vela_ant = {"open": 127500.0, "high": 127800.0, "low": 127300.0, "close": 127600.0}
        vela_atu = {"open": 127600.0, "high": 127650.0, "low": 127100.0, "close": 127200.0}

        alerta = detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts)

        assert alerta is not None
        assert alerta.padrao == PatraoAlerta.SMC_CHOCH
        assert alerta.sinal_smc_nome == "CHoCH"
        assert alerta.nivel == NivelAlerta.CRÍTICO

    def test_choch_bullish_quando_estrutura_baixa_rompe_high(self, detector, ts):
        """
        CASE: Estrutura anterior era BAIXA e close rompe high anterior
        WHEN: detectar_smc chamado
        THEN: AlertaOportunidade com padrao SMC_CHOCH
        """
        # Injeta estrutura BAIXA diretamente
        detector._historico_estrutura["WIN$N"] = "BAIXA"

        # close > high_ant -> CHoCH Bullish (CHoCH tem prioridade sobre BOS)
        vela_ant = {"open": 126700.0, "high": 126900.0, "low": 126500.0, "close": 126600.0}
        vela_atu = {"open": 126600.0, "high": 127200.0, "low": 126500.0, "close": 127100.0}

        alerta = detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts)

        assert alerta is not None
        assert alerta.padrao == PatraoAlerta.SMC_CHOCH

    def test_choch_nao_gerado_sem_historico_de_estrutura(self, detector, ts):
        """
        CASE: Primeiro processamento sem historico estabelecido
        WHEN: detectar_smc chamado — nenhum padrao de faixa acionado
        THEN: Nenhum CHoCH (historico vazio)
        """
        # Vela dentro da faixa — sem BOS/CHoCH
        vela_ant = {"open": 127000.0, "high": 127300.0, "low": 126700.0, "close": 127100.0}
        vela_atu = {"open": 127100.0, "high": 127200.0, "low": 127000.0, "close": 127050.0}

        alerta = detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts)

        assert alerta is None

    def test_choch_confianca_igual_a_0_80(self, detector, ts):
        """
        CASE: CHoCH detectado
        WHEN: verificar confianca
        THEN: confianca deve ser 0.80 (maior que BOS — mudanca de tendencia)
        """
        # Injeta estrutura ALTA para garantir que CHoCH seja disparado
        detector._historico_estrutura["WIN$N"] = "ALTA"
        vela_ant = {"open": 127500.0, "high": 127800.0, "low": 127300.0, "close": 127600.0}
        vela_atu = {"open": 127600.0, "high": 127650.0, "low": 127100.0, "close": 127200.0}

        alerta = detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts)

        assert alerta is not None
        assert alerta.padrao == PatraoAlerta.SMC_CHOCH
        assert alerta.confianca == Decimal("0.80")


# ===========================================================================
# Testes de FVG (Fair Value Gap)
# ===========================================================================

class TestFVG:
    """Suite para deteccao de FVG."""

    def test_fvg_bullish_detectado_quando_low_atual_maior_que_high_tres_velas_atras(self, detector, ts):
        """
        CASE: Gap entre high[0] e low[2] — Bullish FVG (sem BOS nos pares adjacentes)
        WHEN: detectar_smc com historico de 3 candles com gap e velas adjacentes neutras
        THEN: AlertaOportunidade com padrao SMC_FVG
        """
        # vela_ant e vela_atu dentro da mesma faixa (sem BOS)
        # O FVG e detectado via candles_hist
        candles = [
            {"open": 127000.0, "high": 127200.0, "low": 126900.0, "close": 127100.0},
            {"open": 127300.0, "high": 127600.0, "low": 127250.0, "close": 127550.0},
            {"open": 127350.0, "high": 127500.0, "low": 127310.0, "close": 127400.0},
        ]
        # low[2]=127310 > high[0]=127200 -> FVG Bullish
        # vela_ant = c1, vela_atu = c2: close=127400 dentro de [127300, 127600] -> sem BOS
        vela_ant = candles[1]
        vela_atu = candles[2]

        alerta = detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts, candles_hist=candles)

        assert alerta is not None, "Deveria gerar alerta FVG Bullish"
        assert alerta.padrao == PatraoAlerta.SMC_FVG
        assert alerta.sinal_smc_nome == "FVG"

    def test_fvg_nao_detectado_sem_gap(self, detector, ts):
        """
        CASE: Velas consecutivas sem gap
        WHEN: detectar_smc com candles sobrepostos
        THEN: Nenhum FVG gerado
        """
        candles = [
            {"open": 127000.0, "high": 127300.0, "low": 126800.0, "close": 127100.0},
            {"open": 127100.0, "high": 127400.0, "low": 126900.0, "close": 127200.0},
            {"open": 127200.0, "high": 127500.0, "low": 127000.0, "close": 127300.0},
        ]
        vela_ant = candles[1]
        vela_atu = candles[2]

        alerta = detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts, candles_hist=candles)

        assert alerta is None, "Sem gap, nenhum FVG deve ser gerado"

    def test_fvg_retorna_none_com_historico_menor_que_3(self, detector, ts):
        """
        CASE: Menos de 3 candles historicos e velas adjacentes sem BOS/CHoCH
        WHEN: detectar_smc chamado
        THEN: FVG nao avaliado, retorna None
        """
        # Velas adjacentes totalmente dentro da faixa anterior — sem BOS
        vela_ant = {"open": 127000.0, "high": 127300.0, "low": 126700.0, "close": 127100.0}
        vela_atu = {"open": 127100.0, "high": 127200.0, "low": 127050.0, "close": 127150.0}

        # candles_hist com apenas 2 velas — FVG nao pode ser avaliado
        candles_hist = [vela_ant, vela_atu]

        alerta = detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts, candles_hist=candles_hist)

        assert alerta is None


# ===========================================================================
# Testes de campos SMC no alert (AC-2)
# ===========================================================================

class TestCamposSMCNoAlert:
    """Valida que AlertaOportunidade gerado pelo DetectorSMC contem campos SMC."""

    def test_alerta_smc_possui_sinal_smc_nome(self, detector, ts):
        """
        CASE: BOS detectado
        WHEN: acessar campo sinal_smc_nome
        THEN: deve ser 'BOS'
        """
        vela_ant = {"open": 127000.0, "high": 127200.0, "low": 126900.0, "close": 127100.0}
        vela_atu = {"open": 127100.0, "high": 127600.0, "low": 127000.0, "close": 127500.0}

        alerta = detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts)

        assert alerta is not None
        assert alerta.sinal_smc_nome == "BOS"

    def test_alerta_smc_possui_confluencia_strength_entre_1_e_5(self, detector, ts):
        """
        CASE: Qualquer padrao SMC detectado
        WHEN: verificar confluencia_strength
        THEN: deve estar entre 1 e 5 (inclusive)
        """
        vela_ant = {"open": 127000.0, "high": 127200.0, "low": 126900.0, "close": 127100.0}
        vela_atu = {"open": 127100.0, "high": 127600.0, "low": 127000.0, "close": 127500.0}

        alerta = detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts)

        assert alerta is not None
        assert 1 <= alerta.confluencia_strength <= 5

    def test_alerta_smc_trader_pode_ver_sinal_e_true_por_padrao(self, detector, ts):
        """
        CASE: BOS detectado
        WHEN: acessar campo trader_pode_ver_sinal
        THEN: deve ser True
        """
        vela_ant = {"open": 127000.0, "high": 127200.0, "low": 126900.0, "close": 127100.0}
        vela_atu = {"open": 127100.0, "high": 127600.0, "low": 127000.0, "close": 127500.0}

        alerta = detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts)

        assert alerta is not None
        assert alerta.trader_pode_ver_sinal is True

    def test_alerta_smc_confianca_retornada_no_campo_sinal_smc_confianca(self, detector, ts):
        """
        CASE: BOS detectado com confianca 0.70
        WHEN: acessar sinal_smc_confianca
        THEN: igual ao campo confianca principal
        """
        vela_ant = {"open": 127000.0, "high": 127200.0, "low": 126900.0, "close": 127100.0}
        vela_atu = {"open": 127100.0, "high": 127600.0, "low": 127000.0, "close": 127500.0}

        alerta = detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts)

        assert alerta is not None
        assert alerta.sinal_smc_confianca == alerta.confianca


# ===========================================================================
# Testes de performance (AC-4)
# ===========================================================================

class TestPerformanceSMC:
    """Valida que deteccao SMC ocorre dentro de 500ms P95."""

    def test_deteccao_100_velas_abaixo_de_500ms_p95(self, detector, ts):
        """
        CASE: 100 velas processadas sequencialmente
        WHEN: medir tempo de cada deteccao
        THEN: P95 deve ser menor que 500ms
        """
        tempos: list = []

        vela_base = {"open": 127000.0, "high": 127200.0, "low": 126900.0, "close": 127100.0}

        for i in range(100):
            preco = 127000.0 + i * 5
            vela_ant = {"open": preco, "high": preco + 200, "low": preco - 100, "close": preco + 100}
            vela_atu = {"open": preco + 100, "high": preco + 600, "low": preco, "close": preco + 500}

            inicio = time.perf_counter()
            detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts)
            fim = time.perf_counter()

            tempos.append((fim - inicio) * 1000)  # ms

        tempos.sort()
        p95 = tempos[int(len(tempos) * 0.95)]

        assert p95 < 500, f"P95 de {p95:.2f}ms excede limite de 500ms"

    def test_deteccao_com_historico_de_20_velas_abaixo_de_500ms(self, detector, ts):
        """
        CASE: Deteccao FVG com historico completo de 20 velas
        WHEN: detectar_smc com candles_hist de 20 velas
        THEN: tempo < 500ms
        """
        candles_hist = [
            {"open": 127000.0 + i * 10, "high": 127100.0 + i * 10,
             "low": 126900.0 + i * 10, "close": 127050.0 + i * 10}
            for i in range(20)
        ]
        vela_ant = candles_hist[-2]
        vela_atu = candles_hist[-1]

        inicio = time.perf_counter()
        detector.detectar_smc("WIN$N", vela_atu, vela_ant, ts, candles_hist=candles_hist)
        fim = time.perf_counter()

        elapsed_ms = (fim - inicio) * 1000
        assert elapsed_ms < 500, f"Deteccao levou {elapsed_ms:.2f}ms — limite: 500ms"
