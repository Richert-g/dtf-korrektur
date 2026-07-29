import numpy as np

from src.config.defaults import GamutThresholds
from src.core.color.saturation_optimizer import reduce_saturation_pass

CFG = GamutThresholds()


def test_no_out_of_gamut_pixels_no_change():
    rgb = np.full((4, 4, 3), 100, dtype=np.uint8)
    delta = np.zeros((4, 4), dtype=np.float64)
    mask = np.zeros((4, 4), dtype=bool)
    result = reduce_saturation_pass(rgb, delta, mask, CFG)
    assert result.adjusted_pixel_count == 0
    assert np.array_equal(result.rgb, rgb)


def test_saturated_out_of_gamut_pixel_gets_desaturated():
    """Prüft den Reduktionsmechanismus selbst mit einer bewusst von Null
    verschiedenen Konfiguration - der Standardwert von max_auto_saturation_reduction
    ist inzwischen 0.0 (Funktion standardmäßig deaktiviert), das modulweite CFG
    würde hier also nie eine Änderung zeigen."""
    rgb = np.zeros((2, 2, 3), dtype=np.uint8)
    rgb[:, :] = [255, 0, 0]  # sehr gesättigtes Rot
    delta = np.full((2, 2), 10.0)
    mask = np.ones((2, 2), dtype=bool)
    cfg = GamutThresholds(max_auto_saturation_reduction=0.3)
    result = reduce_saturation_pass(rgb, delta, mask, cfg)
    assert result.adjusted_pixel_count == 4
    # Sättigung muss abgenommen haben (G und B Kanal steigen bei Entsättigung von reinem Rot)
    assert result.rgb[0, 0, 1] > rgb[0, 0, 1] or result.rgb[0, 0, 2] > rgb[0, 0, 2]


def test_neutral_gray_pixel_protected():
    rgb = np.full((2, 2, 3), 128, dtype=np.uint8)
    delta = np.full((2, 2), 10.0)
    mask = np.ones((2, 2), dtype=bool)
    result = reduce_saturation_pass(rgb, delta, mask, CFG)
    assert np.array_equal(result.rgb, rgb)
    assert result.adjusted_pixel_count == 0


def test_very_dark_pixel_protected():
    rgb = np.full((2, 2, 3), 5, dtype=np.uint8)
    rgb[:, :, 0] = 8
    delta = np.full((2, 2), 10.0)
    mask = np.ones((2, 2), dtype=bool)
    result = reduce_saturation_pass(rgb, delta, mask, CFG)
    assert result.adjusted_pixel_count == 0


def test_reduction_never_exceeds_configured_maximum():
    rgb = np.zeros((1, 1, 3), dtype=np.uint8)
    rgb[0, 0] = [255, 60, 0]  # gesättigtes Orange
    delta = np.array([[1000.0]])  # extreme Abweichung
    mask = np.array([[True]])
    cfg = GamutThresholds(max_auto_saturation_reduction=0.3)
    result = reduce_saturation_pass(rgb, delta, mask, cfg)

    import cv2

    s_before = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)[0, 0, 1]
    s_after = cv2.cvtColor(result.rgb, cv2.COLOR_RGB2HSV)[0, 0, 1]
    assert s_after >= s_before * (1 - cfg.max_auto_saturation_reduction) - 2
