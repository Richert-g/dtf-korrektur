"""Datenklassen für die automatische Bildanalyse."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from src.models.enums import ImageType, RenderingIntent, WarningSeverity


@dataclass
class AlphaHistogramBucket:
    """Ein Bucket der Alpha-Wert-Verteilung (0-255)."""

    range_start: int
    range_end: int
    pixel_count: int


@dataclass
class SemiTransparentRegionStats:
    """Statistik über zusammenhängende halbtransparente Bereiche."""

    region_count: int = 0
    largest_region_pixels: int = 0
    average_region_pixels: float = 0.0
    mostly_at_outer_edge: bool = False
    covers_large_area: bool = False


@dataclass
class AnalysisWarning:
    code: str
    message: str
    severity: WarningSeverity = WarningSeverity.WARNING


@dataclass
class ClassificationReason:
    """Nachvollziehbare Begründung der automatischen Klassifizierung."""

    signal: str
    value: str
    weight: float = 1.0


@dataclass
class ImageAnalysisResult:
    """Zentrale Datenklasse mit dem vollständigen Analyseergebnis eines Bildes.

    Siehe Prompt Abschnitt 5 für die geforderten Felder.
    """

    # Grunddaten
    input_path: Path = None
    width: int = 0
    height: int = 0
    file_format: str = ""
    file_size_bytes: int = 0

    # Farbraum / ICC
    source_profile: str = "sRGB (angenommen)"
    source_profile_embedded: bool = False
    source_profile_description: str = ""
    color_mode: str = "RGB"

    # Alphakanal
    alpha_present: bool = False
    fully_transparent_count: int = 0
    semi_transparent_count: int = 0
    weak_alpha_count: int = 0
    fully_opaque_count: int = 0
    semi_transparent_ratio: float = 0.0
    alpha_histogram: list[AlphaHistogramBucket] = field(default_factory=list)
    semi_transparent_regions: SemiTransparentRegionStats = field(
        default_factory=SemiTransparentRegionStats
    )
    semi_transparent_mostly_at_edges: bool = False
    likely_soft_shadow: bool = False
    likely_hard_graphic: bool = False
    edge_halo_detected: bool = False
    small_pixel_island_count: int = 0
    small_hole_count: int = 0

    # Farbraum-Analyse
    out_of_gamut_percentage: float = 0.0
    out_of_gamut_percentage_after: float | None = None
    mean_delta_e: float = 0.0
    max_delta_e: float = 0.0

    # Klassifizierung
    detected_type: ImageType = ImageType.UNKNOWN
    classification_confidence: float = 0.0
    classification_reasons: list[ClassificationReason] = field(default_factory=list)

    # Empfehlungen
    recommended_processing_mode: str = ""
    recommended_rendering_intent: RenderingIntent = RenderingIntent.RELATIVE_COLORIMETRIC
    recommended_choke_px: float = 0.0

    # Ergebnis / Protokoll
    warnings: list[AnalysisWarning] = field(default_factory=list)
    selected_actions: list[str] = field(default_factory=list)

    def add_warning(self, code: str, message: str, severity: WarningSeverity = WarningSeverity.WARNING) -> None:
        self.warnings.append(AnalysisWarning(code=code, message=message, severity=severity))

    @property
    def total_pixels(self) -> int:
        return self.width * self.height
