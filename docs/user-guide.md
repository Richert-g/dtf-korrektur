# Bedienungsanleitung

## Schnellstart

1. Ein oder mehrere Bilder in den gestrichelten Bereich ziehen (oder
   "Bild auswählen" / "Ordner auswählen" klicken).
2. Die Anwendung analysiert automatisch und zeigt eine verständliche
   Zusammenfassung ("Das Bild wurde als … erkannt. Automatisch geplante
   Verarbeitung: …").
3. Optional ein ICC-Zielprofil auswählen (für Softproof/Farbanpassung/CMYK-
   Vorschau; ohne Profil wird nur die Transparenz bereinigt).
4. Ausgabeordner prüfen/wählen (Standard: `output`-Unterordner neben dem Bild).
5. Auf **"Automatisch optimieren"** klicken.
6. Ergebnis über die Vorher-/Nachher-Ansicht prüfen, Ausgabeordner öffnen.

## Vorschau-Ansichten

Über die Ansicht-Auswahl oben in der Vorschau stehen nach der Optimierung
zur Verfügung: Original, Ergebnis, Softproof (falls Zielprofil gewählt),
Alpha-Maske, Auf weißem/schwarzem Textil sowie zwei Diff-Ansichten:

- **Entfernte Pixel**: zeigt das (abgedunkelte) Originalbild mit allen durch
  die Alpha-Bereinigung entfernten Pixeln in Rot hervorgehoben.
- **Verstärkte Pixel**: dieselbe Darstellung in Grün für Pixel, die von
  teiltransparent auf volle Deckkraft gesetzt wurden.

So lässt sich genau nachvollziehen, welche Pixel die Automatik verändert hat.

## Mitgelieferte ICC-Profile

Die Anwendung bringt bereits eine Auswahl gängiger, frei verwendbarer
ICC-Profile mit (kein manueller Import nötig) - RGB: Adobe RGB, Apple RGB,
ColorMatch RGB u. a.; CMYK: FOGRA27/28/29/39, GRACoL 2006, SWOP, Japan Color
u. a. Diese erscheinen automatisch in der Profil-Auswahl. Sie eignen sich für
Softproof/Gamut-Tests, ersetzen aber kein herstellerspezifisches DTF-Profil
für Drucker/Folie/Pulver (siehe Hinweise unten).

## Presets

| Preset | Wirkung |
|---|---|
| DTF Auto (Standard) | Automatik anhand der Bildanalyse |
| DTF Logo und Schrift | Harte, saubere Kanten |
| DTF Illustration | Vorsichtige Kantenbehandlung |
| DTF Foto | Minimale Eingriffe, Schatten bleiben erhalten |
| DTF mit weichem Schatten | Für Motive mit Schatten/Rauch/Glow |
| Nur Transparenz bereinigen | Keine Farbanpassung |
| Nur Farben optimieren | Transparenz bleibt unverändert |
| Benutzerdefiniert | Vollständig manuelle Steuerung |

## Erweiterte Einstellungen

Über den Button "Erweiterte Einstellungen" erreichbar: Alpha-Modus und
-Schwellenwerte, Halo-Korrektur-Stärke, ICC-Zielprofil/Rendering-Intent/
Schwarzpunktkompensation, maximale Sättigungsreduktion, Export-Optionen
(Alpha-Maske, Weißunterlegung, CMYK-Vorschau, Metadaten, Überschreibverhalten).
Jede Einstellung hat einen Tooltip.

## Eigene ICC-Profile hinzufügen

1. "Importieren…" neben der Profil-Auswahl klicken.
2. `.icc`- oder `.icm`-Datei wählen.
3. Das Profil wird geprüft (defekte Profile werden abgelehnt) und lokal nach
   `%LOCALAPPDATA%\DTFKorrektur\profiles` kopiert.
4. Es erscheint danach in der Profil-Auswahlliste.

## Wichtige Hinweise (keine falschen Versprechen)

- Eine Bildschirmvorschau ist **keine Garantie** für das endgültige
  Druckergebnis.
- Das Ergebnis hängt zusätzlich von Drucker, Tinte, Folie/Pulver, RIP, Textil
  und Pressparametern ab.
- Ein passendes ICC-Profil ist für eine realistische Farbvorschau notwendig.
- Die endgültige Weißunterlegung wird normalerweise im DTF-RIP erzeugt - die
  hier erzeugte Weißmaske ist nur eine Vorschau/Hilfsdatei.
- Ein gewöhnliches generisches CMYK-Profil ist nicht automatisch ein
  korrektes DTF-Profil.

## Bekannte technische Grenzen

- **PSD/AVIF**: nur eingeschränkte Unterstützung über Pillow-Bordmittel; ohne
  zusätzliche Plugins (z. B. `pillow-avif-plugin`) schlägt der Import mit
  einer klaren Fehlermeldung fehl, statt die Anwendung zum Absturz zu bringen.
- **Kein mitgeliefertes DTF-/CMYK-Referenzprofil**: für Softproof, Gamut-
  Analyse und CMYK-Export muss der Benutzer ein eigenes ICC-Profil
  importieren (siehe `color-management.md`).
- **Delta-E-Messung** verwendet CIE76 in Lab (D65) auf Basis einer sRGB-
  Näherung der Quellfarben - ausreichend für eine praxisnahe Gamut-Warnung,
  aber kein Ersatz für professionelle Farbmesstechnik.
- **Sehr große Bilder**: Die Verarbeitung erfolgt vollständig über NumPy/OpenCV
  im Arbeitsspeicher (kein explizites Chunking über die Festplatte). Bei
  Bildern deutlich über ca. 40 Megapixeln kann der Speicherverbrauch spürbar
  steigen.
- **Vorschau vs. Export**: Die Bildschirmvorschau wird bei sehr großen Bildern
  automatisch verkleinert (siehe `MAX_PREVIEW_DIMENSION_PX`); der Export
  rechnet immer mit den vollen Originaldaten.
- **Weißunterlegungsmaske und CMYK-TIFF** sind ausdrücklich nur Vorschau-/
  Hilfsdateien, keine produktionsfertigen RIP-Daten.
- **PSD-Ebenen** werden nicht einzeln unterstützt - Pillow liest PSD-Dateien
  nur als zusammengeführtes Composite-Bild.
