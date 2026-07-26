"""Weißunterlegungsmaske als Vorschau-/Hilfsdatei (Prompt Abschnitt 11).

Wichtig: Dies ist nur eine Vorschau/Hilfsdatei. Die endgültige Weißkanalsteuerung
erfolgt üblicherweise im DTF-RIP - siehe Prompt Abschnitt 26.
"""
from __future__ import annotations

import cv2
import numpy as np


def recommend_choke_px(width: int, height: int) -> float:
    """Grobe, größenabhängige Empfehlung für den Weißunterlegungs-Choke in Pixeln."""
    smaller_side = min(width, height)
    value = smaller_side / 500.0
    return float(np.clip(value, 1.0, 4.0))


def generate_white_mask(rgba: np.ndarray, choke_px: float) -> np.ndarray:
    """Erzeugt eine Graustufen-Maske (weiß = wird unterlegt) mit optionalem Choke."""
    alpha = rgba[:, :, 3]
    mask = (alpha > 0).astype(np.uint8) * 255

    if choke_px > 0:
        k = max(1, int(round(choke_px)))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k * 2 + 1, k * 2 + 1))
        mask = cv2.erode(mask, kernel)

    return mask
