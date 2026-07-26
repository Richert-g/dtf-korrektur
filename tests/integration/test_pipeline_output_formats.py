from pathlib import Path

from PIL import Image

from src.config.defaults import ProcessingSettings
from src.core.pipeline import process_image
from src.models.enums import OutputFormat
from tests.fixtures.synthetic_images import make_logo_with_white_halo

_FOGRA39 = "resources/profiles/CMYK/CoatedFOGRA39.icc"


def _process(tmp_path: Path, fmt: OutputFormat, **export_overrides):
    src = tmp_path / "logo.png"
    make_logo_with_white_halo().save(src)
    settings = ProcessingSettings()
    settings.export.output_format = fmt
    for key, value in export_overrides.items():
        setattr(settings.export, key, value)
    return process_image(src, settings, tmp_path / "out")


def test_plain_string_output_format_does_not_crash(tmp_path: Path):
    """Regression: OutputFormat erbt von str, daher kann settings.export.output_format
    aus manchen Quellen (z. B. einer PySide6-QComboBox, siehe main_window.py) als
    reiner str statt als Enum-Member ankommen. process_image() darf dabei nicht
    mit AttributeError abstuerzen (output_format.value wird intern aufgerufen)."""
    report = _process(tmp_path, "png_rgb")  # bewusst reiner str statt OutputFormat.PNG_RGB
    assert report.success is True
    assert report.output_format == "png_rgb"


def test_png_output_format_unchanged_default(tmp_path: Path):
    report = _process(tmp_path, OutputFormat.PNG_RGB)
    assert report.success is True
    assert report.output_path.suffix == ".png"
    with Image.open(report.output_path) as img:
        assert img.mode == "RGBA"


def test_tiff_output_format(tmp_path: Path):
    report = _process(tmp_path, OutputFormat.TIFF_RGB)
    assert report.success is True
    assert report.output_path.suffix == ".tiff"
    with Image.open(report.output_path) as img:
        assert img.mode == "RGBA"


def test_jpeg_output_format_warns_about_lost_transparency(tmp_path: Path):
    report = _process(tmp_path, OutputFormat.JPEG_RGB)
    assert report.success is True
    assert report.output_path.suffix == ".jpg"
    assert any("Transparenz" in w for w in report.warnings)
    with Image.open(report.output_path) as img:
        assert img.mode == "RGB"


def test_pdf_output_format_without_profile_fails_cleanly(tmp_path: Path):
    report = _process(tmp_path, OutputFormat.PDF_CMYK)
    assert report.success is False
    assert report.output_path is None
    assert any("ICC-Zielprofil" in e for e in report.errors)


def test_pdf_output_format_with_profile(tmp_path: Path):
    src = tmp_path / "logo.png"
    make_logo_with_white_halo().save(src)
    settings = ProcessingSettings()
    settings.export.output_format = OutputFormat.PDF_CMYK
    settings.color.target_profile_path = _FOGRA39

    report = process_image(src, settings, tmp_path / "out")
    assert report.success is True
    assert report.output_path.suffix == ".pdf"
    assert report.pdf_validated is True
    assert report.output_format == "pdf_cmyk"
