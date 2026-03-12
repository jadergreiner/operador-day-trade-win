import json
from hashlib import sha256

import pandas as pd

from src.infrastructure.backtests.dataset_auditor import audit_dataset


def _write_dataset(tmp_path, *, synthetic: bool) -> str:
    dataset_path = tmp_path / "training_dataset.csv"
    dates = pd.date_range("2026-01-01", periods=4, freq="h")
    df = pd.DataFrame(
        {
            "feature_1": [1.0, 2.0, 3.0, 4.0],
            "label": [0, 1, 0, 1],
        },
        index=dates,
    )
    df.to_csv(dataset_path)

    digest = sha256(dataset_path.read_bytes()).hexdigest()
    metadata = {
        "source": "mt5_export",
        "source_type": "historical_export",
        "symbol": "WINJ26",
        "timeframe": "M5",
        "rows": 4,
        "date_start": dates.min().isoformat(),
        "date_end": dates.max().isoformat(),
        "sha256": digest,
        "synthetic": synthetic,
    }
    dataset_path.with_suffix(".metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )
    return str(dataset_path)


def test_audit_dataset_passes_with_reliable_metadata(tmp_path):
    dataset_path = _write_dataset(tmp_path, synthetic=False)

    result = audit_dataset(dataset_path)

    assert result.reliable is True
    assert result.issues == []
    assert result.rows_detected == 4


def test_audit_dataset_fails_when_dataset_is_synthetic(tmp_path):
    dataset_path = _write_dataset(tmp_path, synthetic=True)

    result = audit_dataset(dataset_path)

    assert result.reliable is False
    assert "dataset_flagged_as_synthetic" in result.issues


def test_audit_dataset_fails_without_metadata(tmp_path):
    dataset_path = tmp_path / "training_dataset.csv"
    dates = pd.date_range("2026-01-01", periods=2, freq="h")
    pd.DataFrame({"feature_1": [1.0, 2.0], "label": [0, 1]}, index=dates).to_csv(
        dataset_path
    )

    result = audit_dataset(str(dataset_path))

    assert result.reliable is False
    assert any(issue.startswith("metadata_missing:") for issue in result.issues)


def test_audit_dataset_fails_with_placeholder_source_type(tmp_path):
    dataset_path = _write_dataset(tmp_path, synthetic=False)
    metadata_path = tmp_path / "training_dataset.metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["source_type"] = "synthetic_placeholder"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    result = audit_dataset(dataset_path)

    assert result.reliable is False
    assert any(
        issue.startswith("metadata_source_type_not_real:")
        for issue in result.issues
    )
