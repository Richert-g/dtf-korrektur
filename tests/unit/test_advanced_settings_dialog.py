import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from src.app.ui.advanced_settings_dialog import AdvancedSettingsDialog
from src.config.defaults import ProcessingSettings


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_weak_threshold_range_excludes_255(qapp):
    settings = ProcessingSettings()
    dlg = AdvancedSettingsDialog(settings)
    assert dlg.weak_threshold.minimum() == 0
    assert dlg.weak_threshold.maximum() == 254


def test_weak_threshold_default_matches_settings(qapp):
    settings = ProcessingSettings()
    dlg = AdvancedSettingsDialog(settings)
    assert dlg.weak_threshold.value() == 241 == settings.alpha.weak_alpha_threshold


def test_weak_threshold_percent_label_updates(qapp):
    settings = ProcessingSettings()
    dlg = AdvancedSettingsDialog(settings)
    dlg.weak_threshold.setValue(241)
    assert "94.5" in dlg.weak_threshold_percent_label.text()
    assert "241 von 255" in dlg.weak_threshold_percent_label.text()


def test_weak_threshold_warning_hidden_below_220(qapp):
    settings = ProcessingSettings()
    dlg = AdvancedSettingsDialog(settings)
    dlg.weak_threshold.setValue(219)
    assert dlg.weak_threshold_warning_label.isHidden()


def test_weak_threshold_warning_shown_from_220(qapp):
    settings = ProcessingSettings()
    dlg = AdvancedSettingsDialog(settings)
    dlg.weak_threshold.setValue(220)
    assert not dlg.weak_threshold_warning_label.isHidden()
    assert "Weiche Schatten" in dlg.weak_threshold_warning_label.text()


def test_apply_to_settings_persists_weak_threshold(qapp):
    settings = ProcessingSettings()
    dlg = AdvancedSettingsDialog(settings)
    dlg.weak_threshold.setValue(180)
    dlg.apply_to_settings()
    assert settings.alpha.weak_alpha_threshold == 180
