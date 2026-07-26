"""Orchestriert die vollständige automatische Bildanalyse (Prompt Abschnitt 5 & 6)."""
from __future__ import annotations

import logging
import time
from pathlib import Path

from src.config.defaults import ProcessingSettings
from src.core.analysis.alpha_analysis import analyze_alpha_channel
from src.core.analysis.image_loader import ImageLoadError, LoadedImage, load_image
from src.models.analysis import ImageAnalysisResult
from src.models.enums import WarningSeverity

logger = logging.getLogger(__name__)


def analyze_image(path: Path, settings: ProcessingSettings) -> tuple[ImageAnalysisResult, LoadedImage]:
    """Führt die vollständige Analyse eines Bildes durch.

    Gibt das Analyseergebnis und das geladene Bild zurück (letzteres wird von der
    weiteren Verarbeitung wiederverwendet, damit das Bild nicht zweimal gelesen wird).
    """
    start = time.perf_counter()
    loaded = load_image(path)
    array = loaded.array

    result = ImageAnalysisResult(
        input_path=path,
        width=array.shape[1],
        height=array.shape[0],
        file_format=loaded.file_format,
        file_size_bytes=path.stat().st_size,
        color_mode=loaded.original_mode,
    )

    if loaded.icc_profile_description:
        result.source_profile = loaded.icc_profile_description
        result.source_profile_embedded = True
        result.source_profile_description = loaded.icc_profile_description
    else:
        result.source_profile = "sRGB (angenommen, kein eingebettetes Profil gefunden)"
        result.source_profile_embedded = False
        result.add_warning(
            "no_icc_profile",
            "Diese Datei enthält kein eingebettetes Farbprofil. Es wird sRGB angenommen.",
            WarningSeverity.INFO,
        )

    alpha_stats = analyze_alpha_channel(array, settings.alpha)
    result.alpha_present = alpha_stats.alpha_present
    result.fully_transparent_count = alpha_stats.fully_transparent_count
    result.semi_transparent_count = alpha_stats.semi_transparent_count
    result.weak_alpha_count = alpha_stats.weak_alpha_count
    result.fully_opaque_count = alpha_stats.fully_opaque_count
    result.semi_transparent_ratio = alpha_stats.semi_transparent_ratio
    result.alpha_histogram = alpha_stats.histogram
    result.semi_transparent_regions = alpha_stats.regions
    result.semi_transparent_mostly_at_edges = alpha_stats.mostly_at_edges
    result.likely_soft_shadow = alpha_stats.likely_soft_shadow
    result.likely_hard_graphic = alpha_stats.likely_hard_graphic
    result.small_pixel_island_count = alpha_stats.small_island_count
    result.small_hole_count = alpha_stats.small_hole_count

    from src.core.classification.classifier import classify_image

    classification = classify_image(array, alpha_stats, settings.classification)
    result.detected_type = classification.image_type
    result.classification_confidence = classification.confidence
    result.classification_reasons = classification.reasons

    if not loaded.had_alpha:
        result.add_warning(
            "no_alpha_channel",
            "Das Bild enthält keinen Alphakanal (keine Transparenz).",
            WarningSeverity.INFO,
        )

    logger.info("Analyse von %s abgeschlossen in %.3fs", path.name, time.perf_counter() - start)
    return result, loaded


def analyze_image_safe(path: Path, settings: ProcessingSettings) -> tuple[ImageAnalysisResult | None, LoadedImage | None, str | None]:
    """Fehlertolerante Variante für die Stapelverarbeitung (Prompt Abschnitt 21)."""
    try:
        result, loaded = analyze_image(path, settings)
        return result, loaded, None
    except ImageLoadError as exc:
        logger.warning("Analyse fehlgeschlagen für %s: %s", path, exc)
        return None, None, str(exc)
    except Exception as exc:  # noqa: BLE001 - bewusst breit, Einzeldatei darf App nicht crashen
        logger.exception("Unerwarteter Fehler bei der Analyse von %s", path)
        return None, None, f"Unerwarteter Fehler: {exc}"
