"""Export der DTF-Hauptausgabe: RGB-PNG mit Transparenz (Prompt Abschnitt 16)."""
from __future__ import annotations

import io
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms

from src.utils.fs_utils import ensure_dir, retry_on_oserror


def _srgb_icc_bytes() -> bytes:
    profile = ImageCms.createProfile("sRGB")
    return ImageCms.ImageCmsProfile(profile).tobytes()


_SRGB_ICC_CACHE: bytes | None = None


def get_srgb_icc_bytes() -> bytes:
    global _SRGB_ICC_CACHE
    if _SRGB_ICC_CACHE is None:
        _SRGB_ICC_CACHE = _srgb_icc_bytes()
    return _SRGB_ICC_CACHE


def export_rgba_png(
    rgba: np.ndarray,
    output_path: Path,
    icc_profile_bytes: bytes | None = None,
    keep_metadata: bool = False,
    dpi: tuple[float, float] | None = None,
) -> None:
    """Schreibt ein RGBA-NumPy-Array als PNG. Bettet ein sRGB-Profil ein, falls keines übergeben wurde."""
    img = Image.fromarray(np.ascontiguousarray(rgba), mode="RGBA")
    icc = icc_profile_bytes if icc_profile_bytes else get_srgb_icc_bytes()
    save_kwargs = {"icc_profile": icc}
    if dpi:
        save_kwargs["dpi"] = dpi
    ensure_dir(output_path.parent)
    retry_on_oserror(lambda: img.save(output_path, format="PNG", **save_kwargs), description=f"PNG-Export {output_path.name}")


def export_alpha_mask_png(rgba: np.ndarray, output_path: Path) -> None:
    """Schreibt den Alphakanal als eigenständige Graustufen-PNG-Maske."""
    alpha = rgba[:, :, 3]
    img = Image.fromarray(alpha, mode="L")
    ensure_dir(output_path.parent)
    retry_on_oserror(lambda: img.save(output_path, format="PNG"), description=f"Alpha-Masken-Export {output_path.name}")
