# Architektur

## Überblick

DTF Korrektur ist eine vollständig lokale Windows-Desktop-Anwendung (PySide6) zur
automatischen Optimierung von Bildern für DTF-Druck und andere Druckverfahren.
Es findet keinerlei Übertragung von Bilddaten an externe Server oder Cloud-Dienste statt.

```
src/
  app/                 Oberfläche, Controller, Hintergrund-Worker
    main.py            Einstiegspunkt
    ui/                PySide6-Widgets (Hauptfenster, Vorschau, Dialoge)
    controllers/        Verbindung UI <-> Kernlogik
    workers/            QThread-Worker für Analyse und Stapelverarbeitung
  core/                 Reine Bildverarbeitungslogik (kein Qt-Import)
    analysis/           Bildimport, Alpha-Analyse, Gesamt-Analyzer
    classification/     Automatische Bildtyp-Erkennung
    alpha/               Alpha-Bereinigung (4 Modi)
    halo/                Farbsaum-/Halo-Korrektur
    color/               ICC-Profilverwaltung, Delta E, Gamut, Sättigungsoptimierung
    export/              PNG/CMYK-TIFF/Alpha-Maske/Weißmaske-Export, Dateinamenslogik
    reporting/           JSON/HTML-Berichte je Bild und für die Stapelverarbeitung
    presets/             Preset-Definitionen
    pipeline.py          Orchestriert alle Schritte für ein einzelnes Bild
  models/               Reine Datenklassen (dataclasses), keine Logik
  config/               Zentrale Konfiguration, Pfade, Laden/Speichern der Einstellungen
  utils/                 Qt-Hilfsfunktionen (NumPy <-> QPixmap), Logging

tests/
  unit/                 Modul-Tests mit synthetischen Bildern
  integration/           End-to-End-Pipeline-Tests
  fixtures/              Generatoren für synthetische Testbilder

resources/
  icons/, profiles/, sample_images/

docs/, scripts/
```

## Designprinzipien

- **Trennung von Kernlogik und UI**: Alles unter `src/core` und `src/models` ist
  frei von Qt-Importen und kann unabhängig von der Oberfläche getestet werden.
- **Zentrale Konfiguration**: Alle Schwellenwerte (Alpha, Halo, Gamut, Klassifizierung)
  liegen gesammelt in `src/config/defaults.py`, nicht verstreut im Code.
- **Getrennte Verarbeitungsschritte**: Alpha-Bereinigung und Farbkonvertierung sind
  unabhängige, einzeln testbare Module (siehe `processing-pipeline.md`).
- **Fehlertoleranz**: Jede Datei wird über `*_safe`-Wrapper verarbeitet, die Fehler
  abfangen und protokollieren, statt die Anwendung oder die Stapelverarbeitung
  abstürzen zu lassen.
- **Reaktionsfähige Oberfläche**: Analyse und Verarbeitung laufen in `QThread`-Workern
  (`src/app/workers`), niemals im UI-Thread.
- **Original bleibt unverändert**: Es wird ausschließlich in einen separaten
  Ausgabeordner geschrieben, das Quellbild wird nie geöffnet zum Schreiben.

## Datenfluss (ein Bild)

```
Datei -> load_image() -> analyze_alpha_channel() -> classify_image()
      -> correct_halo() -> clean_alpha() -> optimize_colors()
      -> export_rgba_png() [+ optionale Exporte] -> Bericht (JSON + HTML)
```

Siehe `processing-pipeline.md` für Details zu jedem Schritt und
`color-management.md` für das ICC-Farbmanagement.

## Vorschau-/Zoom-Architektur

`src/app/ui/zoom_pan_view.py` kapselt Zoom-/Pan-Verhalten (Mausrad-Zoom zum
Cursor, 10-800 %, Doppelklick = einpassen, `zoom_changed`-Signal) einmalig in
der Basisklasse `ZoomPanGraphicsView(QGraphicsView)` sowie den
Werkzeugleisten-Widget `ZoomToolbar`. `ZoomableImageView`
(`zoomable_view.py`, Einzelbild) und `CompareSliderWidget`
(`compare_slider.py`, Vorher/Nachher) leiten beide davon ab, statt die
Zoomlogik zu duplizieren. Der Vorher-Nachher-Vergleich liegt als zwei
`QGraphicsPixmapItem`s in **einer** gemeinsamen Szene (das "Nachher"-Bild
über ein klippendes Eltern-Item auf den Bereich links des Trenners
begrenzt), wodurch beide Bilder durch denselben View-Transform zwangsläufig
synchron zoomen/verschieben - ein Verrutschen zwischen den Bildern ist
architektonisch ausgeschlossen.

## Threading-Modell

- `AnalysisWorker` (QThread): analysiert ein einzelnes Bild für die Vorschau,
  bevor der Benutzer auf "Automatisch optimieren" klickt.
- `BatchWorker` (QThread + `ThreadPoolExecutor`): verarbeitet mehrere Dateien mit
  kontrollierter Parallelität (`DEFAULT_MAX_PARALLEL_WORKERS`, Standard 2),
  unterstützt Abbruch und meldet Fortschritt pro Datei an die Oberfläche.

## Bekannte technische Grenzen

Siehe Abschnitt "Bekannte technische Grenzen" in `user-guide.md`.
