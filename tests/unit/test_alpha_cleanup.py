import numpy as np

from src.config.defaults import ProcessingSettings
from src.core.alpha.alpha_cleanup import clean_alpha
from src.models.enums import AlphaMode, ImageType
from tests.fixtures.synthetic_images import (
    make_large_soft_shadow,
    make_logo_with_white_halo,
    make_small_islands,
    make_transparent_holes,
)


def _arr(img):
    return np.array(img.convert("RGBA"))


def test_noise_only_removes_only_weak_pixels():
    arr = np.zeros((8, 8, 4), dtype=np.uint8)
    arr[:, :, 3] = 200
    arr[0, 0, 3] = 3
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.NOISE_ONLY
    result = clean_alpha(arr, ImageType.PHOTO, settings, report=None)
    assert result.rgba[0, 0, 3] == 0
    assert result.rgba[1, 1, 3] == 200  # unverändert
    assert result.removed_pixel_count == 1


def test_hard_edge_binarizes_alpha():
    arr = _arr(make_logo_with_white_halo())
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.HARD_EDGE
    settings.alpha.edge_feather_radius = 0  # exakte Prüfung ohne gewollte Kanten-Weichzeichnung
    result = clean_alpha(arr, ImageType.HARD_LOGO, settings, report=None)
    unique_values = set(np.unique(result.rgba[:, :, 3]).tolist())
    assert unique_values <= {0, 255}


def test_hard_edge_removes_small_islands():
    arr = _arr(make_small_islands())
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.HARD_EDGE
    settings.alpha.edge_feather_radius = 0  # exakte Prüfung ohne Weichzeichnung
    result = clean_alpha(arr, ImageType.HARD_LOGO, settings, report=None)
    assert result.removed_islands >= 4


def test_hard_edge_closes_small_holes():
    arr = _arr(make_transparent_holes())
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.HARD_EDGE
    settings.alpha.edge_feather_radius = 0
    result = clean_alpha(arr, ImageType.HARD_LOGO, settings, report=None)
    assert result.closed_holes >= 2


def test_auto_mode_does_not_binarize_soft_shadow():
    """Sicherheitsregel: große Schattenflächen dürfen nicht binarisiert werden (Prompt Abschnitt 19)."""
    arr = _arr(make_large_soft_shadow())
    settings = ProcessingSettings()  # AUTO
    result = clean_alpha(arr, ImageType.SOFT_SHADOW, settings, report=None)
    unique_values = np.unique(result.rgba[:, :, 3])
    # weiterhin viele Zwischenwerte vorhanden -> keine Binarisierung
    assert len(unique_values) > 5


def test_soft_cleanup_preserves_true_midrange_alpha():
    arr = np.zeros((16, 16, 4), dtype=np.uint8)
    arr[:, :, 3] = 140  # echter mittlerer Alpha-Wert (~55%), muss erhalten bleiben
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.SOFT_CLEANUP
    result = clean_alpha(arr, ImageType.ILLUSTRATION, settings, report=None)
    assert result.rgba[5, 5, 3] == 140
