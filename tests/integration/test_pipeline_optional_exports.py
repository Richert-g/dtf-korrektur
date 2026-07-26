from pathlib import Path

import numpy as np

from src.config.defaults import ProcessingSettings
from src.core.color.icc_manager import get_srgb_icc_bytes
from src.core.pipeline import process_image
from tests.fixtures.synthetic_images import make_logo_with_white_halo


def test_white_mask_export_creates_file(tmp_path: Path):
    src_path = tmp_path / "logo.png"
    make_logo_with_white_halo().save(src_path)
    output_root = tmp_path / "output"

    settings = ProcessingSettings()
    settings.export.write_white_mask = True

    report = process_image(src_path, settings, output_root)
    white_mask_path = output_root / "masks" / "logo_white_mask.png"
    assert white_mask_path.exists()
    assert any("Weißunterlegung" in s.description for s in report.applied_steps)


def test_cmyk_export_skipped_without_target_profile(tmp_path: Path):
    src_path = tmp_path / "logo.png"
    make_logo_with_white_halo().save(src_path)
    output_root = tmp_path / "output"

    settings = ProcessingSettings()
    settings.export.write_cmyk_tiff = True
    settings.color.target_profile_path = None

    report = process_image(src_path, settings, output_root)
    cmyk_path = output_root / "optimized" / "logo_dtf_cmyk_preview.tiff"
    assert not cmyk_path.exists()
    assert any("druckfertige" in w for w in report.warnings)


def test_cmyk_export_with_non_cmyk_profile_fails_gracefully(tmp_path: Path):
    """Kein CMYK-ICC-Profil im Testsystem verfügbar: ein RGB-Profil als Ziel darf

    beim CMYK-Export nicht abstürzen, sondern nur eine Warnung erzeugen
    (Prompt Abschnitt 9: defekte/inkompatible Profile dürfen nicht crashen).
    """
    src_path = tmp_path / "logo.png"
    make_logo_with_white_halo().save(src_path)
    output_root = tmp_path / "output"

    target_icc_path = tmp_path / "target.icc"
    target_icc_path.write_bytes(get_srgb_icc_bytes())

    settings = ProcessingSettings()
    settings.export.write_cmyk_tiff = True
    settings.color.target_profile_path = str(target_icc_path)

    report = process_image(src_path, settings, output_root)
    cmyk_path = output_root / "optimized" / "logo_dtf_cmyk_preview.tiff"
    assert report.success is True  # Hauptverarbeitung darf trotzdem gelingen
    if not cmyk_path.exists():
        assert any("CMYK" in w for w in report.warnings)


def test_softproof_export_created_when_target_profile_set(tmp_path: Path):
    src_path = tmp_path / "logo.png"
    make_logo_with_white_halo().save(src_path)
    output_root = tmp_path / "output"

    target_icc_path = tmp_path / "target.icc"
    target_icc_path.write_bytes(get_srgb_icc_bytes())

    settings = ProcessingSettings()
    settings.color.target_profile_path = str(target_icc_path)

    process_image(src_path, settings, output_root)
    softproof_path = output_root / "previews" / "logo_softproof.png"
    assert softproof_path.exists()


def test_gamut_warning_skipped_without_out_of_gamut_pixels(tmp_path: Path):
    """sRGB->sRGB-Rundreise hat praktisch keine Out-of-Gamut-Pixel -> keine Datei."""
    src_path = tmp_path / "logo.png"
    make_logo_with_white_halo().save(src_path)
    output_root = tmp_path / "output"

    target_icc_path = tmp_path / "target.icc"
    target_icc_path.write_bytes(get_srgb_icc_bytes())

    settings = ProcessingSettings()
    settings.color.target_profile_path = str(target_icc_path)

    process_image(src_path, settings, output_root)
    gamut_path = output_root / "previews" / "logo_gamut_warning.png"
    assert not gamut_path.exists()


def test_gamut_warning_exported_when_out_of_gamut_pixels_present(tmp_path: Path, monkeypatch):
    """Testet die Export-Verdrahtung isoliert von der echten ICC-Transformation,

    da im Testsystem kein enges Referenzprofil verfügbar ist (siehe
    docs/color-management.md, bekannte Einschränkung).
    """
    from src.core.color.color_pipeline import ColorProcessingInfo

    src_path = tmp_path / "logo.png"
    make_logo_with_white_halo().save(src_path)
    output_root = tmp_path / "output"

    target_icc_path = tmp_path / "target.icc"
    target_icc_path.write_bytes(get_srgb_icc_bytes())

    settings = ProcessingSettings()
    settings.color.target_profile_path = str(target_icc_path)

    def fake_optimize_colors(array, loaded, settings_, report):
        mask = np.zeros(array.shape[:2], dtype=bool)
        mask[10:20, 10:20] = True
        info = ColorProcessingInfo(
            source_profile_name="sRGB",
            target_profile_name="Test",
            target_icc_bytes=None,
            has_valid_target_profile=True,
            out_of_gamut_mask=mask,
        )
        report.out_of_gamut_before = 5.0
        report.out_of_gamut_after = 1.0
        return array, info

    monkeypatch.setattr(
        "src.core.color.color_pipeline.optimize_colors", fake_optimize_colors
    )

    report = process_image(src_path, settings, output_root)
    gamut_path = output_root / "previews" / "logo_gamut_warning.png"
    assert gamut_path.exists()
    assert any("Gamut-Warnung" in s.description for s in report.applied_steps)
