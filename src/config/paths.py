"""Zentrale Pfadverwaltung: lokale Ordner für Profile, Konfiguration, Cache.

Läuft komplett lokal - siehe Prompt Abschnitt "WICHTIG": keine Cloud-Übertragung.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def get_app_root() -> Path:
    """Wurzelverzeichnis des Projekts bzw. der EXE (PyInstaller-kompatibel)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def get_bundled_resources_dir() -> Path:
    """Ordner mit den per `--add-data resources;resources` mitgelieferten Dateien.

    Im Entwicklungsmodus ist das schlicht `<Projekt>/resources`. In der per
    PyInstaller gebauten EXE liegen diese Daten - egal ob `--onedir` (unter
    `_internal/`) oder `--onefile` (im temporären Extraktionsordner) - unter
    `sys._MEIPASS`, NICHT neben der eigentlichen .exe (`get_app_root()`).
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / "resources"
    return get_app_root() / "resources"


def get_user_data_dir() -> Path:
    """Lokaler, beschreibbarer Ordner für Konfiguration/Profile/Cache (%LOCALAPPDATA%)."""
    base = os.environ.get("LOCALAPPDATA")
    if base:
        d = Path(base) / "DTFKorrektur"
    else:
        d = Path.home() / ".dtf_korrektur"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_profiles_dir() -> Path:
    d = get_user_data_dir() / "profiles"
    d.mkdir(parents=True, exist_ok=True)
    bundled = get_bundled_resources_dir() / "profiles"
    if bundled.exists():
        return bundled if any(bundled.iterdir()) else d
    return d


def get_user_profiles_dir() -> Path:
    """Ordner, in den importierte Benutzer-ICC-Profile kopiert werden."""
    d = get_user_data_dir() / "profiles"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_cache_dir() -> Path:
    d = get_user_data_dir() / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_config_file() -> Path:
    return get_user_data_dir() / "settings.json"


def get_presets_file() -> Path:
    return get_user_data_dir() / "presets.json"


def get_app_icon_path() -> Path:
    return get_bundled_resources_dir() / "icons" / "app_icon.ico"


def get_default_output_root(input_path: Path) -> Path:
    """Standard-Ausgabeordner: Unterordner "output" neben dem Eingabeordner/Bild."""
    base = input_path if input_path.is_dir() else input_path.parent
    return base / "output"
