"""Prüft, ob auf GitHub eine neuere Version von DTF Korrektur veröffentlicht wurde.

Rein informativ: es wird nichts automatisch heruntergeladen oder installiert,
nur ein Link zur Release-Seite angeboten (der Benutzer lädt dort bei Bedarf
selbst herunter). Läuft komplett optional - bei fehlendem Internetzugang,
GitHub-Fehlern oder unerwarteten Antworten wird der Check übersprungen und
darf die App niemals zum Absturz bringen oder blockieren (siehe
check_for_update: fängt jede Exception ab).
"""
from __future__ import annotations

import json
import logging
import urllib.request
from dataclasses import dataclass

logger = logging.getLogger(__name__)

GITHUB_RELEASES_LATEST_URL = "https://api.github.com/repos/Richert-g/dtf-korrektur/releases/latest"
REQUEST_TIMEOUT_SECONDS = 4.0


@dataclass
class UpdateCheckResult:
    update_available: bool
    latest_version: str | None = None
    release_url: str | None = None
    error: str | None = None


def _parse_version(version: str) -> tuple[int, ...]:
    """Wandelt z. B. 'v1.0.13' in (1, 0, 13) um - nicht-numerische Suffixe
    (z. B. '-beta') werden dabei ignoriert, um robust gegen Formatabweichungen
    im GitHub-Tag zu bleiben."""
    cleaned = version.strip().lstrip("vV")
    parts = []
    for piece in cleaned.split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def is_newer_version(latest: str, current: str) -> bool:
    return _parse_version(latest) > _parse_version(current)


def check_for_update(
    current_version: str,
    url: str = GITHUB_RELEASES_LATEST_URL,
    timeout: float = REQUEST_TIMEOUT_SECONDS,
) -> UpdateCheckResult:
    try:
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "DTF-Korrektur-UpdateCheck"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - feste https-URL, kein Benutzerinput
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - Update-Check darf die App nie stoeren
        logger.info("Update-Check nicht moeglich (kein Internet oder GitHub nicht erreichbar): %s", exc)
        return UpdateCheckResult(update_available=False, error=str(exc))

    tag_name = data.get("tag_name") if isinstance(data, dict) else None
    release_url = data.get("html_url") if isinstance(data, dict) else None
    if not tag_name:
        return UpdateCheckResult(update_available=False, error="Antwort enthielt kein tag_name.")

    # Defensive Prüfung: nur echte github.com-Links werden später zum Öffnen angeboten.
    if not isinstance(release_url, str) or not release_url.startswith("https://github.com/"):
        release_url = None

    return UpdateCheckResult(
        update_available=is_newer_version(tag_name, current_version),
        latest_version=tag_name,
        release_url=release_url,
    )
