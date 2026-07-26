"""Zusätzliche Rasterformate für das wählbare Hauptausgabeformat (PNG ist der
Standardfall in `png_export.py` und bleibt davon unberührt).

TIFF: verlustfrei, behält den Alphakanal (wie PNG).
JPEG: kennt keine Transparenz - das Bild wird vor dem Speichern auf eine
Volltonfarbe geflacht. Der Aufrufer ist dafür verantwortlich, den Benutzer
per Bericht/Warnung darüber zu informieren.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from src.utils.fs_utils import ensure_dir, retry_on_oserror
from src.utils.image_qt import composite_over_background


def export_rgba_tiff(
    rgba: np.ndarray,
    output_path: Path,
    icc_profile_bytes: bytes | None = None,
    dpi: tuple[float, float] | None = None,
) -> None:
    """Schreibt ein RGBA-NumPy-Array als verlustfreies TIFF (LZW), Transparenz bleibt erhalten."""
    img = Image.fromarray(np.ascontiguousarray(rgba), mode="RGBA")
    save_kwargs: dict = {"compression": "tiff_lzw"}
    if icc_profile_bytes:
        save_kwargs["icc_profile"] = icc_profile_bytes
    if dpi:
        save_kwargs["dpi"] = dpi
    ensure_dir(output_path.parent)
    retry_on_oserror(lambda: img.save(output_path, format="TIFF", **save_kwargs), description=f"TIFF-Export {output_path.name}")


def export_rgb_jpeg(
    rgba: np.ndarray,
    output_path: Path,
    icc_profile_bytes: bytes | None = None,
    quality: int = 95,
    background_rgb: tuple[int, int, int] = (255, 255, 255),
    dpi: tuple[float, float] | None = None,
) -> None:
    """Schreibt ein RGBA-NumPy-Array als JPEG. JPEG kennt keine Transparenz,
    daher wird zuerst auf `background_rgb` geflacht."""
    flattened = composite_over_background(rgba, background_rgb)[:, :, :3]
    img = Image.fromarray(np.ascontiguousarray(flattened), mode="RGB")
    save_kwargs: dict = {"quality": int(quality), "subsampling": 0}
    if icc_profile_bytes:
        save_kwargs["icc_profile"] = icc_profile_bytes
    if dpi:
        save_kwargs["dpi"] = dpi
    ensure_dir(output_path.parent)
    retry_on_oserror(lambda: img.save(output_path, format="JPEG", **save_kwargs), description=f"JPEG-Export {output_path.name}")
