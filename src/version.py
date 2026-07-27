"""Zentrale Versionsnummer der Anwendung.

Muss bei jedem Release manuell synchron zum Aufruf von
scripts\\build_windows.ps1 -AppVersion gehalten werden (siehe README,
Abschnitt "Release erstellen") - der automatische Update-Check
(src.core.update.update_check) vergleicht diesen Wert mit dem neuesten
GitHub-Release-Tag.
"""
from __future__ import annotations

APP_VERSION = "1.0.14"
