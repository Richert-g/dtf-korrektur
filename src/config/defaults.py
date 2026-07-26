"""Zentrale Konfiguration aller Schwellenwerte und Standardeinstellungen.

Alle Schwellenwerte MÜSSEN hier gesammelt werden statt verstreut im Code
(siehe Prompt Abschnitt 7 letzter Satz und Abschnitt 13).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.models.enums import AlphaMode, OutputFormat, RenderingIntent


@dataclass
class AlphaThresholds:
    """Schwellenwerte für die Alpha-Bereinigung (Prompt Abschnitt 7)."""

    # "Pixel löschen bis Alpha-Wert": alle Pixel mit 0 <= Alpha <= Schwellenwert
    # werden vollständig transparent (inklusive Grenze: alpha <= threshold).
    # Standard 241 ist bewusst aggressiv (siehe UI-Warnung ab 220) - im
    # Automatikmodus werden große, nicht am Motivrand liegende weiche Flächen
    # (z. B. Schatten/Glow) davon ausgenommen, siehe
    # core.analysis.alpha_analysis.compute_large_soft_region_mask().
    # Zulässiger Bereich in der Oberfläche: 0-254 (255 wäre "alles löschen").
    weak_alpha_threshold: int = 241
    # Ab diesem Wert zeigt die Oberfläche eine Warnung vor aggressivem Löschen an
    weak_alpha_threshold_warning_from: int = 220
    # Untere Grenze für den mittleren Bereich (5-20 %)
    mid_low_threshold: int = 13
    mid_high_threshold: int = 51  # ~20 % von 255
    # Ab hier gilt ein Pixel als "fast deckend" und wird auf 255 gesetzt
    near_opaque_threshold: int = 242  # ~95 %
    # Harte Kante: automatisch ermittelter Schwellenwert (Fallback-Default)
    hard_edge_default_threshold: int = 128
    # Kleine Pixelinseln (Fläche in Pixel) unterhalb dieser Größe werden entfernt
    min_island_size_px: int = 6
    # Löcher bis zu dieser Größe werden geschlossen
    max_hole_fill_size_px: int = 24
    # Kantenrücknahme in Pixeln (0 = aus)
    edge_choke_px: float = 0.0
    # Kantenglättung (Gaussian-Radius in Pixeln)
    edge_feather_radius: float = 0.6
    # Abstand (in Pixeln) zu deckenden Pixeln, innerhalb dessen Halbtransparenz
    # als "am Motivrand" gilt (statt als eigenständige Fläche/Schatten)
    edge_adjacency_band_px: int = 6
    # Anteil, ab dem Halbtransparenz als "überwiegend am Rand" gilt
    edge_adjacency_ratio_threshold: float = 0.6
    # Verstärkungsfaktor für "Sanfte Bereinigung" im mittleren Alpha-Band (5-20 %),
    # wenn die Pixel NICHT am Motivrand liegen (Prompt Abschnitt 7)
    soft_cleanup_strengthen_factor: float = 1.6
    # Anteil an der Gesamtfläche, ab dem eine zusammenhängende Halbtransparenz-
    # Region als "groß" gilt (z. B. bewusster Schatten/Glow statt Kantenrauschen).
    # Wird sowohl für die Analyse-Statistik als auch für den Automatik-Schutz
    # vor dem "Pixel löschen bis Alpha-Wert"-Schwellenwert verwendet.
    large_region_area_fraction: float = 0.01


@dataclass
class HaloThresholds:
    """Schwellenwerte für Farbsaum-/Halo-Korrektur (Prompt Abschnitt 8)."""

    enabled: bool = True
    # Alpha-Bereich, der als "Randpixel" für die Halo-Korrektur gilt
    edge_alpha_low: int = 5
    edge_alpha_high: int = 250
    # Radius in Pixeln, in dem nach deckenden Nachbarn gesucht wird
    search_radius_px: int = 4
    # Wie stark die Randfarbe an die Nachbarfarbe angeglichen wird (0-1)
    strength: float = 1.0
    # Mindest-Deckkraft eines Nachbarn, damit er als "innerer" Pixel zählt
    inner_neighbor_min_alpha: int = 235


@dataclass
class GamutThresholds:
    """Schwellenwerte für Out-of-Gamut-Erkennung und Farboptimierung (Prompt Abschnitt 10)."""

    # Ab diesem Delta-E-Wert gilt eine Farbe als "out of gamut" / stark abweichend
    delta_e_out_of_gamut: float = 2.3
    # Ab diesem Out-of-Gamut-Flächenanteil wird perzeptiv statt farbmetrisch bevorzugt
    perceptual_preference_threshold_pct: float = 8.0
    # Maximale automatische Sättigungsreduktion (0-1, 0.3 = max. 30 %)
    max_auto_saturation_reduction: float = 0.35
    # Iterationsgrenze für die iterative Farboptimierung
    max_optimization_iterations: int = 4
    # Abbruch, wenn die Verbesserung zwischen zwei Iterationen kleiner ist
    min_improvement_delta_e: float = 0.15
    # Schaltet die gesamte zusätzliche, eigene Gamut-/Sättigungskorrektur nach
    # der ICC-Konvertierung aus (z. B. für das DTF-King-Preset). Ist False,
    # bleibt es bei genau einer einzigen echten ICC-Transformation ohne
    # jede weitere pauschale Farbanpassung.
    enable_auto_gamut_correction: bool = True
    # Hauttonbereich (Lab a*/b* grobe Schätzung) und Grauwerte werden geschont
    protect_skin_tones: bool = True
    protect_neutral_grays: bool = True
    neutral_gray_chroma_max: float = 4.0


@dataclass
class ClassificationThresholds:
    """Schwellenwerte für die automatische Bildtyp-Klassifizierung (Prompt Abschnitt 6)."""

    # Anteil Halbtransparenz an Gesamtfläche, ab dem "große Schattenfläche" angenommen wird
    large_soft_area_ratio: float = 0.04
    # Anteil der Halbtransparenz, der an Außenkanten liegen muss, um als "hart" zu gelten
    edge_only_ratio_threshold: float = 0.85
    # Farbanzahl-Schwelle (angenähert über Histogramm-Buckets) Logo vs. Illustration
    max_unique_colors_hard_graphic: int = 64
    # Kantenkomplexität (Konturlänge / Umfang der Bounding Box)
    high_edge_complexity_ratio: float = 3.0


@dataclass
class ExportSettings:
    output_format: OutputFormat = OutputFormat.PNG_RGB
    write_cmyk_tiff: bool = False
    write_softproof_preview: bool = True
    write_alpha_mask: bool = False
    write_white_mask: bool = False
    white_mask_choke_px: float = 0.0  # 0 = automatisch empfohlenen Wert verwenden
    write_diff_overlays: bool = True  # Vorschau: entfernte/verstärkte Pixel farbig hervorgehoben
    write_gamut_warning: bool = True  # Vorschau: außerhalb des Zielfarbraums liegende Pixel farbig hervorgehoben
    # Vorschau: Zustand direkt nach Alpha-/Halo-Korrektur, VOR jeder Farbkonvertierung
    # (siehe "Transparenzoptimiert - Farben unverändert" in der Ansicht-Auswahl)
    write_transparency_only_preview: bool = True
    write_json_report: bool = True
    write_html_report: bool = True
    keep_metadata: bool = False
    filename_suffix_optimized: str = "_dtf_optimized"
    filename_suffix_softproof: str = "_softproof"
    filename_suffix_alpha_mask: str = "_alpha_mask"
    filename_suffix_white_mask: str = "_white_mask"
    filename_suffix_removed_pixels: str = "_removed_pixels"
    filename_suffix_strengthened_pixels: str = "_strengthened_pixels"
    filename_suffix_gamut_warning: str = "_gamut_warning"
    filename_suffix_report_json: str = "_report.json"
    filename_suffix_report_html: str = "_report.html"
    filename_suffix_pdf: str = "_dtf_king_iso_coated_v2"
    overwrite_existing: bool = False

    # --- Druckfertiger CMYK-PDF-Export (DTF-King) ---
    # Gewünschte Ausgabebreite/-höhe in mm. Ist nur eine der beiden Angaben
    # gesetzt, wird die andere proportional zu den Bildpixeln berechnet. Sind
    # beide None, wird die native Größe bei pdf_target_dpi verwendet.
    pdf_width_mm: float | None = None
    pdf_height_mm: float | None = None
    pdf_target_dpi: float = 300.0
    # Ohne explizite Aktivierung wird nie künstlich hochskaliert, wenn die
    # effektive dpi unter pdf_target_dpi liegt - nur eine Warnung angezeigt.
    pdf_allow_upscale: bool = False


@dataclass
class ColorManagementSettings:
    target_profile_path: str | None = None  # None => sRGB-Fallback
    rendering_intent: RenderingIntent = RenderingIntent.RELATIVE_COLORIMETRIC
    auto_select_intent: bool = True
    black_point_compensation: bool = True
    show_gamut_warning: bool = True


@dataclass
class ProcessingSettings:
    alpha_mode: AlphaMode = AlphaMode.AUTO
    alpha: AlphaThresholds = field(default_factory=AlphaThresholds)
    halo: HaloThresholds = field(default_factory=HaloThresholds)
    gamut: GamutThresholds = field(default_factory=GamutThresholds)
    classification: ClassificationThresholds = field(default_factory=ClassificationThresholds)
    color: ColorManagementSettings = field(default_factory=ColorManagementSettings)
    export: ExportSettings = field(default_factory=ExportSettings)


DEFAULT_SETTINGS = ProcessingSettings()

# Performance-/Systemgrenzen
MAX_PREVIEW_DIMENSION_PX = 1600
CHUNK_SIZE_ROWS = 512  # für chunkweise NumPy-Verarbeitung sehr großer Bilder
LARGE_IMAGE_PIXEL_THRESHOLD = 40_000_000  # ab hier wird gechunkt
DEFAULT_MAX_PARALLEL_WORKERS = 2

SUPPORTED_IMPORT_FORMATS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".psd", ".avif"}
CORE_IMPORT_FORMATS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
