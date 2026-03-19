"""Testes do fluxo de encerramento Head."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


def test_main_publica_relatorio_contexto_no_fluxo_encerramento(
    monkeypatch,
    tmp_path: Path,
) -> None:
    script_path = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "executar_fluxo_head_encerramento.py"
    )
    spec = importlib.util.spec_from_file_location(
        "executar_fluxo_head_encerramento_test",
        script_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)

    calls: dict[str, object] = {}
    executed_steps: list[tuple[str, str]] = []

    monkeypatch.setattr(
        module,
        "_parse_args",
        lambda: SimpleNamespace(base_date="2026-03-19", python="python"),
    )
    monkeypatch.setattr(module, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(
        module,
        "_run_step",
        lambda cmd, name: executed_steps.append((name, " ".join(cmd))),
    )
    monkeypatch.setattr(
        module,
        "_append_reflection",
        lambda base_date: executed_steps.append(("reflection", base_date)),
    )

    def _fake_report(**kwargs):
        calls.update(kwargs)
        return SimpleNamespace(
            latest_markdown_path=tmp_path
            / "outputs"
            / "analysis"
            / "opening_context_vs_result_latest.md"
        )

    monkeypatch.setattr(module, "generate_opening_context_vs_result_report", _fake_report)

    assert module.main() == 0
    assert calls["target_date"] == "2026-03-19"
    assert calls["db_path"] == tmp_path / "data" / "db" / "trading.db"
    assert calls["output_dir"] == tmp_path / "outputs" / "analysis"
    assert calls["outputs_root"] == tmp_path / "outputs"
    assert executed_steps[0][0] == "Sessão Head e persistência (head + diário)"
    assert executed_steps[1] == ("reflection", "2026-03-19")
    assert executed_steps[2][0] == "Geração dataset supervisionado"
    assert executed_steps[3][0] == "Treino incremental"
