from src.config.defaults import ProcessingSettings
from src.core.presets.presets import PRESET_DESCRIPTIONS, apply_preset
from src.models.enums import AlphaMode, PresetName


def test_all_presets_have_descriptions():
    for preset in PresetName:
        assert preset in PRESET_DESCRIPTIONS
        assert len(PRESET_DESCRIPTIONS[preset]) > 0


def test_logo_preset_sets_hard_edge():
    s = ProcessingSettings()
    apply_preset(s, PresetName.DTF_LOGO_TEXT)
    assert s.alpha_mode == AlphaMode.HARD_EDGE


def test_photo_preset_sets_noise_only_and_disables_auto_intent():
    s = ProcessingSettings()
    apply_preset(s, PresetName.DTF_PHOTO)
    assert s.alpha_mode == AlphaMode.NOISE_ONLY
    assert s.color.auto_select_intent is False


def test_transparency_only_clears_target_profile():
    s = ProcessingSettings()
    s.color.target_profile_path = "/some/profile.icc"
    apply_preset(s, PresetName.TRANSPARENCY_ONLY)
    assert s.color.target_profile_path is None


def test_color_only_disables_alpha_and_halo_effect():
    s = ProcessingSettings()
    apply_preset(s, PresetName.COLOR_ONLY)
    assert s.alpha.weak_alpha_threshold == 0
    assert s.halo.enabled is False


def test_custom_preset_does_not_modify_settings():
    s = ProcessingSettings()
    s.alpha_mode = AlphaMode.HARD_EDGE
    apply_preset(s, PresetName.CUSTOM)
    assert s.alpha_mode == AlphaMode.HARD_EDGE
