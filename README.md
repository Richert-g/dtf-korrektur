# DTF Korrektur

Eine Desktop-Anwendung, die Bilder automatisch für DTF-Druck (Direct-to-Film)
und andere Druckverfahren optimiert - Transparenz bereinigen, Farbsäume
korrigieren, Farben ans Druckprofil anpassen. Läuft vollständig lokal, keine
Cloud-Übertragung von Bilddaten.

**Besonders nützlich, wenn du mit einer KI (Midjourney, DALL·E, Stable
Diffusion, ...) Grafiken erzeugst** und diese für den Druck in ein
bestimmtes ICC-Profil (z. B. ein DTF-/CMYK-Profil deines Druckers oder
Dienstleisters) umwandeln willst: KI-generierte Bilder haben oft keinen
sauberen Alphakanal, enthalten stark gesättigte Farben außerhalb des
druckbaren Farbraums und kein eingebettetes Farbprofil. DTF Korrektur
erkennt das automatisch, bereinigt die Transparenz und rechnet die Farben
kontrolliert (mit Softproof- und Gamut-Warnung) auf das Zielprofil um, statt
sie einfach unkontrolliert zu konvertieren.

## Download (Windows)

| Datei | Für wen | Link |
|---|---|---|
| **DTF-Korrektur-Setup.exe** | Empfohlen: normale Installation mit Startmenü-Eintrag & Uninstaller | [Download](https://github.com/Richert-g/dtf-korrektur/releases/download/v1.0.0/DTF-Korrektur-Setup.exe) |
| **DTF-Korrektur-portable.zip** | Portabel, kein Setup nötig - einfach entpacken und starten | [Download](https://github.com/Richert-g/dtf-korrektur/releases/download/v1.0.0/DTF-Korrektur-portable.zip) |

Alle Releases: [github.com/Richert-g/dtf-korrektur/releases](https://github.com/Richert-g/dtf-korrektur/releases)

### Installer verwenden

1. `DTF-Korrektur-Setup.exe` herunterladen und ausführen.
2. Keine Administratorrechte nötig (Installation pro Benutzer).
3. Nach der Installation über das Startmenü "DTF Korrektur" öffnen.
4. Deinstallieren jederzeit über "Apps und Features" oder den Eintrag im
   Startmenü.

### Portable ZIP verwenden

1. `DTF-Korrektur-portable.zip` herunterladen und an einen beliebigen Ort
   entpacken (z. B. USB-Stick, kein Installationsvorgang nötig).
2. `DTF-Korrektur.exe` im entpackten Ordner starten. Der `_internal`-Ordner
   muss dabei im selben Verzeichnis bleiben.

### Bedienung

1. Bild(er) oder einen Ordner in das Fenster ziehen (oder über die Buttons
   auswählen).
2. Optional ein ICC-Zielprofil wählen (mehrere gängige Profile sind bereits
   eingebaut, z. B. FOGRA39, SWOP, GRACoL, Adobe RGB - siehe unten).
3. Auf **"Automatisch optimieren"** klicken.
4. Ergebnis prüfen (Vorher/Nachher, Softproof, Diff-Vorschau) und den
   Ausgabeordner öffnen.

Ausführliche Anleitung: [docs/user-guide.md](docs/user-guide.md)

## Unter Windows selbst kompilieren

```powershell
git clone https://github.com/Richert-g/dtf-korrektur.git
cd dtf-korrektur
py -3.12 -m venv .venv
.venv\Scripts\pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt

# Lokal direkt starten (ohne EXE zu bauen):
.venv\Scripts\python.exe -m src.app.main

# EXE + Installer bauen (benötigt optional Inno Setup für den Installer,
# z. B. per `winget install --id JRSoftware.InnoSetup`):
scripts\build_windows.ps1
```

Ergebnis: `dist\DTF-Korrektur\DTF-Korrektur.exe` (portabel) und
`dist\installer\DTF-Korrektur-Setup.exe` (Installer). Details, inkl. warum
`--onedir` statt `--onefile` verwendet wird und wie das App-Icon eingebunden
ist: [docs/build-windows.md](docs/build-windows.md)

## Unter Linux zum Laufen bringen

Die `.exe`/der Installer sind Windows-spezifisch und laufen unter Linux
nicht direkt (auch nicht über Wine getestet/unterstützt). Die Anwendung
selbst ist aber reines Python + PySide6/Qt und läuft auf Linux problemlos
**aus dem Quellcode**:

```bash
git clone https://github.com/Richert-g/dtf-korrektur.git
cd dtf-korrektur

python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Qt6-Laufzeitabhängigkeiten (Debian/Ubuntu-Beispiel; je nach Distribution
# ggf. abweichend, meist über den Paketmanager der Distribution nötig):
sudo apt install libgl1 libegl1 libxkbcommon0 libdbus-1-3

python -m src.app.main
```

Tests laufen ebenso plattformunabhängig: `pytest tests/ -v`

Wer eine eigenständige Linux-Binary möchte, kann PyInstaller auch unter
Linux verwenden (dort erzeugt es ein Linux-ELF-Binary, kein Windows-EXE):

```bash
python -m PyInstaller --name "DTF-Korrektur" --windowed --onedir \
    --paths . --add-data "resources:resources" src/app/main.py
```

(Unter Linux wird bei `--add-data` ein `:` statt `;` als Trennzeichen
verwendet.) Das wurde in diesem Projekt nicht offiziell getestet/gepflegt -
das primäre Zielsystem ist Windows.

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
PSD/AVIF-Unterstützung, Linux nur aus dem Quellcode lauffähig).
