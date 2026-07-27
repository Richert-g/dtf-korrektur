import numpy as np

from src.config.defaults import ProcessingSettings
from src.core.alpha.alpha_cleanup import clean_alpha
from src.models.enums import AlphaMode, ImageType
from tests.fixtures.synthetic_images import (
    make_large_soft_shadow,
    make_logo_with_white_halo,
    make_small_islands,
    make_transparent_holes,
)


def _arr(img):
    return np.array(img.convert("RGBA"))


def test_noise_only_removes_only_weak_pixels():
    """NOISE_ONLY ist ein reiner "Alpha <= Schwellenwert löschen"-Filter - die
    Schwelle zum Volldeckend-Setzen wird hier bewusst auf 255 gesetzt (=
    de facto deaktiviert), um die Löschung isoliert zu testen (siehe
    test_noise_only_strengthens_near_opaque_pixels für das Zusammenspiel
    beider Schwellen mit Standardwerten)."""
    arr = np.zeros((8, 8, 4), dtype=np.uint8)
    arr[:, :, 3] = 250  # oberhalb des Löschen-Schwellenwerts -> bleibt erhalten
    arr[0, 0, 3] = 3  # unterhalb des Löschen-Schwellenwerts -> wird gelöscht
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.NOISE_ONLY
    settings.alpha.near_opaque_threshold = 255
    assert settings.alpha.weak_alpha_threshold == 241
    result = clean_alpha(arr, ImageType.PHOTO, settings, report=None)
    assert result.rgba[0, 0, 3] == 0
    assert result.rgba[1, 1, 3] == 250  # unverändert
    assert result.removed_pixel_count == 1


def test_noise_only_strengthens_near_opaque_pixels():
    """Pixel ab Alpha-Wert 'near_opaque_threshold' werden auch im NOISE_ONLY-
    Modus auf volle Deckkraft (255) gesetzt - inklusive Grenze (>=, nicht >).
    Der Löschen-Schwellenwert wird hier bewusst niedrig gesetzt, damit der
    mittlere Testwert (100) nicht schon vorher durch die (mit Standardwert
    241 sehr aggressive) Löschung entfernt wird - siehe
    test_noise_only_removes_only_weak_pixels für den umgekehrten Fall."""
    arr = np.zeros((8, 8, 4), dtype=np.uint8)
    arr[:, :, 3] = 100  # deutlich unterhalb -> bleibt unverändert
    arr[0, 0, 3] = 242  # == Standard-Schwellenwert -> wird volldeckend (inklusive Grenze)
    arr[0, 1, 3] = 250  # oberhalb -> wird volldeckend
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.NOISE_ONLY
    settings.alpha.weak_alpha_threshold = 13
    assert settings.alpha.near_opaque_threshold == 242
    result = clean_alpha(arr, ImageType.PHOTO, settings, report=None)
    assert result.rgba[0, 0, 3] == 255
    assert result.rgba[0, 1, 3] == 255
    assert result.rgba[1, 1, 3] == 100  # unverändert
    assert result.strengthened_pixel_count == 2


def test_strengthen_near_opaque_respects_auto_mode_shadow_protection():
    """Im Automatikmodus darf eine erkannte große weiche Fläche (Schatten/Glow)
    nicht durch das Vollmachen auf 255 hart gemacht werden - dieselbe
    Schutzmaske wie beim Löschen muss auch hier greifen."""
    img = make_large_soft_shadow()
    arr = np.array(img)
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.AUTO
    settings.alpha.near_opaque_threshold = 100  # aggressiv, um den Schatten sicher zu treffen

    shadow_alpha_before = arr[:, :, 3].copy()
    candidate_mask = (shadow_alpha_before >= 100) & (shadow_alpha_before < 255)
    assert candidate_mask.any(), "Testbild sollte Schattenpixel im betroffenen Bereich haben"

    result = clean_alpha(arr, ImageType.SOFT_SHADOW, settings, report=None)

    # Die eigentlichen Motiv-Pixel (schon 255) bleiben unberührt, aber die
    # weiche Schattenfläche darf NICHT pauschal auf 255 hochgesetzt worden sein.
    assert not (result.rgba[:, :, 3][candidate_mask] == 255).all()


def test_weak_alpha_threshold_boundary_is_inclusive():
    """alpha <= threshold muss gelöscht werden, NICHT nur alpha < threshold."""
    arr = np.zeros((4, 4, 4), dtype=np.uint8)
    arr[:, :, 3] = 100
    arr[0, 0, 3] = 50  # == Schwellenwert -> muss gelöscht werden (inklusive Grenze)
    arr[0, 1, 3] = 51  # > Schwellenwert -> muss erhalten bleiben
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.NOISE_ONLY
    settings.alpha.weak_alpha_threshold = 50
    result = clean_alpha(arr, ImageType.PHOTO, settings, report=None)
    assert result.rgba[0, 0, 3] == 0
    assert result.rgba[0, 1, 3] == 51


