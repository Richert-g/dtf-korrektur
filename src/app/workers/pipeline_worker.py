"""Hintergrund-Worker für Analyse und Verarbeitung (Prompt Abschnitt 20: UI darf nicht einfrieren).

Verarbeitet mehrere Dateien mit kontrollierter Parallelisierung (Prompt Abschnitt 20)
und unterstützt Abbruch (Prompt Abschnitt 15).
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from src.config.defaults import DEFAULT_MAX_PARALLEL_WORKERS, ProcessingSettings
from src.models.report import BatchSummary, ImageProcessingReport


class BatchWorker(QObject):
    """Läuft in einem eigenen QThread und verarbeitet eine Liste von Dateien."""

    progress = Signal(int, int, str)  # aktuelle Nummer, gesamt, aktueller Dateiname
    file_finished = Signal(object)  # ImageProcessingReport
    file_failed = Signal(str, str)  # pfad, fehlermeldung
    finished = Signal(object)  # BatchSummary
    cancelled = Signal()

    def __init__(
        self,
        files: list[Path],
        settings: ProcessingSettings,
        output_dir: Path,
        process_fn,
        max_workers: int = DEFAULT_MAX_PARALLEL_WORKERS,
    ) -> None:
        super().__init__()
        self._files = files
        self._settings = settings
        self._output_dir = output_dir
        self._process_fn = process_fn
        self._max_workers = max(1, max_workers)
        self._cancel_requested = False

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def run(self) -> None:
        summary = BatchSummary(total_files=len(self._files))
        start = time.perf_counter()
        completed = 0

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            future_to_path = {
                executor.submit(self._process_fn, path, self._settings, self._output_dir): path
                for path in self._files
            }
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                if self._cancel_requested:
                    for f in future_to_path:
                        f.cancel()
                    break
                completed += 1
                self.progress.emit(completed, len(self._files), path.name)
                try:
                    report: ImageProcessingReport = future.result()
                    summary.reports.append(report)
                    if report.success:
                        summary.succeeded += 1
                    else:
                        summary.failed += 1
                    self.file_finished.emit(report)
                except Exception as exc:  # noqa: BLE001 - Einzeldatei darf Batch nicht stoppen
                    summary.failed += 1
                    self.file_failed.emit(str(path), str(exc))

        summary.total_duration_seconds = time.perf_counter() - start
        if self._cancel_requested:
            self.cancelled.emit()
        else:
            self.finished.emit(summary)


def run_batch_in_thread(
    files: list[Path],
    settings: ProcessingSettings,
    output_dir: Path,
    process_fn,
    max_workers: int = DEFAULT_MAX_PARALLEL_WORKERS,
) -> tuple[QThread, BatchWorker]:
    thread = QThread()
    worker = BatchWorker(files, settings, output_dir, process_fn, max_workers=max_workers)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    worker.cancelled.connect(thread.quit)
    return thread, worker
