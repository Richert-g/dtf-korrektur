from pathlib import Path

import numpy as np
from PIL import Image
from PySide6.QtWidgets import QApplication

from src.app.ui.main_window import VIEW_DTF_KING_SOFTPROOF, VIEW_ORIGINAL, VIEW_RESULT, MainWindow
from src.models.report import ImageProcessingReport


def _app():
    return QApplication.instance() or QApplication([])


def _make_report(tmp_path: Path, source_name: str = "motif.png") -> ImageProcessingReport:
    out_root = tmp_path / "out"
    (out_root / "optimized").mkdir(parents=True)
    (out_root / "previews").mkdir(parents=True)

    source_path = tmp_path / source_name
    arr = np.zeros((10, 10, 4), dtype=np.uint8)
    arr[:, :, :3] = [30, 200, 60]
    arr[:, :, 3] = 255
    Image.fromarray(arr, mode="RGBA").save(source_path)

    softproof = np.zeros((10, 10, 4), dtype=np.uint8)
    softproof[:, :, :3] = [80, 170, 65]
    softproof[:, :, 3] = 255
    Image.fromarray(softproof, mode="RGBA").save(out_root / "previews" / "motif_softproof.png")

    report = ImageProcessingReport(source_path=source_path)
    report.output_format = "pdf_cmyk"
    report.output_path = out_root / "optimized" / "motif_dtf_king_iso_coated_v2.pdf"
    report.output_path.write_bytes(b"%PDF-fake")  # kein echtes PDF - nur damit load_image() sauber scheitert
    report.success = True
    return report


def test_load_result_preview_populates_softproof_for_pdf_report(tmp_path: Path):
    _app()
    w = MainWindow()
    report = _make_report(tmp_path)

    w._load_result_preview(report)

    assert w._current_result_rgba is None  # PDF ist kein ladbares RGB-Bild
    assert w._current_softproof_rgba is not None
    assert w.view_mode_combo.currentText() == VIEW_DTF_KING_SOFTPROOF


def test_load_result_preview_view_mode_list_omits_dead_rgb_only_entries(tmp_path: Path):
    _app()
    w = MainWindow()
    report = _make_report(tmp_path)

    w._load_result_preview(report)

    items = [w.view_mode_combo.itemText(i) for i in range(w.view_mode_combo.count())]
    assert VIEW_ORIGINAL in items
    assert VIEW_DTF_KING_SOFTPROOF in items
    assert VIEW_RESULT not in items  # kein RGB-Ergebnis vorhanden -> kein toter Menüpunkt


def test_load_result_preview_still_defaults_to_result_for_normal_png_report(tmp_path: Path):
    _app()
    w = MainWindow()
    out_root = tmp_path / "out"
    (out_root / "optimized").mkdir(parents=True)

    source_path = tmp_path / "logo.png"
    arr = np.zeros((10, 10, 4), dtype=np.uint8)
    arr[:, :, 3] = 255
    Image.fromarray(arr, mode="RGBA").save(source_path)

    result_path = out_root / "optimized" / "logo_dtf_optimized.png"
    Image.fromarray(arr, mode="RGBA").save(result_path)

    report = ImageProcessingReport(source_path=source_path)
    report.output_format = "png_rgb"
    report.output_path = result_path
    report.success = True

    w._load_result_preview(report)

    assert w._current_result_rgba is not None
    assert w.view_mode_combo.currentText() == VIEW_RESULT
