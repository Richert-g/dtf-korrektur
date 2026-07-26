"""Datenklassen für den Ergebnisbericht je Bild (siehe Prompt Abschnitt 18)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from src.models.enums import ImageType, RenderingIntent


@dataclass
class ProcessingStepLog:
    """Protokolleintrag für einen einzelnen Verarbeitungsschritt."""

    name: str
    description: str
    pixels_affected: int = 0
    details: dict = field(default_factory=dict)


@dataclass
class ImageProcessingReport:
    source_path: Path | None = None
    output_path: Path | None = None

    width: int = 0
    height: int = 0
    file_format: str = ""

    source_profile: str = ""
    target_profile: str = ""
    assumed_profiles: list[str] = field(default_factory=list)

    detected_type: ImageType = ImageType.UNKNOWN
    classification_reasons: list[str] = field(default_factory=list)

    transparent_pixel_count: int = 0
    semi_transparent_pixel_count: int = 0
    removed_pixel_count: int = 0
    strengthened_pixel_count: int = 0
    halo_corrected_pixel_count: int = 0
    removed_islands: int = 0
    closed_holes: int = 0

    out_of_gamut_before: float = 0.0
    out_of_gamut_after: float = 0.0
    mean_delta_e: float = 0.0
    max_delta_e: float = 0.0

    rendering_intent: RenderingIntent = RenderingIntent.RELATIVE_COLORIMETRIC
    black_point_compensation: bool = True
    applied_steps: list[ProcessingStepLog] = field(default_factory=list)

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    processing_duration_seconds: float = 0.0

    success: bool = True

    # --- Druckfertiger CMYK-PDF-Export (DTF-King), nur bei output_format="pdf_cmyk" gefüllt ---
    output_format: str = "png_rgb"
    additional_saturation_reduction_applied: bool = False
    additional_gamut_correction_applied: bool = False
    mirrored: bool = False
    pdf_page_count: int = 0
    pdf_page_size_mm: tuple[float, float] | None = None
    pdf_effective_dpi: tuple[float, float] | None = None
    pdf_meets_target_dpi: bool = True
    pdf_icc_output_intent_embedded: bool = False
    pdf_has_transparency_smask: bool = False
    pdf_validated: bool = False
    pdf_validation_errors: list[str] = field(default_factory=list)

    def add_step(self, name: str, description: str, pixels_affected: int = 0, **details) -> None:
        self.applied_steps.append(
            ProcessingStepLog(name=name, description=description, pixels_affected=pixels_affected, details=details)
        )

    def to_dict(self) -> dict:
        def conv(v):
            if isinstance(v, Path):
                return str(v)
            if hasattr(v, "value"):
                return v.value
            return v

        d = {}
        for k, v in self.__dict__.items():
            if k == "applied_steps":
                d[k] = [
                    {"name": s.name, "description": s.description, "pixels_affected": s.pixels_affected, "details": s.details}
                    for s in v
                ]
            elif isinstance(v, list):
                d[k] = [conv(item) for item in v]
            else:
                d[k] = conv(v)
        return d


@dataclass
class BatchSummary:
    """Zusammenfassender Abschlussbericht für Stapelverarbeitung."""

    total_files: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    total_duration_seconds: float = 0.0
    reports: list[ImageProcessingReport] = field(default_factory=list)
