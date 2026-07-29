import numpy as np

from src.config.defaults import ProcessingSettings
from src.core.alpha.alpha_cleanup import clean_alpha
from src.models.enums import AlphaMode, AlphaThresholdOrder, ImageType, WeakAlphaAction
from tests.fixtures.synthetic_images import (
    make_large_soft_shadow,
    make_logo_with_white_halo,
    make_small_islands,
    make_transparent_holes,
)


def _arr(img):
    return np.array(img.convert("RGBA"))


def test_noise_only_removes_only_weak_pixels():
    """NOISE_ONLY ist ein reiner "Alpha <= Schwellenwert bearbeiten"-Filter -
    die Schwelle zum Volldeckend-Setzen wird hier bewusst auf 255 gesetzt (=
    de facto deaktiviert), um die Bearbeitung isoliert zu testen (siehe
    test_noise_only_strengthens_near_opaque_pixels für das Zusammenspiel
    beider Schwellen). weak_alpha_threshold wird hier bewusst auf 241 (statt
    dem seit dieser Version aggressiveren Standardwert 254) gesetzt, damit
    250 als "oberhalb" isoliert getestet werden kann."""
    arr = np.zeros((8, 8, 4), dtype=np.uint8)
    arr[:, :, 3] = 250  # oberhalb des Löschen-Schwellenwerts -> bleibt erhalten
    arr[0, 0, 3] = 3  # unterhalb des Löschen-Schwellenwerts -> wird gelöscht
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.NOISE_ONLY
    settings.alpha.weak_alpha_threshold = 241
    settings.alpha.near_opaque_threshold = 255
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
    """Kernanforderung: im Automatikmodus darf der aggressive Standardwert (254)
    einen erkannten weichen Schatten nicht großflächig löschen."""
    arr = _arr(make_large_soft_shadow())
    settings = ProcessingSettings()  # AUTO, weak_alpha_threshold=254 (Standard)
    assert settings.alpha_mode == AlphaMode.AUTO
    assert settings.alpha.weak_alpha_threshold == 254

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
    assert settings.alpha.weak_alpha_threshold == 254

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
    wirken. weak_alpha_threshold wird hier bewusst auf 241 (statt dem
    aggressiveren Standardwert 254) gesetzt, damit 250 isoliert als "von
    'geringe Deckkraft bearbeiten' nicht betroffen" getestet werden kann."""
    arr = np.zeros((8, 8, 4), dtype=np.uint8)
    arr[:, :, 3] = 250
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.SOFT_CLEANUP
    settings.alpha.weak_alpha_threshold = 241
    settings.alpha.near_opaque_threshold_enabled = False

    result = clean_alpha(arr, ImageType.ILLUSTRATION, settings, report=None)

    assert (result.rgba[:, :, 3] == 250).all()


def test_default_weak_threshold_makes_near_opaque_ineffective_under_remove_first():
    """Dokumentiert eine bewusste Konsequenz der neuen Standardwerte (siehe
    Moduldocstring 'ACHTUNG'): weak_alpha_threshold=254 deckt praktisch den
    gesamten Wertebereich bis 254 ab. Unter der Standard-Reihenfolge
    REMOVE_FIRST wird ein Pixel im "Verstärkungsfenster" von near_opaque_threshold
    (Standard 242) daher bereits VOR der Verstärkung gelöscht - "volle
    Deckkraft setzen" hat unter den Standardwerten dadurch keinen sichtbaren
    Effekt mehr. Für ein Zusammenspiel beider Funktionen muss entweder der
    Schwellenwert von "geringe Deckkraft bearbeiten" unterhalb des
    Schwellenwerts von "volle Deckkraft setzen" liegen, oder threshold_order
    auf STRENGTHEN_FIRST stehen (siehe test_strengthen_first_order_keeps_overlapping_pixel_opaque)."""
    arr = np.zeros((4, 4, 4), dtype=np.uint8)
    arr[:, :, 3] = 245  # läge im (unter den Standardwerten nicht mehr erreichbaren) Verstärkungsfenster
    settings = ProcessingSettings()  # Standardwerte: weak=254, near_opaque=242, REMOVE_FIRST
    settings.alpha_mode = AlphaMode.NOISE_ONLY

    result = clean_alpha(arr, ImageType.PHOTO, settings, report=None)

    assert (result.rgba[:, :, 3] == 0).all()  # gelöscht statt volldeckend gemacht
    assert result.strengthened_pixel_count == 0


