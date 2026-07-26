import numpy as np

from src.core.export.white_mask import generate_white_mask, recommend_choke_px


def test_mask_covers_visible_pixels_without_choke():
    rgba = np.zeros((20, 20, 4), dtype=np.uint8)
    rgba[5:15, 5:15, 3] = 255
    mask = generate_white_mask(rgba, choke_px=0)
    assert mask[10, 10] == 255
    assert mask[0, 0] == 0
    assert int((mask == 255).sum()) == 100


def test_choke_shrinks_mask():
    rgba = np.zeros((40, 40, 4), dtype=np.uint8)
    rgba[10:30, 10:30, 3] = 255
    mask_no_choke = generate_white_mask(rgba, choke_px=0)
    mask_choked = generate_white_mask(rgba, choke_px=2)
    assert int((mask_choked == 255).sum()) < int((mask_no_choke == 255).sum())


def test_recommend_choke_within_reasonable_bounds():
    small = recommend_choke_px(200, 200)
    large = recommend_choke_px(4000, 4000)
    assert 1.0 <= small <= 4.0
    assert 1.0 <= large <= 4.0
    assert large >= small
