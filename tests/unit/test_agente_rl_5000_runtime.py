"""Testes do runtime RL 5000 aderente ao PRD."""

from __future__ import annotations

import importlib
import sys
from datetime import datetime, time as dtime, timedelta
from types import SimpleNamespace

import pandas as pd
import pytest


MODULE_NAME = "scripts.operar_novo_agente_rl_real_antiovertrading"


def _load_module():
    sys.modules.pop(MODULE_NAME, None)
    return importlib.import_module(MODULE_NAME)


def _dados_validos(n: int = 40) -> pd.DataFrame:
    base = 100000.0
    linhas: list[dict[str, float | int]] = []
    for i in range(n):
        preco = base + (i * 5.0)
        linhas.append(
            {
                "open": preco,
                "high": preco + 10.0,
                "low": preco - 10.0,
                "close": preco + 2.0,
                "volume": 1500 + i,
            }
        )
    return pd.DataFrame(linhas)


def test_import_safe_com_debug_release(monkeypatch: pytest.MonkeyPatch) -> None:
    """O módulo deve importar sem instanciar config nem motor no import."""
    monkeypatch.setenv("DEBUG", "release")

    mod = _load_module()

    assert mod.config is None
    assert mod.motor_isolado is None


def test_janelas_operacionais_respeitam_monitoramento_e_corte_de_entrada() -> None:
    mod = _load_module()

    assert mod.verificar_horario_trading(dtime(9, 0)) is True
    assert mod.verificar_horario_trading(dtime(17, 55)) is True
    assert mod.verificar_horario_trading(dtime(17, 56)) is False

    assert mod.verificar_janela_novas_entradas(dtime(17, 25)) is True
    assert mod.verificar_janela_novas_entradas(dtime(17, 26)) is False


def test_verificar_limite_trades_aplica_maximo_do_prd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _load_module()

    monkeypatch.setattr(
        mod,
        "trades_executed_today",
        mod.AntiOvertradingConfig.MAX_TRADES_PER_SESSION,
    )

    assert mod.verificar_limite_trades() is False


def test_verificar_cooldown_pos_sl_prevalece(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _load_module()
    agora = datetime.now()

    monkeypatch.setattr(mod, "last_trade_time", agora - timedelta(minutes=10))
    monkeypatch.setattr(mod, "last_stop_loss_time", agora - timedelta(minutes=5))

    assert mod.verificar_cooldown() is False


def test_inferir_motivo_fechamento_classifica_tp_sl_e_manual() -> None:
    mod = _load_module()
    posicao_buy = SimpleNamespace(
        tipo=mod.TipoPosicao.COMPRADA,
        take_profit=100120.0,
        stop_loss=99880.0,
    )
    posicao_sell = SimpleNamespace(
        tipo=mod.TipoPosicao.VENDIDA,
        take_profit=99880.0,
        stop_loss=100120.0,
    )

    assert mod.inferir_motivo_fechamento(posicao_buy, 100130.0) == mod.MotivoFechamento.TP_ATINGIDO
    assert mod.inferir_motivo_fechamento(posicao_buy, 99870.0) == mod.MotivoFechamento.SL_ATINGIDO
    assert mod.inferir_motivo_fechamento(posicao_sell, 99990.0) == mod.MotivoFechamento.MANUAL


def test_obter_acao_do_modelo_usa_confianca_do_modelo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _load_module()

    class _AgenteFalso:
        def obter_acao_e_confianca(self, _estado, *, modo_producao: bool = True):
            assert modo_producao is True
            return 2, 0.81

    monkeypatch.setattr(mod, "pipeline", SimpleNamespace(_agente=_AgenteFalso()))

    acao, confianca = mod.obter_acao_do_modelo(_dados_validos())

    assert acao == 2
    assert confianca == pytest.approx(0.81)


def test_sl_dinamico_de_compra_usa_minima_do_setup_de_entrada() -> None:
    mod = _load_module()

    linhas: list[dict[str, float | int]] = []
    for i in range(18):
        linhas.append(
            {
                "open": 100000.0 + (i * 5.0),
                "high": 100180.0 + (i * 8.0),
                "low": 99600.0 + i,
                "close": 100010.0 + (i * 5.0),
                "volume": 2000 + i,
            }
        )
    linhas.extend(
        [
            {
                "open": 100090.0,
                "high": 100110.0,
                "low": 100060.0,
                "close": 100100.0,
                "volume": 2100,
            },
            {
                "open": 100100.0,
                "high": 100120.0,
                "low": 100070.0,
                "close": 100105.0,
                "volume": 2101,
            },
        ]
    )
    dados = pd.DataFrame(linhas)

    sl, tp = mod.calcular_sl_tp_dinamico(dados, "Comprar", 100100.0)

    assert sl == pytest.approx(
        100060.0 - mod.AntiOvertradingConfig.STOP_SETUP_BUFFER_PONTOS
    )
    assert tp == pytest.approx(
        float(dados.tail(20)["high"].max()) + mod.AntiOvertradingConfig.TARGET_BUFFER_PONTOS
    )


def test_sl_dinamico_de_venda_usa_maxima_do_setup_de_entrada() -> None:
    mod = _load_module()

    linhas: list[dict[str, float | int]] = []
    for i in range(18):
        linhas.append(
            {
                "open": 100300.0 - (i * 4.0),
                "high": 100500.0 - i,
                "low": 99800.0 - (i * 2.0),
                "close": 100280.0 - (i * 4.0),
                "volume": 2200 + i,
            }
        )
    linhas.extend(
        [
            {
                "open": 100120.0,
                "high": 100140.0,
                "low": 100080.0,
                "close": 100090.0,
                "volume": 2300,
            },
            {
                "open": 100110.0,
                "high": 100150.0,
                "low": 100060.0,
                "close": 100080.0,
                "volume": 2301,
            },
        ]
    )
    dados = pd.DataFrame(linhas)

    sl, tp = mod.calcular_sl_tp_dinamico(dados, "Vender", 100100.0)

    assert sl == pytest.approx(
        100150.0 + mod.AntiOvertradingConfig.STOP_SETUP_BUFFER_PONTOS
    )
    assert tp == pytest.approx(
        float(dados.tail(20)["low"].min()) - mod.AntiOvertradingConfig.TARGET_BUFFER_PONTOS
    )
