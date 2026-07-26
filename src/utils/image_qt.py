"""Hilfsfunktionen für die Umwandlung zwischen NumPy/PIL-Bildern und Qt."""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image
from PySide6.QtGui import QImage, QPixmap


def downscale_for_preview(rgba: np.ndarray, max_dimension: int) -> np.ndarray:
    """Verkleinert ein Bild für die Bildschirmvorschau (Prompt Abschnitt 14).

    Der Export wird davon nicht berührt - dieser rechnet immer mit den
    Originaldaten weiter.
    """
    h, w = rgba.shape[:2]
    largest = max(h, w)
    if largest <= max_dimension:
        return rgba
    scale = max_dimension / largest
    new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
    return cv2.resize(rgba, (new_w, new_h), interpolation=cv2.INTER_AREA)


def rgba_array_to_qpixmap(arr: np.ndarray) -> QPixmap:
    """Wandelt ein HxWx4-uint8-RGBA-NumPy-Array in ein QPixmap um."""
    arr = np.ascontiguousarray(arr)
    h, w, _ = arr.shape
    qimg = QImage(arr.data, w, h, w * 4, QImage.Format.Format_RGBA8888)
    # Kopie, damit der zugrunde liegende NumPy-Speicher unabhängig bleibt
    return QPixmap.fromImage(qimg.copy())


def pil_to_qpixmap(img: Image.Image) -> QPixmap:
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    return rgba_array_to_qpixmap(np.array(img))


def checkerboard_background(w: int, h: int, tile: int = 8) -> np.ndarray:
    """Erzeugt ein Schachbrettmuster als RGBA-Hintergrund für Transparenz-Vorschau."""
    yy, xx = np.mgrid[0:h, 0:w]
    pattern = ((xx // tile) + (yy // tile)) % 2
    arr = np.empty((h, w, 4), dtype=np.uint8)
    arr[pattern == 0] = [230, 230, 230, 255]
    arr[pattern == 1] = [200, 200, 200, 255]
    return arr


def composite_over_background(rgba: np.ndarray, bg_color: tuple[int, int, int]) -> np.ndarray:
    """Rechnet ein RGBA-Bild auf einen deckenden Hintergrund (für Textilsimulation)."""
    rgba = rgba.astype(np.float32)
    alpha = rgba[:, :, 3:4] / 255.0
    bg = np.array(bg_color, dtype=np.float32).reshape(1, 1, 3)
    out_rgb = rgba[:, :, :3] * alpha + bg * (1 - alpha)
    out = np.empty(rgba.shape[:2] + (4,), dtype=np.uint8)
    out[:, :, :3] = np.clip(out_rgb, 0, 255).astype(np.uint8)
    out[:, :, 3] = 255
    return out
