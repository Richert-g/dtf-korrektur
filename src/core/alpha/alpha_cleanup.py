"""Alpha-Bereinigung mit mehreren internen Modi (Prompt Abschnitt 7).

Alle Schwellenwerte kommen zentral aus src.config.defaults.AlphaThresholds.

Hinweis zu "Pixel mit geringer Deckkraft bearbeiten" (`weak_alpha_threshold`,
inklusive Grenze: alpha <= threshold wird bearbeitet, alpha > threshold
bleibt unverändert): Die zugrunde liegende Funktion `_remove_weak_noise`
wendet diesen Schwellenwert für sich genommen GLOBAL auf das gesamte Bild an
- sie kennt keine Bildbereiche. Da der Standardwert (254) bewusst sehr
aggressiv ist, würde eine rein globale Anwendung auch bewusste weiche
Schattenflächen zerstören. Deshalb berechnet `clean_alpha` im AUTOMATIKMODUS
(settings.alpha_mode == AlphaMode.AUTO) zusätzlich eine Schutzmaske
(`compute_large_soft_region_mask`) für große, nicht am Motivrand liegende
Halbtransparenz-Flächen und nimmt diese von der Bearbeitung aus. Wählt der
Benutzer dagegen manuell einen konkreten Modus (z. B. "Nur Störpixel
entfernen"), wird der Schwellenwert bewusst weiterhin auf das gesamte Bild
angewendet - die Oberfläche zeigt dafür eine Warnung an (siehe
AdvancedSettingsDialog).

Über `weak_alpha_action` (`WeakAlphaAction`) lässt sich wählen, WIE die
betroffenen Pixel bearbeitet werden: SET_TRANSPARENT setzt nur den Alpha-
Wert auf 0 (RGB bleibt erhalten, bisheriges Verhalten), DELETE_PIXEL setzt
zusätzlich auch die RGB-Kanäle auf 0 (keine Farbinformationen bleiben
zurück). Die Auswahlmaske selbst (`alpha <= threshold`, ohne Ausnahme für
bereits transparente Pixel) ist für beide Varianten identisch - so kann
DELETE_PIXEL auch bei bereits vorher transparenten Pixeln (Alpha 0) noch
vorhandene RGB-Restwerte entfernen. Für die Berichtszählung
("removed_pixel_count") werden dagegen nur tatsächlich zuvor sichtbare Pixel
(Alpha > 0 vor der Bearbeitung) gezählt, damit der Bericht nicht bereits
unsichtbare Pixel als "entfernt" ausweist.

Symmetrisch dazu setzt "Pixel ab Alpha-Wert auf volle Deckkraft setzen"
(`near_opaque_threshold`, ebenfalls inklusive Grenze: alpha >= threshold wird
auf 255 gesetzt) alle ausreichend deckenden Pixel auf volle Deckkraft. Die
zugrunde liegende Funktion `_strengthen_near_opaque` gilt für NOISE_ONLY und
SOFT_CLEANUP gleichermaßen und wird im Automatikmodus durch dieselbe
Schutzmaske eingeschränkt wie die Bearbeitung - sonst könnte ein dichter Kern
eines bewussten weichen Schattens/Glows fälschlich hart gemacht werden.
ACHTUNG: Bei den Standardwerten (weak=254, near_opaque=242) und der
Standard-Reihenfolge REMOVE_FIRST hat "volle Deckkraft setzen" praktisch
keinen sichtbaren Effekt mehr, da "geringe Deckkraft bearbeiten" bereits
(fast) den gesamten Wertebereich bis 254 abdeckt, bevor die Verstärkung an
die Reihe kommt - für ein sichtbares Zusammenspiel beider Funktionen muss
entweder der Schwellenwert von "geringe Deckkraft" unterhalb des Schwellenwerts
von "volle Deckkraft" liegen, oder `threshold_order` auf STRENGTHEN_FIRST
stehen (siehe unten).

Beide Funktionen lassen sich unabhängig voneinander über
`weak_alpha_threshold_enabled` bzw. `near_opaque_threshold_enabled`
deaktivieren - der jeweils gespeicherte Schwellenwert bleibt dabei
unverändert erhalten, nur der Verarbeitungsschritt selbst wird übersprungen
(`_remove_weak_noise`/`_strengthen_near_opaque` geben das Array dann
unverändert zurück). Sind beide Pixel-Bedingungen für ein Pixel gleichzeitig
erfüllt (nur bei ungewöhnlicher Konfiguration mit sich überschneidenden
Schwellenwerten möglich), entscheidet `threshold_order`
(`AlphaThresholdOrder`), welche Funktion zuerst läuft und damit "gewinnt":
REMOVE_FIRST (Standard, bisheriges Verhalten) lässt die Bearbeitung zuerst
laufen, STRENGTHEN_FIRST kehrt die Reihenfolge um. Bei nicht überschneidenden
Schwellenwerten liefert jede Reihenfolge dasselbe Ergebnis. Die gemeinsame
Anwendung beider Funktionen in der konfigurierten Reihenfolge kapselt
`_apply_alpha_thresholds`.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from src.config.defaults import AlphaThresholds, ProcessingSettings
from src.core.analysis.alpha_analysis import compute_large_soft_region_mask, motif_edge_band_mask
from src.models.enums import AlphaMode, AlphaThresholdOrder, ImageType, WeakAlphaAction
from src.models.report import ImageProcessingReport


@dataclass
class AlphaCleanupResult:
    rgba: np.ndarray
    mode_used: AlphaMode
    removed_pixel_count: int = 0
    strengthened_pixel_count: int = 0
    removed_islands: int = 0
    closed_holes: int = 0


def _mode_for_image_type(image_type: ImageType) -> AlphaMode:
    return {
        ImageType.HARD_LOGO: AlphaMode.HARD_EDGE,
        ImageType.ILLUSTRATION: AlphaMode.SOFT_CLEANUP,
        ImageType.PHOTO: AlphaMode.NOISE_ONLY,
        ImageType.SOFT_SHADOW: AlphaMode.NOISE_ONLY,
        ImageType.UNKNOWN: AlphaMode.NOISE_ONLY,
    }[image_type]


def _remove_weak_noise(
    alpha: np.ndarray, thresholds: AlphaThresholds, protect_mask: np.ndarray | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Gibt (neue Alpha-Werte, Maske aller bearbeiteten Pixel) zurück. Die
    Maske wird unverändert zurückgegeben, auch wenn `weak_alpha_threshold_enabled`
    False ist (dann als reine Nullmaske) - der Aufrufer braucht sie zusätzlich,
    um bei WeakAlphaAction.DELETE_PIXEL auch die RGB-Kanäle zu nullen (siehe
    Moduldokumentation)."""
    if not thresholds.weak_alpha_threshold_enabled:
        return alpha.copy(), np.zeros(alpha.shape, dtype=bool)
    out = alpha.copy()
    # Inklusive Grenze wie gefordert: alpha <= threshold wird bearbeitet
    # (NICHT alpha < threshold), alpha > threshold bleibt unverändert. Bewusst
    # OHNE Ausnahme für bereits transparente Pixel (alpha == 0) - siehe
    # Moduldokumentation zu WeakAlphaAction.DELETE_PIXEL.
    weak_mask = alpha <= thresholds.weak_alpha_threshold
    if protect_mask is not None:
        weak_mask = weak_mask & ~protect_mask
    out[weak_mask] = 0
    return out, weak_mask


