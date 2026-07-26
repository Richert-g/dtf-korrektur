"""Zusammenfassender Abschlussbericht für die Stapelverarbeitung (Prompt Abschnitt 15)."""
from __future__ import annotations

import json
from pathlib import Path

from src.models.report import BatchSummary
from src.utils.fs_utils import ensure_dir


def write_batch_summary_report(summary: BatchSummary, reports_dir: Path) -> Path:
    ensure_dir(reports_dir)
    path = reports_dir / "batch_summary.json"

    data = {
        "total_files": summary.total_files,
        "succeeded": summary.succeeded,
        "failed": summary.failed,
        "skipped": summary.skipped,
        "total_duration_seconds": summary.total_duration_seconds,
        "files": [
            {
                "source": str(r.source_path) if r.source_path else None,
                "output": str(r.output_path) if r.output_path else None,
                "success": r.success,
                "detected_type": r.detected_type.value,
                "warnings": r.warnings,
                "errors": r.errors,
                "duration_seconds": r.processing_duration_seconds,
            }
            for r in summary.reports
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path
