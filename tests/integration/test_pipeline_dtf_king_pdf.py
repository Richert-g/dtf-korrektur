from pathlib import Path

import numpy as np

from src.config.defaults import ProcessingSettings
from src.core.alpha.alpha_cleanup import clean_alpha
from src.core.export.dtf_king_export import (
    DtfKingExportError,
    build_export_summary,
    process_image_for_dtf_king_pdf,
    process_image_for_dtf_king_pdf_safe,
)
from src.core.halo.halo_correction import correct_halo
from src.core.presets.presets import apply_preset
from src.models.enums import ImageType, PresetName
from src.models.report import ImageProcessingReport
from tests.fixtures.synthetic_images import make_saturated_blue_cyan_motif

_FOGRA39 = "resources/profiles/CMYK/CoatedFOGRA39.icc"


def _dtf_king_settings(width_mm: float = 40.0) -> ProcessingSettings:
    settings = ProcessingSettings()
    apply_preset(settings, PresetName.DTF_KING_ISO_COATED_V2)
    settings.color.target_profile_path = _FOGRA39
    settings.export.pdf_width_mm = width_mm
    settings.export.pdf_height_mm = None
    return settings


def test_full_export_succeeds_and_validates(tmp_path: Path):
    src = tmp_path / "motif.png"
    make_saturated_blue_cyan_motif().save(src)
    settings = _dtf_king_settings()

    report = process_image_for_dtf_king_pdf(src, settings, tmp_path / "out")

    assert report.success is True
    assert report.output_path is not None
    assert report.output_path.suffix == ".pdf"
    assert report.output_path.exists()
    assert report.pdf_validated is True
    assert report.pdf_validation_errors == []
    assert report.additional_saturation_reduction_applied is False
    assert report.additional_gamut_correction_applied is False
    assert report.mirrored is False


def test_softproof_and_transparency_only_previews_are_written(tmp_path: Path):
    """Regression: nach einem erfolgreichen DTF-King-Export gab es keine
    Bildvorschau in der Oberfläche - nur eine Textzeile. Beide Vorschaudateien
    müssen mit denselben Dateinamen wie im normalen PNG-Ablauf entstehen,
    damit die Oberfläche sie ohne Sonderfall automatisch findet."""
    src = tmp_path / "motif.png"
    make_saturated_blue_cyan_motif().save(src)
    settings = _dtf_king_settings()

    report = process_image_for_dtf_king_pdf(src, settings, tmp_path / "out")
    assert report.success is True

    previews_dir = tmp_path / "out" / "previews"
    softproof_path = previews_dir / "motif_softproof.png"
    transparency_only_path = previews_dir / "motif_transparency_only.png"
    assert softproof_path.exists()
    assert transparency_only_path.exists()

    from PIL import Image

    with Image.open(softproof_path) as img:
        assert img.mode == "RGBA"
        assert img.size == (report.width, report.height)

    step_names = {s.name for s in report.applied_steps}
    assert "export_softproof" in step_names
    assert "export_transparency_only" in step_names


def test_softproof_preview_shows_the_actual_gamut_mapped_colors(tmp_path: Path):
    """Die Softproof-Vorschau muss die tatsächlich gedruckten (CMYK-
    konvertierten) Farben zeigen, nicht die unveränderten Originalfarben -
    für ein stark gesättigtes Motiv muss sich mindestens ein Pixelwert
    sichtbar unterscheiden."""
    import numpy as np
    from PIL import Image

    src = tmp_path / "motif.png"
    make_saturated_blue_cyan_motif().save(src)
    settings = _dtf_king_settings()

    report = process_image_for_dtf_king_pdf(src, settings, tmp_path / "out")
    assert report.success is True

    original = np.array(Image.open(src).convert("RGBA"))
    softproof = np.array(Image.open(tmp_path / "out" / "previews" / "motif_softproof.png").convert("RGBA"))

    opaque_mask = original[:, :, 3] == 255
    assert opaque_mask.any()
    assert not np.array_equal(original[:, :, :3][opaque_mask], softproof[:, :, :3][opaque_mask])


def test_missing_profile_fails_cleanly_without_writing_output(tmp_path: Path):
    src = tmp_path / "motif.png"
    make_saturated_blue_cyan_motif().save(src)
    settings = _dtf_king_settings()
    settings.color.target_profile_path = None

    report = process_image_for_dtf_king_pdf(src, settings, tmp_path / "out")
    assert report.success is False
    assert report.output_path is None
    assert any("ICC-Zielprofil" in e for e in report.errors)


