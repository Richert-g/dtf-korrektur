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
    # ImageAnalysisResult|None, LoadedImage|None, error:str|None, angeforderter Pfad.
    # Der Pfad ist bewusst Teil des Signals (statt per Lambda im Empfänger
    # nachgereicht) - siehe run_analysis_in_thread() für den Grund.
    finished = Signal(object, object, object, object)
    failed = Signal(str)

    def __init__(self, path: Path, settings: ProcessingSettings) -> None:
        super().__init__()
        self._path = path
        self._settings = settings

    def run(self) -> None:
        from src.core.analysis.analyzer import analyze_image_safe

        result, loaded, error = analyze_image_safe(self._path, self._settings)
        self.finished.emit(result, loaded, error, self._path)


def run_analysis_in_thread(path: Path, settings: ProcessingSettings) -> tuple[QThread, AnalysisWorker]:
    """Startet die Analyse in einem eigenen QThread.

    WICHTIG für Aufrufer: `finished` immer an eine QObject-gebundene Methode
    verbinden (z. B. `self._on_analysis_finished`), NIEMALS an eine Lambda
    oder ein anderes freies Python-Callable. Qt/PySide6 kann die
    Thread-Zugehörigkeit eines gebundenen Slots erkennen und liefert das
    Signal dadurch automatisch per QueuedConnection im GUI-Thread aus. Bei
    einer Lambda fehlt diese Information; Qt führt den Slot dann per
    DirectConnection im Worker-Thread aus - jeder GUI-Zugriff darin (z. B.
    QGraphicsView/QPixmap) verursacht dann einen harten Absturz
    ("access violation"), der unter dem Standard-Offscreen-Testtreiber NICHT
    auffällt und nur mit echtem Rendering reproduzierbar ist. Deshalb trägt
    das `finished`-Signal den angeforderten Pfad als eigenen Parameter statt
    ihn per Lambda-Closure nachzureichen.
    """
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
