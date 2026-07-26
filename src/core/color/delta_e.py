"""Wahrnehmungsorientierte Farbabstände: sRGB -> CIE Lab, Delta E (CIE76) (Prompt Abschnitt 10)."""
from __future__ import annotations

import numpy as np

_SRGB_TO_XYZ = np.array(
    [
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ],
    dtype=np.float64,
)

_D65_WHITE = np.array([0.95047, 1.0, 1.08883], dtype=np.float64)

_EPS = 216.0 / 24389.0
_KAPPA = 24389.0 / 27.0


def srgb_to_linear(rgb_0_1: np.ndarray) -> np.ndarray:
    return np.where(rgb_0_1 <= 0.04045, rgb_0_1 / 12.92, ((rgb_0_1 + 0.055) / 1.055) ** 2.4)


def _f_lab(t: np.ndarray) -> np.ndarray:
    return np.where(t > _EPS, np.cbrt(t), (_KAPPA * t + 16.0) / 116.0)


def rgb_array_to_lab(rgb: np.ndarray) -> np.ndarray:
    """Wandelt ein HxWx3-uint8-sRGB-Array in CIE-Lab (D65) um (float64)."""
    rgb_f = rgb.astype(np.float64) / 255.0
    linear = srgb_to_linear(rgb_f)
    xyz = linear @ _SRGB_TO_XYZ.T
    xyz_n = xyz / _D65_WHITE

    fx, fy, fz = _f_lab(xyz_n[..., 0]), _f_lab(xyz_n[..., 1]), _f_lab(xyz_n[..., 2])
    L = 116.0 * fy - 16.0
    a = 500.0 * (fx - fy)
    b = 200.0 * (fy - fz)
    return np.stack([L, a, b], axis=-1)


def delta_e_cie76(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
    return np.sqrt(np.sum((lab1 - lab2) ** 2, axis=-1))


def is_neutral_gray(lab: np.ndarray, max_chroma: float) -> np.ndarray:
    chroma = np.sqrt(lab[..., 1] ** 2 + lab[..., 2] ** 2)
    return chroma <= max_chroma


def is_skin_tone(lab: np.ndarray) -> np.ndarray:
    """Grobe Schätzung typischer Hautton-Bereiche in Lab (a* leicht positiv/rötlich, b* gelblich)."""
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    return (L > 25) & (L < 90) & (a > 2) & (a < 35) & (b > 8) & (b < 45) & (b > a * 0.4)
