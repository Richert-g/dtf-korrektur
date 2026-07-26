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
    assert s.gamut.max_auto_saturation_reduction == 0.35


def test_dtf_king_preset_keeps_existing_alpha_halo_enabled():
    s = ProcessingSettings()
    apply_preset(s, PresetName.DTF_KING_ISO_COATED_V2)

    assert s.halo.enabled is True


def test_dtf_king_preset_never_silently_substitutes_similar_profile():
    """Ohne ein tatsächlich als 'ISO Coated v2' beschriftetes Profil im
    Bestand darf NIEMALS automatisch z. B. FOGRA39 als Ersatz gewählt werden."""
    s = ProcessingSettings()
    s.color.target_profile_path = "resources/profiles/CMYK/CoatedFOGRA39.icc"
    apply_preset(s, PresetName.DTF_KING_ISO_COATED_V2)

    assert s.color.target_profile_path is None


def test_dtf_king_preset_finds_real_iso_coated_v2_profile_if_imported(monkeypatch):
    from src.core.color.icc_manager import ProfileInfo

    def fake_list_available_profiles():
        return [ProfileInfo(name="ISO Coated v2 (ECI)", path=__import__("pathlib").Path("resources/profiles/CMYK/CoatedFOGRA39.icc"))]

    def fake_validate(path):
        from src.core.color.profile_validation import ProfileValidationResult

        return ProfileValidationResult(ok=True, path=path, description="ISO Coated v2 (ECI)", color_space="CMYK")

    monkeypatch.setattr("src.core.color.icc_manager.list_available_profiles", fake_list_available_profiles)
    monkeypatch.setattr("src.core.color.profile_validation.validate_cmyk_output_profile", fake_validate)

    s = ProcessingSettings()
    apply_preset(s, PresetName.DTF_KING_ISO_COATED_V2)

    assert s.color.target_profile_path is not None
    assert "FOGRA39" in s.color.target_profile_path or "CoatedFOGRA39" in s.color.target_profile_path
