"""Automatische Rendering-Intent-Auswahl (Prompt Abschnitt 9 & 10)."""
from __future__ import annotations

from src.config.defaults import ColorManagementSettings, GamutThresholds
from src.models.enums import ImageType, RenderingIntent

_PERCEPTUAL_TYPES = {ImageType.PHOTO, ImageType.ILLUSTRATION, ImageType.SOFT_SHADOW}


def select_rendering_intent(
    image_type: ImageType,
    out_of_gamut_percentage: float,
    color_cfg: ColorManagementSettings,
    gamut_cfg: GamutThresholds,
) -> tuple[RenderingIntent, str]:
    """Liefert den gewählten Intent sowie eine für den Bericht verständliche Begründung."""
    if not color_cfg.auto_select_intent:
        # RenderingIntent erbt von str - defensiv erneut in das Enum wrappen,
        # falls color_cfg.rendering_intent aus irgendeiner Quelle (z. B. einer
        # QComboBox-Rueckkonvertierung) als reines str-Objekt ankommt.
        return RenderingIntent(color_cfg.rendering_intent), "Manuell vom Benutzer festgelegt."

    if out_of_gamut_percentage >= gamut_cfg.perceptual_preference_threshold_pct:
        return (
            RenderingIntent.PERCEPTUAL,
            f"Hoher Anteil an Farben außerhalb des Zielfarbraums ({out_of_gamut_percentage:.1f}%) -> perzeptiv bevorzugt.",
        )

    if image_type in _PERCEPTUAL_TYPES:
        return (
            RenderingIntent.PERCEPTUAL,
            "Foto, Illustration oder weicher Verlauf erkannt -> perzeptiv für natürliche Farbübergänge.",
        )

    return (
        RenderingIntent.RELATIVE_COLORIMETRIC,
        "Logo/flächige Grafik erkannt -> relativ farbmetrisch für originalgetreue Markenfarben.",
    )
