"""Vorher-Nachher-Vergleich mit verschiebbarem Trenner, auf Basis von ZoomPanGraphicsView.

Beide Bilder liegen als Items in EINER gemeinsamen QGraphicsScene, daher
zoomen und verschieben sich beide automatisch synchron mit dem View-Transform
- es gibt keinen Zustand, der zwischen "vorher" und "nachher" verrutschen
könnte. Das "Nachher"-Bild wird über ein unsichtbares, klippendes
Eltern-Item auf den Bereich links des Trenners begrenzt.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPen, QPixmap
from PySide6.QtWidgets import QGraphicsItem, QGraphicsLineItem, QGraphicsPixmapItem, QGraphicsRectItem

from src.app.ui.zoom_pan_view import ZoomPanGraphicsView

_DIVIDER_HIT_TOLERANCE_PX = 8
_DIVIDER_COLOR = QColor(230, 40, 40)


class CompareSliderWidget(ZoomPanGraphicsView):
    # Normierte Bildposition (0..1, 0..1) eines per Farbpicker angeklickten
    # Pixels - unabhängig von Zoom/Skalierung der angezeigten Vorschau, damit
    # der Aufrufer sie direkt auf die Original-/Ergebnis-Arrays in voller
    # Auflösung umrechnen kann.
    pixel_picked = Signal(float, float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._before_item: QGraphicsPixmapItem | None = None
        self._after_item: QGraphicsPixmapItem | None = None
        self._clip_item: QGraphicsRectItem | None = None
        self._divider_item: QGraphicsLineItem | None = None
        self._split_ratio = 0.5  # Anteil des "Nachher"-Bilds von links (0..1)
        self._dragging_divider = False
        self._picker_mode = False
        self.setMouseTracking(True)

    def set_picker_mode(self, enabled: bool) -> None:
        self._picker_mode = enabled
        if enabled:
            self.setCursor(Qt.CursorShape.CrossCursor)
            self.setDragMode(ZoomPanGraphicsView.DragMode.NoDrag)
        else:
            self.unsetCursor()
            self.setDragMode(ZoomPanGraphicsView.DragMode.ScrollHandDrag)

    def _emit_pixel_picked_at(self, viewport_pos) -> bool:
        """Rechnet eine Viewport-Position in eine normierte (0..1, 0..1)
        Bildposition um und sendet `pixel_picked`. Gibt False zurück, wenn
        außerhalb des Bildinhalts geklickt wurde."""
        if self._content_rect is None or self._content_rect.width() <= 0 or self._content_rect.height() <= 0:
            return False
        scene_pos = self.mapToScene(int(round(viewport_pos.x())), int(round(viewport_pos.y())))
        fx = (scene_pos.x() - self._content_rect.left()) / self._content_rect.width()
        fy = (scene_pos.y() - self._content_rect.top()) / self._content_rect.height()
        if not (0.0 <= fx <= 1.0 and 0.0 <= fy <= 1.0):
            return False
        self.pixel_picked.emit(fx, fy)
        return True

    def set_images(self, before: QPixmap, after: QPixmap) -> None:
        self._scene.clear()
        self._before_item = None
        self._after_item = None
        self._clip_item = None
        self._divider_item = None

        w = max(before.width(), after.width())
        h = max(before.height(), after.height())
        if w <= 0 or h <= 0:
            self.clear_content()
            return

        self._before_item = self._scene.addPixmap(before)
        self._before_item.setZValue(0)

        self._clip_item = QGraphicsRectItem(0, 0, w * self._split_ratio, h)
        self._clip_item.setPen(Qt.PenStyle.NoPen)
        self._clip_item.setBrush(Qt.BrushStyle.NoBrush)
        self._clip_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemClipsChildrenToShape, True)
        self._clip_item.setZValue(1)
        self._scene.addItem(self._clip_item)

        self._after_item = QGraphicsPixmapItem(after, self._clip_item)
        self._after_item.setPos(0, 0)

        pen = QPen(_DIVIDER_COLOR)
        pen.setWidth(2)
        pen.setCosmetic(True)  # bleibt beim Zoomen als 2 Bildschirmpixel breit, statt mitzuskalieren
        self._divider_item = self._scene.addLine(0, 0, 0, 0, pen)
        self._divider_item.setZValue(2)

        self._set_content_rect(QRectF(0, 0, w, h))
        self._update_split_geometry()
        self.fit_to_window()

    # ------------------------------------------------------------ Trenner
    def _update_split_geometry(self) -> None:
        if self._content_rect is None or self._clip_item is None or self._divider_item is None:
            return
        split_x = self._content_rect.width() * self._split_ratio
        h = self._content_rect.height()
        self._clip_item.setRect(0, 0, split_x, h)
        self._divider_item.setLine(split_x, 0, split_x, h)

    def _divider_viewport_x(self) -> float:
        if self._content_rect is None:
            return -1_000_000.0
        scene_x = self._content_rect.left() + self._split_ratio * self._content_rect.width()
        return self.mapFromScene(QPointF(scene_x, 0)).x()

    def _update_split_from_viewport_x(self, viewport_x: float) -> None:
        if self._content_rect is None or self._content_rect.width() <= 0:
            return
        scene_pos = self.mapToScene(int(round(viewport_x)), 0)
        ratio = (scene_pos.x() - self._content_rect.left()) / self._content_rect.width()
        self._split_ratio = max(0.0, min(1.0, ratio))
        self._update_split_geometry()

    # ------------------------------------------------------------- Events
    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self._picker_mode and self._has_content and event.button() == Qt.MouseButton.LeftButton:
            self._emit_pixel_picked_at(event.position())
            event.accept()
            return
        if self._has_content and event.button() == Qt.MouseButton.LeftButton:
            if abs(event.position().x() - self._divider_viewport_x()) <= _DIVIDER_HIT_TOLERANCE_PX:
                self._dragging_divider = True
                self.setCursor(Qt.CursorShape.SplitHCursor)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._dragging_divider:
            self._update_split_from_viewport_x(event.position().x())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._dragging_divider:
            self._dragging_divider = False
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)
