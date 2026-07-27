"""Führt den Update-Check in einem eigenen QThread aus (Prompt Abschnitt 20:
UI darf nicht einfrieren) - siehe pipeline_worker.py für dasselbe Muster
inkl. _KEEPALIVE-Begründung.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal

from src.core.update.update_check import check_for_update

_KEEPALIVE: set[tuple[QThread, QObject]] = set()


class UpdateCheckWorker(QObject):
    finished = Signal(object)  # UpdateCheckResult

    def __init__(self, current_version: str) -> None:
        super().__init__()
        self._current_version = current_version

    def run(self) -> None:
        result = check_for_update(self._current_version)
        self.finished.emit(result)


def run_update_check_in_thread(current_version: str) -> tuple[QThread, UpdateCheckWorker]:
    thread = QThread()
    worker = UpdateCheckWorker(current_version)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)

    entry = (thread, worker)
    _KEEPALIVE.add(entry)

    def _cleanup() -> None:
        _KEEPALIVE.discard(entry)
        thread.deleteLater()
        worker.deleteLater()

    thread.finished.connect(_cleanup)

    return thread, worker