def test_weak_alpha_threshold_255_not_selectable_in_ui_range():
    """255 darf laut Vorgabe nicht wählbar sein (würde auch deckende Pixel löschen)."""
    from src.app.ui.advanced_settings_dialog import AdvancedSettingsDialog

    assert AdvancedSettingsDialog.WEAK_ALPHA_THRESHOLD_MAX == 254


def test_hard_edge_binarizes_alpha():
    arr = _arr(make_logo_with_white_halo())
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.HARD_EDGE
    settings.alpha.edge_feather_radius = 0  # exakte Prüfung ohne gewollte Kanten-Weichzeichnung
    result = clean_alpha(arr, ImageType.HARD_LOGO, settings, report=None)
    unique_values = set(np.unique(result.rgba[:, :, 3]).tolist())
    assert unique_values <= {0, 255}


def test_hard_edge_removes_small_islands():
    arr = _arr(make_small_islands())
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.HARD_EDGE
    settings.alpha.edge_feather_radius = 0  # exakte Prüfung ohne Weichzeichnung
    result = clean_alpha(arr, ImageType.HARD_LOGO, settings, report=None)
    assert result.removed_islands >= 4


def test_hard_edge_closes_small_holes():
    arr = _arr(make_transparent_holes())
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.HARD_EDGE
    settings.alpha.edge_feather_radius = 0
    result = clean_alpha(arr, ImageType.HARD_LOGO, settings, report=None)
    assert result.closed_holes >= 2


def test_auto_mode_does_not_binarize_soft_shadow():
    """Sicherheitsregel: große Schattenflächen dürfen nicht binarisiert werden (Prompt Abschnitt 19)."""
    arr = _arr(make_large_soft_shadow())
    settings = ProcessingSettings()  # AUTO
    result = clean_alpha(arr, ImageType.SOFT_SHADOW, settings, report=None)
    unique_values = np.unique(result.rgba[:, :, 3])
    # weiterhin viele Zwischenwerte vorhanden -> keine Binarisierung
    assert len(unique_values) > 5


def test_soft_cleanup_preserves_true_midrange_alpha():
    """Prüft die Mittelband-Logik der sanften Bereinigung isoliert vom (jetzt
    absichtlich sehr hohen) Standard-Schwellenwert für 'Pixel löschen bis
    Alpha-Wert' - dafür hier explizit ein niedriger Schwellenwert gesetzt."""
    arr = np.zeros((16, 16, 4), dtype=np.uint8)
    arr[:, :, 3] = 140  # echter mittlerer Alpha-Wert (~55%), muss erhalten bleiben
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.SOFT_CLEANUP
    settings.alpha.weak_alpha_threshold = 13
    result = clean_alpha(arr, ImageType.ILLUSTRATION, settings, report=None)
    assert result.rgba[5, 5, 3] == 140


def test_auto_mode_protects_large_soft_shadow_from_high_default_threshold():
    """Kernanforderung: im Automatikmodus darf der aggressive Standardwert (241)
    einen erkannten weichen Schatten nicht großflächig löschen."""
    arr = _arr(make_large_soft_shadow())
    settings = ProcessingSettings()  # AUTO, weak_alpha_threshold=241 (Standard)
    assert settings.alpha_mode == AlphaMode.AUTO
    assert settings.alpha.weak_alpha_threshold == 241

    result = clean_alpha(arr, ImageType.SOFT_SHADOW, settings, report=None)

    original_semi = int(((arr[:, :, 3] > 0) & (arr[:, :, 3] < 255)).sum())
    remaining_semi = int(((result.rgba[:, :, 3] > 0) & (result.rgba[:, :, 3] < 255)).sum())
    # die weiche Fläche darf nicht komplett verschwinden
    assert remaining_semi > original_semi * 0.5


def test_manual_mode_applies_high_threshold_globally_without_protection():
    """Im manuell gewählten Modus gilt der Schwellenwert bewusst für das ganze
    Bild - auch auf große weiche Flächen (die Oberfläche zeigt dafür eine
    Warnung, siehe AdvancedSettingsDialog)."""
    arr = _arr(make_large_soft_shadow())
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.NOISE_ONLY  # explizit gewählt, nicht AUTO
    assert settings.alpha.weak_alpha_threshold == 241

    result = clean_alpha(arr, ImageType.SOFT_SHADOW, settings, report=None)

    remaining_semi = int(((result.rgba[:, :, 3] > 0) & (result.rgba[:, :, 3] < 255)).sum())
    assert remaining_semi == 0  # keine Schutzausnahme im manuellen Modus


