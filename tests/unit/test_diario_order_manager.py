"""
Testes unitarios para DiarioOrderManager v2 (autonomo).

Cobre:
- DiarioPosicaoStatus: abertura, fechamento, atualizacao de preco
- calcular_atr / calcular_momentum
- DiarioOrderManager.consolidar_sinal: todos os caminhos de bloqueio
- DiarioOrderManager._deve_fechar_por_reversao: criterios 1 e 2
- DiarioOrderManager.ciclo: posicao aberta, nova entrada, bloqueios
"""

from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch
import json
import pytest

from src.application.diario_order_manager import (
    CONFIANCA_MINIMA,
    CONFIANCA_MINIMA_CAUTELOSA,
    ALINHAMENTO_MINIMO,
    MAGIC_NUMBER,
    ATR_MINIMO,
    REVERSAO_ATR_MULT,
    REVERSAO_PCT_GANHO,
    SL_ATR_MULT,
    TP_ATR_MULT,
    calcular_atr,
    calcular_momentum,
    DiarioPosicao,
    DiarioPosicaoStatus,
    DiarioOrderManager,
    SinalDiario,
)


# ────────────────────────────────────────────────────────────────
# Helpers / Fakes
# ────────────────────────────────────────────────────────────────


def _fake_candle(open_: float, high: float, low: float, close: float) -> MagicMock:
    c = MagicMock()
    c.open.value = open_
    c.high.value = high
    c.low.value = low
    c.close.value = close
    return c


def _candles_simples(
    n: int = 20, preco_base: float = 100000.0, atr_pts: float = 200.0
) -> list:
    """Cria n candles com ATR aproximado de atr_pts."""
    candles = []
    for i in range(n):
        p = preco_base + i * 10
        candles.append(_fake_candle(p, p + atr_pts * 0.6, p - atr_pts * 0.4, p + 5))
    return candles


def _fake_decisao(
    action: str = "BUY",
    confidence: float = 0.80,
    alignment: float = 0.70,
    macro_bias: str = "BULLISH",
) -> MagicMock:
    d = MagicMock()
    d.action.value = action
    d.confidence = confidence
    d.alignment_score = alignment
    d.macro_bias = macro_bias
    d.technical_bias = "BULLISH"
    d.sentiment_bias = "NEUTRO"
    return d


def _fake_guardian(
    kill_switch: bool = False, bias_override: str = "", penalty: float = 0.0
) -> MagicMock:
    g = MagicMock()
    g.active_kill_switch = kill_switch
    g.bias_override = bias_override
    g.confidence_penalty = penalty
    g.kill_switch_reason = "teste_kill" if kill_switch else ""
    return g


def _configure_live_market_data(
    mt5: MagicMock,
    *,
    petr_open: float = 100.0,
    petr_current: float = 100.2,
    vale_open: float = 50.0,
    vale_current: float = 50.1,
    dol_open: float = 5.215,
    dol_current: float = 5.215,
    ewz_open: float = 30.0,
    ewz_current: float = 30.05,
    ibov_open: float = 100000.0,
    ibov_current: float = 100150.0,
) -> None:
    symbol_data = {
        "PETR4": {"open": petr_open, "current": petr_current},
        "VALE3": {"open": vale_open, "current": vale_current},
        "WDO$N": {"open": dol_open, "current": dol_current},
        "EWZ": {"open": ewz_open, "current": ewz_current},
        "IBOV": {"open": ibov_open, "current": ibov_current},
    }

    def _tick(symbol: str):
        data = symbol_data.get(symbol)
        if data is None:
            return None
        tick = MagicMock()
        tick.last.value = data["current"]
        return tick

    def _daily(symbol: str):
        data = symbol_data.get(symbol)
        if data is None:
            return None
        candle = MagicMock()
        candle.open.value = data["open"]
        return candle

    mt5.select_symbol.return_value = True
    mt5.get_symbol_info_tick.side_effect = _tick
    mt5.get_daily_candle.side_effect = _daily


