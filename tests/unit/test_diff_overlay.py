import numpy as np

from src.core.export.diff_overlay import (
    REMOVED_HIGHLIGHT_COLOR,
    STRENGTHENED_HIGHLIGHT_COLOR,
    compute_removed_pixels_mask,
    compute_strengthened_pixels_mask,
    generate_diff_overlay,
)


def test_removed_mask_detects_visible_to_transparent():
    before = np.array([[255, 0, 128]], dtype=np.uint8)
    after = np.array([[0, 0, 128]], dtype=np.uint8)
    mask = compute_removed_pixels_mask(before, after)
    assert mask.tolist() == [[True, False, False]]


def test_strengthened_mask_detects_partial_to_full():
    before = np.array([[128, 255, 0]], dtype=np.uint8)
    after = np.array([[255, 255, 0]], dtype=np.uint8)
    mask = compute_strengthened_pixels_mask(before, after)
    assert mask.tolist() == [[True, False, False]]


def test_generate_diff_overlay_highlights_masked_pixels():
    context = np.zeros((2, 2, 4), dtype=np.uint8)
    context[:, :, :3] = 200
    context[:, :, 3] = 255
    mask = np.array([[True, False], [False, False]])

    out = generate_diff_overlay(context, mask, REMOVED_HIGHLIGHT_COLOR)

    assert tuple(out[0, 0, :3]) == REMOVED_HIGHLIGHT_COLOR
    assert out[0, 0, 3] == 255
    # nicht maskierte Pixel sind gedimmt, nicht mehr im Original-Farbton
    assert out[1, 1, 0] < 200


def test_generate_diff_overlay_strengthened_color_distinct():
    context = np.zeros((1, 1, 4), dtype=np.uint8)
    context[:, :, 3] = 255
    mask = np.array([[True]])
    out = generate_diff_overlay(context, mask, STRENGTHENED_HIGHLIGHT_COLOR)
    assert tuple(out[0, 0, :3]) == STRENGTHENED_HIGHLIGHT_COLOR
