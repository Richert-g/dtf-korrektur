import json

import pytest

from src.config.config_manager import settings_from_dict, settings_from_dict_strict, settings_to_dict
from src.config.defaults import ProcessingSettings
from src.models.enums import AlphaMode, AlphaThresholdOrder, RenderingIntent, WeakAlphaAction


def test_roundtrip_default_settings():
    settings = ProcessingSettings()
    data = settings_to_dict(settings)
    restored = settings_from_dict(data)

    assert restored.alpha_mode == settings.alpha_mode
    assert restored.alpha.weak_alpha_threshold == settings.alpha.weak_alpha_threshold
    assert restored.color.rendering_intent == settings.color.rendering_intent


def test_roundtrip_modified_settings():
    settings = ProcessingSettings()
    settings.alpha_mode = AlphaMode.HARD_EDGE
    settings.alpha.min_island_size_px = 42
    settings.color.rendering_intent = RenderingIntent.PERCEPTUAL

    data = settings_to_dict(settings)
    json_str = json.dumps(data)
    parsed = json.loads(json_str)
    restored = settings_from_dict(parsed)

    assert restored.alpha_mode == AlphaMode.HARD_EDGE
    assert restored.alpha.min_island_size_px == 42
    assert restored.color.rendering_intent == RenderingIntent.PERCEPTUAL


def test_roundtrip_check_for_updates_enabled():
    settings = ProcessingSettings()
    assert settings.check_for_updates_enabled is True
    settings.check_for_updates_enabled = False

    data = settings_to_dict(settings)
    json_str = json.dumps(data)
    restored = settings_from_dict(json.loads(json_str))

    assert restored.check_for_updates_enabled is False


def test_roundtrip_threshold_order():
    settings = ProcessingSettings()
    settings.alpha.threshold_order = AlphaThresholdOrder.STRENGTHEN_FIRST

    data = settings_to_dict(settings)
    json_str = json.dumps(data)
    restored = settings_from_dict(json.loads(json_str))

    assert restored.alpha.threshold_order == AlphaThresholdOrder.STRENGTHEN_FIRST


def test_roundtrip_weak_alpha_action():
    settings = ProcessingSettings()
    assert settings.alpha.weak_alpha_action == WeakAlphaAction.SET_TRANSPARENT
    settings.alpha.weak_alpha_action = WeakAlphaAction.DELETE_PIXEL

    data = settings_to_dict(settings)
    json_str = json.dumps(data)
    restored = settings_from_dict(json.loads(json_str))

    assert restored.alpha.weak_alpha_action == WeakAlphaAction.DELETE_PIXEL


def test_settings_from_dict_falls_back_to_defaults_on_malformed_data():
    restored = settings_from_dict({"alpha_mode": "does_not_exist_as_enum_value"})
    assert restored == ProcessingSettings()


def test_settings_from_dict_strict_raises_on_malformed_data():
    with pytest.raises(ValueError):
        settings_from_dict_strict({"alpha_mode": "does_not_exist_as_enum_value"})


def test_settings_to_dict_is_json_serializable():
    settings = ProcessingSettings()
    data = settings_to_dict(settings)
    # darf nicht werfen
    json.dumps(data)
