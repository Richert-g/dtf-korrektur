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
zur Verfügung: Original, Optimiertes Ergebnis, Softproof (falls Zielprofil
gewählt), Alpha-Maske, Auf weißem/schwarzem Textil sowie:

- **Entfernte Pixel**: zeigt das (abgedunkelte) Originalbild mit allen durch
  die Alpha-Bereinigung entfernten Pixeln in Rot hervorgehoben.
- **Verstärkte Pixel**: dieselbe Darstellung in Grün für Pixel, die von
  teiltransparent auf volle Deckkraft gesetzt wurden.
- **Gamut-Warnung**: Pixel, die vor der automatischen Farboptimierung
  außerhalb des Zielfarbraums lagen, in Magenta hervorgehoben (nur bei
  gewähltem Zielprofil und tatsächlich vorhandenen Out-of-Gamut-Pixeln).
- **Weißunterlegungsmaske**: die exportierte Weißunterlegungs-Vorschau (nur
  wenn in den erweiterten Einstellungen aktiviert).

So lässt sich genau nachvollziehen, welche Pixel die Automatik verändert hat.
Das Auswahlfeld ist automatisch breit genug für den längsten Eintrag
("Weißunterlegungsmaske") - keine abgeschnittenen Texte, auch bei höherer
Windows-Anzeigeskalierung.

### Zoomen und Verschieben in der Vorschau

Gilt einheitlich für die Einzelansicht und die Vorher-/Nachher-Vergleichsansicht:

- **Mausrad**: hinein-/herauszoomen (10 % bis 800 %), der Bildpunkt unter dem
  Mauszeiger bleibt dabei an derselben Stelle. Die Seite scrollt dabei nicht mit.
- **Ziehen mit gedrückter Maustaste**: verschiebt das Bild (bei der
  Vergleichsansicht: außerhalb des Trennerbereichs).
- **Doppelklick**: passt die Ansicht wieder ans Fenster an.
- Buttons **"Ansicht einpassen"** und **"100 %"** sowie eine Anzeige des
  aktuellen Zoomwerts (z. B. "125 %") stehen oberhalb jeder Vorschau bereit.
- In der Vergleichsansicht liegen beide Bilder in derselben Szene und
  zoomen/verschieben sich dadurch zwangsläufig synchron - sie können nicht
  gegeneinander verrutschen. Der rote Trenner lässt sich weiterhin per Ziehen
  verschieben.

### Farbpicker in der Vorher-/Nachher-Ansicht

Über den Button **"Farbpicker"** oberhalb der Vergleichsansicht aktivieren.
Solange aktiv, verschiebt ein Klick auf das Bild nicht mehr den Trenner,
sondern zeigt darunter für genau diese Bildposition den Farbcode **vorher**
und **nachher** an - jeweils mit Farbfläche, Hex-Code (`#RRGGBB`), RGB-Werten
und Alpha-Wert. So lässt sich exakt nachvollziehen, wie sich ein einzelnes
Pixel durch die Verarbeitung verändert hat. Die Werte stammen aus der vollen
Bildauflösung, nicht aus der (ggf. herunterskalierten) Bildschirmvorschau.
Erneut auf den Button klicken, um zum normalen Trenner-Verhalten
zurückzukehren.

## Ausgabeformat

Über das Feld **"Ausgabeformat"** im rechten Bereich lässt sich unabhängig
vom Preset wählen, welche Datei "Automatisch optimieren" erzeugt:

| Format | Transparenz | Eignung |
|---|---|---|
| PNG | Ja | Standard, verlustfrei, für die meisten DTF-RIPs geeignet |
| TIFF | Ja | Verlustfrei, alternative zu PNG (z. B. für Workflows, die TIFF erwarten) |
| JPEG | Nein - wird auf Weiß geflacht | Kleinere Dateigröße, nur wenn Transparenz nicht benötigt wird |
| PDF | Ja (als Softmask) | Druckfertige, einseitige CMYK-PDF - erfordert ein gültiges CMYK-ICC-Zielprofil, siehe DTF-King-Preset oben |

Wird PDF gewählt (egal ob per Preset oder manuell über dieses Feld), öffnet
sich vor dem Export derselbe Dialog wie beim DTF-King-Preset (Profilprüfung,
Druckgröße/dpi, Zusammenfassung).

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
| DTF-King – ISO Coated v2 (ECI) | Druckfertige CMYK-PDF für den Druckdienstleister DTF-King |
| Benutzerdefiniert | Vollständig manuelle Steuerung |

## Preset "DTF-King – ISO Coated v2 (ECI)"

