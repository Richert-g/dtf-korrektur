import time

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QMessageBox

from src.app.ui.hot_folder_dialog import HotFolderDialog
from src.config.defaults import ProcessingSettings
from src.models.enums import OutputFormat


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_default_state_is_stopped(qapp):
    dlg = HotFolderDialog(ProcessingSettings())
    assert dlg.is_running is False
    assert dlg.btn_toggle.text() == "Starten"
    assert dlg.status_label.text() == "Gestoppt."


def test_start_without_folders_shows_message_and_stays_stopped(qapp, monkeypatch):
    shown = []
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **kw: shown.append(a))

    dlg = HotFolderDialog(ProcessingSettings())
    dlg._on_toggle_clicked()

    assert dlg.is_running is False
    assert len(shown) == 1


def test_start_with_missing_source_dir_shows_message(qapp, monkeypatch, tmp_path):
    shown = []
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **kw: shown.append(a))

    dlg = HotFolderDialog(ProcessingSettings())
    dlg.source_edit.setText(str(tmp_path / "does_not_exist"))
    dlg.output_edit.setText(str(tmp_path / "out"))
    dlg._on_toggle_clicked()

    assert dlg.is_running is False
    assert len(shown) == 1


def test_start_rejects_pdf_cmyk_output_format(qapp, monkeypatch, tmp_path):
    shown = []
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **kw: shown.append(a))

    settings = ProcessingSettings()
    settings.export.output_format = OutputFormat.PDF_CMYK
    source = tmp_path / "in"
    source.mkdir()
    dlg = HotFolderDialog(settings)
    dlg.source_edit.setText(str(source))
    dlg.output_edit.setText(str(tmp_path / "out"))

    dlg._on_toggle_clicked()

    assert dlg.is_running is False
    assert len(shown) == 1


def test_start_toggles_ui_state(qapp, monkeypatch, tmp_path):
    """Prüft nur den UI-Zustandswechsel - der echte Hintergrund-Thread wird
    hier durch einen Fake ersetzt, um den Test schnell und deterministisch zu
    halten (echte Verarbeitung wird in test_hot_folder_worker.py und einem
    dedizierten Integrationstest unten geprüft)."""

    class _FakeThread:
        def start(self):
            pass

        def isRunning(self):
            return False  # in diesem Test bereits "fertig", damit _stop() sofort zurueckkehrt

    class _FakeWorker:
        def __init__(self):
            self.file_processed = _FakeSignal()
            self.stop_requested = False

        def request_stop(self):
            self.stop_requested = True

    class _FakeSignal:
        def connect(self, *_a, **_kw):
            pass

    fake_thread = _FakeThread()
    fake_worker = _FakeWorker()
    monkeypatch.setattr(
        "src.app.ui.hot_folder_dialog.run_hot_folder_in_thread",
        lambda *a, **kw: (fake_thread, fake_worker),
    )

    source = tmp_path / "in"
    source.mkdir()
    dlg = HotFolderDialog(ProcessingSettings())
    dlg.source_edit.setText(str(source))
    dlg.output_edit.setText(str(tmp_path / "out"))

    dlg._on_toggle_clicked()
    assert dlg.is_running is True
    assert dlg.btn_toggle.text() == "Stoppen"
    assert dlg.source_edit.isEnabled() is False

    dlg._on_toggle_clicked()
    assert dlg.is_running is False
    assert dlg.btn_toggle.text() == "Starten"
    assert dlg.source_edit.isEnabled() is True
    assert fake_worker.stop_requested is True


def test_file_processed_appends_to_log(qapp):
    from pathlib import Path

    from src.models.report import ImageProcessingReport

    dlg = HotFolderDialog(ProcessingSettings())
    dlg._on_file_processed(Path("bild.png"), ImageProcessingReport(success=True))
    dlg._on_file_processed(Path("kaputt.png"), ImageProcessingReport(success=False, errors=["defekt"]))

    assert dlg.log_list.count() == 2
    assert "bild.png" in dlg.log_list.item(0).text()
    assert "erfolgreich" in dlg.log_list.item(0).text()
    assert "kaputt.png" in dlg.log_list.item(1).text()
    assert "fehlgeschlagen" in dlg.log_list.item(1).text()


def test_close_while_running_asks_for_confirmation_and_stops_on_yes(qapp, monkeypatch, tmp_path):
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.StandardButton.Yes)

    source = tmp_path / "in"
    source.mkdir()
    (source / "a.png").write_bytes(b"data")
    dlg = HotFolderDialog(ProcessingSettings())
    dlg.source_edit.setText(str(source))
    dlg.output_edit.setText(str(tmp_path / "out"))
    dlg._on_toggle_clicked()
    assert dlg.is_running is True

    dlg.close()

    assert dlg.is_running is False


def test_close_while_running_cancels_on_no(qapp, monkeypatch, tmp_path):
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.StandardButton.No)

    source = tmp_path / "in"
    source.mkdir()
    dlg = HotFolderDialog(ProcessingSettings())
    dlg.source_edit.setText(str(source))
    dlg.output_edit.setText(str(tmp_path / "out"))
    dlg._on_toggle_clicked()
    assert dlg.is_running is True

    dlg.close()

    assert dlg.is_running is True
    dlg._stop()  # aufräumen, damit kein Hintergrund-Thread über den Test hinaus läuft


def test_end_to_end_processes_real_file_via_background_thread(qapp, tmp_path):
    """Echter Integrationstest mit echtem QThread: legt eine Bilddatei in den
    Quellordner, startet den echten Hot-Folder-Worker und wartet (mit
    Zeitlimit), bis die Datei tatsächlich verarbeitet und im Zielordner eine
    Ausgabedatei erzeugt wurde."""
    import numpy as np
    from PIL import Image

    source = tmp_path / "in"
    source.mkdir()
    output = tmp_path / "out"

    img = Image.fromarray(np.full((16, 16, 4), 255, dtype=np.uint8), mode="RGBA")
    img.save(source / "test.png")

    dlg = HotFolderDialog(ProcessingSettings())
    dlg._poll_interval_seconds = 0.02  # schnelle Abtastrate, damit der Test nicht Sekunden warten muss
    dlg.source_edit.setText(str(source))
    dlg.output_edit.setText(str(output))
    dlg._on_toggle_clicked()
    assert dlg.is_running is True

    deadline = time.time() + 5
    while dlg.log_list.count() == 0 and time.time() < deadline:
        qapp.processEvents()
        time.sleep(0.02)

    dlg._stop()

    assert dlg.log_list.count() == 1
    assert "erfolgreich" in dlg.log_list.item(0).text()
