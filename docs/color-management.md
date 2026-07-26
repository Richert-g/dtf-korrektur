# Farbmanagement

## Bibliotheken

ICC-Farbmanagement läuft ausschließlich über `Pillow.ImageCms`, das intern
LittleCMS nutzt. Es werden keine externen Kommandozeilenprogramme aufgerufen.

## Quellprofil

1. Eingebettetes ICC-Profil aus der Bilddatei, falls vorhanden und gültig
   (`core/color/icc_manager.py::load_icc_profile_from_bytes`).
2. Fällt das Profil defekt oder inkompatibel aus: Warnung + Rückfall auf sRGB.
3. Kein eingebettetes Profil: sRGB wird angenommen, im Bericht klar als
   "sRGB (angenommen)" gekennzeichnet.

## Zielprofil

Der Benutzer wählt ein ICC-Zielprofil über die Oberfläche oder importiert eines
(`import_profile`, kopiert lokal nach `%LOCALAPPDATA%\DTFKorrektur\profiles`).
**Ohne Zielprofil** wird keine Farbraum-Anpassung vorgenommen und **kein**
CMYK-Export erzeugt (siehe Sicherheitsregeln in `processing-pipeline.md`).

## Gamut-Analyse und Softproof

Da Pillow/LittleCMS keinen direkten "Prozentsatz außerhalb des Gamuts" liefert,
wird eine **Rundreise-Transformation** verwendet:

```
sRGB (oder Quellprofil) -> Zielprofil -> zurück nach sRGB
```

Die Differenz zwischen Original- und Rundreise-Farbe wird in **CIE Lab**
(D65, manuell in NumPy implementiert, `core/color/delta_e.py`) über die
euklidische Distanz (**Delta E, CIE76**) gemessen. Pixel mit
`ΔE > delta_e_out_of_gamut` (Standard 2.3) gelten als außerhalb des
druckbaren Farbraums.

Dieselbe Rundreise liefert gleichzeitig die **Softproof-Vorschau**
(`ImageCms.buildProofTransform` mit `Flags.SOFTPROOFING`): das Bild wird so
dargestellt, wie es nach der Umwandlung ins Zielprofil aussehen würde.

## Automatische Rendering-Intent-Wahl (`core/color/rendering_intent.py`)

| Bedingung | Intent |
|---|---|
| Out-of-Gamut-Anteil ≥ Schwelle (Standard 8 %) | Perzeptiv |
| Foto / Illustration / weicher Schatten | Perzeptiv |
| Logo / flächige Grafik | Relativ farbmetrisch |

Kann in den erweiterten Einstellungen deaktiviert und manuell überschrieben werden.

## Automatische Farboptimierung (`core/color/saturation_optimizer.py`)

**Keine pauschale globale Sättigungsreduktion.** Nur Pixel, die nach der
Rundreise-Messung tatsächlich außerhalb des Zielfarbraums liegen, werden in
ihrer Sättigung (HSV, über OpenCV) reduziert - proportional zur gemessenen
Abweichung, begrenzt durch `max_auto_saturation_reduction` (Standard 35 %).

Geschützt (nicht verändert):
- Neutrale Grauwerte (`is_neutral_gray`, Lab-Chroma-Schwelle)
- Hauttöne (`is_skin_tone`, grobe Lab-Heuristik)
- Sehr dunkle Pixel (V < 15 in HSV) - Schwarztöne werden nicht unnötig verändert

Der Vorgang läuft iterativ (max. `max_optimization_iterations`, Standard 4)
und bricht ab, wenn die Verbesserung der mittleren Delta-E unter
`min_improvement_delta_e` fällt.

## Mitgelieferte Profile und bekannte Einschränkung

Die Anwendung bringt eine Reihe frei verwendbarer Standard-ICC-Profile mit
(`resources/profiles/RGB`, `resources/profiles/CMYK`: u. a. FOGRA27/28/29/39,
GRACoL 2006, SWOP, Japan Color, Adobe RGB, Apple RGB) - sie erscheinen ohne
manuellen Import in der Profil-Auswahl und eignen sich gut, um Softproof,
Gamut-Analyse und CMYK-Export grundsätzlich auszuprobieren.

Es handelt sich dabei aber um **allgemeine Offset-/Digitaldruck-Profile**,
**kein DTF-spezifisches Profil**. Ein echtes DTF-Profil hängt vom konkreten
Drucker, der Tinte, der Folie/dem Pulver und dem RIP ab und ist in der Regel
herstellerspezifisch. Für ein realistisches Ergebnis sollte der Benutzer,
sobald verfügbar, das passende DTF-ICC-Profil seines Systems importieren
(siehe `user-guide.md`, Abschnitt "Eigene ICC-Profile hinzufügen"). Ein
gewöhnliches generisches CMYK-Profil ist nicht automatisch ein korrektes
DTF-Profil.
