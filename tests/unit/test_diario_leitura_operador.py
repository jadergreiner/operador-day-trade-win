"""
Testes unitarios para diario_leitura_operador.py

Cobre:
- _fase_sessao: correta para cada horario
- _posicao_no_range: todos os extremos e meio
- _qualidade_movimento: FORTE, FRACO, CHOP, SPIKE, pullback
- _calcular_vwap_aproximado: VWAP e TWAP fallback
- _avaliar_barato_caro: desvio, extremos, mean reversion
- _avaliar_correlacoes: alinhada, mista, divergente
- _identificar_armadilhas: cada tipo de armadilha
- _detectar_mudanca_cenario: guardian, kill switch
- _veredicto: penalidades, bonos, direcao preferida
- ler(): sem candles, candles validos, integracao completa
"""
from __future__ import annotations

import pytest
from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional
from unittest.mock import MagicMock, patch

from src.application.diario_leitura_operador import (
    LeituraDeOperador,
    LeituraOperador,
    FASE_ABERTURA,
    FASE_MANHA,
    FASE_ALMOCO,
    FASE_TARDE,
    FASE_FECHAMENTO,
    POSICAO_EXTREMO_ALTO,
    POSICAO_EXTREMO_BAIXO,
    POSICAO_ALTO,
    POSICAO_BAIXO,
    POSICAO_MEIO,
    MOVIMENTO_FORTE,
    MOVIMENTO_FRACO,
    MOVIMENTO_CHOP,
    MOVIMENTO_SPIKE,
    CORRELACAO_ALINHADA,
    CORRELACAO_MISTA,
    CORRELACAO_DIVERGENTE,
    ARMADILHA_ALTA,
    ARMADILHA_MEDIA,
    ARMADILHA_BAIXA,
)


# ── Helpers ─────────────────────────────────────────────────────────────────


@dataclass
class _Preco:
    value: float


@dataclass
class _Candle:
    open: _Preco
    close: _Preco
    high: _Preco
    low: _Preco
    volume: float = 100.0


def _candle(
    o: float,
    c: float,
    h: Optional[float] = None,
    l: Optional[float] = None,
    vol: float = 100.0,
) -> _Candle:
    return _Candle(
        open=_Preco(o),
        close=_Preco(c),
        high=_Preco(h if h is not None else max(o, c)),
        low=_Preco(l if l is not None else min(o, c)),
        volume=vol,
    )


def _candles_alta(n: int = 10, inicio: float = 100_000.0, passo: float = 100.0) -> list:
    return [_candle(inicio + i * passo, inicio + (i + 1) * passo) for i in range(n)]


def _candles_chop(n: int = 6, base: float = 100_000.0) -> list:
    result = []
    for i in range(n):
        if i % 2 == 0:
            result.append(_candle(base, base + 50))
        else:
            result.append(_candle(base + 50, base))
    return result


def _guardião_vazio() -> MagicMock:
    g = MagicMock()
    g.active_alerts = []
    g.active_kill_switch = False
    g.kill_switch_reason = ""
    g.scenario_changes = []
    return g


def _decisao(acao: str = "BUY") -> MagicMock:
    d = MagicMock()
    d.action = acao
    d.macro_bias = "NEUTRO"
    d.fundamental_bias = "NEUTRO"
    return d


# ── _fase_sessao ─────────────────────────────────────────────────────────────


