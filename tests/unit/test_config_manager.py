import json
from pathlib import Path

from src.config.config_manager import settings_from_dict, settings_to_dict
from src.config.defaults import ProcessingSettings
from src.models.enums import AlphaMode, RenderingIntent


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


def test_settings_to_dict_is_json_serializable():
    settings = ProcessingSettings()
    data = settings_to_dict(settings)
    # darf nicht werfen
    json.dumps(data)
