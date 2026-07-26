from pathlib import Path

import numpy as np
import pytest

from src.core.export.pdf_export import PdfExportError, export_cmyk_pdf, validate_cmyk_pdf

_FAKE_ICC = b"NOT_A_REAL_ICC_STREAM_BUT_VALID_BYTES_0123456789"


def _sample_cmyk(w=6, h=4):
    cmyk = np.zeros((h, w, 4), dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            cmyk[y, x] = [x * 10, y * 10, 50, 0]
    cmyk[0, 0] = [255, 0, 0, 0]
    cmyk[h - 1, w - 1] = [0, 255, 0, 0]
    return cmyk


def test_export_creates_single_page_pdf_with_correct_size(tmp_path: Path):
    cmyk = _sample_cmyk()
    alpha = np.full(cmyk.shape[:2], 255, dtype=np.uint8)
    out = tmp_path / "out.pdf"

    has_smask = export_cmyk_pdf(cmyk, alpha, _FAKE_ICC, "Test Profile", 30.0, 20.0, out)
    assert has_smask is False
    assert out.exists()

    result = validate_cmyk_pdf(out, cmyk.shape[1::-1], (30.0, 20.0), "Test Profile", expect_transparency=False)
    assert result.ok, result.errors
    assert result.page_count == 1
    assert result.is_cmyk is True
    assert result.has_smask is False


def test_export_with_transparency_creates_smask(tmp_path: Path):
    cmyk = _sample_cmyk()
    alpha = np.full(cmyk.shape[:2], 255, dtype=np.uint8)
    alpha[0, 0] = 0
    alpha[1, 1] = 128
    out = tmp_path / "out_alpha.pdf"

    has_smask = export_cmyk_pdf(cmyk, alpha, _FAKE_ICC, "Test Profile", 10.0, 10.0, out)
    assert has_smask is True

    result = validate_cmyk_pdf(
        out, cmyk.shape[1::-1], (10.0, 10.0), "Test Profile", expect_transparency=True, expected_cmyk=cmyk
    )
    assert result.ok, result.errors
    assert result.has_smask is True
    assert result.not_mirrored is True


def test_pixel_data_round_trips_exactly_no_mirroring(tmp_path: Path):
    cmyk = _sample_cmyk(w=8, h=5)
    alpha = np.full(cmyk.shape[:2], 255, dtype=np.uint8)
    out = tmp_path / "roundtrip.pdf"
    export_cmyk_pdf(cmyk, alpha, _FAKE_ICC, "Test Profile", 40.0, 25.0, out)

    result = validate_cmyk_pdf(
        out, cmyk.shape[1::-1], (40.0, 25.0), "Test Profile", expect_transparency=False, expected_cmyk=cmyk
    )
    assert result.not_mirrored is True
    assert result.pixel_dimensions_match is True


def test_output_intent_embedded_with_icc_bytes(tmp_path: Path):
    cmyk = _sample_cmyk()
    alpha = np.full(cmyk.shape[:2], 255, dtype=np.uint8)
    out = tmp_path / "outintent.pdf"
    export_cmyk_pdf(cmyk, alpha, _FAKE_ICC, "Test Profile", 10.0, 10.0, out)

    result = validate_cmyk_pdf(out, cmyk.shape[1::-1], (10.0, 10.0), "Test Profile", expect_transparency=False)
    assert result.icc_profile_embedded is True


def test_alpha_shape_mismatch_raises():
    cmyk = _sample_cmyk()
    bad_alpha = np.zeros((2, 2), dtype=np.uint8)
    with pytest.raises(PdfExportError):
        export_cmyk_pdf(cmyk, bad_alpha, _FAKE_ICC, "Test Profile", 10.0, 10.0, Path("unused.pdf"))


def test_wrong_channel_count_raises():
    bad_cmyk = np.zeros((4, 4, 3), dtype=np.uint8)
    alpha = np.full((4, 4), 255, dtype=np.uint8)
    with pytest.raises(PdfExportError):
        export_cmyk_pdf(bad_cmyk, alpha, _FAKE_ICC, "Test Profile", 10.0, 10.0, Path("unused.pdf"))


def test_validate_reports_error_for_missing_file(tmp_path: Path):
    result = validate_cmyk_pdf(tmp_path / "does_not_exist.pdf", (4, 4), (10.0, 10.0), "x", expect_transparency=False)
    assert result.ok is False
    assert result.errors


def test_validate_detects_wrong_transparency_expectation(tmp_path: Path):
    cmyk = _sample_cmyk()
    alpha = np.full(cmyk.shape[:2], 255, dtype=np.uint8)  # keine Transparenz
    out = tmp_path / "no_transparency.pdf"
    export_cmyk_pdf(cmyk, alpha, _FAKE_ICC, "Test Profile", 10.0, 10.0, out)

    result = validate_cmyk_pdf(out, cmyk.shape[1::-1], (10.0, 10.0), "Test Profile", expect_transparency=True)
    assert result.ok is False
    assert any("SMask" in e for e in result.errors)
