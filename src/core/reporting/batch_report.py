"""Zusammenfassender Abschlussbericht für die Stapelverarbeitung (Prompt Abschnitt 15)."""
from __future__ import annotations

import json
from pathlib import Path

from src.models.report import BatchSummary
from src.utils.fs_utils import ensure_dir, retry_on_oserror


def _write_json(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


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
    retry_on_oserror(lambda: _write_json(path, data), description="Batch-Abschlussbericht")
    return path


def format_batch_summary_text(summary: BatchSummary) -> str:
    """Verständliche Textzusammenfassung einer Stapelverarbeitung - wird sowohl
    von der Oberfläche (main_window.py, Anzeige im Zusammenfassungsfeld) als
    auch vom Kommandozeilenmodus (cli.py, Ausgabe auf stdout) genutzt."""
    lines = [
        f"Fertig: {summary.succeeded} von {summary.total_files} Dateien erfolgreich optimiert.",
    ]
    if summary.failed:
        lines.append(f"{summary.failed} Datei(en) fehlgeschlagen.")
    lines.append(f"Dauer: {summary.total_duration_seconds:.1f} s")
    lines.append("")
    for report in summary.reports:
        status = "OK" if report.success else "FEHLER"
        lines.append(f"[{status}] {Path(report.source_path).name if report.source_path else '?'}")
        for w in report.warnings:
            lines.append(f"   Hinweis: {w}")
        for e in report.errors:
            lines.append(f"   Fehler: {e}")
    lines.append("")
    lines.append(
        "Hinweis: Diese Bildschirmvorschau ist keine Garantie für das endgültige Druckergebnis. "
        "Das Ergebnis hängt zusätzlich von Drucker, Tinte, Folie/Pulver, RIP, Textil und Pressparametern ab."
    )
    return "\n".join(lines)
