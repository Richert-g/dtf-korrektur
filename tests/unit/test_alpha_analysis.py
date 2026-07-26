import numpy as np

from src.config.defaults import AlphaThresholds
from src.core.analysis.alpha_analysis import analyze_alpha_channel
from tests.fixtures.synthetic_images import (
    make_fully_opaque,
    make_fully_transparent,
    make_large_soft_shadow,
    make_logo_with_white_halo,
    make_single_semi_transparent_edge_pixel,
    make_small_islands,
    make_transparent_holes,
)

THRESHOLDS = AlphaThresholds()


def _arr(img):
    return np.array(img.convert("RGBA"))


def test_fully_transparent_image():
    stats = analyze_alpha_channel(_arr(make_fully_transparent()), THRESHOLDS)
    assert stats.fully_transparent_count == 32 * 32
    assert stats.semi_transparent_count == 0
    assert stats.fully_opaque_count == 0


def test_fully_opaque_image():
    stats = analyze_alpha_channel(_arr(make_fully_opaque()), THRESHOLDS)
    assert stats.fully_opaque_count == 32 * 32
    assert stats.semi_transparent_count == 0
    assert stats.alpha_present is False or stats.fully_transparent_count == 0


def test_single_semi_transparent_edge_pixel():
    stats = analyze_alpha_channel(_arr(make_single_semi_transparent_edge_pixel()), THRESHOLDS)
    assert stats.semi_transparent_count == 1
    assert stats.mostly_at_edges is True


def test_large_soft_shadow_detected():
    stats = analyze_alpha_channel(_arr(make_large_soft_shadow()), THRESHOLDS)
    assert stats.semi_transparent_count > 0
    assert stats.regions.covers_large_area is True
    assert stats.likely_soft_shadow is True
    assert stats.likely_hard_graphic is False


def test_logo_with_halo_is_hard_graphic():
    stats = analyze_alpha_channel(_arr(make_logo_with_white_halo()), THRESHOLDS)
    assert stats.semi_transparent_count > 0
    assert stats.mostly_at_edges is True


def test_small_islands_detected():
    stats = analyze_alpha_channel(_arr(make_small_islands()), THRESHOLDS)
    assert stats.small_island_count >= 4


def test_transparent_holes_detected():
    stats = analyze_alpha_channel(_arr(make_transparent_holes()), THRESHOLDS)
    assert stats.small_hole_count >= 2


def test_weak_alpha_counted_separately():
    arr = np.zeros((16, 16, 4), dtype=np.uint8)
    arr[:, :, 3] = 255
    arr[0, 0, 3] = 3  # sehr schwaches Pixel
    stats = analyze_alpha_channel(arr, THRESHOLDS)
    assert stats.weak_alpha_count == 1
