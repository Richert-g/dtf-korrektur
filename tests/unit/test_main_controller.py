from src.app.controllers.main_controller import MainController
from src.config.config_manager import save_settings
from src.config.defaults import ProcessingSettings
from src.models.enums import OutputFormat


def test_stale_dtf_king_output_format_is_reset_on_startup(monkeypatch, tmp_path):
    """Regression: Wurde output_format in einer frueheren Sitzung (z. B. beim
    Testen des DTF-King-Presets) als 'pdf_cmyk' gespeichert, darf ein
    Programmneustart NICHT weiterhin im PDF-Modus stecken bleiben - sonst
    versucht 'Automatisch optimieren' fuer ein voellig anderes Preset
    faelschlich eine PDF statt einer PNG zu erzeugen, und die
    Vorher/Nachher-Vorschau bleibt leer."""
    fake_config_file = tmp_path / "settings.json"
    monkeypatch.setattr("src.config.config_manager.get_config_file", lambda: fake_config_file)

    stale = ProcessingSettings()
    stale.export.output_format = OutputFormat.PDF_CMYK
    stale.gamut.enable_auto_gamut_correction = False
    stale.gamut.max_auto_saturation_reduction = 0.0
    save_settings(stale)

    controller = MainController()

    assert controller.settings.export.output_format == OutputFormat.PNG_RGB
    assert controller.settings.gamut.enable_auto_gamut_correction is True
    assert controller.settings.gamut.max_auto_saturation_reduction == 0.0


def test_normal_settings_are_not_altered_on_startup(monkeypatch, tmp_path):
    fake_config_file = tmp_path / "settings.json"
    monkeypatch.setattr("src.config.config_manager.get_config_file", lambda: fake_config_file)

    normal = ProcessingSettings()
    normal.alpha.weak_alpha_threshold = 200
    save_settings(normal)

    controller = MainController()

    assert controller.settings.alpha.weak_alpha_threshold == 200
    assert controller.settings.export.output_format == OutputFormat.PNG_RGB
