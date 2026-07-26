"""Gezielte, lokale Sättigungsreduktion nur in Farbraum-Konfliktbereichen (Prompt Abschnitt 10).

Keine pauschale globale Sättigungsreduktion: nur Pixel, die tatsächlich außerhalb
des Zielfarbraums liegen, werden angepasst - und auch dort nur begrenzt und unter
Schutz von Hauttönen, neutralen Grauwerten und sehr dunklen (Schwarz-)Tönen.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from src.config.defaults import GamutThresholds
from src.core.color.delta_e import is_neutral_gray, is_skin_tone, rgb_array_to_lab

# Gelb/Orange-Bereich im OpenCV-Hue-Raum (0-179) - hier besonders sorgfältig prüfen
_YELLOW_ORANGE_HUE_RANGE = (10, 40)


@dataclass
class SaturationAdjustmentResult:
    rgb: np.ndarray
    adjusted_pixel_count: int
    yellow_orange_adjusted_count: int


def reduce_saturation_pass(
    rgb: np.ndarray, delta_e: np.ndarray, out_of_gamut_mask: np.ndarray, cfg: GamutThresholds
) -> SaturationAdjustmentResult:
    if not out_of_gamut_mask.any():
        return SaturationAdjustmentResult(rgb=rgb.copy(), adjusted_pixel_count=0, yellow_orange_adjusted_count=0)

    lab = rgb_array_to_lab(rgb)
    protect_mask = np.zeros(rgb.shape[:2], dtype=bool)
    if cfg.protect_neutral_grays:
        protect_mask |= is_neutral_gray(lab, cfg.neutral_gray_chroma_max)
    if cfg.protect_skin_tones:
        protect_mask |= is_skin_tone(lab)

    hsv = cv2.cvtColor(np.ascontiguousarray(rgb), cv2.COLOR_RGB2HSV).astype(np.float32)
    # sehr dunkle Pixel nicht antasten (Schwarztöne nicht unnötig verändern)
    protect_mask |= hsv[:, :, 2] < 15

    reduce_target = out_of_gamut_mask & ~protect_mask
    if not reduce_target.any():
        return SaturationAdjustmentResult(rgb=rgb.copy(), adjusted_pixel_count=0, yellow_orange_adjusted_count=0)

    max_delta = float(delta_e[reduce_target].max()) if reduce_target.any() else 1.0
    severity = np.clip(delta_e / max(max_delta, 1e-6), 0.0, 1.0)
    reduction = severity * cfg.max_auto_saturation_reduction

    new_hsv = hsv.copy()
    s = new_hsv[:, :, 1]
    s[reduce_target] = s[reduce_target] * (1.0 - reduction[reduce_target])
    new_hsv[:, :, 1] = s
    new_hsv = np.clip(new_hsv, 0, 255).astype(np.uint8)
    new_rgb = cv2.cvtColor(new_hsv, cv2.COLOR_HSV2RGB)

    hue = hsv[:, :, 0]
    yellow_orange_mask = reduce_target & (hue >= _YELLOW_ORANGE_HUE_RANGE[0]) & (hue <= _YELLOW_ORANGE_HUE_RANGE[1])

    return SaturationAdjustmentResult(
        rgb=new_rgb,
        adjusted_pixel_count=int(reduce_target.sum()),
        yellow_orange_adjusted_count=int(yellow_orange_mask.sum()),
    )
