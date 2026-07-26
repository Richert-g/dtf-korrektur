"""Automatische Analyse des Alphakanals (Prompt Abschnitt 5)."""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from src.config.defaults import AlphaThresholds
from src.models.analysis import AlphaHistogramBucket, SemiTransparentRegionStats


@dataclass
class AlphaAnalysis:
    alpha_present: bool
    fully_transparent_count: int
    semi_transparent_count: int
    weak_alpha_count: int
    fully_opaque_count: int
    semi_transparent_ratio: float
    histogram: list[AlphaHistogramBucket]
    regions: SemiTransparentRegionStats
    mostly_at_edges: bool
    small_island_count: int
    small_hole_count: int
    likely_soft_shadow: bool
    likely_hard_graphic: bool


def _histogram(alpha: np.ndarray, bucket_size: int = 32) -> list[AlphaHistogramBucket]:
    buckets = []
    for start in range(0, 256, bucket_size):
        end = min(start + bucket_size - 1, 255)
        mask = (alpha >= start) & (alpha <= end)
        buckets.append(AlphaHistogramBucket(range_start=start, range_end=end, pixel_count=int(mask.sum())))
    return buckets


def motif_edge_band_mask(alpha: np.ndarray, thresholds: AlphaThresholds) -> np.ndarray:
    """Schmales Band um deckende (>= near_opaque_threshold) Pixel herum.

    Halbtransparenz innerhalb dieses Bandes gilt als 'am Außenrand des Motivs'
    (typisch für Kanten-Antialiasing/Halos). Halbtransparenz weit außerhalb
    davon gilt als eigenständige Fläche (z. B. Schatten, Glow).
    """
    opaque_core = (alpha >= thresholds.near_opaque_threshold).astype(np.uint8)
    band_px = max(1, thresholds.edge_adjacency_band_px)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (band_px * 2 + 1, band_px * 2 + 1))
    dilated = cv2.dilate(opaque_core, kernel, iterations=1)
    return dilated.astype(bool) & ~opaque_core.astype(bool)


def _semi_transparent_region_stats(
    semi_mask: np.ndarray, alpha: np.ndarray, thresholds: AlphaThresholds
) -> tuple[SemiTransparentRegionStats, bool]:
    mask_u8 = (semi_mask.astype(np.uint8)) * 255
    num_labels, _labels, stats, _ = cv2.connectedComponentsWithStats(mask_u8, connectivity=8)
    # Label 0 ist Hintergrund
    areas = stats[1:, cv2.CC_STAT_AREA] if num_labels > 1 else np.array([], dtype=np.int32)

    h, w = semi_mask.shape
    edge_band = motif_edge_band_mask(alpha, thresholds)

    total_semi = int(semi_mask.sum())
    at_edge = int((semi_mask & edge_band).sum())
    mostly_at_edge = (
        (at_edge / total_semi) > thresholds.edge_adjacency_ratio_threshold if total_semi > 0 else False
    )

    covers_large_area = False
    largest = int(areas.max()) if areas.size else 0
    total_pixels = h * w
    if total_pixels > 0 and largest / total_pixels > thresholds.large_region_area_fraction:
        covers_large_area = True

    region_stats = SemiTransparentRegionStats(
        region_count=int(areas.size),
        largest_region_pixels=largest,
        average_region_pixels=float(areas.mean()) if areas.size else 0.0,
        mostly_at_outer_edge=mostly_at_edge,
        covers_large_area=covers_large_area,
    )
    return region_stats, mostly_at_edge


