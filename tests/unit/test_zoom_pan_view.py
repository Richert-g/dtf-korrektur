import numpy as np
import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from src.app.ui.compare_slider import CompareSliderWidget
from src.app.ui.zoom_pan_view import ZoomPanGraphicsView, ZoomToolbar
from src.app.ui.zoomable_view import ZoomableImageView
from src.utils.image_qt import rgba_array_to_qpixmap


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _pixmap(w=100, h=80, value=200):
    arr = np.full((h, w, 4), value, dtype=np.uint8)
    arr[:, :, 3] = 255
    return rgba_array_to_qpixmap(arr)


def test_zoomable_view_fit_sets_zoom(qapp):
    view = ZoomableImageView()
    view.resize(400, 300)
    view.set_pixmap(_pixmap())
    assert view.zoom_percent > 0


def test_zoomable_view_zoom_bounds(qapp):
    view = ZoomableImageView()
    view.resize(400, 300)
    view.set_pixmap(_pixmap())

    view.set_zoom(100.0)  # weit über dem Maximum -> muss geklemmt werden
    assert view.zoom_percent == pytest.approx(ZoomPanGraphicsView.MAX_ZOOM * 100, rel=0.01)

    view.set_zoom(0.001)  # weit unter dem Minimum -> muss geklemmt werden
    assert view.zoom_percent == pytest.approx(ZoomPanGraphicsView.MIN_ZOOM * 100, rel=0.01)


def test_zoomable_view_zoom_100(qapp):
    view = ZoomableImageView()
    view.resize(400, 300)
    view.set_pixmap(_pixmap())
    view.set_zoom(2.5)
    view.zoom_100()
    assert view.zoom_percent == pytest.approx(100.0, rel=0.001)


def test_zoomable_view_wheel_zoom_step(qapp):
    view = ZoomableImageView()
    view.resize(400, 300)
    view.set_pixmap(_pixmap())
    view.zoom_100()
    before = view.zoom_percent
    view._zoom_by(view.ZOOM_STEP)
    assert view.zoom_percent > before
    view._zoom_by(1 / view.ZOOM_STEP)
    assert view.zoom_percent == pytest.approx(before, rel=0.01)


def test_zoomable_view_no_content_no_crash_on_wheel(qapp):
    view = ZoomableImageView()
    view._zoom_by(1.15)  # ohne Bild darf nichts passieren/kein Crash
    assert view.zoom_percent == pytest.approx(100.0)


def test_zoom_changed_signal_emitted(qapp):
    view = ZoomableImageView()
    view.resize(400, 300)
    view.set_pixmap(_pixmap())
    received = []
    view.zoom_changed.connect(received.append)
    view.zoom_100()
    assert len(received) >= 1
    assert received[-1] == pytest.approx(100.0)


def test_compare_slider_set_images_and_zoom_shared(qapp):
    view = CompareSliderWidget()
    view.resize(400, 300)
    before = _pixmap(value=50)
    after = _pixmap(value=200)
    view.set_images(before, after)
    assert view._has_content

    view.set_zoom(3.0)
    # ein einziger Transform für die ganze Szene -> beide Bilder zwangsläufig synchron
    assert view.zoom_percent == pytest.approx(300.0, rel=0.01)
    assert view._before_item.scale() == view._after_item.scale() == 1.0


def test_compare_slider_split_geometry_updates(qapp):
    view = CompareSliderWidget()
    view.resize(400, 300)
    view.set_images(_pixmap(w=200, h=100), _pixmap(w=200, h=100))

    view._split_ratio = 0.25
    view._update_split_geometry()
    assert view._clip_item.rect().width() == pytest.approx(50.0)
    assert view._divider_item.line().x1() == pytest.approx(50.0)

    view._split_ratio = 0.75
    view._update_split_geometry()
    assert view._clip_item.rect().width() == pytest.approx(150.0)


def test_compare_slider_divider_drag_updates_ratio_not_pan(qapp):
    view = CompareSliderWidget()
    view.resize(400, 200)
    view.set_images(_pixmap(w=200, h=100), _pixmap(w=200, h=100))
    view.fit_to_window()

    divider_x = view._divider_viewport_x()
    # Ziehen auf ein Viertel der Breite simulieren (Logik direkt aufgerufen,
    # nicht über echte Maus-Events, um robust offscreen zu bleiben)
    target_x = divider_x - 40
    view._update_split_from_viewport_x(target_x)
    assert view._split_ratio < 0.5


def test_compare_slider_no_images_has_placeholder(qapp):
    view = CompareSliderWidget()
    assert not view._has_content
    assert view.PLACEHOLDER_TEXT == "Keine Vorschau verfügbar"


def test_zoom_toolbar_bind_updates_label(qapp):
    view = ZoomableImageView()
    view.resize(400, 300)
    view.set_pixmap(_pixmap())
    toolbar = ZoomToolbar()
    toolbar.bind(view)
    view.zoom_100()
    assert toolbar.zoom_label.text() == "100 %"

    view.set_zoom(1.5)
    assert toolbar.zoom_label.text() == "150 %"


def test_zoom_toolbar_fit_button_calls_fit(qapp):
    view = ZoomableImageView()
    view.resize(400, 300)
    view.set_pixmap(_pixmap())
    view.set_zoom(5.0)
    toolbar = ZoomToolbar()
    toolbar.bind(view)
    toolbar.btn_fit.click()
    assert view.zoom_percent != pytest.approx(500.0)


def test_zoom_toolbar_100_button_resets_zoom(qapp):
    view = ZoomableImageView()
    view.resize(400, 300)
    view.set_pixmap(_pixmap())
    view.set_zoom(3.0)
    toolbar = ZoomToolbar()
    toolbar.bind(view)
    toolbar.btn_100.click()
    assert view.zoom_percent == pytest.approx(100.0, rel=0.001)