def test_protection_report_step_logged_when_shadow_protected():
    from src.models.report import ImageProcessingReport

    arr = _arr(make_large_soft_shadow())
    settings = ProcessingSettings()
    report = ImageProcessingReport()
    clean_alpha(arr, ImageType.SOFT_SHADOW, settings, report=report)
    assert any("geschützt" in step.description for step in report.applied_steps)


# --- Unabhängige Aktivierung/Deaktivierung der beiden Alpha-Schwellenwerte ---


def test_weak_alpha_threshold_disabled_skips_deletion_in_noise_only():
    arr = np.zeros((8, 8, 4), dtype=np.uint8)
    arr[:, :, 3] = 3  # weit unterhalb des Standard-Löschen-Schwellenwerts (241)
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.NOISE_ONLY
    settings.alpha.weak_alpha_threshold_enabled = False

    result = clean_alpha(arr, ImageType.PHOTO, settings, report=None)

    assert (result.rgba[:, :, 3] == 3).all()  # unverändert, obwohl <= Schwellenwert
    assert result.removed_pixel_count == 0


def test_weak_alpha_threshold_value_kept_while_disabled():
    """Der Schwellenwert selbst bleibt in den Einstellungen unverändert, auch
    wenn die Funktion deaktiviert ist - nur die Anwendung wird übersprungen."""
    settings = ProcessingSettings()
    settings.alpha.weak_alpha_threshold_enabled = False
    settings.alpha.weak_alpha_threshold = 199
    assert settings.alpha.weak_alpha_threshold == 199
    assert settings.alpha.weak_alpha_threshold_enabled is False


def test_near_opaque_threshold_disabled_skips_strengthening_in_noise_only():
    arr = np.zeros((8, 8, 4), dtype=np.uint8)
    arr[:, :, 3] = 250  # oberhalb des Standard-Volldeckend-Schwellenwerts (242)
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.NOISE_ONLY
    settings.alpha.weak_alpha_threshold_enabled = False  # isoliert nur den Strengthen-Test
    settings.alpha.near_opaque_threshold_enabled = False

    result = clean_alpha(arr, ImageType.PHOTO, settings, report=None)

    assert (result.rgba[:, :, 3] == 250).all()  # unverändert, obwohl >= Schwellenwert
    assert result.strengthened_pixel_count == 0


def test_both_thresholds_disabled_leaves_alpha_completely_unchanged():
    arr = np.zeros((8, 8, 4), dtype=np.uint8)
    arr[0, 0, 3] = 0
    arr[1, 1, 3] = 3
    arr[2, 2, 3] = 128
    arr[3, 3, 3] = 250
    arr[4, 4, 3] = 255
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.NOISE_ONLY
    settings.alpha.weak_alpha_threshold_enabled = False
    settings.alpha.near_opaque_threshold_enabled = False

    result = clean_alpha(arr, ImageType.PHOTO, settings, report=None)

    assert np.array_equal(result.rgba[:, :, 3], arr[:, :, 3])
    assert result.removed_pixel_count == 0
    assert result.strengthened_pixel_count == 0


def test_thresholds_independently_toggleable_in_soft_cleanup_mode():
    """Auch im Modus 'Sanfte Bereinigung' (verwendet dieselben zwei Funktionen
    intern über _apply_soft_cleanup) müssen beide Schaltflächen unabhängig
    wirken."""
    arr = np.zeros((8, 8, 4), dtype=np.uint8)
    arr[:, :, 3] = 250
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.SOFT_CLEANUP
    settings.alpha.near_opaque_threshold_enabled = False

    result = clean_alpha(arr, ImageType.ILLUSTRATION, settings, report=None)

    assert (result.rgba[:, :, 3] == 250).all()


def test_disabling_one_threshold_does_not_affect_the_other():
    arr = np.zeros((8, 8, 4), dtype=np.uint8)
    arr[0, 0, 3] = 3  # sollte weiterhin geloescht werden
    arr[1, 1, 3] = 250  # sollte NICHT mehr volldeckend gemacht werden
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.NOISE_ONLY
    settings.alpha.near_opaque_threshold_enabled = False

    result = clean_alpha(arr, ImageType.PHOTO, settings, report=None)

    assert result.rgba[0, 0, 3] == 0
    assert result.rgba[1, 1, 3] == 250
    assert result.removed_pixel_count == 1
    assert result.strengthened_pixel_count == 0
