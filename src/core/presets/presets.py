"""Automatische Presets (Prompt Abschnitt 12).

Presets verändern gezielt einzelne Einstellungen der aktuellen ProcessingSettings,
statt alle Werte zurückzusetzen - manuell in den erweiterten Einstellungen
vorgenommene Feinabstimmungen bleiben dadurch so weit wie möglich erhalten.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from src.config.defaults import ProcessingSettings
from src.models.enums import AlphaMode, OutputFormat, PresetName, RenderingIntent


def _dtf_auto(s: ProcessingSettings) -> None:
    s.alpha_mode = AlphaMode.AUTO
    s.color.auto_select_intent = True
    s.export.write_softproof_preview = True


def _dtf_logo_text(s: ProcessingSettings) -> None:
    s.alpha_mode = AlphaMode.HARD_EDGE
    s.color.auto_select_intent = True


def _dtf_illustration(s: ProcessingSettings) -> None:
    s.alpha_mode = AlphaMode.SOFT_CLEANUP
    s.color.auto_select_intent = True


def _dtf_photo(s: ProcessingSettings) -> None:
    s.alpha_mode = AlphaMode.NOISE_ONLY
    s.color.auto_select_intent = False
    s.color.rendering_intent = RenderingIntent.PERCEPTUAL


def _dtf_soft_shadow(s: ProcessingSettings) -> None:
    s.alpha_mode = AlphaMode.NOISE_ONLY
    s.halo.enabled = True
    s.color.auto_select_intent = True


def _transparency_only(s: ProcessingSettings) -> None:
    s.alpha_mode = AlphaMode.AUTO
    s.color.target_profile_path = None


def _color_only(s: ProcessingSettings) -> None:
    s.alpha_mode = AlphaMode.NOISE_ONLY
    s.alpha.weak_alpha_threshold = 0
    s.halo.enabled = False


def _custom(s: ProcessingSettings) -> None:
    return  # keine Änderungen - der Benutzer steuert alles selbst


def _find_iso_coated_v2_profile_path() -> str | None:
    """Sucht unter mitgelieferten/importierten Profilen eindeutig eines mit
    'ISO Coated v2' in der Beschreibung. Findet NIEMALS ein ähnlich benanntes
    Profil (z. B. FOGRA39) als Ersatz - nur eine exakte Beschreibungs-Teilzeichenkette.
    """
    from src.core.color.icc_manager import list_available_profiles
    from src.core.color.profile_validation import find_profile_by_description_fragment

    candidates = [info.path for info in list_available_profiles()]
    found = find_profile_by_description_fragment(candidates, "iso coated v2")
    return str(found) if found else None


def _dtf_king_iso_coated_v2(s: ProcessingSettings) -> None:
    # --- Quelle ---
    # keine automatische Umwandlung beim Öffnen: die Farbwerte werden erst
    # beim Export durch process_image_for_dtf_king_pdf() einmalig konvertiert.

    # --- Transparenz: bestehende Alpha-/Halo-Korrektur unverändert nutzen ---
    s.alpha_mode = AlphaMode.AUTO
    s.halo.enabled = True

    # --- Farbe: genau eine echte ICC-Konvertierung, keine Zusatzkorrektur ---
    s.color.auto_select_intent = False
    s.color.rendering_intent = RenderingIntent.RELATIVE_COLORIMETRIC
    s.color.black_point_compensation = True
    s.color.show_gamut_warning = True  # rein informativ, löst keine Korrektur aus
    s.gamut.max_auto_saturation_reduction = 0.0
    s.gamut.enable_auto_gamut_correction = False

    # Nur ein Profil setzen, dessen Beschreibung eindeutig "ISO Coated v2"
    # enthält. Wird keines gefunden, bleibt das Feld leer - der Export
    # bricht dann mit einer klaren Meldung ab, statt ein ähnliches Profil
    # (z. B. FOGRA39) stillschweigend zu verwenden.
    found_path = _find_iso_coated_v2_profile_path()
    if found_path:
        s.color.target_profile_path = found_path
    elif s.color.target_profile_path:
        from src.core.color.profile_validation import validate_cmyk_output_profile

        current = validate_cmyk_output_profile(Path(s.color.target_profile_path))
        if not (current.ok and current.description and "iso coated v2" in current.description.lower()):
            s.color.target_profile_path = None
    else:
        s.color.target_profile_path = None

    # --- Ausgabe: einseitige CMYK-PDF, 300 dpi, transparenter Hintergrund ---
    s.export.output_format = OutputFormat.PDF_CMYK
    s.export.pdf_target_dpi = 300.0
    s.export.pdf_allow_upscale = False
    s.export.write_cmyk_tiff = False


PRESET_HANDLERS: dict[PresetName, Callable[[ProcessingSettings], None]] = {
    PresetName.DTF_AUTO: _dtf_auto,
    PresetName.DTF_LOGO_TEXT: _dtf_logo_text,
    PresetName.DTF_ILLUSTRATION: _dtf_illustration,
    PresetName.DTF_PHOTO: _dtf_photo,
    PresetName.DTF_SOFT_SHADOW: _dtf_soft_shadow,
    PresetName.TRANSPARENCY_ONLY: _transparency_only,
    PresetName.COLOR_ONLY: _color_only,
    PresetName.DTF_KING_ISO_COATED_V2: _dtf_king_iso_coated_v2,
    PresetName.CUSTOM: _custom,
}

PRESET_DESCRIPTIONS: dict[PresetName, str] = {
    PresetName.DTF_AUTO: "Automatische Erkennung und Optimierung - für die meisten Bilder geeignet.",
    PresetName.DTF_LOGO_TEXT: "Harte, saubere Kanten für Logos und Schriftzüge.",
    PresetName.DTF_ILLUSTRATION: "Vorsichtige Kantenbehandlung für farbige Illustrationen und KI-Grafiken.",
    PresetName.DTF_PHOTO: "Minimale Eingriffe, Schatten und Verläufe bleiben erhalten.",
    PresetName.DTF_SOFT_SHADOW: "Für Motive mit weichem Schatten, Rauch oder Glow.",
    PresetName.TRANSPARENCY_ONLY: "Nur die Transparenz wird bereinigt, keine Farbanpassung.",
    PresetName.COLOR_ONLY: "Nur die Farben werden für das Druckprofil angepasst, Transparenz bleibt unverändert.",
    PresetName.DTF_KING_ISO_COATED_V2: (
        "Druckfertige einseitige CMYK-PDF für den Druckdienstleister DTF-King: ICC-Konvertierung nach "
        "ISO Coated v2 (ECI), keine zusätzliche Sättigungs-/Gamut-Korrektur, transparenter Hintergrund, "
        "mind. 300 dpi. Benötigt das importierte ICC-Profil 'ISO Coated v2 (ECI)'."
    ),
    PresetName.CUSTOM: "Alle Einstellungen werden manuell im Expertenbereich festgelegt.",
}


# Felder, die AUSSCHLIESSLICH vom DTF-King-Preset gesetzt werden. Damit ein
# Wechsel weg von DTF-King nicht "hängen bleibt" (z. B. output_format bliebe
# sonst dauerhaft auf PDF_CMYK stehen, obwohl ein völlig anderes Preset aktiv
# ist), werden sie vor jedem Preset-Wechsel auf ihren ursprünglichen
# Standardwert zurückgesetzt - der eigentliche Preset-Handler kann sie danach
# gezielt wieder setzen. Alle anderen Einstellungen bleiben unangetastet
# (siehe Moduldocstring: "gezielte Änderungen statt kompletter Reset").
_DEFAULT_SETTINGS_FOR_RESET = ProcessingSettings()


def _reset_dtf_king_only_fields(settings: ProcessingSettings) -> None:
    d = _DEFAULT_SETTINGS_FOR_RESET
    settings.export.output_format = d.export.output_format
    settings.export.pdf_width_mm = d.export.pdf_width_mm
    settings.export.pdf_height_mm = d.export.pdf_height_mm
    settings.export.pdf_target_dpi = d.export.pdf_target_dpi
    settings.export.pdf_allow_upscale = d.export.pdf_allow_upscale
    settings.gamut.enable_auto_gamut_correction = d.gamut.enable_auto_gamut_correction
    settings.gamut.max_auto_saturation_reduction = d.gamut.max_auto_saturation_reduction


def apply_preset(settings: ProcessingSettings, preset: PresetName) -> None:
    handler = PRESET_HANDLERS.get(preset)
    if handler is None:
        raise ValueError(f"Unbekanntes Preset: {preset}")
    _reset_dtf_king_only_fields(settings)
    handler(settings)
