from pathlib import Path

import numpy as np
import pytest

from src.config.defaults import ProcessingSettings
from src.core.analysis.image_loader import load_image
from src.core.color.color_pipeline import optimize_colors
from src.core.color.icc_manager import get_srgb_icc_bytes
from src.models.enums import ImageType
from src.models.report import ImageProcessingReport
from tests.fixtures.synthetic_images import make_saturated_out_of_gamut


def _make_report(image_type=ImageType.ILLUSTRATION) -> ImageProcessingReport:
    r = ImageProcessingReport()
    r.detected_type = image_type
    return r


def test_no_target_profile_leaves_image_unchanged(tmp_path: Path):
    img = make_saturated_out_of_gamut()
    p = tmp_path / "img.png"
    img.save(p)
    loaded = load_image(p)

    settings = ProcessingSettings()
    settings.color.target_profile_path = None
    report = _make_report()

    out, info = optimize_colors(loaded.array, loaded, settings, report)

    assert np.array_equal(out, loaded.array)
    assert info.target_icc_bytes is None
    assert any("Kein ICC-Zielprofil" in w for w in report.warnings)


def test_invalid_target_profile_path_falls_back_gracefully(tmp_path: Path):
    img = make_saturated_out_of_gamut()
    p = tmp_path / "img.png"
    img.save(p)
    loaded = load_image(p)

    settings = ProcessingSettings()
    settings.color.target_profile_path = str(tmp_path / "does_not_exist.icc")
    report = _make_report()

    out, info = optimize_colors(loaded.array, loaded, settings, report)

    assert out.shape == loaded.array.shape
    assert any("konnte nicht geladen werden" in w for w in report.warnings)


def test_round_trip_against_srgb_target_runs_and_is_low_deviation(tmp_path: Path):
    img = make_saturated_out_of_gamut()
    p = tmp_path / "img.png"
    img.save(p)
    loaded = load_image(p)

    target_icc_path = tmp_path / "target_srgb_copy.icc"
    target_icc_path.write_bytes(get_srgb_icc_bytes())

    settings = ProcessingSettings()
    settings.color.target_profile_path = str(target_icc_path)
    report = _make_report(ImageType.PHOTO)

    out, info = optimize_colors(loaded.array, loaded, settings, report)

    assert out.shape == loaded.array.shape
    assert info.target_icc_bytes is not None
    # sRGB -> sRGB Rundreise: minimale Abweichung erwartet
    assert report.out_of_gamut_after <= report.out_of_gamut_before + 1.0
    assert report.mean_delta_e < 5.0


def test_fully_transparent_image_skips_color_processing(tmp_path: Path):
    from tests.fixtures.synthetic_images import make_fully_transparent

    img = make_fully_transparent()
    p = tmp_path / "transparent.png"
    img.save(p)
    loaded = load_image(p)

    target_icc_path = tmp_path / "target.icc"
    target_icc_path.write_bytes(get_srgb_icc_bytes())
    settings = ProcessingSettings()
    settings.color.target_profile_path = str(target_icc_path)
    report = _make_report()

    out, info = optimize_colors(loaded.array, loaded, settings, report)
    assert out.shape == loaded.array.shape
