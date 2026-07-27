"""Benutzerdefinierte, vom Benutzer selbst gespeicherte Presets - ergänzend
zu den festen, im Code definierten Presets (siehe presets.py).

Anders als die eingebauten Presets (die nur gezielt einzelne Felder ändern,
siehe Moduldokumentation presets.py) speichert ein benutzerdefiniertes
Preset die VOLLSTÄNDIGE aktuelle Konfiguration als Momentaufnahme - beim
erneuten Anwenden wird das komplette ProcessingSettings-Objekt ersetzt statt
nur einzelne Felder gesetzt. Ein "hängen bleibendes" Feld wie beim
DTF-King-Preset (siehe reset_dtf_king_only_fields) kann dadurch nicht
auftreten: die Momentaufnahme enthält ohnehin jedes Feld explizit.

Persistiert als eigene JSON-Datei (config.paths.get_presets_file()),
unabhängig von den regulären Anwendungseinstellungen (settings.json) - nutzt
dieselbe generische Serialisierung wie diese (config_manager.settings_to_dict
/ settings_from_dict), damit neue Einstellungsfelder automatisch mit
gespeichert werden, ohne diese Datei anpassen zu müssen.
"""
from __future__ import annotations

import dataclasses
import json
import logging

from src.config.config_manager import settings_from_dict_strict, settings_to_dict
from src.config.defaults import ProcessingSettings
from src.config.paths import get_presets_file
from src.models.enums import PresetName

logger = logging.getLogger(__name__)


class CustomPresetError(ValueError):
    """Ungültiger Name oder nicht vorhandenes Preset - Text ist für die
    direkte Anzeige in der Oberfläche gedacht."""


def _reserved_names() -> set[str]:
    return {p.value.strip().lower() for p in PresetName}


def _validate_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise CustomPresetError("Der Name darf nicht leer sein.")
    if cleaned.lower() in _reserved_names():
        raise CustomPresetError(f"'{cleaned}' ist der Name eines eingebauten Presets und kann nicht verwendet werden.")
    return cleaned


def load_custom_presets() -> dict[str, ProcessingSettings]:
    path = get_presets_file()
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        logger.exception("Konnte benutzerdefinierte Presets nicht laden, ignoriere Datei: %s", path)
        return {}

    result: dict[str, ProcessingSettings] = {}
    for name, settings_data in (data or {}).items():
        try:
            result[name] = settings_from_dict_strict(settings_data)
        except Exception:
            logger.exception("Benutzerdefiniertes Preset '%s' konnte nicht geladen werden, wird übersprungen.", name)
    return result


def _save_all(presets: dict[str, ProcessingSettings]) -> None:
    path = get_presets_file()
    data = {name: settings_to_dict(settings) for name, settings in presets.items()}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_custom_preset(name: str, settings: ProcessingSettings, *, overwrite: bool = False) -> str:
    """Speichert eine vollständige Momentaufnahme von `settings` unter `name`.
    Gibt den bereinigten (getrimmten) Namen zurück. Wirft CustomPresetError
    bei leerem/reserviertem Namen, oder wenn der Name bereits existiert und
    `overwrite` nicht gesetzt ist."""
    cleaned = _validate_name(name)
    presets = load_custom_presets()
    existing_key = next((k for k in presets if k.lower() == cleaned.lower()), None)
    if existing_key is not None and not overwrite:
        raise CustomPresetError(f"Ein benutzerdefiniertes Preset namens '{cleaned}' existiert bereits.")
    if existing_key is not None:
        del presets[existing_key]

    presets[cleaned] = settings
    _save_all(presets)
    return cleaned


def delete_custom_preset(name: str) -> None:
    presets = load_custom_presets()
    if name not in presets:
        raise CustomPresetError(f"Preset '{name}' existiert nicht.")
    del presets[name]
    _save_all(presets)


def rename_custom_preset(old_name: str, new_name: str) -> str:
    """Benennt ein vorhandenes Preset um. Gibt den bereinigten neuen Namen
    zurück. Wirft CustomPresetError, wenn `old_name` nicht existiert oder
    `new_name` ungültig/bereits vergeben ist."""
    presets = load_custom_presets()
    if old_name not in presets:
        raise CustomPresetError(f"Preset '{old_name}' existiert nicht.")
    cleaned = _validate_name(new_name)
    if cleaned.lower() != old_name.lower() and any(k.lower() == cleaned.lower() for k in presets):
        raise CustomPresetError(f"Ein benutzerdefiniertes Preset namens '{cleaned}' existiert bereits.")

    settings = presets.pop(old_name)
    presets[cleaned] = settings
    _save_all(presets)
    return cleaned


def apply_custom_preset(live_settings: ProcessingSettings, custom_settings: ProcessingSettings) -> None:
    """Überträgt eine geladene, eigenständige Preset-Momentaufnahme in ein
    bereits bestehendes ProcessingSettings-Objekt (in-place) - andere Teile
    der Oberfläche (z. B. ein bereits geöffneter Dialog) halten eine
    Referenz auf genau dieses Objekt, ein kompletter Objektaustausch würde
    diese Referenzen veralten lassen."""
    for field in dataclasses.fields(ProcessingSettings):
        setattr(live_settings, field.name, getattr(custom_settings, field.name))
