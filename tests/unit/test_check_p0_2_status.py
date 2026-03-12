import json
from pathlib import Path

from scripts import check_p0_2_status as status_mod


def _write_files(base: Path, *, status_decision: str, decision_decision: str) -> None:
    backtest_dir = base / "backtest"
    backtest_dir.mkdir(parents=True, exist_ok=True)

    (backtest_dir / "p0_2_status.json").write_text(
        json.dumps(
            {
                "completed": True,
                "decision_is_final": True,
                "decision": status_decision,
                "dataset_audit": {"audit_passed": True},
            }
        ),
        encoding="utf-8",
    )
    (backtest_dir / "gate2_decision.json").write_text(
        json.dumps({"decision": decision_decision}),
        encoding="utf-8",
    )


def test_has_final_gate2_decision_requires_consistency(monkeypatch, tmp_path):
    _write_files(tmp_path, status_decision="PASS", decision_decision="FAIL")
    monkeypatch.setattr(status_mod, "STATUS_FILE", tmp_path / "backtest" / "p0_2_status.json")
    monkeypatch.setattr(status_mod, "DECISION_FILE", tmp_path / "backtest" / "gate2_decision.json")

    assert status_mod.has_final_gate2_decision() is False


def test_has_final_gate2_decision_accepts_matching_decision(monkeypatch, tmp_path):
    _write_files(tmp_path, status_decision="FAIL", decision_decision="FAIL")
    monkeypatch.setattr(status_mod, "STATUS_FILE", tmp_path / "backtest" / "p0_2_status.json")
    monkeypatch.setattr(status_mod, "DECISION_FILE", tmp_path / "backtest" / "gate2_decision.json")

    assert status_mod.has_final_gate2_decision() is True
