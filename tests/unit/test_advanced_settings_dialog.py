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


# --- Unabhängige Aktivierung/Deaktivierung der beiden Alpha-Schwellenwerte ---


def test_weak_and_near_opaque_checkboxes_default_checked(qapp):
    settings = ProcessingSettings()
    dlg = AdvancedSettingsDialog(settings)
    assert dlg.weak_enabled_checkbox.isChecked() is True
    assert dlg.near_opaque_enabled_checkbox.isChecked() is True
    assert dlg.weak_threshold.isEnabled() is True
    assert dlg.near_opaque_threshold.isEnabled() is True


def test_unchecking_weak_checkbox_disables_spinbox_but_keeps_value(qapp):
    settings = ProcessingSettings()
    dlg = AdvancedSettingsDialog(settings)
    dlg.weak_threshold.setValue(199)

    dlg.weak_enabled_checkbox.setChecked(False)

    assert dlg.weak_threshold.isEnabled() is False
    assert dlg.weak_threshold.value() == 199  # Wert bleibt erhalten, nur deaktiviert


def test_unchecking_near_opaque_checkbox_disables_spinbox_but_keeps_value(qapp):
    settings = ProcessingSettings()
    dlg = AdvancedSettingsDialog(settings)
    dlg.near_opaque_threshold.setValue(150)

    dlg.near_opaque_enabled_checkbox.setChecked(False)

    assert dlg.near_opaque_threshold.isEnabled() is False
    assert dlg.near_opaque_threshold.value() == 150


def test_rechecking_checkbox_reenables_spinbox_with_same_value(qapp):
    settings = ProcessingSettings()
    dlg = AdvancedSettingsDialog(settings)
    dlg.weak_threshold.setValue(199)

    dlg.weak_enabled_checkbox.setChecked(False)
    dlg.weak_enabled_checkbox.setChecked(True)

    assert dlg.weak_threshold.isEnabled() is True
    assert dlg.weak_threshold.value() == 199


def test_apply_to_settings_persists_enabled_flags_independently(qapp):
    settings = ProcessingSettings()
    dlg = AdvancedSettingsDialog(settings)

    dlg.weak_enabled_checkbox.setChecked(False)
    dlg.near_opaque_enabled_checkbox.setChecked(True)
    dlg.apply_to_settings()

    assert settings.alpha.weak_alpha_threshold_enabled is False
    assert settings.alpha.near_opaque_threshold_enabled is True


def test_apply_to_settings_keeps_threshold_value_while_disabled(qapp):
    """Der Schwellenwert bleibt gespeichert, auch wenn die Checkbox beim
    Übernehmen deaktiviert ist - nur der Verarbeitungsschritt wird übersprungen."""
    settings = ProcessingSettings()
    dlg = AdvancedSettingsDialog(settings)

    dlg.weak_threshold.setValue(77)
    dlg.weak_enabled_checkbox.setChecked(False)
    dlg.apply_to_settings()

    assert settings.alpha.weak_alpha_threshold == 77
    assert settings.alpha.weak_alpha_threshold_enabled is False


def test_dialog_reflects_previously_disabled_state_on_reopen(qapp):
    """Wird der Dialog mit bereits deaktivierter Checkbox neu geöffnet (z. B.
    nach einem vorherigen Speichern), muss die Checkbox weiterhin deaktiviert
    und der gespeicherte Wert unverändert angezeigt werden."""
    settings = ProcessingSettings()
    settings.alpha.weak_alpha_threshold = 90
    settings.alpha.weak_alpha_threshold_enabled = False
    settings.alpha.near_opaque_threshold = 210
    settings.alpha.near_opaque_threshold_enabled = False

    dlg = AdvancedSettingsDialog(settings)

    assert dlg.weak_enabled_checkbox.isChecked() is False
    assert dlg.weak_threshold.value() == 90
    assert dlg.weak_threshold.isEnabled() is False
    assert dlg.near_opaque_enabled_checkbox.isChecked() is False
    assert dlg.near_opaque_threshold.value() == 210
    assert dlg.near_opaque_threshold.isEnabled() is False
