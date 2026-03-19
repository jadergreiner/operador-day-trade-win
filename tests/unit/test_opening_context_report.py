"""Testes do relatorio contexto de abertura vs resultado do dia."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.application.motor_decisao_isolado import (
    MotorDecisaoIsolado,
    MotivoFechamento,
    TipoPosicao,
)
from src.application.opening_context_audit import persist_opening_context_audit
from src.application.opening_context_report import (
    generate_opening_context_vs_result_report,
)


def test_generate_opening_context_vs_result_report_cruza_auditoria_e_trades(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "trading.db"
    outputs_dir = tmp_path / "outputs"
    analysis_dir = outputs_dir / "analysis"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    report_date = datetime.now().date().isoformat()

    contexto = {
        "regime_macro": "CAUTELOSO",
        "vies_intraday": "NEUTRO_LEVEMENTE_BAIXISTA",
        "watchlist": ["PETR4", "VALE3", "DOL"],
        "acao_normalizada": "SELL",
    }

    persist_opening_context_audit(
        str(db_path),
        agent_name="rl_5000",
        source="teste",
        prompt_abertura_agentes="Venda ganha qualidade com DOL forte.",
        macro_context=contexto,
        session_id="agente_dinamico_20260319_090000",
        mode="DINAMICO",
    )

    motor = MotorDecisaoIsolado(
        agent_id="agente_dinamico_20260319_090000",
        data_dir=outputs_dir,
    )
    motor.abrir_posicao(
        ticket=123456,
        tipo=TipoPosicao.VENDIDA,
        preco_entrada=100000.0,
        volume=1.0,
        stop_loss=100200.0,
        take_profit=99600.0,
        contexto_operacional=contexto,
    )
    motor.fechar_posicao(
        123456,
        preco_saida=99800.0,
        motivo=MotivoFechamento.TP_ATINGIDO,
        contexto_operacional=contexto,
    )

    report = generate_opening_context_vs_result_report(
        db_path=db_path,
        output_dir=analysis_dir,
        outputs_root=outputs_dir,
        target_date=report_date,
    )

    assert report.json_path.exists()
    assert report.markdown_path.exists()
    assert report.latest_json_path.exists()
    assert report.latest_markdown_path.exists()
    assert len(report.summaries) == 1

    summary = report.summaries[0]
    assert summary.agent_name == "rl_5000"
    assert summary.trades_closed == 1
    assert summary.wins == 1
    assert summary.pnl_total > 0
    assert summary.alignment_status == "ALINHADO_AO_BIAS"

    payload = json.loads(report.json_path.read_text(encoding="utf-8"))
    assert payload["total_trades_closed"] == 1
    assert payload["summaries"][0]["decision_breakdown"]["ABRIR"] == 1

    latest_payload = json.loads(report.latest_json_path.read_text(encoding="utf-8"))
    assert latest_payload["target_date"] == report_date
    assert latest_payload["latest_markdown_path"].endswith(
        "opening_context_vs_result_latest.md"
    )
