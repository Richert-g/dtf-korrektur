from src.config.defaults import ProcessingSettings
from src.core.presets.presets import apply_preset
from src.models.enums import OutputFormat, PresetName, RenderingIntent


def test_dtf_king_preset_disables_additional_correction():
    s = ProcessingSettings()
    apply_preset(s, PresetName.DTF_KING_ISO_COATED_V2)

    assert s.gamut.enable_auto_gamut_correction is False
    assert s.gamut.max_auto_saturation_reduction == 0.0
    assert s.color.auto_select_intent is False
    assert s.color.rendering_intent == RenderingIntent.RELATIVE_COLORIMETRIC
    assert s.color.black_point_compensation is True
    assert s.export.output_format == OutputFormat.PDF_CMYK
    assert s.export.pdf_target_dpi == 300.0
    assert s.export.pdf_allow_upscale is False


def test_switching_away_from_dtf_king_resets_pdf_only_fields():
    """Regression: nach einem Preset-Wechsel weg von DTF-King darf output_format
    (und die weiteren DTF-King-exklusiven Felder) nicht auf PDF_CMYK haengen
    bleiben - sonst wuerde 'Automatisch optimieren' bei jedem anderen Preset
    weiterhin versuchen, eine PDF statt einer PNG zu erzeugen."""
    s = ProcessingSettings()
    apply_preset(s, PresetName.DTF_KING_ISO_COATED_V2)
    assert s.export.output_format == OutputFormat.PDF_CMYK

    apply_preset(s, PresetName.DTF_AUTO)
    assert s.export.output_format == OutputFormat.PNG_RGB
    assert s.gamut.enable_auto_gamut_correction is True
    assert s.gamut.max_auto_saturation_reduction == 0.15


def test_dtf_king_preset_keeps_existing_alpha_halo_enabled():
    s = ProcessingSettings()
    apply_preset(s, PresetName.DTF_KING_ISO_COATED_V2)

    assert s.halo.enabled is True


def test_dtf_king_preset_keeps_already_selected_profile():
    """Der Benutzer kann im ICC-Zielprofil-Feld frei ein beliebiges CMYK-Profil
    waehlen (z. B. FOGRA39 oder ein importiertes 'ISO Coated v2 (ECI)') - das
    Preset darf ein bereits ausgewaehltes Profil nicht ueberschreiben/loeschen."""
    s = ProcessingSettings()
    s.color.target_profile_path = "resources/profiles/CMYK/CoatedFOGRA39.icc"
    apply_preset(s, PresetName.DTF_KING_ISO_COATED_V2)

    assert s.color.target_profile_path == "resources/profiles/CMYK/CoatedFOGRA39.icc"


def test_dtf_king_preset_defaults_to_fogra39_when_no_profile_selected():
    """Ist kein Zielprofil ausgewaehlt, wird automatisch das mitgelieferte
    Coated FOGRA39 als Standard gesetzt, statt den Export zu blockieren."""
    s = ProcessingSettings()
    assert s.color.target_profile_path is None
    apply_preset(s, PresetName.DTF_KING_ISO_COATED_V2)

    assert s.color.target_profile_path is not None
    assert "CoatedFOGRA39" in s.color.target_profile_path


def test_dtf_king_preset_default_profile_is_a_valid_cmyk_profile():
    from pathlib import Path

    from src.core.color.profile_validation import validate_cmyk_output_profile

    s = ProcessingSettings()
    apply_preset(s, PresetName.DTF_KING_ISO_COATED_V2)

    result = validate_cmyk_output_profile(Path(s.color.target_profile_path))
    assert result.ok is True
