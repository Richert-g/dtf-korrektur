# Bedienungsanleitung

## Schnellstart

1. Ein oder mehrere Bilder in den gestrichelten Bereich ziehen (oder
   "Bild auswählen" / "Ordner auswählen" klicken). Unterstützt werden PNG,
   JPG/JPEG, TIFF, BMP, WebP zuverlässig sowie PSD/AVIF als Best-Effort.
2. Die Anwendung analysiert automatisch und zeigt eine verständliche
   Zusammenfassung ("Das Bild wurde als … erkannt. Automatisch geplante
   Verarbeitung: …").
3. Optional ein ICC-Zielprofil auswählen (für Softproof/Farbanpassung/CMYK-
   Vorschau; ohne Profil wird nur die Transparenz bereinigt).
4. Ausgabeordner prüfen/wählen (Standard: `output`-Unterordner neben dem Bild).
5. Auf **"Automatisch optimieren"** klicken.
6. Ergebnis über die Vorher-/Nachher-Ansicht prüfen, Ausgabeordner öffnen.

Mehrere Dateien werden als Stapel mit Fortschrittsanzeige verarbeitet (Anzahl
paralleler Verarbeitungen intern begrenzt, damit die Oberfläche nicht
einfriert) und lassen sich über **"Abbrechen"** jederzeit stoppen. Über der
Dateiliste lassen sich einzelne ausgewählte Dateien per **"Ausgewählte
entfernen"** (oder Entf-Taste) oder die gesamte Liste per **"Liste leeren"**
wieder aus der Auswahl nehmen, ohne die Originaldateien zu berühren.

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

Zusätzlich stehen drei bewusst klar getrennte Zustände zur Verfügung, damit
sich Transparenzkorrektur und Farbkonvertierung nicht vermischen:

- **"Original – Quellfarbraum"**: das unveränderte Ausgangsbild.
- **"Transparenzoptimiert – Farben unverändert"**: der Zustand direkt nach
  Alpha-/Halo-Korrektur, aber **vor** jeder Farbkonvertierung - zeigt exakt,
  was die Transparenzbereinigung allein bewirkt hat.
- **"DTF-King Softproof – ISO Coated v2"**: dieselbe Softproof-Simulation wie
  oben, hier mit eindeutigem Bezug zum gewählten Zielprofil beschriftet.

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

1. Preset "DTF-King – ISO Coated v2 (ECI)" auswählen.
2. Im Feld **"ICC-Zielprofil"** ein beliebiges CMYK-Profil wählen - z. B.
   eines der mitgelieferten (Standard bei leerem Feld: **Coated FOGRA39**)
   oder das offizielle **"ISO Coated v2 (ECI)"** (einmalig über
   "Importieren…" hinzufügen, z. B. von eci.org). Das Preset überschreibt
   ein bereits gewähltes Profil nicht - die Wahl bleibt bei dir.
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
6. Die Vorschau springt danach automatisch auf **"DTF-King Softproof – ISO
   Coated v2"**: eine Bildschirm-Rückwandlung der tatsächlich in die PDF
   geschriebenen CMYK-Farben, zeigt also, wie die Farben nach der echten
   ICC-Konvertierung aussehen. Über das Ansicht-Auswahlfeld ist außerdem
   weiterhin "Transparenzoptimiert – Farben unverändert" verfügbar (Zustand
   vor der Farbkonvertierung).

Die Bildpixel werden **nie ohne Hinweis künstlich hochskaliert** - reichen sie
für die gewünschte Größe bei 300 dpi nicht aus, erscheint eine Warnung wie
"Die Datei erreicht bei 28,0 cm Breite nur 238 dpi …". Hochskalierung muss im
Dialog ausdrücklich aktiviert werden.

## Erweiterte Einstellungen

Über den Button "Erweiterte Einstellungen" erreichbar, in vier Reitern:
Transparenz, Farbsaum, Farbe, Export. Jede Einstellung hat zusätzlich einen
Tooltip mit Kurzerklärung.

### Alpha-Modus

Bestimmt, wie die Transparenzbereinigung im Detail abläuft:

| Modus | Wirkung |
|---|---|
| **Auto** | wählt automatisch anhand des erkannten Bildtyps einen der drei folgenden Modi |
| **Nur Störpixel entfernen** | minimaler Eingriff: nur die beiden Alpha-Schwellenwerte (löschen/volldeckend machen) werden angewendet |
| **Sanfte Bereinigung** | zusätzlich zu den Schwellenwerten eine gezielte Kantenbehandlung im mittleren Alpha-Bereich (Rauschen am Rand entfernen, echte Halbtransparenz außerhalb des Rands verstärken) |
| **Harte Kante** | binarisiert die gesamte Kante auf 0 oder 255 (automatische Otsu-Schwelle), inklusive Entfernen kleiner Pixelinseln und Schließen kleiner Löcher |

Bei "Auto" wird "Nur Störpixel entfernen" für Fotos und Motive mit weichem
Schatten verwendet, "Sanfte Bereinigung" für Illustrationen und "Harte Kante"
für Logos/Schriftzüge.

### Farbsaum-/Halo-Korrektur

Entfernt weiße/graue/schwarze Farbsäume an halbtransparenten Außenkanten, wie
sie beim Freistellen auf hellem oder dunklem Hintergrund häufig entstehen.
Zieht dazu die Farbe deckender Nachbarpixel iterativ an den Rand heran, bevor
die Alpha-Bereinigung läuft. **Stärke** (0-1) regelt, wie stark die
Randfarbe angeglichen wird; **Suchradius** legt fest, wie weit nach
deckenden Nachbarn gesucht wird. Lässt sich in diesem Reiter komplett
deaktivieren.

### Max. Sättigungsreduktion

Begrenzt, wie stark die automatische Farboptimierung die Sättigung von
Farben reduzieren darf, die außerhalb des gewählten Zielfarbraums liegen
(0 = keine Reduktion, die Farbe bleibt beim reinen ICC-Ergebnis; höhere
Werte erlauben eine stärkere, proportional zur Abweichung skalierte
Entsättigung). Wirkt nur zusätzlich zur eigentlichen ICC-Konvertierung und
nur auf tatsächlich außerhalb des Zielfarbraums liegende Pixel - Hauttöne,
neutrale Grauwerte und sehr dunkle Töne werden dabei ausgenommen. Bei 0
findet keine zusätzliche Korrektur mehr statt (Standardverhalten des
DTF-King-Presets).

### Rendering Intent & Schwarzpunktkompensation (Farbe-Reiter)

**Rendering Intent** legt fest, nach welcher Methode Farben in den
Zielfarbraum überführt werden: "relativ farbmetrisch" verändert bereits
druckbare Farben gar nicht und passt nur die tatsächlichen Ausreißer an
(originaltreu, gut für Logos/Markenfarben); "perzeptiv" staucht den gesamten
Farbraum gleichmäßig (natürlichere Übergänge bei Fotos/Verläufen, aber auch
bereits druckbare Farben werden dabei leicht verändert). Per "Rendering
Intent automatisch wählen" entscheidet die App das anhand des erkannten
Bildtyps und Out-of-Gamut-Anteils selbst; bei deaktivierter Automatik gilt
die manuelle Auswahl. **Schwarzpunktkompensation** verbessert die Zeichnung
in dunklen Bildbereichen bei der Umrechnung, ohne die übrigen Farben zu
verschieben - i. d. R. aktiviert lassen.

### "Pixel mit geringer Deckkraft entfernen" und "... vollständig deckend setzen"

Beide Funktionen lassen sich über eine eigene Checkbox **unabhängig
voneinander** ein- und ausschalten. Ist eine Checkbox deaktiviert, wird das
zugehörige Schwellenwert-Feld ausgegraut, der gespeicherte Wert bleibt aber
erhalten und erscheint beim erneuten Aktivieren unverändert wieder - der
Verarbeitungsschritt selbst wird bei Deaktivierung vollständig übersprungen
(auch in Berichten taucht dann kein entsprechender Schritt mehr auf).

**"Pixel mit geringer Deckkraft entfernen"** löscht alle Pixel mit Alpha-Wert
0 bis einschließlich des eingestellten Schwellenwerts vollständig (0 =
vollständig transparent, 255 = vollständig deckend). Zusätzlich wird eine
Prozentangabe angezeigt (z. B. "241 von 255 - Pixel bis etwa 94,5 %
Deckkraft werden gelöscht"). Standardwert: **241** (bewusst aggressiv),
standardmäßig **aktiviert**. Wählbarer Bereich: 0-254 - 255 ist nicht
wählbar, da dadurch auch vollständig deckende Pixel gelöscht würden.

Ab einem Wert von 220 erscheint der Hinweis: "Hoher Wert: Weiche Schatten,
Rauch, Glow und geglättete Kanten können entfernt werden." Im
**Automatikmodus** (Preset "DTF Auto" bzw. Alpha-Modus "Auto") schützt die
Anwendung erkannte große, weiche Flächen (Schatten/Rauch/Glow) automatisch
vor diesem Schwellenwert. Wird dagegen im Alpha-Modus **manuell** ein
konkreter Modus gewählt (z. B. "Nur Störpixel entfernen"), gilt der
Schwellenwert bewusst für das gesamte Bild - inklusive möglicher weicher
Flächen.

**"Pixel mit hoher Deckkraft vollständig deckend setzen"** ist das
Gegenstück: Setzt alle Pixel mit einem Alpha-Wert ab einschließlich des
eingestellten Schwellenwerts auf volle Deckkraft (255). Ebenfalls mit
Prozentangabe (z. B. "242 von 255 - Pixel ab etwa 94,9 % Deckkraft werden
voll deckend gemacht"). Standardwert: **242**, standardmäßig **aktiviert**.
Wählbarer Bereich: 0-255.

Beide gelten für die Alpha-Modi "Nur Störpixel entfernen" und "Sanfte
Bereinigung" (nicht für "Harte Kante", die eine eigene, automatische
Schwelle verwendet). Im **Automatikmodus** greift für beide dieselbe
Schutzmaske: erkannte große, weiche Flächen (Schatten/Rauch/Glow) werden
weder gelöscht noch pauschal hart gemacht. Im **manuell** gewählten Modus
gilt der jeweils aktivierte Schwellenwert für das gesamte Bild.

## Eigene ICC-Profile hinzufügen

1. "Importieren…" neben der Profil-Auswahl klicken.
2. `.icc`- oder `.icm`-Datei wählen.
3. Das Profil wird geprüft (defekte Profile werden abgelehnt) und lokal nach
   `%LOCALAPPDATA%\DTFKorrektur\profiles` kopiert.
4. Es erscheint danach in der Profil-Auswahlliste.

Im Export-Reiter der erweiterten Einstellungen lässt sich zusätzlich eine
**CMYK-TIFF-Vorschau** aktivieren (erfordert ein gültiges ICC-Zielprofil):
eine auf Weiß geflachte CMYK-Datei zur Kontrolle der Farbumrechnung - eine
reine Vorschau-/Hilfsdatei, kein Ersatz für den PDF-Export.

## Berichte

Zu jedem verarbeiteten Bild werden im Ausgabeordner unter `reports/` zwei
Berichte abgelegt:

- **`<name>_report.json`**: technischer Bericht (alle gemessenen Werte,
  angewendeten Verarbeitungsschritte, Warnungen) - zur Weiterverarbeitung
  oder Fehlersuche.
- **`<name>_report.html`**: verständlich aufbereitete Version zum direkten
  Anschauen im Browser (was wurde geändert, Transparenz-/Farbwerte,
  Hinweise).

Bei einer Stapelverarbeitung entsteht zusätzlich ein zusammenfassender
`batch_summary.json` mit Anzahl erfolgreicher/fehlgeschlagener Dateien und
Gesamtdauer.

## Einstellungen

Alle Einstellungen (Presets, ICC-Profil, Alpha-/Halo-/Farb-Parameter,
Ausgabeformat, Druckgröße usw.) werden automatisch lokal gespeichert
(`%LOCALAPPDATA%\DTFKorrektur\settings.json`) und beim nächsten Programmstart
wieder geladen - keine manuelle Aktion nötig. Ist das zuletzt verwendete
ICC-Zielprofil nicht mehr auffindbar oder beschädigt, erscheint beim Start
ein Hinweisfenster und die Einstellung wird automatisch zurückgesetzt, statt
unbemerkt mit einem ungültigen Profil weiterzuarbeiten.

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
