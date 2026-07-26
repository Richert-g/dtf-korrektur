"""Vorher-Nachher-Vergleich mit verschiebbarem Trenner."""
from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget


class CompareSliderWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._before: QPixmap | None = None
        self._after: QPixmap | None = None
        self._split = 0.5  # 0..1
        self.setMinimumHeight(200)
        self.setMouseTracking(True)
        self._dragging = False

    def set_images(self, before: QPixmap, after: QPixmap) -> None:
        self._before = before
        self._after = after
        self.update()

    def _scaled_rect(self) -> QRect:
        if not self._before:
            return QRect()
        pm = self._before
        scale = min(self.width() / pm.width(), self.height() / pm.height())
        w = int(pm.width() * scale)
        h = int(pm.height() * scale)
        x = (self.width() - w) // 2
        y = (self.height() - h) // 2
        return QRect(x, y, w, h)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().window())
        if not self._before or not self._after:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Keine Vorschau verfügbar")
            return

        rect = self._scaled_rect()
        painter.drawPixmap(rect, self._before)

        split_x = rect.x() + int(rect.width() * self._split)
        after_rect = QRect(rect.x(), rect.y(), split_x - rect.x(), rect.height())
        if after_rect.width() > 0:
            source = QRect(0, 0, int(self._after.width() * self._split), self._after.height())
            painter.drawPixmap(after_rect, self._after, source)

        pen = QPen(Qt.GlobalColor.red)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(split_x, rect.y(), split_x, rect.y() + rect.height())
        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._dragging = True
        self._update_split(event.pos())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._dragging:
            self._update_split(event.pos())

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._dragging = False

    def _update_split(self, pos: QPoint) -> None:
        rect = self._scaled_rect()
        if rect.width() <= 0:
            return
        ratio = (pos.x() - rect.x()) / rect.width()
        self._split = max(0.0, min(1.0, ratio))
        self.update()