def _make_manager(
    tmp_path: Path,
    rewards: list = None,
    confidence_override_path: Path | None = None,
) -> DiarioOrderManager:
    mt5 = MagicMock()
    mt5.get_positions.return_value = []
    mt5.send_order.return_value = "999001"
    mt5.close_position_by_ticket.return_value = True
    _configure_live_market_data(mt5)

    db_path = str(tmp_path / "trading.db")
    session_id = "test_session_001"

    manager = DiarioOrderManager.__new__(DiarioOrderManager)
    manager._mt5 = mt5
    manager._db_path = db_path
    manager._session_id = session_id
    manager._posicao = DiarioPosicaoStatus(session_id, str(tmp_path))
    manager._n_ciclos = 0
    manager._ultimo_sinal = None
    manager._ultimo_snapshot_intraday = None

    rl_reader = MagicMock()
    rl_reader.get_today_rewards.return_value = rewards or []
    rl_reader.get_today_episodes.return_value = []
    manager._rl_reader = rl_reader

    # Mocks para leitura e episodios (adicionados em v3)
    leitor = MagicMock()
    leitura_mock = MagicMock()
    leitura_mock.ajuste_confianca = 0.0
    leitura_mock.divergencia_critica = False
    leitura_mock.risco_armadilha = "BAIXA"
    leitura_mock.direcao_preferida = "NEUTRO"  # sem penalidade de divergencia
    leitor.ler.return_value = leitura_mock
    manager._leitor = leitor

    ep_repo = MagicMock()
    ep_repo.salvar.return_value = None
    manager._ep_repo = ep_repo

    aprendizado = MagicMock()
    contexto_mock = MagicMock()
    contexto_mock.ajuste_fase_almoco = 0.0
    contexto_mock.ajuste_exaustao = 0.0
    contexto_mock.ajuste_armadilha_alta = 0.0
    contexto_mock.ajuste_divergencia = 0.0
    aprendizado.calcular_contexto.return_value = contexto_mock
    manager._aprendizado = aprendizado

    manager._sinal_abertura = None
    manager._ultimo_neutro_registrado = 0
    manager._candles_no_neutro = None
    manager._opening_context_raw = {}
    manager._opening_context = {}
    manager._latest_market_features_path = (
        Path(tmp_path) / "outputs" / "analysis" / "diario_market_features_latest.json"
    )
    if confidence_override_path is not None:
        manager._confidence_override_path = confidence_override_path

    return manager


# ────────────────────────────────────────────────────────────────
# calcular_atr / calcular_momentum
# ────────────────────────────────────────────────────────────────


class TestCalcularAtr:
    def test_atr_calculado_corretamente(self):
        # 15 candles com TR fixo de 200 pts
        candles = [_fake_candle(100000, 100200, 100000, 100100) for _ in range(16)]
        atr = calcular_atr(candles, periodo=14)
        assert atr == pytest.approx(200.0, abs=1.0)

    def test_atr_retorna_minimo_se_poucos_candles(self):
        candles = [_fake_candle(100000, 100050, 99950, 100000) for _ in range(5)]
        atr = calcular_atr(candles)
        assert atr == float(ATR_MINIMO)

    def test_atr_limitado_ao_maximo(self):
        # TR enorme
        candles = [_fake_candle(100000, 105000, 95000, 100000) for _ in range(20)]
        from src.application.diario_order_manager import ATR_MAXIMO

        atr = calcular_atr(candles)
        assert atr <= float(ATR_MAXIMO)

    def test_atr_nao_abaixo_do_minimo(self):
        # TR minusculo
        candles = [_fake_candle(100000, 100001, 99999, 100000) for _ in range(20)]
        atr = calcular_atr(candles)
        assert atr >= float(ATR_MINIMO)


class TestCalcularMomentum:
    def test_momentum_positivo_em_alta(self):
        candles = _candles_simples(n=10, preco_base=100000.0)
        # Ultimo close > 5 velas atras
        mom = calcular_momentum(candles, janela=5)
        assert mom > 0

    def test_momentum_negativo_em_baixa(self):
        candles = list(reversed(_candles_simples(n=10, preco_base=100000.0)))
        mom = calcular_momentum(candles, janela=5)
        assert mom < 0

    def test_momentum_zero_sem_dados(self):
        mom = calcular_momentum([], janela=5)
        assert mom == 0.0

    def test_momentum_zero_poucos_candles(self):
        candles = _candles_simples(n=3)
        mom = calcular_momentum(candles, janela=5)
        assert mom == 0.0


# ────────────────────────────────────────────────────────────────
# DiarioPosicao: serialização
# ────────────────────────────────────────────────────────────────


