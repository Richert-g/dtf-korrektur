"""Einmalige, echte ICC-Konvertierung von RGBA nach CMYK für den druckfertigen
PDF-Export (DTF-King).

Unterschied zu `src.core.export.cmyk_export`: jene Funktion erzeugt eine
FLACHE CMYK-TIFF-Vorschau auf weißem Hintergrund (Transparenz geht verloren)
und bleibt für diesen bestehenden Zweck unverändert. Diese Datei hier liefert
echte, unveränderte CMYK-Bilddaten OHNE Weißhintergrund - der Alphakanal wird
komplett getrennt von der Farbtransformation behandelt und unverändert
zurückgegeben, damit er später als PDF-Softmask verwendet werden kann.

Es findet genau EINE ICC-Transformation statt (RGB-Quellprofil -> CMYK-
Zielprofil). Es wird keine eigene Näherungsformel für Farbumrechnung
verwendet - ausschließlich `PIL.ImageCms` (LittleCMS2).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageCms

from src.models.enums import RenderingIntent

_INTENT_TO_CMS = {
    RenderingIntent.PERCEPTUAL: ImageCms.Intent.PERCEPTUAL,
    RenderingIntent.RELATIVE_COLORIMETRIC: ImageCms.Intent.RELATIVE_COLORIMETRIC,
    RenderingIntent.SATURATION: ImageCms.Intent.SATURATION,
    RenderingIntent.ABSOLUTE_COLORIMETRIC: ImageCms.Intent.ABSOLUTE_COLORIMETRIC,
}


class CmykConversionError(Exception):
    pass


@dataclass
class CmykConversionResult:
    cmyk: np.ndarray  # HxWx4 uint8
    alpha: np.ndarray  # HxW uint8, unverändert aus der Quelle übernommen
    rendering_intent: RenderingIntent
    black_point_compensation: bool


def convert_rgba_to_output_cmyk(
    rgba: np.ndarray,
    source_profile: ImageCms.ImageCmsProfile,
    target_profile: ImageCms.ImageCmsProfile,
    rendering_intent: RenderingIntent,
    black_point_compensation: bool,
) -> CmykConversionResult:
    """Wandelt die RGB-Kanäle eines RGBA-Arrays EINMALIG per echter ICC-
    Transformation nach CMYK um. Der Alphakanal wird nicht in die
    Farbtransformation einbezogen und exakt unverändert zurückgegeben, damit
    transparente/halbtransparente Pixel durch die Konvertierung nicht
    plötzlich sichtbar werden.

    Voraussetzung: RGB-Restwerte unter vollständig transparenten Pixeln
    dürfen keine Farbsäume verursachen. Das wird NICHT hier gelöst, sondern
    dadurch sichergestellt, dass diese Funktion erst NACH der bestehenden
    Halo-Korrektur aufgerufen wird, die die RGB-Werte an teiltransparenten
    Randpixeln bereits aus deckenden Nachbarn rekonstruiert.
    """
    if rgba.ndim != 3 or rgba.shape[2] != 4:
        raise CmykConversionError("Erwarte ein RGBA-Array (H, W, 4).")

    rgb = rgba[:, :, :3]
    alpha = rgba[:, :, 3].copy()

    cms_intent = _INTENT_TO_CMS[rendering_intent]
    flags = ImageCms.Flags.BLACKPOINTCOMPENSATION if black_point_compensation else ImageCms.Flags.NONE

    try:
        transform = ImageCms.buildTransform(
            source_profile, target_profile, "RGB", "CMYK", renderingIntent=cms_intent, flags=flags
        )
        cmyk_img = ImageCms.applyTransform(Image.fromarray(np.ascontiguousarray(rgb), "RGB"), transform)
    except Exception as exc:
        raise CmykConversionError(f"ICC-Konvertierung nach CMYK fehlgeschlagen: {exc}") from exc

    cmyk = np.array(cmyk_img, dtype=np.uint8)
    if cmyk.ndim != 3 or cmyk.shape[2] != 4:
        raise CmykConversionError("Die ICC-Transformation lieferte kein 4-kanaliges CMYK-Ergebnis.")

    return CmykConversionResult(
        cmyk=cmyk,
        alpha=alpha,
        rendering_intent=rendering_intent,
        black_point_compensation=black_point_compensation,
    )
