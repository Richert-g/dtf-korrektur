"""Automatische Presets (Prompt Abschnitt 12).

Presets verändern gezielt einzelne Einstellungen der aktuellen ProcessingSettings,
statt alle Werte zurückzusetzen - manuell in den erweiterten Einstellungen
vorgenommene Feinabstimmungen bleiben dadurch so weit wie möglich erhalten.
"""
from __future__ import annotations

from collections.abc import Callable

from src.config.defaults import ProcessingSettings
from src.models.enums import AlphaMode, PresetName, RenderingIntent


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


PRESET_HANDLERS: dict[PresetName, Callable[[ProcessingSettings], None]] = {
    PresetName.DTF_AUTO: _dtf_auto,
    PresetName.DTF_LOGO_TEXT: _dtf_logo_text,
    PresetName.DTF_ILLUSTRATION: _dtf_illustration,
    PresetName.DTF_PHOTO: _dtf_photo,
    PresetName.DTF_SOFT_SHADOW: _dtf_soft_shadow,
    PresetName.TRANSPARENCY_ONLY: _transparency_only,
    PresetName.COLOR_ONLY: _color_only,
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
    PresetName.CUSTOM: "Alle Einstellungen werden manuell im Expertenbereich festgelegt.",
}


def apply_preset(settings: ProcessingSettings, preset: PresetName) -> None:
    handler = PRESET_HANDLERS.get(preset)
    if handler is None:
        raise ValueError(f"Unbekanntes Preset: {preset}")
    handler(settings)