# --- Verarbeitungsmethode für "geringe Deckkraft bearbeiten" ---


def test_default_action_is_set_transparent():
    settings = ProcessingSettings()
    assert settings.alpha.weak_alpha_action == WeakAlphaAction.SET_TRANSPARENT


def test_set_transparent_action_keeps_rgb_unchanged():
    arr = np.zeros((4, 4, 4), dtype=np.uint8)
    arr[:, :, 0:3] = [200, 100, 50]
    arr[:, :, 3] = 10
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.NOISE_ONLY
    settings.alpha.weak_alpha_action = WeakAlphaAction.SET_TRANSPARENT

    result = clean_alpha(arr, ImageType.PHOTO, settings, report=None)

    assert (result.rgba[:, :, 3] == 0).all()
    assert np.array_equal(result.rgba[:, :, 0:3], arr[:, :, 0:3])  # RGB bleibt erhalten


def test_delete_pixel_action_zeros_rgb_too():
    arr = np.zeros((4, 4, 4), dtype=np.uint8)
    arr[:, :, 0:3] = [200, 100, 50]
    arr[:, :, 3] = 10
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.NOISE_ONLY
    settings.alpha.weak_alpha_action = WeakAlphaAction.DELETE_PIXEL

    result = clean_alpha(arr, ImageType.PHOTO, settings, report=None)

    assert (result.rgba[:, :, 3] == 0).all()
    assert (result.rgba[:, :, 0:3] == 0).all()  # keine Farbinformationen bleiben zurück


def test_delete_pixel_action_also_clears_rgb_of_already_transparent_pixels():
    """Anders als SET_TRANSPARENT gilt DELETE_PIXEL bewusst auch für Pixel, die
    schon vorher Alpha=0 hatten (siehe Moduldokumentation zur fehlenden
    alpha>0-Ausnahme) - so werden auch dort eventuell vorhandene RGB-
    Restwerte entfernt."""
    arr = np.zeros((2, 2, 4), dtype=np.uint8)
    arr[:, :, 0:3] = [123, 45, 67]
    arr[:, :, 3] = 0  # bereits vollständig transparent, mit Restfarbe
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.NOISE_ONLY
    settings.alpha.weak_alpha_action = WeakAlphaAction.DELETE_PIXEL

    result = clean_alpha(arr, ImageType.PHOTO, settings, report=None)

    assert (result.rgba[:, :, 0:3] == 0).all()
    assert result.removed_pixel_count == 0  # nicht als "entfernt" gezählt - war schon unsichtbar


def test_delete_pixel_action_also_applies_in_soft_cleanup_mode():
    arr = np.zeros((16, 16, 4), dtype=np.uint8)
    arr[:, :, 0:3] = [10, 20, 30]
    arr[:, :, 3] = 5
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.SOFT_CLEANUP
    settings.alpha.weak_alpha_action = WeakAlphaAction.DELETE_PIXEL

    result = clean_alpha(arr, ImageType.ILLUSTRATION, settings, report=None)

    assert (result.rgba[:, :, 3] == 0).all()
    assert (result.rgba[:, :, 0:3] == 0).all()


def test_weak_threshold_boundary_alpha_above_threshold_stays_untouched_including_rgb():
    """Alpha > Schwellenwert muss unabhängig von der Verarbeitungsmethode
    vollständig unverändert bleiben (weder Alpha noch RGB)."""
    arr = np.zeros((2, 2, 4), dtype=np.uint8)
    arr[:, :, 0:3] = [11, 22, 33]
    arr[:, :, 3] = 100
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.NOISE_ONLY
    settings.alpha.weak_alpha_threshold = 99
    settings.alpha.weak_alpha_action = WeakAlphaAction.DELETE_PIXEL
    settings.alpha.near_opaque_threshold_enabled = False

    result = clean_alpha(arr, ImageType.PHOTO, settings, report=None)

    assert np.array_equal(result.rgba, arr)


# --- Konfigurierbare Reihenfolge bei sich überschneidenden Schwellenwerten ---


def test_threshold_order_defaults_to_remove_first():
    settings = ProcessingSettings()
    assert settings.alpha.threshold_order == AlphaThresholdOrder.REMOVE_FIRST


