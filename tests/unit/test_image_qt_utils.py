import numpy as np

from src.utils.image_qt import checkerboard_background, composite_over_background, downscale_for_preview


def test_downscale_reduces_large_image():
    rgba = np.zeros((3000, 2000, 4), dtype=np.uint8)
    out = downscale_for_preview(rgba, max_dimension=1000)
    assert max(out.shape[:2]) <= 1000
    assert abs((out.shape[0] / out.shape[1]) - (3000 / 2000)) < 0.01


def test_downscale_leaves_small_image_unchanged():
    rgba = np.zeros((100, 80, 4), dtype=np.uint8)
    out = downscale_for_preview(rgba, max_dimension=1000)
    assert out.shape == rgba.shape


def test_checkerboard_background_shape():
    bg = checkerboard_background(20, 10)
    assert bg.shape == (10, 20, 4)


def test_composite_over_background_opaque_result():
    rgba = np.zeros((4, 4, 4), dtype=np.uint8)
    rgba[:, :, 3] = 128
    rgba[:, :, 0] = 255
    out = composite_over_background(rgba, (0, 0, 0))
    assert (out[:, :, 3] == 255).all()
    assert out[0, 0, 0] < 255  # durch schwarzen Hintergrund abgedunkelt
