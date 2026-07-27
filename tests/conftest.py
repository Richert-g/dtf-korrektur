import pytest


@pytest.fixture(autouse=True)
def _no_real_update_check(monkeypatch):
    """Verhindert echte Netzwerkzugriffe während der Tests: MainWindow würde
    sonst bei jeder Instanziierung einen echten Update-Check gegen die
    GitHub-API auslösen (langsam, offline-/CI-abhängig, flaky). Einzelne
    Tests für den Update-Check selbst rufen die Auswertung direkt auf
    (_on_update_check_finished) statt über den echten Netzwerk-Worker."""
    monkeypatch.setattr("src.app.ui.main_window.MainWindow._start_update_check", lambda self: None)
