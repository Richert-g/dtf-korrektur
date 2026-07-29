"""Zentrale Aufzählungstypen für die DTF-Korrektur-Anwendung."""
from __future__ import annotations

from enum import Enum


class ImageType(str, Enum):
    """Automatisch erkannter Bildtyp (siehe Prompt Abschnitt 6)."""

    HARD_LOGO = "hard_logo"
    ILLUSTRATION = "illustration"
    PHOTO = "photo"
    SOFT_SHADOW = "soft_shadow"
    UNKNOWN = "unknown"


class AlphaMode(str, Enum):
    """Interner Alpha-Bereinigungsmodus (siehe Prompt Abschnitt 7)."""

    AUTO = "auto"
    HARD_EDGE = "hard_edge"
    SOFT_CLEANUP = "soft_cleanup"
    NOISE_ONLY = "noise_only"


class AlphaThresholdOrder(str, Enum):
    """Reihenfolge, in der "Pixel löschen" und "Pixel volldeckend setzen"
    angewendet werden. Nur relevant, wenn sich die beiden Schwellenwerte
    überschneiden (sonst identisches Ergebnis in beiden Reihenfolgen)."""

    REMOVE_FIRST = "remove_first"
    STRENGTHEN_FIRST = "strengthen_first"


class WeakAlphaAction(str, Enum):
    """Wie mit Pixeln umgegangen wird, deren Alpha-Wert kleiner oder gleich dem
    "geringe Deckkraft"-Schwellenwert ist (siehe AlphaThresholds.weak_alpha_action)."""

    SET_TRANSPARENT = "set_transparent"  # Pixel bleibt erhalten, Alpha wird 0
    DELETE_PIXEL = "delete_pixel"  # Pixel wird vollständig entfernt (Alpha UND RGB genullt)


class RenderingIntent(str, Enum):
    PERCEPTUAL = "perceptual"
    RELATIVE_COLORIMETRIC = "relative_colorimetric"
    SATURATION = "saturation"
    ABSOLUTE_COLORIMETRIC = "absolute_colorimetric"


class WarningSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class OutputFormat(str, Enum):
    PNG_RGB = "png_rgb"
    TIFF_RGB = "tiff_rgb"
    JPEG_RGB = "jpeg_rgb"
    CMYK_TIFF = "cmyk_tiff"
    SOFTPROOF_PNG = "softproof_png"
    ALPHA_MASK_PNG = "alpha_mask_png"
    WHITE_MASK_PNG = "white_mask_png"
    PDF_CMYK = "pdf_cmyk"


class PresetName(str, Enum):
    DTF_AUTO = "DTF Auto"
    DTF_LOGO_TEXT = "DTF Logo und Schrift"
    DTF_ILLUSTRATION = "DTF Illustration"
    DTF_PHOTO = "DTF Foto"
    DTF_SOFT_SHADOW = "DTF mit weichem Schatten"
    TRANSPARENCY_ONLY = "Nur Transparenz bereinigen"
    COLOR_ONLY = "Nur Farben optimieren"
    DTF_KING_ISO_COATED_V2 = "DTF-King – ISO Coated v2 (ECI)"
    CUSTOM = "Benutzerdefiniert"