class TestDiarioPosicao:
    def test_to_dict_campos_obrigatorios(self):
        pos = DiarioPosicao(
            aberta=True,
            ticket=123,
            direcao="BUY",
            preco_entrada=100000.0,
            sl=99700.0,
            tp=100500.0,
            atr_entrada=200.0,
        )
        d = pos.to_dict()
        assert d["aberta"] is True
        assert d["ticket"] == 123
        assert d["atr_entrada"] == 200.0

    def test_from_dict_round_trip(self):
        original = DiarioPosicao(
            aberta=True,
            ticket=456,
            direcao="SELL",
            preco_entrada=99000.0,
            sl=99300.0,
            tp=98400.0,
            atr_entrada=180.0,
            max_ganho_pts=150.0,
        )
        recuperado = DiarioPosicao.from_dict(original.to_dict())
        assert recuperado.direcao == "SELL"
        assert recuperado.atr_entrada == 180.0
        assert recuperado.max_ganho_pts == 150.0

    def test_from_dict_valores_padrao(self):
        pos = DiarioPosicao.from_dict({})
        assert pos.aberta is False
        assert pos.atr_entrada == 0.0


# ────────────────────────────────────────────────────────────────
# DiarioPosicaoStatus
# ────────────────────────────────────────────────────────────────


class TestDiarioPosicaoStatus:
    def test_registrar_abertura_persiste_json(self, tmp_path):
        st = DiarioPosicaoStatus("sess1", str(tmp_path))
        st.registrar_abertura(
            ticket=1001,
            direcao="BUY",
            preco_entrada=100000.0,
            sl=99700.0,
            tp=100500.0,
            atr_entrada=200.0,
        )
        assert st.tem_posicao_aberta()
        json_path = tmp_path / "agente_posicao_diarios_sess1.json"
        assert json_path.exists()
        dados = json.loads(json_path.read_text())
        assert dados["atr_entrada"] == 200.0

    def test_registrar_fechamento(self, tmp_path):
        st = DiarioPosicaoStatus("sess2", str(tmp_path))
        st.registrar_abertura(
            ticket=2001, direcao="SELL", preco_entrada=99000.0, sl=99300.0, tp=98400.0
        )
        st.registrar_fechamento("teste")
        assert not st.tem_posicao_aberta()

    def test_atualizar_preco_max_ganho_buy(self, tmp_path):
        st = DiarioPosicaoStatus("sess3", str(tmp_path))
        st.registrar_abertura(
            ticket=3001, direcao="BUY", preco_entrada=100000.0, sl=99700.0, tp=100500.0
        )
        st.atualizar_preco(100250.0)
        assert st.posicao.max_ganho_pts == pytest.approx(250.0)

    def test_atualizar_preco_max_ganho_sell(self, tmp_path):
        st = DiarioPosicaoStatus("sess4", str(tmp_path))
        st.registrar_abertura(
            ticket=4001, direcao="SELL", preco_entrada=100000.0, sl=100300.0, tp=99400.0
        )
        st.atualizar_preco(99700.0)
        assert st.posicao.max_ganho_pts == pytest.approx(300.0)

    def test_max_ganho_nao_reduz(self, tmp_path):
        st = DiarioPosicaoStatus("sess5", str(tmp_path))
        st.registrar_abertura(
            ticket=5001, direcao="BUY", preco_entrada=100000.0, sl=99700.0, tp=100500.0
        )
        st.atualizar_preco(100300.0)
        st.atualizar_preco(100100.0)
        assert st.posicao.max_ganho_pts == pytest.approx(300.0)

    def test_recarregar_do_arquivo(self, tmp_path):
        st = DiarioPosicaoStatus("sess6", str(tmp_path))
        st.registrar_abertura(
            ticket=6001,
            direcao="BUY",
            preco_entrada=100000.0,
            sl=99700.0,
            tp=100500.0,
            atr_entrada=200.0,
        )
        st2 = DiarioPosicaoStatus("sess6", str(tmp_path))
        assert st2.posicao.atr_entrada == 200.0


# ────────────────────────────────────────────────────────────────
# _deve_fechar_por_reversao
# ────────────────────────────────────────────────────────────────


