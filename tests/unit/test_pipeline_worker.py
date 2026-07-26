from pathlib import Path

from src.app.workers.pipeline_worker import BatchWorker
from src.config.defaults import ProcessingSettings
from src.models.report import ImageProcessingReport


def _fake_process(path: Path, settings, output_dir) -> ImageProcessingReport:
    report = ImageProcessingReport(source_path=path, output_path=output_dir / path.name, success=True)
    return report


def test_batch_worker_processes_all_files_and_emits_finished(qtbot=None):
    files = [Path(f"file{i}.png") for i in range(5)]
    worker = BatchWorker(files, ProcessingSettings(), Path("out"), _fake_process, max_workers=2)

    finished_summaries = []
    file_finished_reports = []
    worker.finished.connect(finished_summaries.append)
    worker.file_finished.connect(file_finished_reports.append)

    worker.run()

    assert len(finished_summaries) == 1
    summary = finished_summaries[0]
    assert summary.total_files == 5
    assert summary.succeeded == 5
    assert summary.failed == 0
    assert len(file_finished_reports) == 5


def _fake_process_with_error(path: Path, settings, output_dir) -> ImageProcessingReport:
    if "bad" in path.name:
        raise ValueError("Simulierter Fehler")
    return ImageProcessingReport(source_path=path, success=True)


def test_batch_worker_continues_after_single_file_error():
    files = [Path("good1.png"), Path("bad.png"), Path("good2.png")]
    worker = BatchWorker(files, ProcessingSettings(), Path("out"), _fake_process_with_error, max_workers=1)

    finished_summaries = []
    failures = []
    worker.finished.connect(finished_summaries.append)
    worker.file_failed.connect(lambda path, err: failures.append((path, err)))

    worker.run()

    summary = finished_summaries[0]
    assert summary.total_files == 3
    assert summary.succeeded == 2
    assert summary.failed == 1
    assert len(failures) == 1


def test_batch_worker_cancel_emits_cancelled_not_finished():
    files = [Path(f"file{i}.png") for i in range(20)]
    worker = BatchWorker(files, ProcessingSettings(), Path("out"), _fake_process, max_workers=2)
    worker.request_cancel()

    cancelled_events = []
    finished_events = []
    worker.cancelled.connect(lambda: cancelled_events.append(True))
    worker.finished.connect(lambda s: finished_events.append(s))

    worker.run()

    assert len(cancelled_events) == 1
    assert len(finished_events) == 0
