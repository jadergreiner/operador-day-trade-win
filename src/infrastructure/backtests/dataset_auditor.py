"""
Auditoria de dataset para reteste P0-2.

Garante rastreabilidade minima antes de tratar o Gate 2 como decisao final.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List

import json

import pandas as pd


REQUIRED_METADATA_FIELDS = {
    "source",
    "source_type",
    "symbol",
    "timeframe",
    "rows",
    "date_start",
    "date_end",
    "sha256",
    "synthetic",
}


@dataclass
class DatasetAuditResult:
    dataset_path: str
    metadata_path: str
    reliable: bool
    rows_detected: int
    date_start_detected: str | None
    date_end_detected: str | None
    sha256_detected: str
    issues: List[str]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _compute_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_dataset(dataset_path: str) -> DatasetAuditResult:
    """Valida se o dataset possui rastreabilidade suficiente para Gate 2."""
    dataset = Path(dataset_path)
    metadata_path = dataset.with_suffix(".metadata.json")
    issues: List[str] = []
    metadata: Dict[str, Any] = {}
    rows_detected = 0
    date_start_detected = None
    date_end_detected = None
    sha256_detected = ""

    if not dataset.exists():
        issues.append(f"dataset_missing:{dataset}")
        return DatasetAuditResult(
            dataset_path=str(dataset),
            metadata_path=str(metadata_path),
            reliable=False,
            rows_detected=rows_detected,
            date_start_detected=date_start_detected,
            date_end_detected=date_end_detected,
            sha256_detected=sha256_detected,
            issues=issues,
            metadata=metadata,
        )

    sha256_detected = _compute_sha256(dataset)

    if not metadata_path.exists():
        issues.append(f"metadata_missing:{metadata_path}")
    else:
        with metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)

        missing_fields = sorted(REQUIRED_METADATA_FIELDS - set(metadata))
        if missing_fields:
            issues.append(f"metadata_missing_fields:{','.join(missing_fields)}")

    df = pd.read_csv(dataset, index_col=0, parse_dates=True)
    rows_detected = len(df)
    if rows_detected:
        sorted_index = df.index.sort_values()
        date_start_detected = sorted_index[0].isoformat()
        date_end_detected = sorted_index[-1].isoformat()
        if not df.index.is_monotonic_increasing:
            issues.append("index_not_monotonic_increasing")
        if df.index.has_duplicates:
            issues.append("index_has_duplicates")

    if metadata:
        if bool(metadata.get("synthetic", True)):
            issues.append("dataset_flagged_as_synthetic")
        if metadata.get("rows") != rows_detected:
            issues.append(
                f"row_count_mismatch:expected={metadata.get('rows')},actual={rows_detected}"
            )
        expected_sha256 = str(metadata.get("sha256", "")).lower()
        if expected_sha256 != sha256_detected.lower():
            issues.append("sha256_mismatch")
        if metadata.get("date_start") != date_start_detected:
            issues.append(
                f"date_start_mismatch:expected={metadata.get('date_start')},actual={date_start_detected}"
            )
        if metadata.get("date_end") != date_end_detected:
            issues.append(
                f"date_end_mismatch:expected={metadata.get('date_end')},actual={date_end_detected}"
            )

    return DatasetAuditResult(
        dataset_path=str(dataset),
        metadata_path=str(metadata_path),
        reliable=not issues,
        rows_detected=rows_detected,
        date_start_detected=date_start_detected,
        date_end_detected=date_end_detected,
        sha256_detected=sha256_detected,
        issues=issues,
        metadata=metadata,
    )
