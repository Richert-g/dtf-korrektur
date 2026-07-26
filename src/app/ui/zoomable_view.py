"""Zoom- und verschiebbare Bildansicht auf Basis von QGraphicsView."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QWheelEvent
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsView


class ZoomableImageView(QGraphicsView):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setRenderHints(self.renderHints())
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self._zoom = 1.0

    def set_pixmap(self, pixmap: QPixmap, reset_view: bool = True) -> None:
        self._scene.clear()
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(self._pixmap_item.boundingRect())
        if reset_view:
            self._zoom = 1.0
            self.resetTransform()
            self.fit_to_window()

    def fit_to_window(self) -> None:
        if self._pixmap_item is None:
            return
        self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        if self._pixmap_item is None:
            return
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        self._zoom = max(0.05, min(40.0, self._zoom * factor))
        self.scale(factor, factor)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
