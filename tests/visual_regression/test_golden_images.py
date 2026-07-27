"""Visuelle Regressionstests: laufen die echte Verarbeitungspipeline auf
festen synthetischen Bildern und vergleichen das Ergebnis pixelweise gegen
ein eingechecktes Referenzbild (siehe golden_utils.py). Sollen unbeabsichtigte
Qualitätsänderungen zwischen Versionen auffangen, die reine Logik-Tests
(z. B. test_alpha_cleanup.py) nicht abdecken, weil sie nur einzelne Aspekte
isoliert prüfen statt des vollständigen End-zu-End-Ergebnisses.
"""
from tests.visual_regression.golden_utils import assert_matches_golden, run_scenario


def test_hard_logo_white_halo_matches_golden(tmp_path):
    result = run_scenario("hard_logo_white_halo", tmp_path)
    assert_matches_golden(result, "hard_logo_white_halo")


def test_illustration_soft_cleanup_matches_golden(tmp_path):
    result = run_scenario("illustration_soft_cleanup", tmp_path)
    assert_matches_golden(result, "illustration_soft_cleanup")


def test_soft_shadow_auto_protection_matches_golden(tmp_path):
    result = run_scenario("soft_shadow_auto_protection", tmp_path)
    assert_matches_golden(result, "soft_shadow_auto_protection")


def test_small_islands_hard_edge_matches_golden(tmp_path):
    result = run_scenario("small_islands_hard_edge", tmp_path)
    assert_matches_golden(result, "small_islands_hard_edge")


def test_transparent_holes_hard_edge_matches_golden(tmp_path):
    result = run_scenario("transparent_holes_hard_edge", tmp_path)
    assert_matches_golden(result, "transparent_holes_hard_edge")


def test_saturated_motif_fogra39_matches_golden(tmp_path):
    result = run_scenario("saturated_motif_fogra39", tmp_path)
    assert_matches_golden(result, "saturated_motif_fogra39")
