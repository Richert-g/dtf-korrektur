"""Laden/Speichern der Anwendungseinstellungen als lokale JSON-Datei."""
from __future__ import annotations

import dataclasses
import json
import logging
from enum import Enum
from pathlib import Path

from src.config.defaults import ProcessingSettings, DEFAULT_SETTINGS
from src.config.paths import get_config_file

logger = logging.getLogger(__name__)


def _to_jsonable(obj):
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _to_jsonable(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, list):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    return obj


def _from_jsonable(cls, data):
    if data is None:
        return None
    if dataclasses.is_dataclass(cls):
        kwargs = {}
        field_types = {f.name: f.type for f in dataclasses.fields(cls)}
        defaults = {f.name: f for f in dataclasses.fields(cls)}
        for name, value in (data or {}).items():
            if name not in field_types:
                continue
            ftype = defaults[name].type
            resolved = _resolve_type(cls, name)
            if resolved is not None and dataclasses.is_dataclass(resolved):
                kwargs[name] = _from_jsonable(resolved, value)
            elif resolved is not None and isinstance(resolved, type) and issubclass(resolved, Enum):
                kwargs[name] = resolved(value)
            else:
                kwargs[name] = value
        return cls(**kwargs)
    return data


def _resolve_type(cls, field_name):
    """Löst den tatsächlichen Feldtyp auf (für dataclass/Enum-Erkennung)."""
    import typing

    hints = typing.get_type_hints(cls)
    t = hints.get(field_name)
    return t


def settings_to_dict(settings: ProcessingSettings) -> dict:
    return _to_jsonable(settings)


def settings_from_dict(data: dict) -> ProcessingSettings:
    try:
        return _from_jsonable(ProcessingSettings, data)
    except Exception:
        logger.exception("Konnte gespeicherte Einstellungen nicht laden, verwende Standardwerte.")
        return ProcessingSettings()


def load_settings() -> ProcessingSettings:
    path = get_config_file()
    if not path.exists():
        return ProcessingSettings()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return settings_from_dict(data)
    except Exception:
        logger.exception("Fehler beim Laden von %s, verwende Standardwerte.", path)
        return ProcessingSettings()


def save_settings(settings: ProcessingSettings) -> None:
    path = get_config_file()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings_to_dict(settings), f, indent=2, ensure_ascii=False)
    except OSError:
        logger.exception("Fehler beim Speichern von %s", path)