def _strengthen_near_opaque(
    alpha: np.ndarray, thresholds: AlphaThresholds, protect_mask: np.ndarray | None = None
) -> tuple[np.ndarray, int]:
    if not thresholds.near_opaque_threshold_enabled:
        return alpha.copy(), 0
    out = alpha.copy()
    # Inklusive Grenze wie bei "Pixel löschen bis Alpha-Wert": alpha >= threshold
    # wird auf volle Deckkraft gesetzt (NICHT alpha > threshold).
    strengthen_mask = (alpha >= thresholds.near_opaque_threshold) & (alpha < 255)
    if protect_mask is not None:
        strengthen_mask = strengthen_mask & ~protect_mask
    out[strengthen_mask] = 255
    return out, int(strengthen_mask.sum())


def _apply_alpha_thresholds(
    alpha: np.ndarray, thresholds: AlphaThresholds, protect_mask: np.ndarray | None = None
) -> tuple[np.ndarray, np.ndarray, int]:
    """Wendet Bearbeiten (geringe Deckkraft) und Volldeckend-Setzen in der
    konfigurierten Reihenfolge an (siehe Moduldokumentation zu
    `threshold_order`). Rückgabe: (neue Alpha-Werte, Maske der von "geringe
    Deckkraft bearbeiten" betroffenen Pixel, Anzahl verstärkter Pixel)."""
    if thresholds.threshold_order == AlphaThresholdOrder.STRENGTHEN_FIRST:
        alpha, strengthened = _strengthen_near_opaque(alpha, thresholds, protect_mask)
        alpha, weak_mask = _remove_weak_noise(alpha, thresholds, protect_mask)
    else:
        alpha, weak_mask = _remove_weak_noise(alpha, thresholds, protect_mask)
        alpha, strengthened = _strengthen_near_opaque(alpha, thresholds, protect_mask)
    return alpha, weak_mask, strengthened


