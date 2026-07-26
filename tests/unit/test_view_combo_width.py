import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QComboBox

from src.app.ui.main_window import (
    ALL_VIEW_MODE_LABELS,
    VIEW_COMBO_FALLBACK_MIN_WIDTH_PX,
    VIEW_WHITE_MASK,
    _compute_view_combo_min_width,
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_all_labels_present_and_unique(qapp):
    assert len(ALL_VIEW_MODE_LABELS) == len(set(ALL_VIEW_MODE_LABELS))
    assert VIEW_WHITE_MASK in ALL_VIEW_MODE_LABELS  # der längste erwartete Eintrag


def test_min_width_covers_longest_label(qapp):
    combo = QComboBox()
    from PySide6.QtGui import QFontMetrics

    metrics = QFontMetrics(combo.font())
    longest = max(ALL_VIEW_MODE_LABELS, key=lambda t: metrics.horizontalAdvance(t))

    width = _compute_view_combo_min_width(combo, ALL_VIEW_MODE_LABELS)
    combo.resize(width, combo.height())

    # Die Breite muss die Textbreite des längsten Eintrags plus Rand abdecken
    assert width >= metrics.horizontalAdvance(longest)
    assert width >= VIEW_COMBO_FALLBACK_MIN_WIDTH_PX


def test_min_width_respects_fallback_for_short_labels(qapp):
    combo = QComboBox()
    width = _compute_view_combo_min_width(combo, ["A", "B"])
    assert width == VIEW_COMBO_FALLBACK_MIN_WIDTH_PX


def test_no_text_is_truncated_with_ellipsis(qapp):
    """Regressionstest für 'Auf weißem Textil' & Co. - keine '…'-Kürzung."""
    combo = QComboBox()
    width = _compute_view_combo_min_width(combo, ALL_VIEW_MODE_LABELS)
    combo.setMinimumWidth(width)
    combo.addItems(ALL_VIEW_MODE_LABELS)

    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFontMetrics

    metrics = QFontMetrics(combo.font())
    for label in ALL_VIEW_MODE_LABELS:
        elided = metrics.elidedText(label, Qt.TextElideMode.ElideRight, width - 40)
        assert elided == label, f"Text würde bei Breite {width} abgeschnitten: {label!r} -> {elided!r}"