def test_remove_first_order_deletes_overlapping_pixel():
    """Bei sich überschneidenden Schwellenwerten (weak >= near_opaque) gewinnt
    im Standardmodus REMOVE_FIRST die Löschung: das Pixel wird zuerst auf 0
    gesetzt, danach greift die Volldeckend-Prüfung nicht mehr (0 < near_opaque)."""
    arr = np.zeros((4, 4, 4), dtype=np.uint8)
    arr[:, :, 3] = 180  # erfüllt beide Bedingungen im überlappenden Bereich
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.NOISE_ONLY
    settings.alpha.weak_alpha_threshold = 200
    settings.alpha.near_opaque_threshold = 150
    settings.alpha.threshold_order = AlphaThresholdOrder.REMOVE_FIRST

    result = clean_alpha(arr, ImageType.PHOTO, settings, report=None)

    assert (result.rgba[:, :, 3] == 0).all()
    assert result.removed_pixel_count == 16
    assert result.strengthened_pixel_count == 0


def test_strengthen_first_order_keeps_overlapping_pixel_opaque():
    """Mit STRENGTHEN_FIRST wird dasselbe Pixel zuerst auf volle Deckkraft (255)
    gesetzt - danach ist es kein Kandidat mehr für die Löschung
    (255 > weak_alpha_threshold), bleibt also erhalten statt gelöscht zu werden."""
    arr = np.zeros((4, 4, 4), dtype=np.uint8)
    arr[:, :, 3] = 180
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.NOISE_ONLY
    settings.alpha.weak_alpha_threshold = 200
    settings.alpha.near_opaque_threshold = 150
    settings.alpha.threshold_order = AlphaThresholdOrder.STRENGTHEN_FIRST

    result = clean_alpha(arr, ImageType.PHOTO, settings, report=None)

    assert (result.rgba[:, :, 3] == 255).all()
    assert result.strengthened_pixel_count == 16
    assert result.removed_pixel_count == 0


def test_threshold_order_has_no_effect_without_overlapping_thresholds():
    """Bei nicht überschneidenden Schwellenwerten liefern beide Reihenfolgen
    dasselbe Ergebnis. Seit dem aggressiveren Standardwert für "geringe
    Deckkraft bearbeiten" (254) überschneiden sich die STANDARD-Schwellenwerte
    (254/242) tatsächlich - hier daher bewusst ein niedrigerer, nicht
    überschneidender Wert (100 < 242) gesetzt."""
    arr = np.zeros((8, 8, 4), dtype=np.uint8)
    arr[:, :, 3] = 150
    arr[0, 0, 3] = 3
    arr[0, 1, 3] = 250

    results = {}
    for order in AlphaThresholdOrder:
        settings = ProcessingSettings()
        settings.alpha_mode = AlphaMode.NOISE_ONLY
        settings.alpha.weak_alpha_threshold = 100
        settings.alpha.threshold_order = order
        results[order] = clean_alpha(arr, ImageType.PHOTO, settings, report=None).rgba[:, :, 3]

    assert np.array_equal(results[AlphaThresholdOrder.REMOVE_FIRST], results[AlphaThresholdOrder.STRENGTHEN_FIRST])


def test_threshold_order_also_applies_in_soft_cleanup_mode():
    """_apply_soft_cleanup nutzt denselben gemeinsamen Reihenfolge-Mechanismus."""
    arr = np.zeros((4, 4, 4), dtype=np.uint8)
    arr[:, :, 3] = 180
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.SOFT_CLEANUP
    settings.alpha.weak_alpha_threshold = 200
    settings.alpha.near_opaque_threshold = 150
    settings.alpha.threshold_order = AlphaThresholdOrder.STRENGTHEN_FIRST

    result = clean_alpha(arr, ImageType.ILLUSTRATION, settings, report=None)

    assert (result.rgba[:, :, 3] == 255).all()


def test_disabling_one_threshold_does_not_affect_the_other():
    arr = np.zeros((8, 8, 4), dtype=np.uint8)
    arr[0, 0, 3] = 3  # sollte weiterhin geloescht werden
    arr[1, 1, 3] = 250  # sollte NICHT mehr volldeckend gemacht werden
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.NOISE_ONLY
    settings.alpha.weak_alpha_threshold = 241  # nicht der (jetzt aggressivere) Standardwert 254
    settings.alpha.near_opaque_threshold_enabled = False

    result = clean_alpha(arr, ImageType.PHOTO, settings, report=None)

    assert result.rgba[0, 0, 3] == 0
    assert result.rgba[1, 1, 3] == 250
    assert result.removed_pixel_count == 1
    assert result.strengthened_pixel_count == 0
