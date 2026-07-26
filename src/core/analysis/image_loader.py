"""Lokaler Bildimport ohne externe Kommandozeilenprogramme (Prompt Abschnitt 16).

Unterstützt zuverlässig: PNG, JPG/JPEG, TIFF, BMP, WebP.
PSD und AVIF werden nur mit reduzierter Unterstützung versucht (best effort),
sofern die installierten Pillow-Plugins dies zulassen.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms, UnidentifiedImageError

from src.config.defaults import CORE_IMPORT_FORMATS, SUPPORTED_IMPORT_FORMATS

logger = logging.getLogger(__name__)


class ImageLoadError(Exception):
    """Wird ausgelöst, wenn eine Bilddatei nicht sicher geladen werden kann."""


@dataclass
class LoadedImage:
    path: Path
    pil_image: Image.Image  # immer im Modus RGBA nach dem Laden
    array: np.ndarray  # HxWx4 uint8, RGBA
    original_mode: str
    file_format: str
    icc_profile_bytes: bytes | None
    icc_profile_description: str | None
    had_alpha: bool
    dpi: tuple[float, float] | None = None


def is_supported_file(path: Path, include_extended: bool = True) -> bool:
    ext = path.suffix.lower()
    if include_extended:
        return ext in SUPPORTED_IMPORT_FORMATS
    return ext in CORE_IMPORT_FORMATS


def _extract_icc_description(icc_bytes: bytes | None) -> str | None:
    if not icc_bytes:
        return None
    try:
        profile = ImageCms.ImageCmsProfile(__import__("io").BytesIO(icc_bytes))
        return ImageCms.getProfileDescription(profile).strip()
    except Exception:
        logger.warning("ICC-Profil konnte nicht gelesen werden (defekt oder inkompatibel).", exc_info=True)
        return None


def load_image(path: Path) -> LoadedImage:
    """Lädt ein Bild robust und liefert ein normalisiertes RGBA-Ergebnis.

    Wirft ImageLoadError bei beschädigten oder nicht unterstützten Dateien,
    statt die Anwendung abstürzen zu lassen (Prompt Abschnitt 21).
    """
    path = Path(path)
    if not path.exists():
        raise ImageLoadError(f"Datei nicht gefunden: {path}")
    if not is_supported_file(path):
        raise ImageLoadError(f"Dateiformat nicht unterstützt: {path.suffix}")

    try:
        with Image.open(path) as img:
            img.load()
            file_format = (img.format or path.suffix.lstrip(".").upper())
            original_mode = img.mode
            icc_bytes = img.info.get("icc_profile")
            dpi = img.info.get("dpi")

            had_alpha = "A" in img.mode or "transparency" in img.info
            if img.mode == "P":
                had_alpha = "transparency" in img.info
                img = img.convert("RGBA")
            elif img.mode not in ("RGB", "RGBA", "L", "LA"):
                img = img.convert("RGBA")

            if img.mode != "RGBA":
                img = img.convert("RGBA")

            array = np.array(img, dtype=np.uint8)
            if array.ndim == 2:
                array = np.stack([array] * 4, axis=-1)

            icc_description = _extract_icc_description(icc_bytes)

            return LoadedImage(
                path=path,
                pil_image=img,
                array=array,
                original_mode=original_mode,
                file_format=file_format,
                icc_profile_bytes=icc_bytes,
                icc_profile_description=icc_description,
                had_alpha=had_alpha,
                dpi=dpi,
            )
    except UnidentifiedImageError as exc:
        raise ImageLoadError(f"Datei ist beschädigt oder kein gültiges Bild: {path.name}") from exc
    except (OSError, ValueError) as exc:
        raise ImageLoadError(f"Fehler beim Laden von {path.name}: {exc}") from exc
