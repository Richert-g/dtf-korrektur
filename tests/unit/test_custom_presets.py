import pytest

from src.config.defaults import ProcessingSettings
from src.core.presets.custom_presets import (
    CustomPresetError,
    apply_custom_preset,
    delete_custom_preset,
    load_custom_presets,
    rename_custom_preset,
    save_custom_preset,
)
from src.models.enums import AlphaMode, PresetName


@pytest.fixture(autouse=True)
def _isolated_presets_file(tmp_path, monkeypatch):
    fake_file = tmp_path / "presets.json"
    monkeypatch.setattr("src.core.presets.custom_presets.get_presets_file", lambda: fake_file)
    return fake_file


def test_load_returns_empty_dict_when_no_file_exists():
    assert load_custom_presets() == {}


def test_save_and_load_roundtrip():
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.HARD_EDGE
    settings.alpha.weak_alpha_threshold = 111

    cleaned = save_custom_preset("Mein Preset", settings)

    assert cleaned == "Mein Preset"
    loaded = load_custom_presets()
    assert "Mein Preset" in loaded
    assert loaded["Mein Preset"].alpha_mode == AlphaMode.HARD_EDGE
    assert loaded["Mein Preset"].alpha.weak_alpha_threshold == 111


def test_save_trims_whitespace_from_name():
    cleaned = save_custom_preset("  Mit Leerzeichen  ", ProcessingSettings())
    assert cleaned == "Mit Leerzeichen"
    assert "Mit Leerzeichen" in load_custom_presets()


def test_save_rejects_empty_name():
    with pytest.raises(CustomPresetError, match="darf nicht leer sein"):
        save_custom_preset("   ", ProcessingSettings())


def test_save_rejects_reserved_builtin_name():
    with pytest.raises(CustomPresetError, match="eingebauten Presets"):
        save_custom_preset(PresetName.DTF_AUTO.value, ProcessingSettings())


def test_save_rejects_duplicate_name_without_overwrite():
    save_custom_preset("Foo", ProcessingSettings())
    with pytest.raises(CustomPresetError, match="existiert bereits"):
        save_custom_preset("Foo", ProcessingSettings())


def test_save_duplicate_name_case_insensitive_without_overwrite():
    save_custom_preset("Foo", ProcessingSettings())
    with pytest.raises(CustomPresetError, match="existiert bereits"):
        save_custom_preset("foo", ProcessingSettings())


def test_save_with_overwrite_replaces_existing_entry():
    settings_a = ProcessingSettings()
    settings_a.alpha.weak_alpha_threshold = 100
    save_custom_preset("Foo", settings_a)

    settings_b = ProcessingSettings()
    settings_b.alpha.weak_alpha_threshold = 200
    save_custom_preset("Foo", settings_b, overwrite=True)

    loaded = load_custom_presets()
    assert len(loaded) == 1
    assert loaded["Foo"].alpha.weak_alpha_threshold == 200


def test_delete_removes_entry():
    save_custom_preset("Foo", ProcessingSettings())
    delete_custom_preset("Foo")
    assert load_custom_presets() == {}


def test_delete_raises_for_unknown_name():
    with pytest.raises(CustomPresetError, match="existiert nicht"):
        delete_custom_preset("Unbekannt")


def test_rename_renames_entry_and_keeps_settings():
    settings = ProcessingSettings()
    settings.alpha.weak_alpha_threshold = 77
    save_custom_preset("Alt", settings)

    cleaned = rename_custom_preset("Alt", "Neu")

    assert cleaned == "Neu"
    loaded = load_custom_presets()
    assert "Alt" not in loaded
    assert "Neu" in loaded
    assert loaded["Neu"].alpha.weak_alpha_threshold == 77


def test_rename_raises_for_unknown_old_name():
    with pytest.raises(CustomPresetError, match="existiert nicht"):
        rename_custom_preset("Unbekannt", "Neu")


def test_rename_raises_when_new_name_collides_with_other_preset():
    save_custom_preset("A", ProcessingSettings())
    save_custom_preset("B", ProcessingSettings())
    with pytest.raises(CustomPresetError, match="existiert bereits"):
        rename_custom_preset("A", "B")


def test_rename_allows_case_only_change():
    save_custom_preset("foo", ProcessingSettings())
    cleaned = rename_custom_preset("foo", "Foo")
    assert cleaned == "Foo"
    assert set(load_custom_presets()) == {"Foo"}


def test_rename_rejects_reserved_new_name():
    save_custom_preset("Alt", ProcessingSettings())
    with pytest.raises(CustomPresetError, match="eingebauten Presets"):
        rename_custom_preset("Alt", PresetName.DTF_AUTO.value)


def test_corrupted_presets_file_is_ignored_gracefully(_isolated_presets_file):
    _isolated_presets_file.write_text("{not valid json", encoding="utf-8")
    assert load_custom_presets() == {}


def test_one_malformed_entry_does_not_break_loading_others(_isolated_presets_file):
    import json

    from src.config.config_manager import settings_to_dict

    good = settings_to_dict(ProcessingSettings())
    _isolated_presets_file.write_text(
        json.dumps({"Gut": good, "Kaputt": {"alpha_mode": "does_not_exist_as_enum_value"}}), encoding="utf-8"
    )

    loaded = load_custom_presets()
    assert "Gut" in loaded
    assert "Kaputt" not in loaded


def test_apply_custom_preset_mutates_in_place():
    live = ProcessingSettings()
    custom = ProcessingSettings()
    custom.alpha_mode = AlphaMode.SOFT_CLEANUP
    custom.alpha.weak_alpha_threshold = 55
    custom.halo.enabled = False

    apply_custom_preset(live, custom)

    assert live.alpha_mode == AlphaMode.SOFT_CLEANUP
    assert live.alpha.weak_alpha_threshold == 55
    assert live.halo.enabled is False


def test_apply_custom_preset_preserves_object_identity():
    live = ProcessingSettings()
    identity = id(live)
    custom = ProcessingSettings()
    custom.alpha_mode = AlphaMode.HARD_EDGE

    apply_custom_preset(live, custom)

    assert id(live) == identity
    assert live.alpha_mode == AlphaMode.HARD_EDGE