def _hard_edge_threshold(alpha_u8: np.ndarray, thresholds: AlphaThresholds) -> int:
    # Wenn kaum/keine echte Zwischenwert-Verteilung existiert (z. B. bereits reines
    # 0/255-Alpha), liefert Otsu einen entarteten Randwert (0 oder 255), da die
    # Streuung zwischen den Klassen für jeden Schnittpunkt identisch ist.
    if np.unique(alpha_u8).size <= 2 or alpha_u8.min() == alpha_u8.max():
        return thresholds.hard_edge_default_threshold
    otsu_value, _ = cv2.threshold(np.ascontiguousarray(alpha_u8), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if otsu_value <= 0 or otsu_value >= 255:
        return thresholds.hard_edge_default_threshold
    return int(otsu_value)


def _remove_small_islands(alpha: np.ndarray, min_size: int) -> tuple[np.ndarray, int]:
    out = alpha.copy()
    visible_u8 = (out > 0).astype(np.uint8) * 255
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(visible_u8, connectivity=8)
    removed = 0
    for i in range(1, num_labels):
        if stats[i, cv2.CC_STAT_AREA] < min_size:
            out[labels == i] = 0
            removed += 1
    return out, removed


def _close_small_holes(rgba: np.ndarray, max_size: int) -> tuple[np.ndarray, int]:
    out = rgba.copy()
    alpha = out[:, :, 3]
    h, w = alpha.shape
    transparent_u8 = (alpha == 0).astype(np.uint8) * 255
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(transparent_u8, connectivity=8)
    hole_mask = np.zeros((h, w), dtype=bool)
    closed = 0
    for i in range(1, num_labels):
        x, y, bw, bh, area = stats[i, :5]
        touches_border = x == 0 or y == 0 or (x + bw) >= w or (y + bh) >= h
        if not touches_border and area <= max_size:
            hole_mask |= labels == i
            closed += 1
    if closed == 0:
        return out, 0

    out[:, :, 3][hole_mask] = 255
    # RGB der neu geschlossenen Löcher aus der Umgebung rekonstruieren
    inpaint_mask = hole_mask.astype(np.uint8) * 255
    rgb_bgr = cv2.cvtColor(out[:, :, :3], cv2.COLOR_RGB2BGR)
    inpainted_bgr = cv2.inpaint(rgb_bgr, inpaint_mask, 3, cv2.INPAINT_TELEA)
    out[:, :, :3] = cv2.cvtColor(inpainted_bgr, cv2.COLOR_BGR2RGB)
    return out, closed


def _apply_hard_edge(rgba: np.ndarray, thresholds: AlphaThresholds) -> tuple[np.ndarray, int, int, int, int]:
    out = rgba.copy()
    alpha_u8 = out[:, :, 3]
    threshold = _hard_edge_threshold(alpha_u8, thresholds)

    hard_mask = alpha_u8 >= threshold
    removed = int(((alpha_u8 > 0) & ~hard_mask).sum())
    strengthened = int(((alpha_u8 < 255) & hard_mask).sum())
    out[:, :, 3] = np.where(hard_mask, 255, 0).astype(np.uint8)

    out[:, :, 3], removed_islands = _remove_small_islands(out[:, :, 3], thresholds.min_island_size_px)
    out, closed_holes = _close_small_holes(out, thresholds.max_hole_fill_size_px)

    if thresholds.edge_choke_px > 0:
        k = max(1, int(round(thresholds.edge_choke_px)))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k * 2 + 1, k * 2 + 1))
        eroded = cv2.erode((out[:, :, 3] > 0).astype(np.uint8), kernel)
        out[:, :, 3] = np.where(eroded > 0, out[:, :, 3], 0)

    if thresholds.edge_feather_radius > 0:
        out[:, :, 3] = cv2.GaussianBlur(
            out[:, :, 3], (0, 0), sigmaX=thresholds.edge_feather_radius
        )

    return out, removed, strengthened, removed_islands, closed_holes


def _apply_soft_cleanup(
    rgba: np.ndarray, thresholds: AlphaThresholds, protect_mask: np.ndarray | None = None
) -> tuple[np.ndarray, int, int]:
    out = rgba.copy()
    original_alpha = rgba[:, :, 3]
    a = out[:, :, 3].copy()

    a, weak_mask, strengthened = _apply_alpha_thresholds(a, thresholds, protect_mask)
    removed = int((weak_mask & (original_alpha > 0)).sum())

    mid_band_mask = (original_alpha > thresholds.mid_low_threshold) & (original_alpha <= thresholds.mid_high_threshold)
    edge_band = motif_edge_band_mask(original_alpha, thresholds)

    remove_in_edge = mid_band_mask & edge_band
    a[remove_in_edge] = 0
    removed += int(remove_in_edge.sum())

    boost_outside_edge = mid_band_mask & ~edge_band
    boosted = np.clip(
        original_alpha[boost_outside_edge].astype(np.float32) * thresholds.soft_cleanup_strengthen_factor, 0, 255
    ).astype(np.uint8)
    a[boost_outside_edge] = boosted
    strengthened += int(boost_outside_edge.sum())

    out[:, :, 3] = a
    if thresholds.weak_alpha_action == WeakAlphaAction.DELETE_PIXEL and weak_mask.any():
        out[:, :, 0:3][weak_mask] = 0
    return out, removed, strengthened


