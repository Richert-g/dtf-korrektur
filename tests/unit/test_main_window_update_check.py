from PySide6.QtWidgets import QApplication

from src.app.ui.main_window import MainWindow
from src.core.update.update_check import UpdateCheckResult


def _app():
    return QApplication.instance() or QApplication([])


def test_update_banner_hidden_by_default():
    _app()
    w = MainWindow()
    # isVisible() haengt zusaetzlich davon ab, ob das (im Test nie gezeigte)
    # Fenster selbst sichtbar ist - isHidden() spiegelt dagegen direkt den
    # zuletzt gesetzten setVisible()-Zustand des Banners wider.
    assert w.update_banner.isHidden() is True


def test_banner_shown_when_update_available():
    _app()
    w = MainWindow()

    w._on_update_check_finished(
        UpdateCheckResult(update_available=True, latest_version="v9.9.9", release_url="https://github.com/x/y")
    )

    assert w.update_banner.isHidden() is False
    assert "v9.9.9" in w.update_banner_label.text()
    assert w.btn_show_update.isEnabled() is True


def test_banner_stays_hidden_when_no_update_available():
    _app()
    w = MainWindow()

    w._on_update_check_finished(UpdateCheckResult(update_available=False, latest_version="v1.0.13"))

    assert w.update_banner.isHidden() is True


def test_banner_shown_but_show_button_disabled_without_trusted_url():
    """release_url kann None sein (z. B. verworfen, weil kein echter
    github.com-Link) - der Hinweis soll trotzdem erscheinen, nur der Link-
    Button ist dann deaktiviert."""
    _app()
    w = MainWindow()

    w._on_update_check_finished(UpdateCheckResult(update_available=True, latest_version="v9.9.9", release_url=None))

    assert w.update_banner.isHidden() is False
    assert w.btn_show_update.isEnabled() is False


def test_show_update_opens_release_url(monkeypatch):
    _app()
    w = MainWindow()
    w._latest_release_url = "https://github.com/x/y"

    opened = []
    monkeypatch.setattr("src.app.ui.main_window.QDesktopServices.openUrl", lambda url: opened.append(url.toString()))

    w._on_show_update_clicked()

    assert opened == ["https://github.com/x/y"]


def test_dismiss_update_hides_banner_and_persists_setting(monkeypatch, tmp_path):
    fake_config_file = tmp_path / "settings.json"
    monkeypatch.setattr("src.config.config_manager.get_config_file", lambda: fake_config_file)

    _app()
    w = MainWindow()
    w._on_update_check_finished(
        UpdateCheckResult(update_available=True, latest_version="v9.9.9", release_url="https://github.com/x/y")
    )
    assert w.update_banner.isHidden() is False

    w._on_dismiss_update_clicked()

    assert w.update_banner.isHidden() is True
    assert w.controller.settings.check_for_updates_enabled is False
    assert fake_config_file.exists()
