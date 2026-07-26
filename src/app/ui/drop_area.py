"""Drag-and-drop-Bereich für Bilder und Ordner."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from src.config.defaults import SUPPORTED_IMPORT_FORMATS


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
        paths = []
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if local:
                paths.append(Path(local))
        collected = self._collect_supported_files(paths)
        if collected:
            self.files_dropped.emit(collected)

    @staticmethod
    def _collect_supported_files(paths: list[Path]) -> list[Path]:
        result: list[Path] = []
        for p in paths:
            if p.is_dir():
                for child in sorted(p.rglob("*")):
                    if child.is_file() and child.suffix.lower() in SUPPORTED_IMPORT_FORMATS:
                        result.append(child)
            elif p.is_file() and p.suffix.lower() in SUPPORTED_IMPORT_FORMATS:
                result.append(p)
        return result
