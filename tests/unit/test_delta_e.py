import numpy as np

from src.core.color.delta_e import delta_e_cie76, is_neutral_gray, is_skin_tone, rgb_array_to_lab


def test_black_vs_black_zero_delta():
    black = np.zeros((1, 1, 3), dtype=np.uint8)
    lab = rgb_array_to_lab(black)
    assert delta_e_cie76(lab, lab)[0, 0] < 1e-6


def test_white_vs_black_large_delta():
    white = np.full((1, 1, 3), 255, dtype=np.uint8)
    black = np.zeros((1, 1, 3), dtype=np.uint8)
    lab_w = rgb_array_to_lab(white)
    lab_b = rgb_array_to_lab(black)
    delta = delta_e_cie76(lab_w, lab_b)[0, 0]
    assert delta > 90  # L von ~100 auf 0


def test_similar_colors_small_delta():
    a = np.array([[[200, 100, 50]]], dtype=np.uint8)
    b = np.array([[[202, 101, 49]]], dtype=np.uint8)
    delta = delta_e_cie76(rgb_array_to_lab(a), rgb_array_to_lab(b))[0, 0]
    assert delta < 3.0


def test_neutral_gray_detected():
    gray = rgb_array_to_lab(np.array([[[128, 128, 128]]], dtype=np.uint8))
    assert is_neutral_gray(gray, max_chroma=4.0)[0, 0]


def test_saturated_color_not_neutral_gray():
    red = rgb_array_to_lab(np.array([[[255, 0, 0]]], dtype=np.uint8))
    assert not is_neutral_gray(red, max_chroma=4.0)[0, 0]


def test_typical_skin_tone_detected():
    skin = rgb_array_to_lab(np.array([[[224, 172, 135]]], dtype=np.uint8))
    assert is_skin_tone(skin)[0, 0]


def test_pure_blue_not_skin_tone():
    blue = rgb_array_to_lab(np.array([[[0, 0, 255]]], dtype=np.uint8))
    assert not is_skin_tone(blue)[0, 0]
