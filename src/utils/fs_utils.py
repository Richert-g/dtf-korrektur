"""Robuste Dateisystem-Hilfsfunktionen.

Auf synchronisierten Ordnern (z. B. OneDrive Files-On-Demand) kann das
Anlegen eines neuen Ordners oder das anschließende Schreiben einer Datei
darin vereinzelt transient fehlschlagen (WinError 2/3, "Bad file
descriptor"), obwohl der Zielpfad gültig ist - der Cloud-Sync-Filtertreiber
"sieht" den neuen Ordner/die neue Datei kurzzeitig noch nicht, auch wenn der
mkdir()- bzw. open()-Aufruf selbst keine Ausnahme geworfen hat. `ensure_dir`
prüft deshalb nach dem Anlegen zusätzlich aktiv die Sichtbarkeit, und
`retry_on_oserror` kapselt beliebige Schreiboperationen mit Wiederholung.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def ensure_dir(path: Path, retries: int = 6, delay_seconds: float = 0.25) -> Path:
    """Legt einen Ordner an und wartet bis er tatsächlich sichtbar ist.

    Ein erfolgreicher mkdir()-Aufruf reicht auf synchronisierten Ordnern nicht
    immer aus - anschließend wird zusätzlich per is_dir() verifiziert.
    """
    last_error: OSError | None = None
    for attempt in range(1, retries + 1):
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            last_error = exc
        else:
            if path.is_dir():
                return path
            last_error = OSError(2, "Ordner wurde angelegt, ist aber (noch) nicht sichtbar", str(path))

        if attempt < retries:
            logger.warning(
                "Ordner konnte nicht sicher angelegt werden (Versuch %d/%d): %s - %s",
                attempt, retries, path, last_error,
            )
            time.sleep(delay_seconds)

    assert last_error is not None
    raise last_error


def retry_on_oserror(
    func: Callable[[], T], retries: int = 5, delay_seconds: float = 0.25, description: str = "Dateioperation"
) -> T:
    """Führt `func()` aus und wiederholt bei OSError (z. B. transiente Cloud-Sync-Sperren).

    `func` muss die komplette Operation (öffnen, schreiben, schließen) in einem
    Aufruf kapseln, damit ein Wiederholungsversuch nicht auf einer halb
    geschriebenen Datei aufsetzt.
    """
    last_error: OSError | None = None
    for attempt in range(1, retries + 1):
        try:
            return func()
        except OSError as exc:
            last_error = exc
            if attempt < retries:
                logger.warning(
                    "%s fehlgeschlagen (Versuch %d/%d): %s", description, attempt, retries, exc
                )
                time.sleep(delay_seconds)
    assert last_error is not None
    raise last_error