def compute_large_soft_region_mask(alpha: np.ndarray, thresholds: AlphaThresholds) -> np.ndarray:
    """Pixel, die zu einer großen, nicht überwiegend am Motivrand liegenden
    halbtransparenten Fläche gehören (typisch für bewusste weiche Schatten,
    Rauch oder Glow - Prompt Abschnitt 6 Typ D).

    Wird im Automatikmodus verwendet, um diese Bereiche vor einem pauschalen
    "Pixel löschen bis Alpha-Wert"-Schwellenwert zu schützen (siehe
    core.alpha.alpha_cleanup.clean_alpha). Nutzt dieselbe Größen- und
    Randabstands-Logik wie _semi_transparent_region_stats/covers_large_area,
    liefert aber eine Pro-Pixel-Maske statt einer Aggregat-Statistik.
    """
    semi_mask = (alpha > 0) & (alpha < 255)
    if not semi_mask.any():
        return np.zeros_like(alpha, dtype=bool)

    mask_u8 = semi_mask.astype(np.uint8) * 255
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask_u8, connectivity=8)
    if num_labels <= 1:
        return np.zeros_like(alpha, dtype=bool)

    edge_band = motif_edge_band_mask(alpha, thresholds)
    total_pixels = alpha.size
    protect = np.zeros_like(alpha, dtype=bool)

    for label_id in range(1, num_labels):
        area = int(stats[label_id, cv2.CC_STAT_AREA])
        if total_pixels == 0 or area / total_pixels <= thresholds.large_region_area_fraction:
            continue  # zu klein, um als bewusster Schatten/Glow zu gelten
        region_mask = labels == label_id
        at_edge_ratio = (region_mask & edge_band).sum() / area
        if at_edge_ratio <= thresholds.edge_adjacency_ratio_threshold:
            protect[region_mask] = True

    return protect


def _count_small_islands(alpha: np.ndarray, min_island_size_px: int) -> int:
    visible_mask = (alpha > 0).astype(np.uint8) * 255
    num_labels, _, stats, _ = cv2.connectedComponentsWithStats(visible_mask, connectivity=8)
    if num_labels <= 1:
        return 0
    areas = stats[1:, cv2.CC_STAT_AREA]
    return int((areas < min_island_size_px).sum())


def _count_small_holes(alpha: np.ndarray, max_hole_fill_size_px: int) -> int:
    transparent_mask = (alpha == 0).astype(np.uint8) * 255
    num_labels, _labels, stats, _ = cv2.connectedComponentsWithStats(transparent_mask, connectivity=8)
    if num_labels <= 1:
        return 0
    h, w = alpha.shape
    count = 0
    for i in range(1, num_labels):
        x, y, bw, bh, area = stats[i]
        touches_border = x == 0 or y == 0 or (x + bw) >= w or (y + bh) >= h
        if not touches_border and area <= max_hole_fill_size_px:
            count += 1
    return count


def analyze_alpha_channel(rgba: np.ndarray, thresholds: AlphaThresholds) -> AlphaAnalysis:
    """Analysiert den Alphakanal eines RGBA-NumPy-Arrays (HxWx4, uint8)."""
    alpha = rgba[:, :, 3]
    total = alpha.size

    fully_transparent = int((alpha == 0).sum())
    fully_opaque = int((alpha == 255).sum())
    semi_mask = (alpha > 0) & (alpha < 255)
    semi_count = int(semi_mask.sum())
    weak_count = int(((alpha > 0) & (alpha <= thresholds.weak_alpha_threshold)).sum())

    visible_total = total - fully_transparent
    semi_ratio = (semi_count / visible_total) if visible_total > 0 else 0.0

    histogram = _histogram(alpha)
    regions, mostly_at_edges = _semi_transparent_region_stats(semi_mask, alpha, thresholds)

    small_islands = _count_small_islands(alpha, thresholds.min_island_size_px)
    small_holes = _count_small_holes(alpha, thresholds.max_hole_fill_size_px)

    likely_soft_shadow = regions.covers_large_area and not mostly_at_edges
    likely_hard_graphic = mostly_at_edges and not regions.covers_large_area

    alpha_present = bool(semi_count > 0 or fully_transparent > 0)

    return AlphaAnalysis(
        alpha_present=alpha_present,
        fully_transparent_count=fully_transparent,
        semi_transparent_count=semi_count,
        weak_alpha_count=weak_count,
        fully_opaque_count=fully_opaque,
        semi_transparent_ratio=semi_ratio,
        histogram=histogram,
        regions=regions,
        mostly_at_edges=mostly_at_edges,
        small_island_count=small_islands,
        small_hole_count=small_holes,
        likely_soft_shadow=likely_soft_shadow,
        likely_hard_graphic=likely_hard_graphic,
    )
