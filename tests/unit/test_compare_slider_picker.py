from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import QApplication

from src.app.ui.compare_slider import CompareSliderWidget


def _app():
    return QApplication.instance() or QApplication([])


def _make_widget(w=100, h=80) -> CompareSliderWidget:
    _app()
    widget = CompareSliderWidget()
    widget.resize(400, 300)
    before = QPixmap(w, h)
    after = QPixmap(w, h)
    widget.set_images(before, after)
    return widget


def test_set_picker_mode_toggles_state_and_drag_mode():
    widget = _make_widget()
    assert widget._picker_mode is False

    widget.set_picker_mode(True)
    assert widget._picker_mode is True
    assert widget.dragMode() == CompareSliderWidget.DragMode.NoDrag

    widget.set_picker_mode(False)
    assert widget._picker_mode is False
    assert widget.dragMode() == CompareSliderWidget.DragMode.ScrollHandDrag


def test_pixel_picked_emits_normalized_coordinates_in_picker_mode():
    widget = _make_widget()
    widget.set_picker_mode(True)
    widget.fit_to_window()

    received = []
    widget.pixel_picked.connect(lambda fx, fy: received.append((fx, fy)))

    center = widget.viewport().rect().center()
    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(center),
        QPointF(center),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    widget.mousePressEvent(event)

    assert len(received) == 1
    fx, fy = received[0]
    assert 0.0 <= fx <= 1.0
    assert 0.0 <= fy <= 1.0
    # Klick auf die Bildmitte sollte ungefaehr (0.5, 0.5) ergeben
    assert abs(fx - 0.5) < 0.05
    assert abs(fy - 0.5) < 0.05


def test_divider_drag_still_works_when_picker_mode_is_off():
    widget = _make_widget()
    widget.fit_to_window()
    assert widget._picker_mode is False

    divider_x = widget._divider_viewport_x()
    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(divider_x, 10),
        QPointF(divider_x, 10),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    widget.mousePressEvent(event)
    assert widget._dragging_divider is True


def test_click_outside_content_does_not_emit_in_picker_mode():
    widget = _make_widget()
    widget.set_picker_mode(True)
    widget.fit_to_window()

    received = []
    widget.pixel_picked.connect(lambda fx, fy: received.append((fx, fy)))

    # weit außerhalb des Viewports (negative Koordinate)
    ok = widget._emit_pixel_picked_at(QPointF(-500, -500))
    assert ok is False
    assert received == []
