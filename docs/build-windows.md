# Windows-Build

## Voraussetzungen

- Windows 10/11
- Python 3.12 (z. B. über `py -3.12` verfügbar)
- Optional, für einen echten Installer: [Inno Setup 6](https://jrsoftware.org/isinfo.php)
  (kostenlos), z. B. per `winget install --id JRSoftware.InnoSetup`

## Virtuelle Umgebung einrichten

```powershell
py -3.12 -m venv .venv
.venv\Scripts\pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt
```

## Tests ausführen

```powershell
scripts\run_tests.ps1
```

oder direkt:

```powershell
.venv\Scripts\python.exe -m pytest tests/ -v
```

## Lokal starten (ohne Build)

```powershell
.venv\Scripts\python.exe -m src.app.main
```

## App-Icon erzeugen

Das Icon wird programmatisch erzeugt (kein externes Bildmaterial nötig) und
liegt unter `resources/icons/app_icon.ico`. Bereits vorhanden - bei Bedarf
neu erzeugen mit:

```powershell
.venv\Scripts\python.exe scripts\generate_icon.py
```

## Windows-EXE und Installer erstellen

```powershell
scripts\build_windows.ps1
```

Das Skript:

1. erzeugt bei Bedarf das App-Icon,
2. räumt alte `build`/`dist`-Ordner robust auf (mit Wiederholungsversuchen,
   falls z. B. ein Virenscanner oder OneDrive-Sync kurzzeitig eine Datei
   sperrt),
3. baut mit PyInstaller im `--onedir`-Modus (zuverlässiger und schneller
   startend als `--onefile`), inkl. Icon und `resources/`-Ordner,
4. baut zusätzlich einen **zweiten, eigenständigen Konsolen-Build** für den
   Kommandozeilen-/Automatisierungsmodus (`src/cli.py`, siehe README,
   Abschnitt "Kommandozeilen-/Automatisierungsmodus") - bewusst ein
   separater Build statt eines Schalters an der GUI-EXE, da diese mit
   `--windowed` gebaut wird und daher kein Konsolenfenster hat (keine
   stdout-Ausgabe, keine für einen Taskplaner auswertbaren Exit-Codes).
   `src/cli.py` hat keine PySide6-Abhängigkeit, der Build bringt daher kein
   Qt mit und fällt entsprechend kleiner aus,
5. erstellt zusätzlich einen echten Windows-Installer mit Inno Setup, **falls
   `ISCC.exe` gefunden wird** - andernfalls wird dieser Schritt übersprungen
   und eine Installationsanleitung ausgegeben. Der Installer bündelt beide
   Builds (GUI unter `{app}\`, CLI unter `{app}\cli\`, in getrennten
   Unterordnern wegen der jeweils eigenen `_internal`-Abhängigkeiten).

Ergebnis:

```
dist\DTF-Korrektur\DTF-Korrektur.exe            <- eigenständige GUI-App (Ordner kopierbar)
dist\DTF-Korrektur\_internal\...
dist\DTF-Korrektur-CLI\DTF-Korrektur-CLI.exe    <- Kommandozeilen-/Automatisierungsmodus (Ordner kopierbar)
dist\DTF-Korrektur-CLI\_internal\...
dist\installer\DTF-Korrektur-Setup.exe          <- richtiger Installer (falls Inno Setup vorhanden), enthält beide
```

`DTF-Korrektur-Setup.exe` installiert die App ins Startmenü (mit
Verknüpfung, optionalem Desktop-Icon und Uninstaller), ganz ohne
Administratorrechte (`PrivilegesRequired=lowest` in `scripts\installer.iss`).
Getestet über eine stille Installation (`/VERYSILENT /DIR=...`) inklusive
Start der installierten EXE - lief fehlerfrei durch.

Der komplette `dist\DTF-Korrektur`-Ordner (ohne Installer) funktioniert
weiterhin eigenständig und kann auch einfach kopiert werden - keine
Internetverbindung nötig (siehe Prompt-Vorgabe "vollständig lokal").

Für eine einzelne EXE-Datei statt eines Ordners (etwas langsamerer Start):

```powershell
.venv\Scripts\python.exe -m PyInstaller --name "DTF-Korrektur" --windowed --onefile --icon resources\icons\app_icon.ico --paths . --add-data "resources;resources" src/app/main.py
```

## Manuell verifiziert

- PyInstaller-Onedir-Build erfolgreich, `DTF-Korrektur.exe` probeweise
  gestartet (Prozess blieb aktiv, kein Absturz).
- Inno-Setup-Installer erfolgreich kompiliert, still installiert
  (`/VERYSILENT`) und die installierte EXE probeweise gestartet.
- Gebündelte ICC-Profile (`resources/profiles/CMYK`, `resources/profiles/RGB`)
  sowie das Icon wurden in der installierten Version am erwarteten Ort
  (`_internal\resources\...`) gefunden.

## Bekannte Build-Hinweise

- `PyInstaller` erkennt PySide6, NumPy, OpenCV und Pillow über die mitgelieferten
  Hooks aus `pyinstaller-hooks-contrib` automatisch - keine manuellen
  `--hidden-import`-Angaben nötig.
- Der Ordner `resources/` (Icons, mitgelieferte ICC-Profile, Beispielbilder)
  wird über `--add-data resources;resources` mit ausgeliefert. **Wichtig:**
  Zur Laufzeit liegen diese Daten in der gebauten EXE unter `sys._MEIPASS`
  (bei `--onedir` faktisch `_internal/resources`), **nicht** neben der .exe
  selbst - siehe `src/config/paths.py::get_bundled_resources_dir()`.
- Eigene ICC-Profile werden automatisch erkannt, wenn sie vor dem Build in
  `resources/profiles/` (auch in Unterordnern wie `CMYK/`, `RGB/`) abgelegt
  werden.
- Der CLI-Build (`src/cli.py`, keine PySide6-Abhängigkeit im Code) bindet
  PyInstallers automatischer Analyse zufolge trotzdem PySide6/shiboken6 mit
  ein, obwohl kein tatsächlich importierter Code-Pfad das braucht - deshalb
  im Skript explizit `--exclude-module PySide6 --exclude-module shiboken6`
  (geprüft: Build läuft ohne Warnungen zu fehlenden Modulen durch, spart
  ca. 30 % Speicherplatz im `dist`-Ordner).
- `$ErrorActionPreference` in den PowerShell-Skripten ist bewusst `Continue`
  statt `Stop`: Native Tools wie PyInstaller/ISCC schreiben auch reine
  INFO-Meldungen nach stderr, was PowerShell 5.1 bei `Stop` fälschlich als
  Abbruchfehler werten würde. Fehler werden stattdessen explizit über
  `$LASTEXITCODE` geprüft.
