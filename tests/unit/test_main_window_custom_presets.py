import pytest
from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox

from src.app.ui.main_window import MainWindow
from src.core.presets.custom_presets import load_custom_presets, save_custom_preset
from src.models.enums import AlphaMode, PresetName


def _app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _isolated_presets_file(tmp_path, monkeypatch):
    fake_file = tmp_path / "presets.json"
    monkeypatch.setattr("src.core.presets.custom_presets.get_presets_file", lambda: fake_file)


def test_combo_lists_builtins_only_when_no_custom_presets_exist():
    _app()
    w = MainWindow()
    values = [w.preset_combo.itemData(i) for i in range(w.preset_combo.count())]
    assert values == list(PresetName)


def test_combo_appends_custom_presets_after_separator():
    from src.config.defaults import ProcessingSettings

    save_custom_preset("Mein Preset", ProcessingSettings())

    _app()
    w = MainWindow()
    w._reload_preset_combo()

    labels = [w.preset_combo.itemText(i) for i in range(w.preset_combo.count())]
    assert labels[len(PresetName)] == ""  # Trennlinie hat keinen Text
    assert "Mein Preset" in labels


def test_selecting_custom_preset_via_combo_applies_its_settings():
    """Regressionstest: currentData() kann fuer PresetName (str-Enum) ein
    reines str-Objekt statt des Enum-Members liefern - _on_preset_changed
    darf ein benutzerdefiniertes Preset dadurch nicht fälschlich ignorieren
    (siehe Kommentar in main_window._on_preset_changed)."""
    from src.config.defaults import ProcessingSettings

    custom = ProcessingSettings()
    custom.alpha_mode = AlphaMode.HARD_EDGE
    custom.alpha.weak_alpha_threshold = 123
    save_custom_preset("Mein Preset", custom)

    _app()
    w = MainWindow()
    w._reload_preset_combo()

    idx = w.preset_combo.findData("Mein Preset")
    assert idx >= 0
    w.preset_combo.setCurrentIndex(idx)

    assert w.controller.settings.alpha_mode == AlphaMode.HARD_EDGE
    assert w.controller.settings.alpha.weak_alpha_threshold == 123


def test_selecting_builtin_preset_still_works_after_custom_presets_added():
    from src.config.defaults import ProcessingSettings
    from src.models.enums import OutputFormat

    save_custom_preset("Mein Preset", ProcessingSettings())

    _app()
    w = MainWindow()
    w._reload_preset_combo()

    idx = w.preset_combo.findData(PresetName.DTF_KING_ISO_COATED_V2)
    w.preset_combo.setCurrentIndex(idx)

    assert w.controller.settings.export.output_format == OutputFormat.PDF_CMYK


def test_save_custom_preset_via_dialog(monkeypatch):
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **kw: ("Neues Preset", True)))

    _app()
    w = MainWindow()
    w._on_save_custom_preset_clicked()

    assert "Neues Preset" in load_custom_presets()
    assert w.preset_combo.currentData() == "Neues Preset"


def test_save_custom_preset_cancelled_does_nothing(monkeypatch):
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **kw: ("Neues Preset", False)))

    _app()
    w = MainWindow()
    w._on_save_custom_preset_clicked()

    assert load_custom_presets() == {}


def test_save_custom_preset_existing_name_asks_to_overwrite_and_confirms(monkeypatch):
    from src.config.defaults import ProcessingSettings

    save_custom_preset("Foo", ProcessingSettings())
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **kw: ("Foo", True)))
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.StandardButton.Yes)

    _app()
    w = MainWindow()
    w.controller.settings.alpha.weak_alpha_threshold = 199
    w._on_save_custom_preset_clicked()

    assert load_custom_presets()["Foo"].alpha.weak_alpha_threshold == 199


def test_save_custom_preset_existing_name_declined_overwrite_keeps_old(monkeypatch):
    from src.config.defaults import ProcessingSettings

    save_custom_preset("Foo", ProcessingSettings())
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **kw: ("Foo", True)))
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.StandardButton.No)

    _app()
    w = MainWindow()
    w.controller.settings.alpha.weak_alpha_threshold = 199
    w._on_save_custom_preset_clicked()

    assert load_custom_presets()["Foo"].alpha.weak_alpha_threshold != 199


def test_manage_custom_presets_reloads_combo_when_changed(monkeypatch):
    from src.app.ui.custom_preset_manager_dialog import CustomPresetManagerDialog
    from src.config.defaults import ProcessingSettings

    save_custom_preset("Wird geloescht", ProcessingSettings())

    _app()
    w = MainWindow()
    w._reload_preset_combo()
    assert w.preset_combo.findData("Wird geloescht") >= 0

    def _fake_exec(self):
        from src.core.presets.custom_presets import delete_custom_preset

        delete_custom_preset("Wird geloescht")
        self.changed = True
        return 0

    monkeypatch.setattr(CustomPresetManagerDialog, "exec", _fake_exec)

    w._on_manage_custom_presets_clicked()

    assert w.preset_combo.findData("Wird geloescht") == -1