def clean_alpha(
    rgba: np.ndarray,
    image_type: ImageType,
    settings: ProcessingSettings,
    report: ImageProcessingReport | None = None,
) -> AlphaCleanupResult:
    thresholds = settings.alpha
    is_auto = settings.alpha_mode == AlphaMode.AUTO
    mode = settings.alpha_mode
    if mode == AlphaMode.AUTO:
        mode = _mode_for_image_type(image_type)

    # Schutz großer, bewusster weicher Flächen (Schatten/Glow) vor dem
    # "Pixel löschen bis Alpha-Wert"-Schwellenwert - nur im Automatikmodus.
    # Im manuell gewählten Modus darf der Benutzer den Wert ausdrücklich auf
    # das gesamte Bild anwenden (siehe Moduldokumentation oben).
    protect_mask = None
    protected_pixel_count = 0
    if is_auto and mode in (AlphaMode.NOISE_ONLY, AlphaMode.SOFT_CLEANUP):
        protect_mask = compute_large_soft_region_mask(rgba[:, :, 3], thresholds)
        if not protect_mask.any():
            protect_mask = None
        else:
            protected_pixel_count = int(protect_mask.sum())

    if mode == AlphaMode.NOISE_ONLY:
        out = rgba.copy()
        original_alpha = out[:, :, 3].copy()
        out[:, :, 3], weak_mask, strengthened = _apply_alpha_thresholds(out[:, :, 3], thresholds, protect_mask)
        removed = int((weak_mask & (original_alpha > 0)).sum())
        if thresholds.weak_alpha_action == WeakAlphaAction.DELETE_PIXEL and weak_mask.any():
            out[:, :, 0:3][weak_mask] = 0
        result = AlphaCleanupResult(
            rgba=out, mode_used=mode, removed_pixel_count=removed, strengthened_pixel_count=strengthened
        )
    elif mode == AlphaMode.SOFT_CLEANUP:
        out, removed, strengthened = _apply_soft_cleanup(rgba, thresholds, protect_mask)
        result = AlphaCleanupResult(
            rgba=out, mode_used=mode, removed_pixel_count=removed, strengthened_pixel_count=strengthened
        )
    elif mode == AlphaMode.HARD_EDGE:
        out, removed, strengthened, islands, holes = _apply_hard_edge(rgba, thresholds)
        result = AlphaCleanupResult(
            rgba=out,
            mode_used=mode,
            removed_pixel_count=removed,
            strengthened_pixel_count=strengthened,
            removed_islands=islands,
            closed_holes=holes,
        )
    else:
        raise ValueError(f"Unbekannter Alpha-Modus: {mode}")

    if report is not None:
        report.removed_pixel_count += result.removed_pixel_count
        report.strengthened_pixel_count += result.strengthened_pixel_count
        report.removed_islands += result.removed_islands
        report.closed_holes += result.closed_holes
        if result.removed_pixel_count:
            report.add_step(
                "alpha_cleanup_remove",
                f"{result.removed_pixel_count} fast unsichtbare oder unerwünschte Randpixel entfernt.",
                pixels_affected=result.removed_pixel_count,
            )
        if result.strengthened_pixel_count:
            report.add_step(
                "alpha_cleanup_strengthen",
                f"{result.strengthened_pixel_count} fast deckende Pixel auf volle Deckkraft gesetzt.",
                pixels_affected=result.strengthened_pixel_count,
            )
        if result.removed_islands:
            report.add_step(
                "alpha_cleanup_islands",
                f"{result.removed_islands} kleine Pixelinseln entfernt.",
                pixels_affected=result.removed_islands,
            )
        if result.closed_holes:
            report.add_step(
                "alpha_cleanup_holes",
                f"{result.closed_holes} kleine transparente Löcher geschlossen.",
                pixels_affected=result.closed_holes,
            )
        if protected_pixel_count:
            report.add_step(
                "alpha_cleanup_shadow_protection",
                f"{protected_pixel_count} Pixel einer erkannten weichen Fläche (z. B. Schatten/Glow) "
                "wurden vor dem Löschen über den Alpha-Schwellenwert geschützt.",
                pixels_affected=protected_pixel_count,
            )

    return result
