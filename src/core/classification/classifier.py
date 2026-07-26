"""Automatische Bildtyp-Klassifizierung (Prompt Abschnitt 6).

Unterscheidet zwischen hartem Logo/Schriftzug, Illustration/KI-Grafik, Foto
und Motiv mit Schatten/Rauch/Glow. Jede Entscheidung wird mit nachvollziehbaren
Gründen protokolliert (siehe ImageAnalysisResult.classification_reasons).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from src.config.defaults import ClassificationThresholds
from src.core.analysis.alpha_analysis import AlphaAnalysis
from src.models.analysis import ClassificationReason
from src.models.enums import ImageType


@dataclass
class ClassificationResult:
    image_type: ImageType
    confidence: float
    reasons: list[ClassificationReason] = field(default_factory=list)


def _estimate_unique_colors(rgb: np.ndarray, visible_mask: np.ndarray, levels_per_channel: int = 16) -> int:
    if not visible_mask.any():
        return 0
    step = 256 // levels_per_channel
    quant = (rgb // step).astype(np.int32)
    pixels = quant[visible_mask]
    codes = pixels[:, 0] * levels_per_channel * levels_per_channel + pixels[:, 1] * levels_per_channel + pixels[:, 2]
    return int(np.unique(codes).size)


def _edge_complexity_ratio(alpha: np.ndarray, min_alpha: int = 16) -> float:
    """Verhältnis von Silhouetten-Umfang zu Umfang eines flächengleichen Kreises.

    Werte nahe 1.0 = einfache, glatte Silhouette. Deutlich größere Werte =
    komplexe, verschachtelte Außenkante (typisch für Illustrationen).
    """
    mask = (alpha >= min_alpha).astype(np.uint8) * 255
    area = int((mask > 0).sum())
    if area == 0:
        return 0.0
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        return 0.0
    perimeter = sum(cv2.arcLength(c, True) for c in contours)
    circle_perimeter = 2 * np.sqrt(np.pi * area)
    if circle_perimeter <= 0:
        return 0.0
    return float(perimeter / circle_perimeter)


def classify_image(
    rgba: np.ndarray, alpha_stats: AlphaAnalysis, thresholds: ClassificationThresholds
) -> ClassificationResult:
    h, w = rgba.shape[:2]
    total = h * w
    rgb = rgba[:, :, :3]
    alpha = rgba[:, :, 3]
    visible_mask = alpha > 16

    unique_colors = _estimate_unique_colors(rgb, visible_mask)
    edge_complexity = _edge_complexity_ratio(alpha)
    opaque_ratio = alpha_stats.fully_opaque_count / total if total else 0.0
    negligible_transparency = alpha_stats.semi_transparent_count / total < 0.0005 and (
        alpha_stats.fully_transparent_count / total
    ) < 0.02

    reasons = [
        ClassificationReason("geschätzte Farbanzahl", str(unique_colors)),
        ClassificationReason("Kantenkomplexität (1.0 = glatt)", f"{edge_complexity:.2f}"),
        ClassificationReason("Halbtransparenz überwiegend am Motivrand", str(alpha_stats.mostly_at_edges)),
        ClassificationReason("große zusammenhängende Halbtransparenz-Fläche", str(alpha_stats.regions.covers_large_area)),
        ClassificationReason("Anteil vollständig deckender Pixel", f"{opaque_ratio:.2%}"),
    ]

    if alpha_stats.semi_transparent_count > 0 and alpha_stats.regions.covers_large_area and not alpha_stats.mostly_at_edges:
        return ClassificationResult(
            image_type=ImageType.SOFT_SHADOW,
            confidence=0.8,
            reasons=reasons + [ClassificationReason("Entscheidung", "große weiche Halbtransparenz-Fläche abseits der Motivkante -> Schatten/Glow")],
        )

    if negligible_transparency and unique_colors > 8 * thresholds.max_unique_colors_hard_graphic:
        return ClassificationResult(
            image_type=ImageType.PHOTO,
            confidence=0.75,
            reasons=reasons + [ClassificationReason("Entscheidung", "kaum Transparenz und sehr hohe Farbvarianz -> Foto")],
        )

    is_hard_edge_signal = alpha_stats.mostly_at_edges or (negligible_transparency and opaque_ratio > 0.9)
    is_simple_colors = unique_colors <= thresholds.max_unique_colors_hard_graphic
    is_simple_edges = edge_complexity < thresholds.high_edge_complexity_ratio

    if is_hard_edge_signal and is_simple_colors and is_simple_edges:
        return ClassificationResult(
            image_type=ImageType.HARD_LOGO,
            confidence=0.75,
            reasons=reasons + [ClassificationReason("Entscheidung", "klare Kante, wenige Farben, keine große Schattenfläche -> Logo/Schrift")],
        )

    return ClassificationResult(
        image_type=ImageType.ILLUSTRATION,
        confidence=0.55,
        reasons=reasons + [ClassificationReason("Entscheidung", "viele Farben oder komplexe Außenkante -> Illustration/KI-Grafik")],
    )
