"""Drag-and-drop-Bereiche für Bilder und Ordner (Drop-Zone und Dateiliste)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import QLabel, QListWidget, QVBoxLayout, QWidget

# collect_supported_files lebt in utils.file_collection (bewusst Qt-frei,
# wird auch vom Kommandozeilenmodus cli.py genutzt) - hier nur re-exportiert,
# damit bestehende Importe (main_window.py, Tests) unverändert bleiben.
from src.utils.file_collection import collect_supported_files

__all__ = ["DropArea", "DropListWidget", "collect_supported_files"]


def _urls_to_paths(event) -> list[Path]:
    paths = []
    for url in event.mimeData().urls():
        local = url.toLocalFile()
        if local:
            paths.append(Path(local))
    return paths


class DropArea(QWidget):
    """Nimmt Dateien und Ordner per Drag & Drop entgegen."""

    files_dropped = Signal(list)  # list[Path]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(160)
        self.setObjectName("DropArea")

        layout = QVBoxLayout(self)
        self._label = QLabel(
            "Bild(er) oder Ordner hierher ziehen\n\n(PNG, JPG, TIFF, BMP, WebP)"
        )
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setWordWrap(True)
        layout.addWidget(self._label)
        self.setStyleSheet(
            "#DropArea { border: 2px dashed #888; border-radius: 8px; background: rgba(128,128,128,0.06); }"
        )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802 (Qt-Namenskonvention)
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        collected = collect_supported_files(_urls_to_paths(event))
        if collected:
            self.files_dropped.emit(collected)


class DropListWidget(QListWidget):
    """QListWidget, das zusätzlich zur normalen Dateiauswahl auch Drag & Drop
    von Dateien/Ordnern direkt auf die Liste entgegennimmt - wie DropArea,
    nur eben auch über der bereits ausgewählten Liste statt nur der
    gestrichelten Box darüber."""

    files_dropped = Signal(list)  # list[Path]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        if not event.mimeData().hasUrls():
            super().dropEvent(event)
            return
        collected = collect_supported_files(_urls_to_paths(event))
        if collected:
            self.files_dropped.emit(collected)
