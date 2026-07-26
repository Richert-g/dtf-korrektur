"""Hintergrund-Worker für die Einzelbild-Analyse (Vorschau vor der eigentlichen Optimierung)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from src.config.defaults import ProcessingSettings

# Modul-globale Liste, die laufende, "verwaiste" Thread/Worker-Paare (z. B.
# weil der Benutzer schnell zur nächsten Datei gewechselt ist) am Leben hält,
# bis sie von selbst fertig werden. Zwei Gefahren, die das verhindert:
# 1. Wird ein QThread von Python vorzeitig vergessen, während er noch läuft,
#    bricht Qt den gesamten Prozess hart ab ("Destroyed while still running").
# 2. Wird das Worker-QObject vorzeitig vergessen (z. B. weil eine UI-Referenz
#    wie self._analysis_worker überschrieben wird), bevor der Thread es
#    tatsächlich ausgeführt hat, läuft der Thread für immer leer weiter, ohne
#    abzustürzen, aber auch ohne jemals fertig zu werden - der Worker MUSS
#    also genauso am Leben gehalten werden wie der Thread selbst.
_KEEPALIVE: set[tuple[QThread, QObject]] = set()


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

    entry = (thread, worker)
    _KEEPALIVE.add(entry)

    def _cleanup() -> None:
        _KEEPALIVE.discard(entry)
        thread.deleteLater()
        worker.deleteLater()

    thread.finished.connect(_cleanup)

    return thread, worker