class TestDeveFecharPorReversao:
    def _atr_entrada(self) -> float:
        return 200.0

    def _limite_reversao(self) -> float:
        return self._atr_entrada() * REVERSAO_ATR_MULT

    def test_reversao_absoluta_buy(self, tmp_path):
        mgr = _make_manager(tmp_path)
        atr = self._atr_entrada()
        mgr._posicao.registrar_abertura(
            ticket=1,
            direcao="BUY",
            preco_entrada=100000.0,
            sl=99700.0,
            tp=100500.0,
            atr_entrada=atr,
        )
        mgr._posicao.atualizar_preco(100200.0)
        preco_reversao = 100200.0 - self._limite_reversao() - 1
        deve, motivo = mgr._deve_fechar_por_reversao(preco_reversao)
        assert deve is True
        assert "reversao" in motivo

    def test_reversao_absoluta_sell(self, tmp_path):
        mgr = _make_manager(tmp_path)
        atr = self._atr_entrada()
        mgr._posicao.registrar_abertura(
            ticket=2,
            direcao="SELL",
            preco_entrada=100000.0,
            sl=100300.0,
            tp=99400.0,
            atr_entrada=atr,
        )
        mgr._posicao.atualizar_preco(99800.0)
        preco_reversao = 99800.0 + self._limite_reversao() + 1
        deve, motivo = mgr._deve_fechar_por_reversao(preco_reversao)
        assert deve is True

    def test_sem_reversao_movimento_pequeno(self, tmp_path):
        mgr = _make_manager(tmp_path)
        atr = self._atr_entrada()
        limite = self._limite_reversao()  # 1.2 * 200 = 240
        mgr._posicao.registrar_abertura(
            ticket=3,
            direcao="BUY",
            preco_entrada=100000.0,
            sl=99700.0,
            tp=100500.0,
            atr_entrada=atr,
        )
        mgr._posicao.atualizar_preco(100200.0)
        # Recuo de apenas 50 pts (< 240 → nao aciona criterio 1)
        # max_ganho=200 >= 0.8*200=160 → criterio 2 pode ativar
        # ganho_atual = 100170 - 100000 = 170, devolvido = 200-170=30 < 120 → nao ativa
        preco_pequeno = 100170.0
        deve, _ = mgr._deve_fechar_por_reversao(preco_pequeno)
        assert deve is False

    def test_devolucao_ganho_maximo(self, tmp_path):
        """Devolucao de 60% do ganho maximo ativa fechamento."""
        mgr = _make_manager(tmp_path)
        atr = 200.0
        mgr._posicao.registrar_abertura(
            ticket=4,
            direcao="BUY",
            preco_entrada=100000.0,
            sl=99700.0,
            tp=100500.0,
            atr_entrada=atr,
        )
        # Ganho maximo de 400 pts (> 0.8 * 200 = 160)
        mgr._posicao.atualizar_preco(100400.0)
        # Recuar para max_ganho ainda sendo 400 mas ultimo_preco = 100200
        mgr._posicao.atualizar_preco(100200.0)

        # Agora: ultimo=100200, max_ganho=400
        # move_contra = 100200 - preco_teste → deve ser < limite (240)
        # devolucao = 400 - (preco_teste - 100000)
        # Para ativar: devolucao >= 400 * 0.60 = 240
        #   => ganho_atual <= 160 => preco <= 100160
        # Para NAO ativar criterio 1: move_contra < 240 (limite ATR=1.2*200)
        #   => 100200 - preco < 240 => preco > 99960
        # Usar preco=100150: move_contra=50 < 240 ✓, devolucao=250 >= 240 ✓
        deve, motivo = mgr._deve_fechar_por_reversao(100150.0)
        assert deve is True
        assert "devolucao" in motivo

    def test_sem_posicao_nao_fecha(self, tmp_path):
        mgr = _make_manager(tmp_path)
        deve, _ = mgr._deve_fechar_por_reversao(100000.0)
        assert deve is False

    def test_ganho_pequeno_nao_aciona_devolucao(self, tmp_path):
        """Ganho abaixo de 0.8*ATR nao ativa criterio de devolucao."""
        mgr = _make_manager(tmp_path)
        atr = 200.0
        mgr._posicao.registrar_abertura(
            ticket=5,
            direcao="BUY",
            preco_entrada=100000.0,
            sl=99700.0,
            tp=100500.0,
            atr_entrada=atr,
        )
        # Ganho maximo de 100 pts (< 0.8*200=160 → abaixo do limiar)
        mgr._posicao.atualizar_preco(100100.0)
        # Preco volta para a entrada: ganho_atual=0, devolvido=100
        # Mas nao deve acionar pois ganho_max < limiar
        deve, _ = mgr._deve_fechar_por_reversao(100000.0)
        assert deve is False


# ────────────────────────────────────────────────────────────────
# consolidar_sinal
# ────────────────────────────────────────────────────────────────


