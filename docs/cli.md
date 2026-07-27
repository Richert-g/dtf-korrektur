# Kommandozeilen-/Automatisierungsmodus

Batch-Verarbeitung ohne Oberfläche - für Automatisierung über den Windows-
Taskplaner, Linux-`cron` oder macOS `launchd`. Nutzt dieselbe Verarbeitungs-
Pipeline wie die grafische Oberfläche (Alpha-/Halo-Korrektur, ICC-
Farbmanagement, alle Presets), aber ohne jede Qt-Abhängigkeit.

## Aufruf

**Windows** (nach Installation, siehe unten):

```powershell
"C:\Program Files\DTF Korrektur\cli\DTF-Korrektur-CLI.exe" --output "C:\Ausgabe" --preset "DTF Auto" "C:\Eingabe"
```

**Windows/Linux/macOS aus dem Quellcode** (venv aktiviert, siehe README für
die jeweilige Einrichtung):

```bash
python -m src.cli --output /pfad/zur/ausgabe --preset "DTF Auto" /pfad/zum/eingabeordner
```

## Argumente

| Argument | Pflicht | Bedeutung |
|---|---|---|
| `inputs` (positional) | ja | Eine oder mehrere Bilddateien oder Ordner (Ordner werden rekursiv nach unterstützten Formaten durchsucht: PNG, JPG/JPEG, TIFF, BMP, WebP; PSD/AVIF als Best-Effort). |
| `--output`, `-o` | ja | Ausgabeordner. Wird bei Bedarf angelegt. |
| `--preset`, `-p` | nein | Name eines eingebauten Presets (`DTF Auto`, `DTF Logo und Schrift`, `DTF Illustration`, `DTF Foto`, `DTF mit weichem Schatten`, `Nur Transparenz bereinigen`, `Nur Farben optimieren`, `DTF-King – ISO Coated v2 (ECI)`, `Benutzerdefiniert`) oder eines über die Oberfläche gespeicherten benutzerdefinierten Presets. Standard: `DTF Auto`. |
| `--format` | nein | Überschreibt das vom Preset gewählte Ausgabeformat: `png`, `tiff`, `jpeg` oder `pdf`. |
| `--workers` | nein | Maximale Anzahl paralleler Verarbeitungen. Standard: 2 (siehe `DEFAULT_MAX_PARALLEL_WORKERS`). |
| `--overwrite` | nein | Bestehende Ausgabedateien überschreiben statt automatisch einen neuen Dateinamen zu wählen. |
| `--quiet` | nein | Nur die Abschlusszusammenfassung ausgeben, keine Fortschrittszeile pro Datei. |

Vollständige Hilfe: `DTF-Korrektur-CLI.exe --help` bzw. `python -m src.cli --help`

## Exit-Codes

| Code | Bedeutung |
|---|---|
| `0` | Alle Dateien erfolgreich verarbeitet. |
| `1` | Mindestens eine Datei fehlgeschlagen (Details in der Ausgabe und in `<Ausgabeordner>\reports\batch_summary.json`). |
| `2` | Ungültiger Aufruf (z. B. unbekanntes Preset, keine unterstützten Bilddateien gefunden). |

Diese Codes lassen sich in Taskplaner/cron/launchd direkt auswerten, um bei
einem Fehlschlag eine Benachrichtigung auszulösen.

## Benutzerdefinierte Presets im CLI-Modus

Ein in der Oberfläche über "Als Preset speichern…" gespeichertes Preset
lässt sich per `--preset "Mein Preset"` genauso wie ein eingebautes Preset
verwenden - die Presets werden aus derselben Datei geladen
(`%LOCALAPPDATA%\DTFKorrektur\presets.json` unter Windows, siehe
`config.paths.get_user_data_dir()` für die jeweilige Plattform).

## Der DTF-King-PDF-Export im CLI-Modus

Anders als in der Oberfläche (die vor jedem DTF-King-Export einen Dialog zur
Bestätigung von Breite/Höhe/DPI zeigt) läuft der PDF-Export im CLI-Modus
**vollständig unbeaufsichtigt** mit den im Preset/den Standardeinstellungen
hinterlegten Werten (Standard: 300 dpi, native Bildgröße, keine
Hochskalierung). Ein ICC-Zielprofil muss im verwendeten Preset bereits
gesetzt sein (beim eingebauten DTF-King-Preset ist das automatisch Coated
FOGRA39, falls kein anderes Profil gewählt wurde) - fehlt es, schlägt die
betroffene Datei mit einer klaren Fehlermeldung fehl (Exit-Code 1), ohne den
gesamten Lauf abzubrechen.

## Windows: Installation und Taskplaner

Nach der Installation über `DTF-Korrektur-Setup.exe` liegt die Konsolen-EXE
unter `<Installationsordner>\cli\DTF-Korrektur-CLI.exe` (Standard:
`C:\Program Files\DTF Korrektur\cli\DTF-Korrektur-CLI.exe`).

Aufgabe im Taskplaner einrichten (Beispiel per `schtasks`, täglich 22:00 Uhr):

```powershell
schtasks /Create /TN "DTF Korrektur Batch" /TR "\"C:\Program Files\DTF Korrektur\cli\DTF-Korrektur-CLI.exe\" --output \"C:\DTF\Ausgabe\" --preset \"DTF Auto\" \"C:\DTF\Eingabe\"" /SC DAILY /ST 22:00
```

Oder über die grafische Taskplaner-Oberfläche: Aktion "Programm starten" mit
obigem Pfad und den Argumenten ab `--output ...`.

## Linux: cron

```bash
# crontab -e
0 22 * * * cd /pfad/zum/projekt && .venv/bin/python -m src.cli --output /pfad/ausgabe --preset "DTF Auto" /pfad/eingabe >> /var/log/dtf-korrektur.log 2>&1
```

## macOS: launchd

`~/Library/LaunchAgents/com.dtfkorrektur.batch.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.dtfkorrektur.batch</string>
    <key>ProgramArguments</key>
    <array>
        <string>/pfad/zum/projekt/.venv/bin/python</string>
        <string>-m</string>
        <string>src.cli</string>
        <string>--output</string>
        <string>/pfad/ausgabe</string>
        <string>--preset</string>
        <string>DTF Auto</string>
        <string>/pfad/eingabe</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/pfad/zum/projekt</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>22</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/dtf-korrektur.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/dtf-korrektur.log</string>
</dict>
</plist>
```

Laden mit `launchctl load ~/Library/LaunchAgents/com.dtfkorrektur.batch.plist`.
