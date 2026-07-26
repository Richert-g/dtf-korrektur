"""Robuste Dateisystem-Hilfsfunktionen.

Auf synchronisierten Ordnern (z. B. OneDrive Files-On-Demand) kann das Anlegen
eines neuen Ordners vereinzelt transient mit WinError 2/3 fehlschlagen, obwohl
der Zielpfad gültig ist. `ensure_dir` fängt das ab und versucht es kurz erneut,
bevor der Fehler an den Aufrufer weitergereicht wird.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def ensure_dir(path: Path, retries: int = 3, delay_seconds: float = 0.3) -> Path:
    last_error: OSError | None = None
    for attempt in range(1, retries + 1):
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except OSError as exc:
            last_error = exc
            if attempt < retries:
                logger.warning(
                    "Ordner konnte nicht angelegt werden (Versuch %d/%d): %s - %s",
                    attempt, retries, path, exc,
                )
                time.sleep(delay_seconds)
    assert last_error is not None
    raise last_error
