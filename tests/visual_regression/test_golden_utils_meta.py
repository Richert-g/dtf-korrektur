"""Testet die Vergleichslogik der visuellen Regressionstests selbst (siehe
golden_utils.py) - stellt sicher, dass das Sicherheitsnetz tatsächlich
greift: eine echte Abweichung muss durchfallen, ein fehlendes Referenzbild
muss eine klare Fehlermeldung liefern, winzige/harmlose Abweichungen dürfen
dagegen nicht fälschlich durchfallen."""
import numpy as np
import pytest
from PIL import Image

from tests.visual_regression import golden_utils


@pytest.fixture(autouse=True)
def _isolated_golden_dir(tmp_path, monkeypatch):
    """Verhindert, dass diese Meta-Tests versehentlich die echten
    Referenzbilder unter tests/fixtures/golden/ lesen oder überschreiben."""
    monkeypatch.setattr(golden_utils, "GOLDEN_DIR", tmp_path)


def _save(arr: np.ndarray, name: str) -> None:
    Image.fromarray(arr, mode="RGBA").save(golden_utils.golden_path(name))


def test_identical_image_passes():
    arr = np.full((10, 10, 4), 128, dtype=np.uint8)
    _save(arr, "identical")

    golden_utils.assert_matches_golden(arr, "identical")  # darf nicht werfen


def test_tiny_deviation_below_threshold_passes():
    golden = np.full((10, 10, 4), 128, dtype=np.uint8)
    _save(golden, "tiny_diff")

    actual = golden.copy()
    actual[0, 0] = 129  # Abweichung von 1, unterhalb DEFAULT_MAX_PIXEL_DIFF

    golden_utils.assert_matches_golden(actual, "tiny_diff")  # darf nicht werfen


def test_large_deviation_fails():
    golden = np.full((10, 10, 4), 0, dtype=np.uint8)
    golden[:, :, 3] = 255
    _save(golden, "large_diff")

    actual = np.full((10, 10, 4), 255, dtype=np.uint8)  # komplett anders

    with pytest.raises(pytest.fail.Exception, match="Visuelle Regression"):
        golden_utils.assert_matches_golden(actual, "large_diff")


def test_deviation_just_above_fraction_threshold_fails():
    """Ein einzelner stark abweichender Pixel in einem großen Bild darf nicht
    durchfallen (Anteil zu klein) - abweicht der Anteil aber über die Grenze
    hinaus (hier: absichtlich 1 von 4 Pixeln in einem 2x2-Bild), muss der
    Test durchfallen."""
    golden = np.zeros((2, 2, 4), dtype=np.uint8)
    golden[:, :, 3] = 255
    _save(golden, "quarter_diff")

    actual = golden.copy()
    actual[0, 0] = [255, 255, 255, 255]  # 1 von 4 Pixeln = 25% Abweichung

    with pytest.raises(pytest.fail.Exception, match="Visuelle Regression"):
        golden_utils.assert_matches_golden(actual, "quarter_diff")


def test_size_mismatch_fails_with_clear_message():
    golden = np.zeros((10, 10, 4), dtype=np.uint8)
    _save(golden, "size_mismatch")

    actual = np.zeros((20, 20, 4), dtype=np.uint8)

    with pytest.raises(pytest.fail.Exception, match="Bildgröße weicht ab"):
        golden_utils.assert_matches_golden(actual, "size_mismatch")


def test_missing_golden_file_fails_with_actionable_message():
    actual = np.zeros((10, 10, 4), dtype=np.uint8)

    with pytest.raises(pytest.fail.Exception, match="Referenzbild fehlt"):
        golden_utils.assert_matches_golden(actual, "does_not_exist")


def test_end_to_end_pipeline_change_is_actually_detected(tmp_path):
    """Sanity-Check der gesamten Kette (nicht nur der Vergleichsfunktion
    isoliert): ein bewusst verfälschtes Referenzbild gegen das echte,
    aktuelle Pipeline-Ergebnis muss durchfallen - stellt sicher, dass der
    Mechanismus tatsächlich Regressionen aufdecken würde."""
    result = golden_utils.run_scenario("small_islands_hard_edge", tmp_path)

    faked_golden = 255 - result
    faked_golden[:, :, 3] = result[:, :, 3]
    _save(faked_golden, "small_islands_hard_edge")

    with pytest.raises(pytest.fail.Exception, match="Visuelle Regression"):
        golden_utils.assert_matches_golden(result, "small_islands_hard_edge")
