"""Hot-Folder-Automatikmodus: überwacht einen Quellordner und liefert neu
aufgetauchte, fertig kopierte Bilddateien zur automatischen Verarbeitung mit
den aktuell konfigurierten Einstellungen.

Bewusst einfache Polling-Implementierung statt einer OS-Dateisystem-
Überwachung (z. B. über eine zusätzliche watchdog-Abhängigkeit) - eine
Sekunden-Latenz ist für einen Druckerei-Workflow unproblematisch, und die
App bleibt frei von einer zusätzlichen Bibliotheksabhängigkeit.

Eine Datei gilt erst als "fertig kopiert" (verarbeitungsbereit), wenn ihre
Dateigröße über zwei aufeinanderfolgende Abtastungen unverändert bleibt -
verhindert, dass eine noch unvollständig geschriebene/kopierte Datei
angefasst wird. Bereits verarbeitete Dateien werden nur für die Laufzeit
dieses Watcher-Objekts gemerkt (kein persistentes Verarbeitungs-Log) - nach
einem Neustart der App würden unveränderte Dateien im Quellordner daher
erneut verarbeitet.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from src.config.defaults import SUPPORTED_IMPORT_FORMATS, ProcessingSettings
from src.models.report import ImageProcessingReport

DEFAULT_POLL_INTERVAL_SECONDS = 2.0

ProcessFn = Callable[[Path, ProcessingSettings, Path], ImageProcessingReport]


@dataclass
class _PendingFile:
    size: int


class HotFolderWatcher:
    """Zustandsbehaftete Ordnerüberwachung: ein Aufruf von `poll()` prüft den
    Quellordner einmal und gibt die Liste der neu als "stabil" erkannten
    Dateien zurück (noch nicht als verarbeitet markiert)."""

    def __init__(self, source_dir: Path) -> None:
        self.source_dir = source_dir
        self._pending: dict[Path, _PendingFile] = {}
        self._processed: set[Path] = set()

    def poll(self) -> list[Path]:
        if not self.source_dir.is_dir():
            return []

        ready: list[Path] = []
        seen_now: set[Path] = set()
        for path in sorted(self.source_dir.iterdir()):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_IMPORT_FORMATS:
                continue
            if path in self._processed:
                continue
            seen_now.add(path)
            try:
                size = path.stat().st_size
            except OSError:
                continue

            prior = self._pending.get(path)
            if prior is not None and prior.size == size:
                ready.append(path)
                del self._pending[path]
            else:
                self._pending[path] = _PendingFile(size=size)

        # Dateien, die verschwunden sind, bevor sie stabil wurden (z. B.
        # manuell wieder gelöscht), aus der Merkliste entfernen.
        for path in list(self._pending):
            if path not in seen_now:
                del self._pending[path]

        return ready

    def mark_processed(self, path: Path) -> None:
        self._processed.add(path)

    @property
    def processed_count(self) -> int:
        return len(self._processed)


def run_hot_folder_loop(
    source_dir: Path,
    output_dir: Path,
    settings: ProcessingSettings,
    process_fn: ProcessFn,
    should_stop: Callable[[], bool],
    on_file_processed: Callable[[Path, ImageProcessingReport], None],
    poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
) -> None:
    """Blockierende Überwachungsschleife - für den Einsatz in einem eigenen
    Hintergrund-Thread gedacht (siehe app.workers.hot_folder_worker).
    `process_fn` muss fehlertolerant sein und darf nicht werfen (siehe
    core.pipeline.process_image_safe) - ein Fehler bei einer Datei darf die
    Überwachung nicht stoppen."""
    watcher = HotFolderWatcher(source_dir)
    while not should_stop():
        for path in watcher.poll():
            if should_stop():
                return
            report = process_fn(path, settings, output_dir)
            watcher.mark_processed(path)
            on_file_processed(path, report)
        time.sleep(poll_interval)
