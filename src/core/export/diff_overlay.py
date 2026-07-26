"""Diff-Masken-Vorschau: entfernte/verstärkte Pixel farbig hervorgehoben.

Zeigt das Originalbild gedimmt als Kontext, mit den betroffenen Pixeln in
einer klaren Signalfarbe bei voller Deckkraft - für eine nachvollziehbare
Vorschau der automatischen Alpha-Bereinigung (Prompt Abschnitt 14).
"""
from __future__ import annotations

import numpy as np

REMOVED_HIGHLIGHT_COLOR = (230, 40, 40)  # Rot: entfernte Pixel
STRENGTHENED_HIGHLIGHT_COLOR = (40, 200, 90)  # Grün: verstärkte Pixel
GAMUT_WARNING_HIGHLIGHT_COLOR = (230, 30, 200)  # Magenta: außerhalb des Zielfarbraums


def generate_diff_overlay(
    context_rgba: np.ndarray,
    mask: np.ndarray,
    highlight_color: tuple[int, int, int],
    dim_factor: float = 0.35,
) -> np.ndarray:
    """Erzeugt eine RGBA-Vorschau: Kontextbild gedimmt, `mask`-Pixel farbig hervorgehoben."""
    out = context_rgba.astype(np.float32).copy()
    out[:, :, :3] *= dim_factor
    out[:, :, 3] *= dim_factor
    out = np.clip(out, 0, 255).astype(np.uint8)

    out[mask, 0] = highlight_color[0]
    out[mask, 1] = highlight_color[1]
    out[mask, 2] = highlight_color[2]
    out[mask, 3] = 255
    return out


def compute_removed_pixels_mask(alpha_before: np.ndarray, alpha_after: np.ndarray) -> np.ndarray:
    """Pixel, die sichtbar waren und durch die Bereinigung vollständig entfernt wurden."""
    return (alpha_before > 0) & (alpha_after == 0)


def compute_strengthened_pixels_mask(alpha_before: np.ndarray, alpha_after: np.ndarray) -> np.ndarray:
    """Pixel, die teiltransparent waren und auf volle Deckkraft gesetzt wurden."""
    return (alpha_before > 0) & (alpha_before < 255) & (alpha_after == 255)
