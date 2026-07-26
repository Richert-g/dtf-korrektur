import json
from pathlib import Path

from src.core.reporting.batch_report import write_batch_summary_report
from src.models.report import BatchSummary, ImageProcessingReport


def test_batch_summary_report_written(tmp_path: Path):
    summary = BatchSummary(total_files=2, succeeded=1, failed=1, total_duration_seconds=1.5)
    r1 = ImageProcessingReport(source_path=Path("a.png"), success=True)
    r2 = ImageProcessingReport(source_path=Path("b.png"), success=False)
    r2.errors.append("kaputt")
    summary.reports = [r1, r2]

    path = write_batch_summary_report(summary, tmp_path / "reports")
    assert path.exists()

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["total_files"] == 2
    assert data["succeeded"] == 1
    assert data["failed"] == 1
    assert len(data["files"]) == 2
    assert data["files"][1]["errors"] == ["kaputt"]