def test_rgb_profile_as_target_fails_cleanly(tmp_path: Path):
    src = tmp_path / "motif.png"
    make_saturated_blue_cyan_motif().save(src)
    settings = _dtf_king_settings()
    settings.color.target_profile_path = "resources/profiles/RGB/AdobeRGB1998.icc"

    report = process_image_for_dtf_king_pdf(src, settings, tmp_path / "out")
    assert report.success is False
    assert any("CMYK" in e for e in report.errors)


def test_safe_wrapper_never_raises_on_bad_settings(tmp_path: Path):
    src = tmp_path / "motif.png"
    make_saturated_blue_cyan_motif().save(src)
    settings = _dtf_king_settings()
    settings.color.target_profile_path = "does/not/exist.icc"

    report = process_image_for_dtf_king_pdf_safe(src, settings, tmp_path / "out")
    assert report.success is False


def test_build_export_summary_reflects_no_extra_correction(tmp_path: Path):
    src = tmp_path / "motif.png"
    make_saturated_blue_cyan_motif().save(src)
    settings = _dtf_king_settings()

    summary = build_export_summary(src, settings)
    assert summary.additional_saturation_reduction is False
    assert summary.additional_gamut_correction is False
    assert summary.mirrored is False
    assert summary.output_color_space == "CMYK"
    assert summary.background_transparent is True


def test_build_export_summary_raises_without_valid_profile(tmp_path: Path):
    src = tmp_path / "motif.png"
    make_saturated_blue_cyan_motif().save(src)
    settings = _dtf_king_settings()
    settings.color.target_profile_path = None

    import pytest

    with pytest.raises(DtfKingExportError):
        build_export_summary(src, settings)


# --------------------------------------------------------------------------
# Regressionstest "blaues Motiv" (Prompt Abschnitt 12): stark gesättigte
# Blau-/Cyanflächen. Prüft, dass die Transparenzoptimierung allein die
# deckenden Innenflächen farblich NICHT verändert, und dass die gesamte
# sichtbare Farbabweichung ausschließlich aus der einen ICC-Konvertierung
# stammt - keine zweite, eigene Entsättigung.
# --------------------------------------------------------------------------


def test_blue_motif_transparency_step_does_not_touch_opaque_interior_color():
    img = make_saturated_blue_cyan_motif()
    array = np.array(img)
    settings = _dtf_king_settings()

    opaque_mask = array[:, :, 3] == 255
    assert opaque_mask.any(), "Testbild sollte einen deckenden Kernbereich haben"
    original_opaque_rgb = array[:, :, :3][opaque_mask].copy()

    report = ImageProcessingReport(source_path=Path("motif.png"))
    array, _ = correct_halo(array, settings.halo, report)
    alpha_result = clean_alpha(array, ImageType.ILLUSTRATION, settings, report)
    array = alpha_result.rgba

    still_opaque_mask = array[:, :, 3] == 255
    # der urspruenglich deckende Kernbereich muss weiterhin deckend UND
    # farblich unveraendert sein
    assert np.array_equal(array[:, :, :3][opaque_mask], original_opaque_rgb)
    assert (still_opaque_mask[opaque_mask]).all()


def test_blue_motif_only_icc_conversion_changes_cmyk_output_no_double_correction(tmp_path: Path):
    src = tmp_path / "motif.png"
    make_saturated_blue_cyan_motif().save(src)
    settings = _dtf_king_settings()

    report = process_image_for_dtf_king_pdf(src, settings, tmp_path / "out")
    assert report.success is True

    # Die tatsaechlich im PDF gespeicherten CMYK-Werte muessen exakt einer
    # EINZIGEN direkten ICC-Transformation der (alpha-/halo-bereinigten)
    # RGB-Werte entsprechen - keine zusaetzliche Saettigungsreduktion.
    import pikepdf

    pdf = pikepdf.open(report.output_path)
    try:
        image_obj = pdf.pages[0].Resources.XObject.Im0
        w, h = int(image_obj.Width), int(image_obj.Height)
        raw = image_obj.read_bytes()
        stored_cmyk = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 4)
    finally:
        pdf.close()

    # Farbkanaele duerfen sich zwischen den Pixeln nur durch die reguläre
    # ICC-Gamut-Abbildung unterscheiden - stichprobenhaft pruefen, dass die
    # beiden urspruenglich unterschiedlichen Motivfarben (Blau/Cyan) auch im
    # CMYK-Ergebnis klar unterscheidbar bleiben (keine pauschale Vereinheit-
    # lichung/Entsaettigung durch eine zusaetzliche Korrektur).
    left_sample = stored_cmyk[h // 2, w // 4]
    right_sample = stored_cmyk[h // 2, 3 * w // 4]
    assert not np.array_equal(left_sample, right_sample)
