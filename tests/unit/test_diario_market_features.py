"""Testes unitarios para o canal intraday de features do Diario."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
import sqlite3

from src.application.diario_market_features import (
    DiarioMarketFeaturesSnapshot,
    apply_diario_soft_feature_influence,
    build_contexto_operacional_com_diario,
    calculate_exhaustion_score,
    calculate_reversal_score,
    detect_usd_flow_state,
    fetch_latest_diario_market_features_snapshot,
    load_diario_market_features_payload,
    persist_diario_market_features_snapshot,
    summarize_correlated_confirmations,
)
from src.application.services.diary_feedback import DiaryFeedback, save_diary_feedback


def _price(value: float) -> SimpleNamespace:
    return SimpleNamespace(value=value)


def _candle(open_: float, close: float, high: float | None = None, low: float | None = None):
    high_value = close if high is None else high
    low_value = close if low is None else low
    return SimpleNamespace(
        open=_price(open_),
        high=_price(high_value),
        low=_price(low_value),
        close=_price(close),
    )


def _live_confirmation(
    *,
    petr_delta: float = 0.20,
    vale_delta: float = 0.18,
    dol_delta: float = 0.25,
    dol_price: float = 5.26,
    ibov_delta: float = -0.20,
    ewz_delta: float = -0.18,
) -> dict:
    return {
        "dol_forte": dol_delta >= 0.20,
        "symbols": {
            "PETR4": {"available": True, "delta_pct": petr_delta},
            "VALE3": {"available": True, "delta_pct": vale_delta},
            "DOL": {
                "available": True,
                "delta_pct": dol_delta,
                "price_current": dol_price,
            },
            "IBOV": {"available": True, "delta_pct": ibov_delta},
            "EWZ": {"available": True, "delta_pct": ewz_delta},
        },
    }


def _sample_snapshot(timestamp: str) -> DiarioMarketFeaturesSnapshot:
    return DiarioMarketFeaturesSnapshot(
        timestamp=timestamp,
        session_id="sessao_diario",
        symbol="WIN$N",
        direction_hint="SELL",
        confidence=0.78,
        macro_regime="CAUTELOSO",
        vies_intraday="NEUTRO_LEVEMENTE_BAIXISTA",
        reversal_score=0.74,
        exhaustion_score=0.68,
        usd_flow_state="COMPRA_FORTE_ACIMA_REFERENCIA",
        usd_flow_delta_pct=0.31,
        usd_above_reference=True,
        heavyweights_confirmation="CONFIRMANDO_VENDA",
        ibov_confirmation="CONFIRMANDO_VENDA",
        ewz_confirmation="CONFIRMANDO_VENDA",
        guardian_state={"kill_switch_ativo": False},
        tags=["stress_dolar", "reversao_alta"],
        explanations=["snapshot_teste"],
        source_metrics={"atr": 180.0},
    )


def test_persist_snapshot_cria_registro_e_latest_json(tmp_path: Path) -> None:
    db_path = tmp_path / "trading.db"
    latest_json = tmp_path / "outputs" / "analysis" / "diario_market_features_latest.json"
    snapshot = _sample_snapshot(datetime.now().isoformat(timespec="seconds"))

    row_id = persist_diario_market_features_snapshot(
        db_path,
        snapshot,
        latest_json_path=latest_json,
    )

    assert row_id > 0
    latest = fetch_latest_diario_market_features_snapshot(db_path)
    assert latest is not None
    assert latest["direction_hint"] == "SELL"
    assert latest_json.exists()


def test_load_payload_trata_snapshot_stale_com_neutralizacao(tmp_path: Path) -> None:
    db_path = tmp_path / "trading.db"
    latest_json = tmp_path / "outputs" / "analysis" / "diario_market_features_latest.json"
    old_timestamp = (datetime.now() - timedelta(seconds=180)).isoformat(timespec="seconds")
    persist_diario_market_features_snapshot(
        db_path,
        _sample_snapshot(old_timestamp),
        latest_json_path=latest_json,
    )

    payload = load_diario_market_features_payload(
        db_path,
        latest_json_path=latest_json,
        stale_after_seconds=90,
    )

    assert payload["available"] is True
    assert payload["is_stale"] is True
    assert payload["effective_snapshot"]["direction_hint"] == "NEUTRO"
    assert payload["effective_snapshot"]["confidence"] == 0.0


def test_calculate_reversal_score_detecta_reversao_apos_esticada() -> None:
    candles = [
        _candle(100.0, 101.0),
        _candle(101.0, 102.0),
        _candle(102.0, 103.0),
        _candle(103.0, 104.0),
        _candle(104.0, 105.0),
        _candle(105.0, 103.8),
    ]

    score, direction_hint, metrics = calculate_reversal_score(candles, atr=1.5)

    assert direction_hint == "SELL"
    assert score > 0.55
    assert metrics["stretch_move_points"] > 0


def test_calculate_exhaustion_score_detecta_exaustao_sem_continuidade() -> None:
    candles = [
        _candle(100.0, 101.2),
        _candle(101.2, 102.0),
        _candle(102.0, 102.5),
        _candle(102.5, 102.7),
        _candle(102.7, 102.55),
    ]

    score, direction_hint, metrics = calculate_exhaustion_score(candles)

    assert direction_hint == "SELL"
    assert score >= 0.70
    assert metrics["continuation_fail"] is True


def test_detect_usd_flow_and_correlated_confirmations() -> None:
    live_confirmation = _live_confirmation()
    opening_context = {
        "contexto_operacional": {
            "rates_fx": {"fx_reference_band": [5.21, 5.22]},
        }
    }

    state, delta_pct, above_reference, metrics = detect_usd_flow_state(
        live_confirmation,
        opening_context,
    )
    confirmations = summarize_correlated_confirmations(live_confirmation)

    assert state == "COMPRA_FORTE_ACIMA_REFERENCIA"
    assert delta_pct == 0.25
    assert above_reference is True
    assert metrics["reference_high"] == 5.22
    assert confirmations["heavyweights_confirmation"] == "CONFIRMANDO_COMPRA"
    assert confirmations["ibov_confirmation"] == "CONFIRMANDO_VENDA"
    assert confirmations["ewz_confirmation"] == "CONFIRMANDO_VENDA"


def test_build_contexto_operacional_com_diario_anexa_snapshot_e_influencia() -> None:
    diario_payload = {
        "available": True,
        "source": "sqlite",
        "is_stale": False,
        "age_seconds": 12.0,
        "stale_after_seconds": 90,
        "snapshot": _sample_snapshot(datetime.now().isoformat(timespec="seconds")).to_dict(),
        "effective_snapshot": _sample_snapshot(datetime.now().isoformat(timespec="seconds")).to_dict(),
    }
    influence = apply_diario_soft_feature_influence("Vender", 0.66, diario_payload)

    contexto = build_contexto_operacional_com_diario(
        {
            "regime_macro": "CAUTELOSO",
            "vies_intraday": "NEUTRO_LEVEMENTE_BAIXISTA",
            "watchlist": ["PETR4", "VALE3", "DOL"],
        },
        base_payload={"contexto_abertura_liberado": True},
        diario_payload=diario_payload,
        diario_influence=influence,
        action="Vender",
        model_confidence=0.66,
    )

    assert contexto["diario_market_features_available"] is True
    assert contexto["diario_market_features"]["direction_hint"] == "SELL"
    assert (
        contexto["diario_market_features_soft_influence"]["alignment"] == "ALIGNED"
    )
    assert contexto["confidence_used_diario_adjusted"] > 0.66


def test_concurrent_writes_no_mesmo_sqlite_nao_explodem(tmp_path: Path) -> None:
    db_path = tmp_path / "trading.db"
    latest_json = tmp_path / "outputs" / "analysis" / "diario_market_features_latest.json"

    def write_snapshot(idx: int) -> int:
        payload = _sample_snapshot(datetime.now().isoformat(timespec="seconds"))
        payload.session_id = f"sessao_{idx}"
        return persist_diario_market_features_snapshot(
            db_path,
            payload,
            latest_json_path=latest_json,
        )

    def write_feedback(idx: int) -> int:
        feedback = DiaryFeedback(
            date="2026-03-20",
            timestamp=datetime.now().isoformat(timespec="seconds"),
            source=f"teste_{idx}",
            nota_agente=idx + 1,
            alertas_criticos=[f"alerta_{idx}"],
        )
        return save_diary_feedback(str(db_path), feedback)

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(write_snapshot, 1),
            executor.submit(write_feedback, 1),
            executor.submit(write_snapshot, 2),
            executor.submit(write_feedback, 2),
        ]
        results = [future.result() for future in futures]

    assert all(result > 0 for result in results)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM diario_market_features")
    snapshot_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM diary_feedback")
    feedback_count = cursor.fetchone()[0]
    conn.close()

    assert snapshot_count == 2
    assert feedback_count == 2
