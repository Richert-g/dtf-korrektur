"""Zoom- und verschiebbare Einzelbild-Vorschau auf Basis von ZoomPanGraphicsView."""
from __future__ import annotations

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem

from src.app.ui.zoom_pan_view import ZoomPanGraphicsView


class ZoomableImageView(ZoomPanGraphicsView):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._pixmap_item: QGraphicsPixmapItem | None = None

    def set_pixmap(self, pixmap: QPixmap, reset_view: bool = True) -> None:
        self._scene.clear()
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._set_content_rect(self._pixmap_item.boundingRect())
        if reset_view:
            self.fit_to_window()