Erzeugt statt eines RGB-PNGs eine **einseitige, druckfertige CMYK-PDF** mit
eingebettetem ICC-Zielprofil, echter Transparenz (Softmask) und mindestens
300 dpi bei der gewählten Druckgröße - ohne jede zusätzliche, hausgemachte
Sättigungs- oder Gamut-Korrektur nach der ICC-Konvertierung. Die Farbe
entsteht ausschließlich durch die eine, echte ICC-Transformation.

**So verwendest du es:**

1. Das offizielle ICC-Profil **"ISO Coated v2 (ECI)"** einmalig über
   "Importieren…" hinzufügen (z. B. von eci.org). Die App ersetzt es
   **niemals** automatisch durch ein ähnliches, bereits mitgeliefertes
   Profil (z. B. FOGRA39) - ohne dieses konkrete Profil bricht der Export
   mit einer klaren Fehlermeldung ab.
2. Preset "DTF-King – ISO Coated v2 (ECI)" auswählen. Wurde das Profil in
   Schritt 1 bereits importiert, wird es automatisch als Zielprofil
   übernommen (erkennbar an "ISO Coated v2" in der Profilbeschreibung).
3. Bild(er) auswählen, Ausgabeordner wählen, auf "Automatisch optimieren"
   klicken.
4. Es öffnet sich ein Dialog: ICC-Profilstatus, Breite/Höhe/Ziel-dpi (Standard
   300 dpi, Höhe automatisch proportional zur Breite, oder beides manuell
   festlegen), sowie eine vollständige Zusammenfassung vor dem eigentlichen
   Export. Der "Exportieren"-Button ist deaktiviert, solange kein gültiges
   CMYK-Zielprofil vorliegt.
5. Nach dem Export wird die erzeugte PDF automatisch erneut geöffnet und
   geprüft (Seitenzahl, Farbraum, eingebettetes Profil, Transparenzmaske,
   Seitengröße). Nur bei erfolgreicher Prüfung gilt der Export als
   abgeschlossen.

Die Bildpixel werden **nie ohne Hinweis künstlich hochskaliert** - reichen sie
für die gewünschte Größe bei 300 dpi nicht aus, erscheint eine Warnung wie
"Die Datei erreicht bei 28,0 cm Breite nur 238 dpi …". Hochskalierung muss im
Dialog ausdrücklich aktiviert werden.

## Erweiterte Einstellungen

Über den Button "Erweiterte Einstellungen" erreichbar: Alpha-Modus und
-Schwellenwerte, Halo-Korrektur-Stärke, ICC-Zielprofil/Rendering-Intent/
Schwarzpunktkompensation, maximale Sättigungsreduktion, Export-Optionen
(Alpha-Maske, Weißunterlegung, CMYK-Vorschau, Metadaten, Überschreibverhalten).
Jede Einstellung hat einen Tooltip.

### "Pixel löschen bis Alpha-Wert"

Löscht alle Pixel mit Alpha-Wert 0 bis einschließlich des eingestellten
Werts vollständig (0 = vollständig transparent, 255 = vollständig deckend).
Zusätzlich wird eine Prozentangabe angezeigt (z. B. "241 von 255 - Pixel bis
etwa 94,5 % Deckkraft werden gelöscht"). Standardwert: **241** (bewusst
aggressiv). Wählbarer Bereich: 0-254 - 255 ist nicht wählbar, da dadurch auch
vollständig deckende Pixel gelöscht würden.

Ab einem Wert von 220 erscheint der Hinweis: "Hoher Wert: Weiche Schatten,
Rauch, Glow und geglättete Kanten können entfernt werden." Im
**Automatikmodus** (Preset "DTF Auto" bzw. Alpha-Modus "Auto") schützt die
Anwendung erkannte große, weiche Flächen (Schatten/Rauch/Glow) automatisch
vor diesem Schwellenwert. Wird dagegen im Alpha-Modus **manuell** ein
konkreter Modus gewählt (z. B. "Nur Störpixel entfernen"), gilt der
Schwellenwert bewusst für das gesamte Bild - inklusive möglicher weicher
Flächen.

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
- **Bereits gespeicherte Einstellungen** (`%LOCALAPPDATA%\DTFKorrektur\settings.json`)
  behalten beim Programm-Update ihren bisherigen Wert - z. B. übernimmt eine
  bereits existierende Installation nicht automatisch den neuen
  Standardwert 241 für "Pixel löschen bis Alpha-Wert". Zum Zurücksetzen auf
  die aktuellen Standardwerte die Datei löschen (App dabei geschlossen
  lassen) oder den Wert manuell in den erweiterten Einstellungen anpassen.
