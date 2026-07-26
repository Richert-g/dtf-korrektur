"""Hintergrund-Worker für die Einzelbild-Analyse (Vorschau vor der eigentlichen Optimierung)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from src.config.defaults import ProcessingSettings


class AnalysisWorker(QObject):
    finished = Signal(object, object, object)  # ImageAnalysisResult|None, LoadedImage|None, error:str|None
    failed = Signal(str)

    def __init__(self, path: Path, settings: ProcessingSettings) -> None:
        super().__init__()
        self._path = path
        self._settings = settings

    def run(self) -> None:
        from src.core.analysis.analyzer import analyze_image_safe

        result, loaded, error = analyze_image_safe(self._path, self._settings)
        self.finished.emit(result, loaded, error)


def run_analysis_in_thread(path: Path, settings: ProcessingSettings) -> tuple[QThread, AnalysisWorker]:
    thread = QThread()
    worker = AnalysisWorker(path, settings)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    return thread, worker
