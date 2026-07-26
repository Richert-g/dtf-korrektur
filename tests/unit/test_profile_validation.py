from pathlib import Path

from src.core.color.profile_validation import find_profile_by_description_fragment, validate_cmyk_output_profile

_CMYK_PROFILE = Path("resources/profiles/CMYK/CoatedFOGRA39.icc")
_RGB_PROFILE = Path("resources/profiles/RGB/AdobeRGB1998.icc")


def test_valid_cmyk_profile_passes():
    result = validate_cmyk_output_profile(_CMYK_PROFILE)
    assert result.ok is True
    assert result.color_space == "CMYK"
    assert "FOGRA39" in (result.description or "")
    assert result.device_class == "prtr"


def test_rgb_profile_rejected_as_cmyk_target():
    result = validate_cmyk_output_profile(_RGB_PROFILE)
    assert result.ok is False
    assert "RGB" in result.error
    assert result.color_space == "RGB"


def test_missing_file_rejected():
    result = validate_cmyk_output_profile(Path("this/file/does/not/exist.icc"))
    assert result.ok is False
    assert "nicht gefunden" in result.error


def test_non_icc_extension_rejected():
    result = validate_cmyk_output_profile(Path("requirements.txt"))
    assert result.ok is False
    assert ".icc" in result.error or ".icm" in result.error


def test_corrupted_icc_bytes_rejected(tmp_path: Path):
    bad_file = tmp_path / "broken.icc"
    bad_file.write_bytes(b"NOT_A_VALID_ICC_PROFILE_" + b"\x00" * 32)
    result = validate_cmyk_output_profile(bad_file)
    assert result.ok is False
    assert "beschädigt" in result.error or "kein gültiges" in result.error


def test_find_profile_by_description_fragment_finds_unique_match(monkeypatch):
    from src.core.color import profile_validation as pv

    def fake_validate(path):
        if path == Path("fake_iso_coated_v2.icc"):
            return pv.ProfileValidationResult(ok=True, path=path, description="ISO Coated v2 (ECI)", color_space="CMYK")
        return pv.ProfileValidationResult(ok=True, path=path, description="Some Other Profile", color_space="CMYK")

    monkeypatch.setattr(pv, "validate_cmyk_output_profile", fake_validate)
    found = find_profile_by_description_fragment(
        [Path("fake_iso_coated_v2.icc"), Path("other.icc")], "iso coated v2"
    )
    assert found == Path("fake_iso_coated_v2.icc")


def test_find_profile_by_description_fragment_returns_none_without_match():
    # Realer Bestand ohne "ISO Coated v2": darf NIEMALS ein ähnlich benanntes
    # Profil wie FOGRA39 als Ersatz zurückgeben.
    found = find_profile_by_description_fragment([_CMYK_PROFILE, _RGB_PROFILE], "iso coated v2")
    assert found is None
