"""Gemeinsame Zoom-/Pan-Basis für alle Vorschauansichten.

Kapselt die Zoomlogik EINMAL (Mausrad-Zoom zum Cursor, Grenzen, Doppelklick
zum Einpassen, Zoomwert-Signal) statt sie in jeder Vorschau-Ansicht separat
zu duplizieren. `ZoomableImageView` (Einzelbild) und `CompareGraphicsView`
(Vorher/Nachher) leiten beide von dieser Klasse ab, sodass sich Zoomen und
Verschieben für alle Ansichten identisch verhalten.
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QPainter, QWheelEvent
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel, QPushButton, QWidget


class ZoomPanGraphicsView(QGraphicsView):
    """QGraphicsView mit einheitlichem Zoom-/Pan-Verhalten für Bildvorschauen."""

    MIN_ZOOM = 0.10  # 10 %
    MAX_ZOOM = 8.0  # 800 %
    ZOOM_STEP = 1.15
    PLACEHOLDER_TEXT = "Keine Vorschau verfügbar"

    zoom_changed = Signal(float)  # aktueller Zoom in Prozent, z. B. 125.0

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._content_rect: QRectF | None = None
        self._zoom = 1.0
        self._has_content = False

        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setRenderHints(
            QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing
        )
        # Verhindert Flackern bei häufigen Neuzeichnungen (Zoom/Pan).
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    # ------------------------------------------------------------- Inhalt
    def _set_content_rect(self, rect: QRectF) -> None:
        self._content_rect = rect
        self.setSceneRect(rect)
        self._has_content = not rect.isEmpty()

    def clear_content(self) -> None:
        self._scene.clear()
        self._content_rect = None
        self._has_content = False
        self._zoom = 1.0

    # --------------------------------------------------------------- Zoom
    @property
    def zoom_percent(self) -> float:
        return self._zoom * 100.0

    def fit_to_window(self) -> None:
        """Passt das Bild an das Fenster an (Doppelklick / Button "Einpassen")."""
        if not self._has_content or self._content_rect is None or self._content_rect.isEmpty():
            return
        self.resetTransform()
        self.fitInView(self._content_rect, Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom = self.transform().m11()
        self.zoom_changed.emit(self.zoom_percent)

    def zoom_100(self) -> None:
        """Setzt den Zoom auf exakt 100 % (1 Bildpixel = 1 Bildschirmpixel)."""
        if not self._has_content:
            return
        self.resetTransform()
        self._zoom = 1.0
        self.zoom_changed.emit(self.zoom_percent)

    def set_zoom(self, factor: float) -> None:
        """Setzt den Zoom auf einen absoluten Faktor (1.0 = 100 %), zentriert auf die Ansichtsmitte."""
        if not self._has_content:
            return
        factor = max(self.MIN_ZOOM, min(self.MAX_ZOOM, factor))
        if abs(factor - self._zoom) < 1e-6:
            return
        scale_factor = factor / self._zoom
        self.scale(scale_factor, scale_factor)
        self._zoom = factor
        self.zoom_changed.emit(self.zoom_percent)

    def _zoom_by(self, factor: float) -> None:
        """Multiplikativer Zoomschritt (z. B. durch Mausrad), Anker bleibt unter dem Cursor."""
        if not self._has_content:
            return
        new_zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self._zoom * factor))
        if abs(new_zoom - self._zoom) < 1e-9:
            return
        applied_factor = new_zoom / self._zoom
        self.scale(applied_factor, applied_factor)
        self._zoom = new_zoom
        self.zoom_changed.emit(self.zoom_percent)

    # ------------------------------------------------------------- Events
    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        if not self._has_content:
            event.ignore()
            return
        delta = event.angleDelta().y()
        if delta == 0:
            event.ignore()
            return
        factor = self.ZOOM_STEP if delta > 0 else (1.0 / self.ZOOM_STEP)
        self._zoom_by(factor)
        # Verhindert, dass das Mausrad-Ereignis zusätzlich die Seite/den
        # umgebenden Bereich scrollt.
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        self.fit_to_window()
        super().mouseDoubleClickEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        if not self._has_content:
            painter = QPainter(self.viewport())
            painter.drawText(self.viewport().rect(), Qt.AlignmentFlag.AlignCenter, self.PLACEHOLDER_TEXT)
            painter.end()


class ZoomToolbar(QWidget):
    """Kompakte Werkzeugleiste: aktueller Zoomwert + 'Einpassen' + '100 %'.

    Wird pro Vorschau-Ansicht einmal erzeugt und an eine ZoomPanGraphicsView
    gebunden (`bind`), statt Zoom-Anzeige/Buttons für jede Ansicht erneut zu
    implementieren.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.zoom_label = QLabel("100 %")
        self.zoom_label.setMinimumWidth(56)
        self.btn_fit = QPushButton("Ansicht einpassen")
        self.btn_100 = QPushButton("100 %")

        layout.addWidget(self.zoom_label)
        layout.addWidget(self.btn_fit)
        layout.addWidget(self.btn_100)
        layout.addStretch(1)

        self._view: ZoomPanGraphicsView | None = None

    def bind(self, view: ZoomPanGraphicsView) -> None:
        self._view = view
        view.zoom_changed.connect(self._on_zoom_changed)
        self.btn_fit.clicked.connect(view.fit_to_window)
        self.btn_100.clicked.connect(view.zoom_100)
        self._on_zoom_changed(view.zoom_percent)

    def _on_zoom_changed(self, percent: float) -> None:
        self.zoom_label.setText(f"{percent:.0f} %")
