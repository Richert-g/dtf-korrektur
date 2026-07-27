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
| **DTF-Korrektur-Setup.exe** | Empfohlen: normale Installation mit Startmenü-Eintrag & Uninstaller | [Download](https://github.com/Richert-g/dtf-korrektur/releases/latest/download/DTF-Korrektur-Setup.exe) |
| **DTF-Korrektur-portable.zip** | Portabel, kein Setup nötig - einfach entpacken und starten | [Download](https://github.com/Richert-g/dtf-korrektur/releases/latest/download/DTF-Korrektur-portable.zip) |

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

## Unter macOS zum Laufen bringen

Die `.exe`/der Installer sind Windows-spezifisch und laufen unter macOS
nicht. Die Anwendung ist aber reines Python + PySide6/Qt und läuft auf macOS
problemlos **aus dem Quellcode** - sowohl auf Intel- als auch auf
Apple-Silicon-Macs (M1/M2/M3/…), da alle Abhängigkeiten native arm64-Wheels
mitbringen:

```bash
git clone https://github.com/Richert-g/dtf-korrektur.git
cd dtf-korrektur

python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

python -m src.app.main
```

Python 3.12 fehlt auf macOS meist von Haus aus - am einfachsten per
[Homebrew](https://brew.sh) installieren: `brew install python@3.12`. Extra
Qt-Systembibliotheken wie unter Linux sind **nicht** nötig, PySide6 bringt
seine eigenen Qt-Frameworks mit.

Tests laufen ebenso plattformunabhängig: `pytest tests/ -v`

Lokale Einstellungen/Profile landen mangels `%LOCALAPPDATA%` automatisch
unter `~/.dtf_korrektur/` - keine gesonderte Konfiguration nötig.

Wer ein eigenständiges `.app`-Bundle möchte, kann PyInstaller auch unter
macOS verwenden:

```bash
python -m PyInstaller --name "DTF-Korrektur" --windowed --onedir \
    --paths . --add-data "resources:resources" src/app/main.py
```

Das erzeugte `dist/DTF-Korrektur.app` ist unsigniert - macOS Gatekeeper
blockiert es beim ersten Start ("nicht verifizierter Entwickler"). Abhilfe:
im Finder mit Rechtsklick → "Öffnen" statt Doppelklick, oder
`xattr -dr com.apple.quarantine dist/DTF-Korrektur.app` im Terminal. Auch das
wurde in diesem Projekt nicht offiziell getestet/gepflegt - das primäre
Zielsystem ist Windows.

## Funktionsumfang

**Bildimport & Analyse**
- PNG, JPG/JPEG, TIFF, BMP, WebP (PSD/AVIF als Best-Effort); Drag & Drop,
  Einzelbild oder ganzer Ordner; Stapelverarbeitung mehrerer Dateien mit
  Fortschrittsanzeige, Abbruch und kontrollierter Parallelität.
- Automatische Bildtyp-Erkennung (Logo/Schrift, Illustration, Foto, Motiv mit
  weichem Schatten/Glow) steuert die Automatik-Verarbeitung.

**Transparenz-/Alpha-Bereinigung**
- Vier Modi: Auto, Nur Störpixel entfernen, Sanfte Bereinigung, Harte Kante
  (Otsu-Schwelle).
- **Pixel löschen bis Alpha-Wert** und **Pixel ab Alpha-Wert auf volle
  Deckkraft setzen** - beide mit einstellbarem Schwellenwert, inklusiver
  Grenze und automatischem Schutz großer, bewusster weicher Flächen
  (Schatten/Rauch/Glow) im Automatikmodus.
- Entfernung kleiner Pixelinseln, Schließen kleiner transparenter Löcher,
  Kantenrücknahme/-glättung.
- **Farbsaum-/Halo-Korrektur** an halbtransparenten Kanten.

**Farbmanagement (ICC, via LittleCMS)**
- Automatische Quellprofil-Erkennung (sonst sRGB angenommen), frei wählbares
  ICC-Zielprofil (mitgeliefert: FOGRA, GRACoL, SWOP, JapanColor, Adobe RGB
  u. a.; eigene Profile importierbar und werden vor Verwendung geprüft).
- Rendering Intent (automatisch oder manuell) und Schwarzpunktkompensation.
- Gezielte, abschaltbare Sättigungsoptimierung für Farben außerhalb des
  Zielfarbraums (schützt Hauttöne/Grau/Schwarz).
- **Softproof**- und **Gamut-Warnung**-Vorschau (rein informativ).

**Vorschau & Kontrolle**
- Zoom (Mausrad, 10-800 %), Verschieben, Einpassen/100 % in jeder Ansicht.
- Vorher/Nachher-Vergleich mit verschiebbarem Trenner, synchronem Zoom sowie
  drei klar getrennten Zuständen (Original / nur Transparenz / Softproof).
- **Farbpicker** im Vergleich: Klick auf ein Pixel zeigt Hex-Code, RGB und
  Alpha vorher/nachher an derselben Stelle in voller Auflösung.
- Diff-Vorschau: entfernte/verstärkte Pixel farbig hervorgehoben.

**Presets**
DTF Auto, Logo und Schrift, Illustration, Foto, weicher Schatten, Nur
Transparenz, Nur Farben, **DTF-King - ISO Coated v2 (ECI)** (siehe unten),
Benutzerdefiniert.

**Ausgabeformat** - frei wählbar, unabhängig vom Preset:
- **PNG** (Standard, mit Transparenz) / **TIFF** (verlustfrei, mit Transparenz)
  / **JPEG** (ohne Transparenz, auf Volltonfarbe geflacht)
- **PDF**: einseitige, druckfertige CMYK-PDF mit eingebettetem ICC-Profil,
  echter Transparenz-Softmask, Mindestauflösungs-Prüfung (300 dpi) und
  automatischer Nachvalidierung der erzeugten Datei - z. B. für den
  DTF-King-Workflow.

Zusätzlich optional exportierbar: Alpha-Maske, Weißunterlegungs-Vorschau,
CMYK-TIFF-Vorschau, sowie ein technischer JSON- und ein verständlicher
HTML-Bericht pro Bild (inkl. zusammenfassendem Stapelbericht).

**Update-Check**
Prüft beim Start unaufdringlich im Hintergrund gegen die öffentliche
GitHub-Releases-API, ob eine neuere Version verfügbar ist (kein
Auto-Download, keine persönlichen Daten, jederzeit abschaltbar).

Ausführliche Erklärung aller Funktionen: [docs/user-guide.md](docs/user-guide.md)

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
