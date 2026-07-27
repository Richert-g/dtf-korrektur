"""Hot-Folder-Automatikmodus: nicht-modaler Dialog zum Überwachen eines
Quellordners und automatischen Verarbeiten neu auftauchender Bilddateien mit
den aktuell im Hauptfenster konfigurierten Einstellungen (Preset, ICC-Profil,
Alpha-/Halo-/Farbparameter). Läuft weiter im Hintergrund, auch wenn der
Dialog geschlossen wird - siehe closeEvent (fragt beim Schließen nach, falls
die Überwachung noch aktiv ist, statt sie unbemerkt weiterlaufen zu lassen).
"""
from __future__ import annotations

import datetime as _dt
import time
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.app.workers.hot_folder_worker import HotFolderWorker, run_hot_folder_in_thread
from src.config.defaults import ProcessingSettings
from src.core.automation.hot_folder import DEFAULT_POLL_INTERVAL_SECONDS
from src.core.pipeline import process_image_safe
from src.models.enums import OutputFormat
from src.models.report import ImageProcessingReport


class HotFolderDialog(QDialog):
    def __init__(self, settings: ProcessingSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Hot-Folder-Automatikmodus")
        self.resize(560, 420)
        self.setModal(False)
        self.settings = settings

        self._thread = None
        self._worker: HotFolderWorker | None = None
        # Als eigenes Attribut (statt Literal im Aufruf) ausgelagert, damit
        # Tests eine kurze Abtastrate einsetzen koennen, ohne echte Sekunden
        # warten zu muessen (siehe test_hot_folder_dialog.py).
        self._poll_interval_seconds = DEFAULT_POLL_INTERVAL_SECONDS

        layout = QVBoxLayout(self)

        info = QLabel(
            "Überwacht einen Ordner und verarbeitet neu hinzukommende Bilddateien "
            "automatisch mit den aktuell im Hauptfenster gewählten Einstellungen "
            "(Preset, ICC-Profil, Alpha-/Halo-/Farbparameter). Läuft weiter im "
            "Hintergrund, solange dieser Dialog geöffnet bleibt."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        source_row = QHBoxLayout()
        self.source_edit = QLineEdit()
        self.source_edit.setPlaceholderText("Quellordner (wird überwacht)")
        self.btn_select_source = QPushButton("Wählen…")
        source_row.addWidget(self.source_edit, stretch=1)
        source_row.addWidget(self.btn_select_source)
        layout.addLayout(source_row)

        output_row = QHBoxLayout()
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Zielordner (Ergebnisse)")
        self.btn_select_output = QPushButton("Wählen…")
        output_row.addWidget(self.output_edit, stretch=1)
        output_row.addWidget(self.btn_select_output)
        layout.addLayout(output_row)

        self.status_label = QLabel("Gestoppt.")
        layout.addWidget(self.status_label)

        self.btn_toggle = QPushButton("Starten")
        layout.addWidget(self.btn_toggle)

        layout.addWidget(QLabel("Verlauf:"))
        self.log_list = QListWidget()
        layout.addWidget(self.log_list, stretch=1)

        self.btn_select_source.clicked.connect(self._on_select_source_clicked)
        self.btn_select_output.clicked.connect(self._on_select_output_clicked)
        self.btn_toggle.clicked.connect(self._on_toggle_clicked)

    # ------------------------------------------------------------- Helpers
    def _on_select_source_clicked(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Quellordner wählen")
        if path:
            self.source_edit.setText(path)

    def _on_select_output_clicked(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Zielordner wählen")
        if path:
            self.output_edit.setText(path)

    @property
    def is_running(self) -> bool:
        return self._worker is not None

    def _on_toggle_clicked(self) -> None:
        if self.is_running:
            self._stop()
        else:
            self._start()

    def _start(self) -> None:
        source_text = self.source_edit.text().strip()
        output_text = self.output_edit.text().strip()
        if not source_text or not output_text:
            QMessageBox.information(self, "Angaben fehlen", "Bitte Quell- und Zielordner wählen.")
            return
        source_dir = Path(source_text)
        output_dir = Path(output_text)
        if not source_dir.is_dir():
            QMessageBox.information(self, "Ungültiger Quellordner", f"Ordner nicht gefunden: {source_dir}")
            return
        output_dir.mkdir(parents=True, exist_ok=True)

        if self.settings.export.output_format == OutputFormat.PDF_CMYK:
            QMessageBox.information(
                self,
                "Nicht unterstützt im Automatikmodus",
                "Der DTF-King-PDF-Export erfordert für jedes Bild eine manuelle Größen-/"
                "DPI-Bestätigung und kann daher nicht unbeaufsichtigt im Hot-Folder-Modus "
                "laufen. Bitte im Hauptfenster ein anderes Ausgabeformat wählen (z. B. PNG).",
            )
            return

        self._thread, self._worker = run_hot_folder_in_thread(
            source_dir, output_dir, self.settings, process_image_safe, poll_interval=self._poll_interval_seconds
        )
        self._worker.file_processed.connect(self._on_file_processed)
        self._thread.start()

        self.source_edit.setEnabled(False)
        self.output_edit.setEnabled(False)
        self.btn_select_source.setEnabled(False)
        self.btn_select_output.setEnabled(False)
        self.btn_toggle.setText("Stoppen")
        self.status_label.setText(f"Läuft – überwacht: {source_dir}")

    def _stop(self) -> None:
        # Wartet tatsaechlich auf das Thread-Ende, statt nur das Stopp-Flag zu
        # setzen: ein noch laufender QThread beim Beenden der App (z. B.
        # waehrend time.sleep() im Poll-Intervall) kollidiert sonst mit der
        # Interpreter-Terminierung - reproduzierter nativer Absturz (Windows:
        # STATUS_STACK_BUFFER_OVERRUN).
        #
        # Bewusst KEIN einfacher blockierender QThread.wait()-Aufruf: worker.
        # stopped ist ueber eine Warteschlangen-Verbindung mit thread.quit()
        # verbunden (Signal wird im Worker-Thread ausgeloest, thread.quit()
        # gehoert dem Haupt-Thread) - diese Verbindung wird erst zugestellt,
        # wenn der Haupt-Thread seine Ereignisschleife verarbeitet. Ein reines
        # wait() blockiert genau das und fuehrt zu einem (nur durch das
        # Zeitlimit begrenzten) Deadlock. Die folgende Schleife haelt die
        # Ereignisschleife stattdessen am Laufen, waehrend sie auf das
        # tatsaechliche Thread-Ende wartet.
        if self._worker is not None:
            self._worker.request_stop()
        if self._thread is not None:
            # Grosszuegiger, aber endlicher Puffer: request_stop() wirkt erst
            # NACH einer evtl. noch laufenden Einzeldatei-Verarbeitung (siehe
            # run_hot_folder_loop) - bei sehr grossen Bildern kann das laenger
            # als das reine Poll-Intervall dauern.
            deadline = time.monotonic() + self._poll_interval_seconds + 30.0
            while self._thread.isRunning() and time.monotonic() < deadline:
                QApplication.processEvents()
                time.sleep(0.01)
        self._worker = None
        self._thread = None

        self.source_edit.setEnabled(True)
        self.output_edit.setEnabled(True)
        self.btn_select_source.setEnabled(True)
        self.btn_select_output.setEnabled(True)
        self.btn_toggle.setText("Starten")
        self.status_label.setText("Gestoppt.")

    def _on_file_processed(self, path: Path, report: ImageProcessingReport) -> None:
        timestamp = _dt.datetime.now().strftime("%H:%M:%S")
        if report.success:
            self.log_list.addItem(f"[{timestamp}] {path.name}: erfolgreich verarbeitet")
        else:
            self.log_list.addItem(f"[{timestamp}] {path.name}: fehlgeschlagen - {'; '.join(report.errors)}")
        self.log_list.scrollToBottom()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt-Override
        if self.is_running:
            answer = QMessageBox.question(
                self,
                "Überwachung beenden?",
                "Der Hot-Folder-Modus läuft noch. Beim Schließen dieses Fensters wird die "
                "Überwachung gestoppt. Fortfahren?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._stop()
        event.accept()
