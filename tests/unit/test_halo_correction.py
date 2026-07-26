import numpy as np

from src.config.defaults import HaloThresholds
from src.core.halo.halo_correction import correct_halo
from tests.fixtures.synthetic_images import (
    make_black_motif_gray_edge,
    make_illustration_soft_edge,
    make_large_soft_shadow,
    make_logo_with_white_halo,
)

THRESH = HaloThresholds()


def _arr(img):
    return np.array(img.convert("RGBA"))


def test_white_halo_around_black_circle_is_darkened():
    arr = _arr(make_logo_with_white_halo())
    alpha = arr[:, :, 3]
    halo_band = (alpha > 0) & (alpha < 255)
    before_brightness = arr[:, :, :3][halo_band].mean()

    corrected, changed = correct_halo(arr, THRESH, report=None)
    after_brightness = corrected[:, :, :3][halo_band].mean()

    assert changed > 0
    assert after_brightness < before_brightness  # weniger weiß, näher am schwarzen Kern


def test_black_motif_gray_edge_pulled_towards_black():
    arr = _arr(make_black_motif_gray_edge())
    alpha = arr[:, :, 3]
    edge_band = (alpha > 0) & (alpha < 255)
    before = arr[:, :, :3][edge_band].mean()

    corrected, changed = correct_halo(arr, THRESH, report=None)
    after = corrected[:, :, :3][edge_band].mean()

    assert changed > 0
    assert after < before


def test_illustration_soft_edge_runs_without_error():
    arr = _arr(make_illustration_soft_edge())
    corrected, _changed = correct_halo(arr, THRESH, report=None)
    assert corrected.shape == arr.shape


def test_soft_shadow_interior_not_destroyed():
    """Der weiche Schattenbereich weit entfernt vom harten Motiv darf nicht verändert werden."""
    arr = _arr(make_large_soft_shadow())
    h, w = arr.shape[:2]

    # Punkt deutlich unterhalb des harten Motivs, weit im Inneren der Schattenfläche
    shadow_point = (int(h * 0.85), int(w * 0.5))
    before_pixel = arr[shadow_point].copy()

    corrected, _ = correct_halo(arr, THRESH, report=None)
    after_pixel = corrected[shadow_point]

    assert tuple(before_pixel) == tuple(after_pixel)


def test_alpha_channel_never_modified_by_halo_correction():
    arr = _arr(make_logo_with_white_halo())
    corrected, _ = correct_halo(arr, THRESH, report=None)
    assert np.array_equal(arr[:, :, 3], corrected[:, :, 3])


def test_disabled_halo_correction_is_noop():
    arr = _arr(make_logo_with_white_halo())
    disabled = HaloThresholds(enabled=False)
    corrected, changed = correct_halo(arr, disabled, report=None)
    assert changed == 0
    assert np.array_equal(arr, corrected)
