import numpy as np
import pytest

from src.core.export.print_size import (
    compute_print_size,
    mm_to_points,
    required_pixel_dimensions,
    resize_rgba_to_print_size,
)


def test_native_size_at_target_dpi_when_no_mm_given():
    result = compute_print_size(pixel_width=3000, pixel_height=1500, target_dpi=300.0)
    assert result.effective_dpi == pytest.approx(300.0)
    assert result.meets_target_dpi is True
    assert result.width_mm == pytest.approx(3000 / 300.0 * 25.4)
    assert result.height_mm == pytest.approx(1500 / 300.0 * 25.4)


def test_height_computed_proportionally_from_width():
    result = compute_print_size(pixel_width=2000, pixel_height=1000, target_dpi=300.0, width_mm=100.0)
    assert result.height_mm == pytest.approx(50.0)


def test_width_computed_proportionally_from_height():
    result = compute_print_size(pixel_width=2000, pixel_height=1000, target_dpi=300.0, height_mm=50.0)
    assert result.width_mm == pytest.approx(100.0)


def test_dpi_warning_matches_required_wording_example():
    # 28cm breit, ~238dpi -> Pixelbreite = 28/25.4*238
    px_w = round(280.0 / 25.4 * 238)
    result = compute_print_size(pixel_width=px_w, pixel_height=1000, target_dpi=300.0, width_mm=280.0)
    assert result.meets_target_dpi is False
    assert result.warning is not None
    assert "28.0 cm Breite" in result.warning
    assert "238 dpi" in result.warning
    assert "300 dpi" in result.warning


def test_meets_target_dpi_when_enough_pixels():
    result = compute_print_size(pixel_width=4000, pixel_height=2000, target_dpi=300.0, width_mm=100.0)
    assert result.meets_target_dpi is True
    assert result.warning is None


def test_required_pixel_dimensions():
    w, h = required_pixel_dimensions(width_mm=25.4, height_mm=25.4, target_dpi=300.0)
    assert w == 300
    assert h == 300


def test_resize_never_upscales_without_explicit_flag():
    rgba = np.zeros((50, 50, 4), dtype=np.uint8)
    # Zielgröße würde 300x300px benötigen (viel mehr als die 50x50 vorhandenen)
    result, resized = resize_rgba_to_print_size(rgba, width_mm=25.4, height_mm=25.4, target_dpi=300.0, allow_upscale=False)
    assert resized is False
    assert result.shape == (50, 50, 4)


def test_resize_upscales_when_explicitly_allowed():
    rgba = np.zeros((50, 50, 4), dtype=np.uint8)
    result, resized = resize_rgba_to_print_size(rgba, width_mm=25.4, height_mm=25.4, target_dpi=300.0, allow_upscale=True)
    assert resized is True
    assert result.shape == (300, 300, 4)


def test_resize_downscales_automatically_without_flag():
    rgba = np.zeros((600, 600, 4), dtype=np.uint8)
    result, resized = resize_rgba_to_print_size(rgba, width_mm=25.4, height_mm=25.4, target_dpi=300.0, allow_upscale=False)
    assert resized is True
    assert result.shape == (300, 300, 4)


def test_mm_to_points():
    assert mm_to_points(25.4) == pytest.approx(72.0)


def test_invalid_pixel_dimensions_raise():
    with pytest.raises(ValueError):
        compute_print_size(pixel_width=0, pixel_height=10, target_dpi=300.0)
