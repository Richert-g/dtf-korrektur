# Verarbeitungspipeline

Jedes Bild durchläuft `src/core/pipeline.py::process_image()` in dieser Reihenfolge:

## 1. Laden (`core/analysis/image_loader.py`)

Lädt PNG/JPG/TIFF/BMP/WebP (PSD/AVIF nur eingeschränkt, siehe Grenzen) robust als
RGBA-NumPy-Array. Beschädigte Dateien lösen `ImageLoadError` aus, statt die
Anwendung abstürzen zu lassen.

## 2. Alpha-Analyse (`core/analysis/alpha_analysis.py`)

Ermittelt: transparente/halbtransparente/deckende Pixelanzahl, Alpha-Histogramm,
zusammenhängende halbtransparente Bereiche (über `cv2.connectedComponentsWithStats`),
ob Halbtransparenz überwiegend am **Motivrand** liegt (nicht am Bildrand! - ermittelt
über ein Dilations-Band um deckende Pixel, `motif_edge_band_mask`), kleine
Pixelinseln und kleine Löcher.

## 3. Klassifizierung (`core/classification/classifier.py`)

Ordnet das Bild anhand der Alpha-Analyse und einer groben Farb-/Kantenkomplexitäts-
schätzung einem von vier Typen zu: **Logo/Schrift**, **Illustration**, **Foto**,
**weicher Schatten**. Jede Entscheidung wird mit Gründen protokolliert
(`ImageAnalysisResult.classification_reasons` bzw. `ImageProcessingReport.classification_reasons`).

## 4. Halo-/Farbsaumkorrektur (`core/halo/halo_correction.py`)

**Läuft bewusst vor der Alpha-Bereinigung**, solange die halbtransparenten
Randpixel noch existieren. Verfahren: iterative, radiusbegrenzte
Farbfortschreibung von deckenden Nachbarpixeln nach außen (ähnlich einem
Push-Pull-Weichzeichner). Nur RGB wird verändert, Alpha bleibt unangetastet.
Pixel ohne erreichbaren deckenden Nachbarn (z. B. isolierte dünne Details)
bleiben unverändert, um Details nicht zu zerstören.

## 5. Alpha-Bereinigung (`core/alpha/alpha_cleanup.py`)

Vier Modi (`AlphaMode`): `AUTO`, `HARD_EDGE`, `SOFT_CLEANUP`, `NOISE_ONLY`.
Im Modus `AUTO` wird anhand des erkannten Bildtyps automatisch gewählt:

| Bildtyp | Modus |
|---|---|
| Logo/Schrift | Harte Kante (Otsu-Schwelle, Inseln/Löcher, optionaler Choke) |
| Illustration | Sanfte Bereinigung (positionsabhängig am Motivrand) |
| Foto | Nur Störpixel entfernen |
| Weicher Schatten | Nur Störpixel entfernen (keine Binarisierung!) |

Alle Schwellenwerte kommen aus `AlphaThresholds` (`src/config/defaults.py`).

### "Pixel mit geringer Deckkraft bearbeiten" (`weak_alpha_threshold`)

Zentrale Einstellung in NOISE_ONLY und SOFT_CLEANUP: alle Pixel mit
`Alpha <= Schwellenwert` werden bearbeitet (inklusive Grenze:
`alpha <= threshold`, nicht `alpha < threshold`; bewusst OHNE Ausnahme für
bereits transparente Pixel, siehe unten), alle Pixel mit `Alpha >
Schwellenwert` bleiben unverändert. Standard: **254** (Bereich 0-254 in der
Oberfläche; 255 ist nicht wählbar, da dadurch auch vollständig deckende
Pixel betroffen wären).

Über `weak_alpha_action` (`WeakAlphaAction`) wird gesteuert, WIE die
betroffenen Pixel bearbeitet werden: `SET_TRANSPARENT` (Standard) setzt nur
den Alpha-Wert auf 0 (RGB bleibt erhalten), `DELETE_PIXEL` setzt zusätzlich
auch die RGB-Kanäle auf 0 (keine Farbinformationen bleiben zurück - auch
bei bereits vorher transparenten Pixeln, daher die fehlende
`alpha > 0`-Ausnahme in der Auswahlmaske). Für die Berichtszählung
("removed_pixel_count") werden trotzdem nur tatsächlich zuvor sichtbare
Pixel gezählt.

