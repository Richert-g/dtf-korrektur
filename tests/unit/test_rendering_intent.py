from src.config.defaults import ColorManagementSettings, GamutThresholds
from src.core.color.rendering_intent import select_rendering_intent
from src.models.enums import ImageType, RenderingIntent

COLOR_CFG = ColorManagementSettings()
GAMUT_CFG = GamutThresholds()


def test_photo_defaults_to_perceptual():
    intent, _ = select_rendering_intent(ImageType.PHOTO, 1.0, COLOR_CFG, GAMUT_CFG)
    assert intent == RenderingIntent.PERCEPTUAL


def test_logo_defaults_to_relative_colorimetric():
    intent, _ = select_rendering_intent(ImageType.HARD_LOGO, 1.0, COLOR_CFG, GAMUT_CFG)
    assert intent == RenderingIntent.RELATIVE_COLORIMETRIC


def test_high_out_of_gamut_forces_perceptual_even_for_logo():
    high_pct = GAMUT_CFG.perceptual_preference_threshold_pct + 5
    intent, reason = select_rendering_intent(ImageType.HARD_LOGO, high_pct, COLOR_CFG, GAMUT_CFG)
    assert intent == RenderingIntent.PERCEPTUAL
    assert "Farbraum" in reason or "Zielfarbraum" in reason


def test_manual_intent_overrides_auto_selection():
    manual_cfg = ColorManagementSettings(auto_select_intent=False, rendering_intent=RenderingIntent.SATURATION)
    intent, reason = select_rendering_intent(ImageType.PHOTO, 50.0, manual_cfg, GAMUT_CFG)
    assert intent == RenderingIntent.SATURATION