class TestFaseSessao:
    def setup_method(self):
        self.leitor = LeituraDeOperador()

    def _at(self, hora: time) -> str:
        now = datetime.now().replace(hour=hora.hour, minute=hora.minute, second=0)
        with patch("src.application.diario_leitura_operador.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.now.return_value.time.return_value = now.time()
            return self.leitor._fase_sessao()

    def test_abertura(self):
        leitor = LeituraDeOperador()
        with patch("src.application.diario_leitura_operador.datetime") as mock_dt:
            mock_dt.now.return_value.time.return_value = time(9, 30)
            assert leitor._fase_sessao() == FASE_ABERTURA

    def test_manha(self):
        leitor = LeituraDeOperador()
        with patch("src.application.diario_leitura_operador.datetime") as mock_dt:
            mock_dt.now.return_value.time.return_value = time(11, 0)
            assert leitor._fase_sessao() == FASE_MANHA

    def test_almoco(self):
        leitor = LeituraDeOperador()
        with patch("src.application.diario_leitura_operador.datetime") as mock_dt:
            mock_dt.now.return_value.time.return_value = time(12, 30)
            assert leitor._fase_sessao() == FASE_ALMOCO

    def test_tarde(self):
        leitor = LeituraDeOperador()
        with patch("src.application.diario_leitura_operador.datetime") as mock_dt:
            mock_dt.now.return_value.time.return_value = time(15, 0)
            assert leitor._fase_sessao() == FASE_TARDE

    def test_fechamento(self):
        leitor = LeituraDeOperador()
        with patch("src.application.diario_leitura_operador.datetime") as mock_dt:
            mock_dt.now.return_value.time.return_value = time(16, 30)
            assert leitor._fase_sessao() == FASE_FECHAMENTO


# ── _posicao_no_range ────────────────────────────────────────────────────────


class TestPosicaoNoRange:
    def setup_method(self):
        self.leitor = LeituraDeOperador()

    def test_extremo_alto(self):
        assert (
            self.leitor._posicao_no_range(99_500, 100_000, 90_000)
            == POSICAO_EXTREMO_ALTO
        )

    def test_alto(self):
        assert self.leitor._posicao_no_range(97_000, 100_000, 90_000) == POSICAO_ALTO

    def test_meio(self):
        assert self.leitor._posicao_no_range(95_000, 100_000, 90_000) == POSICAO_MEIO

    def test_baixo(self):
        assert self.leitor._posicao_no_range(92_000, 100_000, 90_000) == POSICAO_BAIXO

    def test_extremo_baixo(self):
        assert (
            self.leitor._posicao_no_range(90_100, 100_000, 90_000)
            == POSICAO_EXTREMO_BAIXO
        )

    def test_high_igual_low_retorna_meio(self):
        assert self.leitor._posicao_no_range(100_000, 100_000, 100_000) == POSICAO_MEIO


# ── _qualidade_movimento ─────────────────────────────────────────────────────


class TestQualidadeMovimento:
    def setup_method(self):
        self.leitor = LeituraDeOperador()

    def test_poucos_candles_retorna_chop(self):
        q, ex, pb = self.leitor._qualidade_movimento([_candle(100, 110)] * 3)
        assert q == MOVIMENTO_CHOP
        assert ex is False
        assert pb is False

    def test_spike_ultimo_maior_2_5x(self):
        # 4 candles com corpo 50; media das 5 incluindo o spike:
        # para ultimo > media*2.5, precisamos que ultimo/(media)*>2.5
        # Se primeiros 4 = 10 cada e ultimo = 500:
        # media = (10*4+500)/5 = 540/5 = 108, ultimo/media = 500/108 = 4.6x → SPIKE
        candles = [_candle(100_000, 100_010)] * 4  # corpo 10
        candles.append(_candle(100_000, 100_500))  # corpo 500 >> 2.5x
        q, ex, pb = self.leitor._qualidade_movimento(candles)
        assert q == MOVIMENTO_SPIKE

    def test_chop_alternancia(self):
        # Alta-baixa-alta-baixa-alta → 4 mudancas
        cs = [
            _candle(100, 110),
            _candle(110, 100),
            _candle(100, 110),
            _candle(110, 100),
            _candle(100, 110),
        ]
        q, ex, pb = self.leitor._qualidade_movimento(cs)
        assert q == MOVIMENTO_CHOP

    def test_forte_direcional(self):
        # 5 velas em alta, corpos crescentes
        candles = [
            _candle(100_000, 100_200),  # corpo 200
            _candle(100_200, 100_450),  # corpo 250
            _candle(100_450, 100_750),  # corpo 300
            _candle(100_750, 101_100),  # corpo 350
            _candle(101_100, 101_500),  # corpo 400
        ]
        q, ex, pb = self.leitor._qualidade_movimento(candles)
        assert q == MOVIMENTO_FORTE
        assert ex is False

    def test_fraco_exaustao(self):
        # 5 velas em alta mas corpos decrescentes nas ultimas 3
        candles = [
            _candle(100_000, 100_400),  # corpo 400
            _candle(100_400, 100_800),  # corpo 400
            _candle(100_800, 101_200),  # ultimo 3: corpo 400
            _candle(101_200, 101_450),  # corpo 250
            _candle(101_450, 101_550),  # corpo 100 (< 50% da media ~350)
        ]
        q, ex, pb = self.leitor._qualidade_movimento(candles)
        assert ex is True
        assert q == MOVIMENTO_FRACO

    def test_pullback_saudavel(self):
        # 4 velas em alta + 1 vela contra com corpo menor
        candles = [
            _candle(100_000, 100_300),
            _candle(100_300, 100_600),
            _candle(100_600, 100_900),
            _candle(100_900, 101_200),
            _candle(101_200, 101_050),  # contra, corpo 150 < 60% de 300
        ]
        q, ex, pb = self.leitor._qualidade_movimento(candles)
        assert pb is True


# ── _calcular_vwap_aproximado ────────────────────────────────────────────────


class TestVwap:
    def setup_method(self):
        self.leitor = LeituraDeOperador()

    def test_sem_candles_retorna_zero(self):
        assert self.leitor._calcular_vwap_aproximado([]) == 0.0

    def test_candle_unico(self):
        c = _candle(100, 100, h=110, l=90, vol=100)
        vwap = self.leitor._calcular_vwap_aproximado([c])
        # preco tipico = (110+90+100)/3 = 100
        assert vwap == pytest.approx(100.0)

    def test_dois_candles_ponderado(self):
        c1 = _candle(100, 100, h=110, l=90, vol=100)  # tipico=100
        c2 = _candle(200, 200, h=210, l=190, vol=300)  # tipico=200
        vwap = self.leitor._calcular_vwap_aproximado([c1, c2])
        # (100*100 + 200*300) / 400 = (10000 + 60000)/400 = 175
        assert vwap == pytest.approx(175.0)

    def test_fallback_sem_volume(self):
        # volume=0 → usa 1 como fallback → TWAP
        c = _candle(100, 110, h=120, l=90, vol=0)
        vwap = self.leitor._calcular_vwap_aproximado([c])
        # preco tipico = (120+90+110)/3 = 106.67
        assert vwap == pytest.approx((120 + 90 + 110) / 3)


# ── _avaliar_barato_caro ─────────────────────────────────────────────────────


class TestBaratoCaro:
    def setup_method(self):
        self.leitor = LeituraDeOperador()

    def test_na_vwap(self):
        desvio, dir, extremo, mr = self.leitor._avaliar_barato_caro(
            100_000, 100_000, 200.0, 101_000, 99_000
        )
        assert desvio == 0.0
        assert dir == "NA_VWAP"
        assert extremo is False

    def test_acima_vwap(self):
        desvio, dir, extremo, mr = self.leitor._avaliar_barato_caro(
            100_500, 100_000, 200.0, 101_000, 99_000
        )
        assert desvio == 500.0
        assert dir == "ACIMA"

    def test_abaixo_vwap(self):
        desvio, dir, extremo, mr = self.leitor._avaliar_barato_caro(
            99_500, 100_000, 200.0, 101_000, 99_000
        )
        assert dir == "ABAIXO"

    def test_extremo_alto_sem_mean_reversion(self):
        # Preco em 95% do range mas desvio < 1.5 ATR → extremo=True, mr=False
        # range = 1000, top 10% = >=99_900
        # desvio = 99_950 - 99_700 = 250 = 1.25 ATR (< 1.5)
        desvio, dir, extremo, mr = self.leitor._avaliar_barato_caro(
            99_950, 99_700, 200.0, 100_000, 99_000
        )
        assert extremo is True
        assert mr is False  # desvio 250 < 300 (1.5*200)

    def test_mean_reversion_ativo(self):
        # Preco em extremo E desvio > 1.5 ATR
        # range = 1000, extremo top 10% = >=99_900
        # vwap = 99_500, desvio = 99_950 - 99_500 = 450 > 300 (1.5*200)
        desvio, dir, extremo, mr = self.leitor._avaliar_barato_caro(
            99_950, 99_500, 200.0, 100_000, 99_000
        )
        assert extremo is True
        assert mr is True


# ── _avaliar_correlacoes ─────────────────────────────────────────────────────


class TestCorrelacoes:
    def setup_method(self):
        self.leitor = LeituraDeOperador()

    def test_neutro_retorna_mista(self):
        estado, d, s, c, div = self.leitor._avaliar_correlacoes(
            "NEUTRO", [], MagicMock()
        )
        assert estado == CORRELACAO_MISTA

    def test_alinhada_buy(self):
        # WIN quer subir → dolar fraco (score<0), SP500 alto (score>0), commodities alta (score>0)
        items = [
            {"category": "DOLAR_CAMBIO", "symbol": "DOLAR", "score": "-2"},
            {"category": "INDICES_GLOBAIS", "symbol": "SP500", "score": "3"},
            {"category": "COMMODITIES", "symbol": "PETR4", "score": "1"},
        ]
        decisao = MagicMock()
        decisao.macro_bias = "NEUTRO"
        decisao.fundamental_bias = "NEUTRO"
        estado, d, s, c, div = self.leitor._avaliar_correlacoes("BUY", items, decisao)
        assert estado == CORRELACAO_ALINHADA
        assert d is True
        assert s is True
        assert c is True
        assert div is False

    def test_divergente_todos_contra(self):
        # WIN quer subir mas todos os correlatos contra
        items = [
            {
                "category": "DOLAR_CAMBIO",
                "symbol": "DOLAR",
                "score": "3",
            },  # dolar forte = contra BUY
            {
                "category": "INDICES_GLOBAIS",
                "symbol": "SP500",
                "score": "-2",
            },  # SP cai = contra BUY
            {
                "category": "COMMODITIES",
                "symbol": "PETR4",
                "score": "-1",
            },  # commodities cai = contra BUY
        ]
        decisao = MagicMock()
        decisao.macro_bias = "NEUTRO"
        decisao.fundamental_bias = "NEUTRO"
        estado, d, s, c, div = self.leitor._avaliar_correlacoes("BUY", items, decisao)
        assert estado == CORRELACAO_DIVERGENTE
        assert div is True

    def test_fallback_macro_bias_bull(self):
        # Sem items macro, usa macro_bias BULL para WIN BUY
        decisao = MagicMock()
        decisao.macro_bias = "BULL"
        decisao.fundamental_bias = "BULL"
        estado, d, s, c, div = self.leitor._avaliar_correlacoes("BUY", [], decisao)
        assert d is True
        assert s is True


# ── _identificar_armadilhas ──────────────────────────────────────────────────


class TestArmadilhas:
    def setup_method(self):
        self.leitor = LeituraDeOperador()

    def _arm(self, **kwargs) -> tuple:
        defaults = dict(
            fase=FASE_MANHA,
            posicao=POSICAO_MEIO,
            qualidade=MOVIMENTO_FORTE,
            exaustao=False,
            correlacao=CORRELACAO_ALINHADA,
            divergencia=False,
            range_pts=1000.0,
            desvio_vwap_pts=0.0,
            atr=200.0,
            candles=[],
        )
        defaults.update(kwargs)
        return self.leitor._identificar_armadilhas(**defaults)

    def test_sem_armadilhas_retorna_baixa(self):
        risco, arm = self._arm()
        assert risco == ARMADILHA_BAIXA
        assert arm == []

    def test_abertura_falsa(self):
        risco, arm = self._arm(fase=FASE_ABERTURA, posicao=POSICAO_EXTREMO_ALTO)
        assert any("ABERTURA_FALSA" in a for a in arm)

    def test_fakeout(self):
        risco, arm = self._arm(posicao=POSICAO_EXTREMO_ALTO, qualidade=MOVIMENTO_FRACO)
        assert any("FAKEOUT_PROVAVEL" in a for a in arm)

    def test_spike_almoco(self):
        risco, arm = self._arm(fase=FASE_ALMOCO, qualidade=MOVIMENTO_SPIKE)
        assert any("SPIKE_ALMOCO" in a for a in arm)

    def test_exaustao(self):
        risco, arm = self._arm(exaustao=True)
        assert any("EXAUSTAO_DETECTADA" in a for a in arm)

    def test_divergencia_critica(self):
        risco, arm = self._arm(divergencia=True)
        assert any("DIVERGENCIA_CRITICA" in a for a in arm)

    def test_perseguindo_movimento(self):
        # Desvio > 1.8 * ATR = 1.8 * 200 = 360
        risco, arm = self._arm(desvio_vwap_pts=400.0, atr=200.0)
        assert any("PERSEGUINDO_MOVIMENTO" in a for a in arm)

    def test_chop_fechamento(self):
        risco, arm = self._arm(fase=FASE_FECHAMENTO, qualidade=MOVIMENTO_CHOP)
        assert any("CHOP_FECHAMENTO" in a for a in arm)

    def test_multiplas_armadilhas_risco_alta(self):
        # Divergencia (3) + Exaustao (2) = score 5 → ALTA
        risco, arm = self._arm(divergencia=True, exaustao=True)
        assert risco == ARMADILHA_ALTA

    def test_uma_armadilha_risco_media(self):
        # FAKEOUT (2) = score 2 → MEDIA
        risco, arm = self._arm(posicao=POSICAO_EXTREMO_ALTO, qualidade=MOVIMENTO_FRACO)
        assert risco == ARMADILHA_MEDIA


# ── _detectar_mudanca_cenario ────────────────────────────────────────────────


class TestMudancaCenario:
    def setup_method(self):
        self.leitor = LeituraDeOperador()

    def test_sem_mudanca(self):
        g = _guardião_vazio()
        mudou, motivo = self.leitor._detectar_mudanca_cenario(g, [], MagicMock())
        assert mudou is False
        assert motivo == ""

    def test_kill_switch(self):
        g = _guardião_vazio()
        g.active_kill_switch = True
        g.kill_switch_reason = "drawdown_limit"
        mudou, motivo = self.leitor._detectar_mudanca_cenario(g, [], MagicMock())
        assert mudou is True
        assert "kill switch" in motivo.lower()

    def test_alerta_critico(self):
        g = _guardião_vazio()
        alerta = MagicMock()
        alerta.severity = "CRITICAL"
        g.active_alerts = [alerta]
        mudou, motivo = self.leitor._detectar_mudanca_cenario(g, [], MagicMock())
        assert mudou is True

    def test_scenario_changes(self):
        g = _guardião_vazio()
        g.scenario_changes = ["bear_market_detected"]
        mudou, motivo = self.leitor._detectar_mudanca_cenario(g, [], MagicMock())
        assert mudou is True


# ── _veredicto ───────────────────────────────────────────────────────────────


class TestVeredicto:
    def setup_method(self):
        self.leitor = LeituraDeOperador()

    def _v(self, **kwargs) -> tuple:
        defaults = dict(
            fase=FASE_MANHA,
            qualidade=MOVIMENTO_FORTE,
            exaustao=False,
            pullback=False,
            correlacao=CORRELACAO_ALINHADA,
            divergencia=False,
            risco_armadilha=ARMADILHA_BAIXA,
            posicao=POSICAO_MEIO,
            mean_reversion=False,
            cenario_mudou=False,
            direcao_decisao="BUY",
        )
        defaults.update(kwargs)
        return self.leitor._veredicto(**defaults)

    def test_momento_favoravel_ideal(self):
        momento, dir, conf, resumo, ajuste = self._v()
        assert momento is True
        assert ajuste > 0  # bonus manha + correlacao alinhada

    def test_almoco_e_feature_nao_veto(self):
        momento, dir, conf, resumo, ajuste = self._v(
            fase=FASE_ALMOCO,
            qualidade=MOVIMENTO_CHOP,
            correlacao=CORRELACAO_MISTA,
        )
        assert dir == "BUY"
        assert "feature" in resumo.lower()
        assert momento is False

    def test_divergencia_nao_favoravel(self):
        momento, dir, conf, resumo, ajuste = self._v(divergencia=True)
        assert momento is False
        assert dir == "NEUTRO"

    def test_pullback_boost(self):
        _, _, _, _, ajuste_base = self._v()
        _, _, _, _, ajuste_pb = self._v(pullback=True)
        assert ajuste_pb > ajuste_base

    def test_mean_reversion_direcao_sell(self):
        _, dir, _, _, _ = self._v(mean_reversion=True, posicao=POSICAO_EXTREMO_ALTO)
        assert dir == "SELL"

    def test_mean_reversion_direcao_buy(self):
        _, dir, _, _, _ = self._v(mean_reversion=True, posicao=POSICAO_EXTREMO_BAIXO)
        assert dir == "BUY"

    def test_exaustao_no_meio_penalidade(self):
        _, _, _, _, ajuste_base = self._v()
        _, _, _, _, ajuste_exaustao = self._v(exaustao=True, posicao=POSICAO_MEIO)
        assert ajuste_exaustao < ajuste_base

    def test_confianca_limites(self):
        _, _, confianca, _, _ = self._v()
        assert 0.30 <= confianca <= 0.95

    def test_cenario_mudou_penalidade(self):
        _, _, _, _, ajuste_base = self._v()
        _, _, _, _, ajuste_mudanca = self._v(cenario_mudou=True)
        assert ajuste_mudanca < ajuste_base


# ── ler() ────────────────────────────────────────────────────────────────────


class TestLer:
    def setup_method(self):
        self.leitor = LeituraDeOperador()
        self.guardian = _guardião_vazio()
        self.decisao = _decisao("BUY")

    def test_sem_candles_retorna_leitura_vazia(self):
        leitura = self.leitor.ler([], self.decisao, self.guardian)
        assert isinstance(leitura, LeituraOperador)
        assert leitura.qualidade_movimento == MOVIMENTO_CHOP
        assert leitura.momento_favoravel is False
        assert leitura.ajuste_confianca < 0

    def test_com_candles_retorna_leitura_completa(self):
        candles = _candles_alta(20)
        leitura = self.leitor.ler(candles, self.decisao, self.guardian, atr=200.0)
        assert isinstance(leitura, LeituraOperador)
        assert leitura.fase_sessao in (
            FASE_ABERTURA,
            FASE_MANHA,
            FASE_ALMOCO,
            FASE_TARDE,
            FASE_FECHAMENTO,
        )
        assert isinstance(leitura.timestamp, str)
        assert isinstance(leitura.resumo, str)
        assert isinstance(leitura.ajuste_confianca, float)

    def test_range_pts_calculado(self):
        candles = [
            _candle(100_000, 100_200, h=100_300, l=99_900),
            _candle(100_200, 100_400, h=100_500, l=100_100),
        ]
        leitura = self.leitor.ler(candles, self.decisao, self.guardian, atr=200.0)
        # max high = 100_500, min low = 99_900 → range = 600
        assert leitura.range_pts == pytest.approx(600.0)

    def test_guardian_kill_switch_detectado(self):
        self.guardian.active_kill_switch = True
        candles = _candles_alta(10)
        leitura = self.leitor.ler(candles, self.decisao, self.guardian)
        assert leitura.cenario_mudou is True

    def test_macro_items_aceitos(self):
        candles = _candles_alta(10)
        items = [
            {"category": "DOLAR_CAMBIO", "symbol": "DOLAR", "score": "-2"},
            {"category": "INDICES_GLOBAIS", "symbol": "SP500", "score": "2"},
        ]
        leitura = self.leitor.ler(
            candles, self.decisao, self.guardian, macro_items=items
        )
        assert isinstance(leitura, LeituraOperador)

    def test_desvio_vwap_positivo(self):
        # Todos candles com preco tipico em 100_000 e ultimo fechamento 100_500
        candles = [_candle(100_000, 100_000, h=100_100, l=99_900)] * 9
        candles.append(_candle(100_400, 100_500, h=100_600, l=100_400))
        leitura = self.leitor.ler(candles, self.decisao, self.guardian, atr=200.0)
        assert leitura.desvio_vwap_pts > 0

    def test_range_expandindo_verdadeiro(self):
        # Primeiros candles pequenos, ultimos grandes
        candles = []
        for i in range(5):
            candles.append(
                _candle(
                    100_000 + i * 10,
                    100_050 + i * 10,
                    h=100_060 + i * 10,
                    l=99_990 + i * 10,
                )
            )
        for i in range(5):
            candles.append(
                _candle(
                    100_050 + i * 300,
                    100_350 + i * 300,
                    h=100_400 + i * 300,
                    l=100_000 + i * 300,
                )
            )
        leitura = self.leitor.ler(candles, self.decisao, self.guardian, atr=200.0)
        assert leitura.range_expandindo is True
