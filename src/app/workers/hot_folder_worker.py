"""Führt die Hot-Folder-Überwachung in einem eigenen QThread aus (Prompt
Abschnitt 20: UI darf nicht einfrieren) - siehe pipeline_worker.py für
dasselbe Muster inkl. _KEEPALIVE-Begründung. Anders als BatchWorker läuft
dieser Worker dauerhaft weiter, bis request_stop() aufgerufen wird.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from src.config.defaults import ProcessingSettings
from src.core.automation.hot_folder import DEFAULT_POLL_INTERVAL_SECONDS, ProcessFn, run_hot_folder_loop

_KEEPALIVE: set[tuple[QThread, QObject]] = set()


class HotFolderWorker(QObject):
    file_processed = Signal(object, object)  # Path, ImageProcessingReport
    stopped = Signal()

    def __init__(
        self,
        source_dir: Path,
        output_dir: Path,
        settings: ProcessingSettings,
        process_fn: ProcessFn,
        poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
    ) -> None:
        super().__init__()
        self._source_dir = source_dir
        self._output_dir = output_dir
        self._settings = settings
        self._process_fn = process_fn
        self._poll_interval = poll_interval
        self._stop_requested = False

    def request_stop(self) -> None:
        self._stop_requested = True

    def run(self) -> None:
        run_hot_folder_loop(
            self._source_dir,
            self._output_dir,
            self._settings,
            self._process_fn,
            should_stop=lambda: self._stop_requested,
            on_file_processed=lambda path, report: self.file_processed.emit(path, report),
            poll_interval=self._poll_interval,
        )
        self.stopped.emit()


def run_hot_folder_in_thread(
    source_dir: Path,
    output_dir: Path,
    settings: ProcessingSettings,
    process_fn: ProcessFn,
    poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
) -> tuple[QThread, HotFolderWorker]:
    thread = QThread()
    worker = HotFolderWorker(source_dir, output_dir, settings, process_fn, poll_interval=poll_interval)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.stopped.connect(thread.quit)

    entry = (thread, worker)
    _KEEPALIVE.add(entry)

    def _cleanup() -> None:
        _KEEPALIVE.discard(entry)
        thread.deleteLater()
        worker.deleteLater()

    thread.finished.connect(_cleanup)

    return thread, worker
