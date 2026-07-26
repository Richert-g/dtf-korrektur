# DTF Korrektur

Eine lokale Windows-Desktop-Anwendung, die Bilder automatisch für DTF-Druck
(Direct-to-Film) und andere Druckverfahren optimiert - Transparenz bereinigen,
Farbsäume korrigieren, Farben ans Druckprofil anpassen. Läuft vollständig
lokal, keine Cloud-Übertragung von Bilddaten.

Da sie auf Python basiert, kann sie auch unter Linux benutzt werden.

## Funktionsumfang

- **Automatische Analyse & Klassifizierung**: erkennt Logo/Schrift,
  Illustration, Foto oder Motiv mit weichem Schatten und wählt passende
  Verarbeitungsschritte.
- **Alpha-Bereinigung**: vier Modi (Auto/Harte Kante/Sanfte Bereinigung/Nur
  Störpixel), Otsu-Schwelle, Entfernung kleiner Pixelinseln, Schließen
  kleiner Löcher.
- **Farbsaum-/Halo-Korrektur** an halbtransparenten Kanten.
- **ICC-Farbmanagement**: Quell-/Zielprofil, Softproof, Gamut-Analyse
  (Delta E in Lab), automatische Rendering-Intent-Wahl, gezielte
  Sättigungsoptimierung mit Schutz für Hauttöne/Grau/Schwarz.
- **Diff-Vorschau**: entfernte/verstärkte Pixel farbig hervorgehoben.
- **Presets** (DTF Auto, Logo, Illustration, Foto, weicher Schatten, …),
  Stapelverarbeitung mit kontrollierter Parallelität und Abbruch.
- **Export**: RGB-PNG mit Transparenz (Hauptausgabe), optional Alpha-Maske,
  Weißunterlegungs-Vorschau, CMYK-TIFF-Vorschau, Softproof, JSON/HTML-Bericht.
- Bringt bereits gängige RGB-/CMYK-ICC-Profile mit (FOGRA, GRACoL, SWOP,
  Adobe RGB u. a.).

## Schnellstart

```powershell
py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python.exe -m src.app.main
```

Tests: `scripts\run_tests.ps1` · Windows-EXE + Installer bauen:
`scripts\build_windows.ps1`

## Dokumentation

- [docs/architecture.md](docs/architecture.md) - Aufbau des Codes
- [docs/processing-pipeline.md](docs/processing-pipeline.md) - Verarbeitungsschritte im Detail
- [docs/color-management.md](docs/color-management.md) - ICC-Farbmanagement
- [docs/build-windows.md](docs/build-windows.md) - EXE/Installer bauen
- [docs/user-guide.md](docs/user-guide.md) - Bedienungsanleitung

## Technologie

Python 3.12, PySide6, Pillow/ImageCms (LittleCMS), NumPy, OpenCV, PyInstaller.

## Bekannte Grenzen

Siehe "Bekannte technische Grenzen" in [docs/user-guide.md](docs/user-guide.md)
(u. a. kein DTF-spezifisches Referenzprofil enthalten, eingeschränkte
PSD/AVIF-Unterstützung).
