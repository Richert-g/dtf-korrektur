"""Gemeinsame Infrastruktur für die visuellen Regressionstests
(Golden-Image-Vergleich): führt die echte Verarbeitungspipeline
(core.pipeline.process_image) auf festen synthetischen Testbildern aus und
vergleicht das Ergebnis pixelweise gegen ein eingechecktes Referenzbild
unter tests/fixtures/golden/.

Bewusst eine kleine Toleranz statt exaktem Bit-Vergleich (siehe
DEFAULT_MAX_PIXEL_DIFF/DEFAULT_MAX_DIFF_FRACTION): winzige, harmlose
Abweichungen durch z. B. eine neue LittleCMS-/OpenCV-Version sollen nicht
automatisch als Regression durchfallen, eine echte Qualitätsänderung
(anderer Schwellenwert, andere Kantenbehandlung, andere Farbkonvertierung)
aber zuverlässig auffallen.

Referenzbilder werden NIE automatisch von einem Testlauf erzeugt oder
überschrieben - nur über scripts/update_golden_images.py, das ein
Entwickler nach bewusster, manueller Sichtprüfung ausführt und den Commit
anschließend selbst verantwortet.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from src.config.defaults import ProcessingSettings
from src.core.pipeline import process_image
from src.models.enums import AlphaMode
from tests.fixtures.synthetic_images import (
    make_illustration_soft_edge,
    make_large_soft_shadow,
    make_logo_with_white_halo,
    make_saturated_blue_cyan_motif,
    make_small_islands,
    make_transparent_holes,
)

GOLDEN_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "golden"

# Wie stark sich ein einzelner Pixel (max. Kanalabstand, 0-255) unterscheiden
# darf, ohne als "abweichend" gezählt zu werden.
DEFAULT_MAX_PIXEL_DIFF = 3
# Wie groß der Anteil abweichender Pixel maximal sein darf (0-1).
DEFAULT_MAX_DIFF_FRACTION = 0.005

BUNDLED_FOGRA39_PROFILE = "resources/profiles/CMYK/CoatedFOGRA39.icc"


def _quiet_export_settings(settings: ProcessingSettings) -> None:
    """Reduziert Nebendateien auf das für den Bildvergleich Nötige - schneller
    Testlauf, keine für dieses Testziel irrelevanten Berichte/Overlays."""
    e = settings.export
    e.write_diff_overlays = False
    e.write_gamut_warning = False
    e.write_alpha_mask = False
    e.write_white_mask = False
    e.write_cmyk_tiff = False
    e.write_json_report = False
    e.write_html_report = False
    e.write_transparency_only_preview = False
    e.write_softproof_preview = False


def _hard_logo_scenario() -> tuple[Image.Image, ProcessingSettings]:
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.HARD_EDGE
    _quiet_export_settings(settings)
    return make_logo_with_white_halo(), settings


def _illustration_soft_cleanup_scenario() -> tuple[Image.Image, ProcessingSettings]:
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.SOFT_CLEANUP
    _quiet_export_settings(settings)
    return make_illustration_soft_edge(), settings


def _soft_shadow_auto_scenario() -> tuple[Image.Image, ProcessingSettings]:
    settings = ProcessingSettings()  # AUTO
    _quiet_export_settings(settings)
    return make_large_soft_shadow(), settings


def _small_islands_hard_edge_scenario() -> tuple[Image.Image, ProcessingSettings]:
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.HARD_EDGE
    _quiet_export_settings(settings)
    return make_small_islands(), settings


def _transparent_holes_hard_edge_scenario() -> tuple[Image.Image, ProcessingSettings]:
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.HARD_EDGE
    _quiet_export_settings(settings)
    return make_transparent_holes(), settings


def _saturated_motif_with_icc_scenario() -> tuple[Image.Image, ProcessingSettings]:
    settings = ProcessingSettings()  # AUTO
    settings.color.target_profile_path = BUNDLED_FOGRA39_PROFILE
    settings.color.auto_select_intent = False
    _quiet_export_settings(settings)
    return make_saturated_blue_cyan_motif(), settings


# Name -> Fabrikfunktion, die (Eingabebild, Settings) liefert. Der Name ist
# zugleich der Dateiname unter tests/fixtures/golden/<name>.png - wird sowohl
# von den Tests als auch von scripts/update_golden_images.py verwendet, damit
# beide garantiert dieselben Szenarien kennen.
GOLDEN_SCENARIOS: dict[str, Callable[[], tuple[Image.Image, ProcessingSettings]]] = {
    "hard_logo_white_halo": _hard_logo_scenario,
    "illustration_soft_cleanup": _illustration_soft_cleanup_scenario,
    "soft_shadow_auto_protection": _soft_shadow_auto_scenario,
    "small_islands_hard_edge": _small_islands_hard_edge_scenario,
    "transparent_holes_hard_edge": _transparent_holes_hard_edge_scenario,
    "saturated_motif_fogra39": _saturated_motif_with_icc_scenario,
}


def run_scenario(name: str, tmp_path: Path) -> np.ndarray:
    image, settings = GOLDEN_SCENARIOS[name]()
    input_path = tmp_path / "input.png"
    image.save(input_path)
    output_root = tmp_path / "output"

    report = process_image(input_path, settings, output_root)
    assert report.success, f"Verarbeitung für Szenario '{name}' fehlgeschlagen: {report.errors}"
    assert report.output_path is not None

    result = Image.open(report.output_path).convert("RGBA")
    return np.array(result)


def golden_path(name: str) -> Path:
    return GOLDEN_DIR / f"{name}.png"


def assert_matches_golden(
    actual_rgba: np.ndarray,
    name: str,
    max_pixel_diff: int = DEFAULT_MAX_PIXEL_DIFF,
    max_diff_fraction: float = DEFAULT_MAX_DIFF_FRACTION,
) -> None:
    path = golden_path(name)
    if not path.exists():
        pytest.fail(
            f"Referenzbild fehlt: {path}. Mit 'python scripts/update_golden_images.py' erzeugen, "
            "das Ergebnis von Auge prüfen und dann als bewussten Commit einchecken."
        )

    golden_rgba = np.array(Image.open(path).convert("RGBA"))
    if golden_rgba.shape != actual_rgba.shape:
        pytest.fail(
            f"Visuelle Regression bei '{name}': Bildgröße weicht ab "
            f"(Referenz {golden_rgba.shape} vs. aktuell {actual_rgba.shape})."
        )

    diff = np.abs(golden_rgba.astype(np.int16) - actual_rgba.astype(np.int16)).max(axis=-1)
    differing_fraction = float((diff > max_pixel_diff).mean())

    if differing_fraction > max_diff_fraction:
        pytest.fail(
            f"Visuelle Regression bei '{name}': {differing_fraction * 100:.2f}% der Pixel weichen um "
            f"mehr als {max_pixel_diff} (von 255) vom Referenzbild {path.name} ab "
            f"(erlaubt: {max_diff_fraction * 100:.2f}%). Falls die Änderung beabsichtigt ist: "
            "'python scripts/update_golden_images.py' ausführen, Ergebnis von Auge prüfen, neu committen."
        )
