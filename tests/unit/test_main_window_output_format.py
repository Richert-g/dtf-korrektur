import numpy as np
from PySide6.QtWidgets import QApplication

from src.app.ui.main_window import MainWindow, _format_picker_result, _rgba_to_hex
from src.models.enums import OutputFormat, PresetName


def _app():
    return QApplication.instance() or QApplication([])


def test_output_format_combo_syncs_with_dtf_king_preset():
    _app()
    w = MainWindow()

    assert w.output_format_combo.currentData() == OutputFormat.PNG_RGB

    idx = w.preset_combo.findData(PresetName.DTF_KING_ISO_COATED_V2)
    w.preset_combo.setCurrentIndex(idx)
    assert w.output_format_combo.currentData() == OutputFormat.PDF_CMYK

    idx_auto = w.preset_combo.findData(PresetName.DTF_AUTO)
    w.preset_combo.setCurrentIndex(idx_auto)
    assert w.output_format_combo.currentData() == OutputFormat.PNG_RGB


def test_manual_output_format_selection_updates_settings():
    _app()
    w = MainWindow()

    idx = w.output_format_combo.findData(OutputFormat.TIFF_RGB)
    w.output_format_combo.setCurrentIndex(idx)
    assert w.controller.settings.export.output_format == OutputFormat.TIFF_RGB


def test_manual_output_format_selection_yields_real_enum_not_plain_str():
    """Regression: QComboBox.currentData() kann für str-basierte Enums (siehe
    RenderingIntent-Absturz) ein reines str-Objekt statt des Enum-Members
    liefern. settings.export.output_format.value wird in pipeline.py direkt
    aufgerufen - ein reiner String dort würde mit AttributeError abstürzen."""
    _app()
    w = MainWindow()

    idx = w.output_format_combo.findData(OutputFormat.PDF_CMYK)
    w.output_format_combo.setCurrentIndex(idx)

    fmt = w.controller.settings.export.output_format
    assert type(fmt) is OutputFormat
    assert fmt.value == "pdf_cmyk"


def test_rgba_to_hex():
    assert _rgba_to_hex(np.array([255, 0, 128, 255])) == "#FF0080"
    assert _rgba_to_hex(np.array([0, 0, 0, 0])) == "#000000"


def test_format_picker_result_contains_hex_and_rgb_for_both_states():
    before = np.array([255, 0, 0, 255], dtype=np.uint8)
    after = np.array([10, 20, 30, 128], dtype=np.uint8)
    html = _format_picker_result(4, 7, before, after)

    assert "(4, 7)" in html
    assert "#FF0000" in html
    assert "#0A141E" in html
    assert "Alpha=255" in html
    assert "Alpha=128" in html


def test_compare_pixel_picked_maps_normalized_coordinates_to_full_resolution():
    _app()
    w = MainWindow()

    original = np.zeros((20, 40, 4), dtype=np.uint8)
    original[:, :20] = [255, 0, 0, 255]
    original[:, 20:] = [0, 255, 0, 255]
    result = np.zeros((20, 40, 4), dtype=np.uint8)
    result[:, :20] = [0, 0, 255, 255]
    result[:, 20:] = [255, 255, 0, 255]

    w._current_original_rgba = original
    w._current_result_rgba = result

    w._on_compare_pixel_picked(0.1, 0.5)  # linke Haelfte
    assert "#FF0000" in w.picker_result_label.text()
    assert "#0000FF" in w.picker_result_label.text()

    w._on_compare_pixel_picked(0.9, 0.5)  # rechte Haelfte
    assert "#00FF00" in w.picker_result_label.text()
    assert "#FFFF00" in w.picker_result_label.text()
