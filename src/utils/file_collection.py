"""Sammelt unterstützte Bilddateien aus einer Liste von Dateien/Ordnern.

Bewusst ohne jede Qt-Abhängigkeit (im Unterschied zu app.ui.drop_area, das
diese Funktion für Drag & Drop re-exportiert) - wird auch vom Kommandozeilen-
modus (cli.py) genutzt, der komplett ohne PySide6 auskommen soll (siehe
dortigen Moduldocstring)."""
from __future__ import annotations

from pathlib import Path

from src.config.defaults import SUPPORTED_IMPORT_FORMATS


def collect_supported_files(paths: list[Path]) -> list[Path]:
    """Sammelt aus einer Liste von Dateien/Ordnern alle unterstützten Bilddateien
    (Ordner werden rekursiv durchsucht)."""
    result: list[Path] = []
    for p in paths:
        if p.is_dir():
            for child in sorted(p.rglob("*")):
                if child.is_file() and child.suffix.lower() in SUPPORTED_IMPORT_FORMATS:
                    result.append(child)
        elif p.is_file() and p.suffix.lower() in SUPPORTED_IMPORT_FORMATS:
            result.append(p)
    return result
