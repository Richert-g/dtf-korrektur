"""Optionale CMYK-TIFF-Vorschau (Prompt Abschnitt 11 & 16).

Sicherheitsregel (Prompt Abschnitt 19): Ohne echtes, vom Benutzer gewähltes
Zielprofil wird KEINE angeblich 'druckfertige' CMYK-Datei erzeugt.
Da CMYK keine Transparenz kennt, wird für diese Vorschau auf einem weißen
Hintergrund geflacht.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageCms

from src.core.color.icc_manager import get_srgb_profile
from src.utils.fs_utils import ensure_dir
from src.utils.image_qt import composite_over_background


class CmykExportError(Exception):
    pass


def export_cmyk_tiff_preview(
    rgba: np.ndarray,
    target_profile: ImageCms.ImageCmsProfile,
    rendering_intent_cms,
    black_point_compensation: bool,
    output_path: Path,
) -> None:
    flattened = composite_over_background(rgba, (255, 255, 255))[:, :, :3]
    flags = ImageCms.Flags.BLACKPOINTCOMPENSATION if black_point_compensation else ImageCms.Flags.NONE
    try:
        transform = ImageCms.buildTransform(
            get_srgb_profile(), target_profile, "RGB", "CMYK", renderingIntent=rendering_intent_cms, flags=flags
        )
        cmyk_img = ImageCms.applyTransform(Image.fromarray(np.ascontiguousarray(flattened), "RGB"), transform)
    except Exception as exc:
        raise CmykExportError(f"CMYK-Konvertierung fehlgeschlagen: {exc}") from exc

    ensure_dir(output_path.parent)
    cmyk_img.save(output_path, format="TIFF", icc_profile=target_profile.tobytes())