Die zugrunde liegende Funktion `_remove_weak_noise` wendet diesen Wert für
sich genommen **global** auf das gesamte Bild an - sie kennt keine
Bildbereiche. Da 254 bewusst sehr aggressiv ist, würde eine rein globale
Anwendung auch bewusste weiche Schattenflächen zerstören. Deshalb berechnet
`clean_alpha` **nur im Automatikmodus** (`settings.alpha_mode == AUTO`)
zusätzlich eine Schutzmaske über
`core.analysis.alpha_analysis.compute_large_soft_region_mask()`: große,
nicht überwiegend am Motivrand liegende Halbtransparenz-Flächen (typisch für
Schatten/Rauch/Glow) werden von der Bearbeitung ausgenommen. Wählt der
Benutzer dagegen manuell einen konkreten Modus (z. B. "Nur Störpixel
entfernen"), gilt der Schwellenwert bewusst für das gesamte Bild - die
Oberfläche zeigt dafür ab einem Wert von 220 eine Warnung an
(`AdvancedSettingsDialog`).

**Achtung Standardwerte:** Bei `weak_alpha_threshold=254` und
`near_opaque_threshold=242` (beide Standard) überschneiden sich die
Wertebereiche - unter der Standard-Reihenfolge `AlphaThresholdOrder.REMOVE_FIRST`
hat "Pixel ab Alpha-Wert auf volle Deckkraft setzen" dadurch praktisch
keinen sichtbaren Effekt mehr, da die betroffenen Pixel schon vorher
bearbeitet wurden (siehe Moduldocstring in `alpha_cleanup.py` für Details
zur konfigurierbaren Reihenfolge über `threshold_order`).

## 6. Farboptimierung / ICC (`core/color/color_pipeline.py`)

Siehe `color-management.md` für Details. Kurzfassung: Quell- und Zielprofil
bestimmen, Rundreise-Transformation zur Delta-E-Messung (Lab, CIE76),
automatische Rendering-Intent-Wahl, gezielte (nicht pauschale) Sättigungs-
reduktion nur in Farbraum-Konfliktbereichen, iterativ bis zur Konvergenz.

## 7. Export (`core/export/`)

- **Hauptausgabe**: RGB-PNG mit Transparenz, sRGB-Profil eingebettet
  (`png_export.py`).
- **Optional**: Alpha-Maske (PNG), Weißunterlegungs-Vorschau mit Choke
  (`white_mask.py` - nur Hilfsdatei!), CMYK-TIFF-Vorschau (`cmyk_export.py`,
  nur mit gültigem Zielprofil, siehe Sicherheitsregeln), Softproof-PNG.

## 8. Bericht (`core/reporting/`)

JSON (`report_writer.py::write_json_report`) und verständliches HTML
(`write_html_report`) je Bild; zusammenfassender `batch_summary.json`
(`batch_report.py`) für die gesamte Stapelverarbeitung.

## Sicherheitsmechanismen (Prompt Abschnitt 19)

- Große, zusammenhängende halbtransparente Flächen (`covers_large_area` und
  nicht überwiegend am Rand) werden als `SOFT_SHADOW` klassifiziert und landen
  automatisch im nicht-binarisierenden `NOISE_ONLY`-Modus.
- CMYK-Export wird ohne gültiges, vom Benutzer gewähltes Zielprofil
  **verweigert** (nur eine Warnung, kein Absturz).
- Defekte ICC-Profile führen zu einem Rückfall auf sRGB mit Warnung, nicht zum
  Abbruch.
- Jede fehlerhafte Einzeldatei wird übersprungen und protokolliert
  (`process_image_safe`), die Stapelverarbeitung läuft weiter.