class TestConsolidarSinal:
    def test_sinal_valido_pode_operar(self, tmp_path):
        mgr = _make_manager(tmp_path)
        candles = _candles_simples(n=20, atr_pts=200.0)
        decisao = _fake_decisao("BUY", confidence=0.80, alignment=0.72)
        guardian = _fake_guardian()

        with patch.object(mgr, "_no_pregao", return_value=True):
            sinal = mgr.consolidar_sinal(decisao, candles, guardian)

        assert sinal.pode_operar is True
        assert sinal.direcao == "BUY"
        assert sinal.sl < sinal.preco_atual  # SL abaixo para BUY
        assert sinal.tp > sinal.preco_atual  # TP acima para BUY

    def test_sl_tp_calculados_por_atr(self, tmp_path):
        mgr = _make_manager(tmp_path)
        candles = _candles_simples(n=20, atr_pts=200.0)
        decisao = _fake_decisao("BUY", confidence=0.80, alignment=0.72)
        guardian = _fake_guardian()

        with patch.object(mgr, "_no_pregao", return_value=True):
            sinal = mgr.consolidar_sinal(decisao, candles, guardian)

        atr = sinal.atr
        # SL deve ser ~1.5*ATR abaixo e TP ~2.5*ATR acima
        assert abs((sinal.preco_atual - sinal.sl) - atr * SL_ATR_MULT) < 10
        assert abs((sinal.tp - sinal.preco_atual) - atr * TP_ATR_MULT) < 10

    def test_sl_tp_sell_invertidos(self, tmp_path):
        mgr = _make_manager(tmp_path)
        candles = _candles_simples(n=20, atr_pts=200.0)
        decisao = _fake_decisao("SELL", confidence=0.80, alignment=0.72)
        guardian = _fake_guardian()

        with patch.object(mgr, "_no_pregao", return_value=True):
            sinal = mgr.consolidar_sinal(decisao, candles, guardian)

        assert sinal.sl > sinal.preco_atual  # SL acima para SELL
        assert sinal.tp < sinal.preco_atual  # TP abaixo para SELL

    def test_bloqueio_kill_switch(self, tmp_path):
        mgr = _make_manager(tmp_path)
        candles = _candles_simples()
        decisao = _fake_decisao("BUY")
        guardian = _fake_guardian(kill_switch=True)

        with patch.object(mgr, "_no_pregao", return_value=True):
            sinal = mgr.consolidar_sinal(decisao, candles, guardian)

        assert sinal.pode_operar is False
        assert sinal.direcao == "NEUTRO"
        assert "kill_switch" in sinal.motivo_bloqueio

    def test_bloqueio_fora_do_pregao(self, tmp_path):
        mgr = _make_manager(tmp_path)
        candles = _candles_simples()
        decisao = _fake_decisao("BUY", confidence=0.90, alignment=0.80)
        guardian = _fake_guardian()

        with patch.object(mgr, "_no_pregao", return_value=False):
            sinal = mgr.consolidar_sinal(decisao, candles, guardian)

        assert sinal.pode_operar is False
        assert "pregao" in sinal.motivo_bloqueio

    def test_bloqueio_alinhamento_baixo(self, tmp_path):
        mgr = _make_manager(tmp_path)
        candles = _candles_simples()
        decisao = _fake_decisao("BUY", confidence=0.85, alignment=0.40)
        guardian = _fake_guardian()

        with patch.object(mgr, "_no_pregao", return_value=True):
            sinal = mgr.consolidar_sinal(decisao, candles, guardian)

        assert sinal.pode_operar is False
        assert "alinhamento" in sinal.motivo_bloqueio

    def test_bloqueio_confianca_baixa(self, tmp_path):
        mgr = _make_manager(tmp_path)
        candles = _candles_simples()
        decisao = _fake_decisao("BUY", confidence=0.30, alignment=0.75)
        guardian = _fake_guardian()

        with patch.object(mgr, "_no_pregao", return_value=True):
            sinal = mgr.consolidar_sinal(decisao, candles, guardian)

        assert sinal.pode_operar is False
        assert "confianca" in sinal.motivo_bloqueio

    def test_bloqueio_trend_follow_baixa_confianca(self, tmp_path):
        mgr = _make_manager(tmp_path)
        candles = _candles_simples()
        decisao = _fake_decisao("NEUTRO", confidence=0.07, alignment=0.82)
        guardian = _fake_guardian()

        leitura_mock = MagicMock()
        leitura_mock.ajuste_confianca = -0.22
        leitura_mock.divergencia_critica = False
        leitura_mock.risco_armadilha = "MEDIA"
        leitura_mock.direcao_preferida = "SELL"
        leitura_mock.pullback_saudavel = True
        leitura_mock.resumo = "Pullback saudavel: entrada na direcao da tendencia"
        leitura_mock.armadilhas = []
        mgr._leitor.ler.return_value = leitura_mock

        with patch.object(mgr, "_no_pregao", return_value=True):
            sinal = mgr.consolidar_sinal(decisao, candles, guardian)

        assert sinal.pode_operar is False
        assert sinal.motivo_bloqueio.startswith("trend_follow_baixa_confianca:")
        assert "direcao_neutro" not in sinal.motivo_bloqueio

    def test_gatilho_diario_de_confianca_usa_override_cauteloso(self, tmp_path):
        override_path = tmp_path / "confidence_override_today.json"
        override_path.write_text(
            json.dumps(
                {
                    "confidence_current": 0.32,
                }
            ),
            encoding="utf-8",
        )

        mgr = _make_manager(
            tmp_path,
            confidence_override_path=override_path,
        )

        assert mgr._confidence_gate_minima() == pytest.approx(
            CONFIANCA_MINIMA_CAUTELOSA
        )

    def test_bloqueio_hold(self, tmp_path):
        mgr = _make_manager(tmp_path)
        candles = _candles_simples()
        decisao = _fake_decisao("HOLD", confidence=0.85, alignment=0.80)
        guardian = _fake_guardian()

        with patch.object(mgr, "_no_pregao", return_value=True):
            sinal = mgr.consolidar_sinal(decisao, candles, guardian)

        assert sinal.direcao == "NEUTRO"
        assert sinal.pode_operar is False

    def test_guardian_bias_contra_inverte(self, tmp_path):
        mgr = _make_manager(tmp_path)
        candles = _candles_simples()
        decisao = _fake_decisao("BUY", confidence=0.80, alignment=0.72)
        guardian = _fake_guardian(bias_override="CONTRA")

        with patch.object(mgr, "_no_pregao", return_value=True):
            sinal = mgr.consolidar_sinal(decisao, candles, guardian)

        assert sinal.direcao == "SELL"

    def test_contexto_abertura_bloqueia_buy_contra_vies_baixista(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr._opening_context = {
            "vies_intraday": "NEUTRO_LEVEMENTE_BAIXISTA",
            "watchlist": ["PETR4", "VALE3", "DOL"],
        }
        candles = _candles_simples()
        decisao = _fake_decisao("BUY", confidence=0.68, alignment=0.62)
        guardian = _fake_guardian()

        with patch.object(mgr, "_no_pregao", return_value=True):
            sinal = mgr.consolidar_sinal(decisao, candles, guardian)

        assert sinal.pode_operar is False
        assert "contexto_abertura" in sinal.motivo_bloqueio
        assert "vies_intraday_baixista" in sinal.contexto_flags

    def test_confirmacao_live_bloqueia_compra_sem_petr_vale_dol_ewz_ibov(
        self, tmp_path
    ):
        mgr = _make_manager(tmp_path)
        _configure_live_market_data(
            mgr._mt5,
            petr_current=99.9,
            vale_current=49.9,
            dol_current=5.24,
            ewz_current=29.90,
            ibov_current=99850.0,
        )
        mgr._opening_context = {
            "vies_intraday": "NEUTRO",
            "watchlist": ["PETR4", "VALE3", "DOL", "EWZ", "IBOV"],
            "contexto_operacional": {
                "rates_fx": {"fx_reference_band": [5.21, 5.22]},
            },
        }
        candles = _candles_simples()
        decisao = _fake_decisao("BUY", confidence=0.85, alignment=0.80)
        guardian = _fake_guardian()

        with patch.object(mgr, "_no_pregao", return_value=True):
            sinal = mgr.consolidar_sinal(decisao, candles, guardian)

        assert sinal.pode_operar is False
        assert "compra_sem_confirmacao_live" in sinal.contexto_flags
        assert sinal.confirmacao_live["monitors_negative"] == ["EWZ", "IBOV"]

    def test_penalidade_guardian_reduz_confianca(self, tmp_path):
        mgr = _make_manager(tmp_path)
        candles = _candles_simples()
        # Confianca base de 0.68 com penalidade 10 pts = -0.10 → 0.58 < limiar
        decisao = _fake_decisao("BUY", confidence=0.68, alignment=0.75)
        guardian = _fake_guardian(penalty=10.0)

        with patch.object(mgr, "_no_pregao", return_value=True):
            sinal = mgr.consolidar_sinal(decisao, candles, guardian)

        assert sinal.confianca < CONFIANCA_MINIMA

    def test_win_rate_alto_aumenta_confianca(self, tmp_path):
        # 10 acertos em 10 avaliados (100% wr) → bonus +0.08
        rewards = [{"is_evaluated": 1, "was_correct": 1}] * 10
        mgr = _make_manager(tmp_path, rewards=rewards)
        candles = _candles_simples()
        # Confianca base levemente abaixo do limiar
        decisao = _fake_decisao(
            "BUY", confidence=CONFIANCA_MINIMA - 0.06, alignment=0.75
        )
        guardian = _fake_guardian()

        with patch.object(mgr, "_no_pregao", return_value=True):
            sinal = mgr.consolidar_sinal(decisao, candles, guardian)

        assert sinal.confianca >= CONFIANCA_MINIMA

    def test_win_rate_baixo_penaliza_confianca(self, tmp_path):
        # 2 acertos em 10 (20% wr) → penalidade -0.12
        rewards = [{"is_evaluated": 1, "was_correct": 1}] * 2 + [
            {"is_evaluated": 1, "was_correct": 0}
        ] * 8
        mgr = _make_manager(tmp_path, rewards=rewards)
        candles = _candles_simples()
        decisao = _fake_decisao("BUY", confidence=0.70, alignment=0.75)
        guardian = _fake_guardian()

        with patch.object(mgr, "_no_pregao", return_value=True):
            sinal = mgr.consolidar_sinal(decisao, candles, guardian)

        # 0.70 - 0.12 = 0.58 < 0.60
        assert sinal.confianca < CONFIANCA_MINIMA
        assert sinal.pode_operar is False

    def test_momentum_contraditorio_penaliza(self, tmp_path):
        """Momentum forte contra a direcao reduz confianca."""
        mgr = _make_manager(tmp_path)
        # Candles em queda forte (momentum muito negativo)
        candles = list(reversed(_candles_simples(n=20, atr_pts=200.0)))
        decisao = _fake_decisao("BUY", confidence=0.68, alignment=0.72)
        guardian = _fake_guardian()

        with patch.object(mgr, "_no_pregao", return_value=True):
            sinal = mgr.consolidar_sinal(decisao, candles, guardian)

        # Momentum negativo forte deve ter reduzido a confianca
        assert sinal.momentum < 0


# ────────────────────────────────────────────────────────────────
# ciclo completo
# ────────────────────────────────────────────────────────────────


class TestCiclo:
    def test_ciclo_abre_posicao(self, tmp_path):
        mgr = _make_manager(tmp_path)
        candles = _candles_simples(n=20, atr_pts=200.0)
        decisao = _fake_decisao("BUY", confidence=0.80, alignment=0.75)
        guardian = _fake_guardian()

        with patch.object(mgr, "_no_pregao", return_value=True):
            resultado = mgr.ciclo(decisao, candles, guardian)

        assert resultado["acao"] == "ORDEM_ENVIADA"
        assert resultado["posicao_aberta"] is True
        mgr._mt5.send_order.assert_called_once()

    def test_ciclo_sell_abre_correto(self, tmp_path):
        mgr = _make_manager(tmp_path)
        candles = _candles_simples(n=20, atr_pts=200.0)
        decisao = _fake_decisao("SELL", confidence=0.80, alignment=0.75)
        guardian = _fake_guardian()

        with patch.object(mgr, "_no_pregao", return_value=True):
            resultado = mgr.ciclo(decisao, candles, guardian)

        assert resultado["acao"] == "ORDEM_ENVIADA"
        pos = mgr._posicao.posicao
        assert pos.direcao == "SELL"
        assert pos.sl > pos.preco_entrada  # SL acima para SELL

    def test_ciclo_bloqueado_fora_pregao(self, tmp_path):
        mgr = _make_manager(tmp_path)
        candles = _candles_simples()
        decisao = _fake_decisao("BUY", confidence=0.90, alignment=0.80)
        guardian = _fake_guardian()

        with patch.object(mgr, "_no_pregao", return_value=False):
            resultado = mgr.ciclo(decisao, candles, guardian)

        assert resultado["acao"] == "BLOQUEADO"
        mgr._mt5.send_order.assert_not_called()

    def test_ciclo_publica_snapshot_intraday_mesmo_bloqueado(self, tmp_path):
        mgr = _make_manager(tmp_path)
        candles = _candles_simples()
        decisao = _fake_decisao("BUY", confidence=0.90, alignment=0.80)
        guardian = _fake_guardian()

        with patch.object(mgr, "_no_pregao", return_value=False):
            resultado = mgr.ciclo(decisao, candles, guardian)

        snapshot = resultado["diario_market_features"]
        assert snapshot is not None
        assert snapshot["session_id"] == "test_session_001"
        assert snapshot["symbol"] == "WIN$N"
        assert snapshot["macro_regime"] == ""
        assert mgr._latest_market_features_path.exists()

    def test_ciclo_monitora_posicao_aberta(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr._posicao.registrar_abertura(
            ticket=7001,
            direcao="BUY",
            preco_entrada=100000.0,
            sl=99700.0,
            tp=100500.0,
            atr_entrada=200.0,
        )
        # MT5 retorna posicao aberta
        mgr._mt5.get_positions.return_value = [
            {"ticket": 7001, "magic": MAGIC_NUMBER, "price_current": 100050.0}
        ]
        candles = _candles_simples()
        decisao = _fake_decisao("BUY")
        guardian = _fake_guardian()

        with patch.object(mgr, "_no_pregao", return_value=True):
            resultado = mgr.ciclo(decisao, candles, guardian)

        assert resultado["acao"] == "MONITORANDO"
        assert resultado["posicao_aberta"] is True
        mgr._mt5.send_order.assert_not_called()

    def test_ciclo_detecta_fechamento_mt5(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr._posicao.registrar_abertura(
            ticket=8001,
            direcao="BUY",
            preco_entrada=100000.0,
            sl=99700.0,
            tp=100500.0,
            atr_entrada=200.0,
        )
        mgr._mt5.get_positions.return_value = []  # MT5 ja fechou

        candles = _candles_simples()
        decisao = _fake_decisao("BUY")
        guardian = _fake_guardian()

        with patch.object(mgr, "_no_pregao", return_value=True):
            resultado = mgr.ciclo(decisao, candles, guardian)

        assert resultado["acao"] == "POSICAO_FECHADA_MT5"
        assert not mgr._posicao.tem_posicao_aberta()

    def test_ciclo_fecha_por_reversao(self, tmp_path):
        mgr = _make_manager(tmp_path)
        atr = 200.0
        mgr._posicao.registrar_abertura(
            ticket=9001,
            direcao="BUY",
            preco_entrada=100000.0,
            sl=99700.0,
            tp=100500.0,
            atr_entrada=atr,
        )
        mgr._posicao.atualizar_preco(100300.0)

        # Preco reverteu > 1.2*200=240 desde ultimo (100300)
        preco_reversao = 100300.0 - atr * REVERSAO_ATR_MULT - 1
        mgr._mt5.get_positions.return_value = [
            {"ticket": 9001, "magic": MAGIC_NUMBER, "price_current": preco_reversao}
        ]

        candles = _candles_simples()
        decisao = _fake_decisao("BUY")
        guardian = _fake_guardian()

        with patch.object(mgr, "_no_pregao", return_value=True):
            resultado = mgr.ciclo(decisao, candles, guardian)

        assert resultado["acao"] == "FECHAMENTO_REVERSAO"
        mgr._mt5.close_position_by_ticket.assert_called_with(9001)

    def test_ciclo_fecha_por_guardian(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr._posicao.registrar_abertura(
            ticket=10001,
            direcao="BUY",
            preco_entrada=100000.0,
            sl=99700.0,
            tp=100500.0,
            atr_entrada=200.0,
        )
        mgr._mt5.get_positions.return_value = [
            {"ticket": 10001, "magic": MAGIC_NUMBER, "price_current": 100050.0}
        ]

        candles = _candles_simples()
        decisao = _fake_decisao("BUY")
        guardian = _fake_guardian(kill_switch=True)

        with patch.object(mgr, "_no_pregao", return_value=True):
            resultado = mgr.ciclo(decisao, candles, guardian)

        assert resultado["acao"] == "FECHAMENTO_GUARDIAN"
        mgr._mt5.close_position_by_ticket.assert_called_with(10001)

    def test_ciclo_incrementa_contador(self, tmp_path):
        mgr = _make_manager(tmp_path)
        candles = _candles_simples()
        decisao = _fake_decisao("HOLD")
        guardian = _fake_guardian()

        with patch.object(mgr, "_no_pregao", return_value=True):
            mgr.ciclo(decisao, candles, guardian)
            mgr.ciclo(decisao, candles, guardian)

        assert mgr._n_ciclos == 2
