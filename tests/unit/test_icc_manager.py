from pathlib import Path

import pytest

from src.core.color.icc_manager import (
    ICCProfileError,
    get_srgb_icc_bytes,
    get_srgb_profile,
    import_profile,
    list_available_profiles,
    load_icc_profile,
    load_icc_profile_from_bytes,
    profile_color_space,
    profile_description,
)
from tests.fixtures.synthetic_images import make_invalid_icc_bytes


def test_srgb_profile_available():
    profile = get_srgb_profile()
    assert profile_color_space(profile) == "RGB"
    assert len(get_srgb_icc_bytes()) > 0


def test_load_valid_icc_bytes():
    data = get_srgb_icc_bytes()
    profile = load_icc_profile_from_bytes(data)
    assert profile is not None
    assert "sRGB" in profile_description(profile) or profile_description(profile)


def test_load_invalid_icc_bytes_returns_none():
    profile = load_icc_profile_from_bytes(make_invalid_icc_bytes())
    assert profile is None


def test_load_icc_profile_from_missing_file(tmp_path: Path):
    profile = load_icc_profile(tmp_path / "does_not_exist.icc")
    assert profile is None


def test_import_profile_copies_and_validates(tmp_path, monkeypatch):
    icc_path = tmp_path / "source" / "MyProfile.icc"
    icc_path.parent.mkdir(parents=True)
    icc_path.write_bytes(get_srgb_icc_bytes())

    user_profiles_dir = tmp_path / "user_profiles"
    monkeypatch.setattr("src.core.color.icc_manager.get_user_profiles_dir", lambda: user_profiles_dir)
    user_profiles_dir.mkdir(parents=True, exist_ok=True)

    info = import_profile(icc_path, display_name="Test DTF Profil")
    assert info.path.exists()
    assert info.path.parent == user_profiles_dir


def test_import_invalid_profile_raises(tmp_path, monkeypatch):
    bad_path = tmp_path / "broken.icc"
    bad_path.write_bytes(make_invalid_icc_bytes())

    user_profiles_dir = tmp_path / "user_profiles"
    monkeypatch.setattr("src.core.color.icc_manager.get_user_profiles_dir", lambda: user_profiles_dir)

    with pytest.raises(ICCProfileError):
        import_profile(bad_path)


def test_import_non_icc_extension_raises(tmp_path):
    bad_path = tmp_path / "notaprofile.txt"
    bad_path.write_text("hello")
    with pytest.raises(ICCProfileError):
        import_profile(bad_path)


def test_list_available_profiles_finds_imported(tmp_path, monkeypatch):
    user_profiles_dir = tmp_path / "user_profiles"
    user_profiles_dir.mkdir(parents=True, exist_ok=True)
    bundled_dir = tmp_path / "bundled_empty"
    monkeypatch.setattr("src.core.color.icc_manager.get_user_profiles_dir", lambda: user_profiles_dir)
    monkeypatch.setattr("src.core.color.icc_manager.get_profiles_dir", lambda: bundled_dir)

    (user_profiles_dir / "custom.icc").write_bytes(get_srgb_icc_bytes())
    profiles = list_available_profiles()
    assert any(p.path.name == "custom.icc" for p in profiles)
