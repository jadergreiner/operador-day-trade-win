from __future__ import annotations

from decimal import Decimal

import scripts.start_journals_full_display as journals


def test_current_daily_confidence_gate_uses_daily_override(monkeypatch) -> None:
    monkeypatch.setattr(journals, "load_daily_confidence_override", lambda path=None: 0.32)

    gate = journals._current_daily_confidence_gate()

    assert gate == Decimal("0.35")
