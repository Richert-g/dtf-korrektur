"""Farbsaum-/Halo-Korrektur an halbtransparenten Außenkanten (Prompt Abschnitt 8).

Vorgehen (lokale Farbfortschreibung / Edge-Color-Propagation):
1. Randpixel = Pixel mit Alpha im halbtransparenten Bereich.
2. Iterative, radiusbegrenzte Ausbreitung der Farbe deckender Nachbarpixel
   nach außen (ähnlich einem Weichzeichnungs-"Push-Pull").
3. Nur die RGB-Werte der Randpixel werden angepasst - der Alpha-Wert bleibt
   unverändert und wird erst in der nachfolgenden Alpha-Bereinigung verändert.
4. Pixel ohne erreichbaren deckenden Nachbarn (z. B. isolierte dünne Details,
   die komplett von anderen halbtransparenten Pixeln umgeben sind) bleiben
   unangetastet, damit Details nicht zerstört werden.
"""
from __future__ import annotations

import cv2
import numpy as np

from src.config.defaults import HaloThresholds
from src.models.report import ImageProcessingReport


def correct_halo(
    rgba: np.ndarray, thresholds: HaloThresholds, report: ImageProcessingReport | None = None
) -> tuple[np.ndarray, int]:
    if not thresholds.enabled:
        return rgba, 0

    alpha = rgba[:, :, 3]
    edge_mask = (alpha >= thresholds.edge_alpha_low) & (alpha <= thresholds.edge_alpha_high)
    if not edge_mask.any():
        return rgba, 0

    opaque_mask = alpha >= thresholds.inner_neighbor_min_alpha
    if not opaque_mask.any():
        return rgba, 0

    rgb = rgba[:, :, :3].astype(np.float32)
    mask = opaque_mask.astype(np.float32)
    color = rgb * mask[..., None]

    radius = max(1, thresholds.search_radius_px)
    for _ in range(radius):
        sum_color = cv2.boxFilter(color, ddepth=-1, ksize=(3, 3), normalize=False, borderType=cv2.BORDER_CONSTANT)
        sum_mask = cv2.boxFilter(mask, ddepth=-1, ksize=(3, 3), normalize=False, borderType=cv2.BORDER_CONSTANT)
        sum_mask_safe = np.maximum(sum_mask, 1e-6)
        filled = sum_color / sum_mask_safe[..., None]

        newly_filled = (mask == 0) & (sum_mask > 0)
        color = np.where(newly_filled[..., None], filled, color)
        mask = np.where(newly_filled, 1.0, mask)

    apply_mask = edge_mask & (mask > 0.5)
    if not apply_mask.any():
        return rgba, 0

    strength = float(np.clip(thresholds.strength, 0.0, 1.0))
    out = rgba.copy()
    original_rgb = rgba[:, :, :3].astype(np.float32)
    blended = original_rgb * (1 - strength) + color * strength
    out_rgb = out[:, :, :3].astype(np.float32)
    out_rgb[apply_mask] = blended[apply_mask]
    out[:, :, :3] = np.clip(out_rgb, 0, 255).astype(np.uint8)

    changed = np.any(out[:, :, :3] != rgba[:, :, :3], axis=-1) & apply_mask
    changed_count = int(changed.sum())

    if changed_count > 0 and report is not None:
        report.add_step(
            "halo_correction",
            f"{changed_count} Farbsaum-Pixel an halbtransparenten Kanten korrigiert.",
            pixels_affected=changed_count,
        )

    return out, changed_count
