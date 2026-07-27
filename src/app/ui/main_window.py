"""Hauptfenster (Prompt Abschnitt 4 & 25): bewusst einfach gehalten."""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFontMetrics, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.app.controllers.main_controller import MainController
from src.app.ui.advanced_settings_dialog import AdvancedSettingsDialog
from src.app.ui.compare_slider import CompareSliderWidget
from src.app.ui.drop_area import DropArea, DropListWidget, collect_supported_files
from src.app.ui.dtf_king_export_dialog import DtfKingExportDialog
from src.app.ui.zoom_pan_view import ZoomToolbar
from src.app.ui.zoomable_view import ZoomableImageView
from src.app.workers.analysis_worker import run_analysis_in_thread
from src.app.workers.pipeline_worker import run_batch_in_thread
from src.app.workers.update_check_async import AsyncUpdateChecker
from src.config.defaults import MAX_PREVIEW_DIMENSION_PX
from src.core.analysis.image_loader import load_image
from src.core.export.dtf_king_export import process_image_for_dtf_king_pdf_safe
from src.core.pipeline import process_image_safe
from src.core.update.update_check import UpdateCheckResult
from src.models.enums import OutputFormat, PresetName
from src.utils.image_qt import (
    checkerboard_background,
    composite_over_background,
    downscale_for_preview,
    rgba_array_to_qpixmap,
)
from src.version import APP_VERSION

logger = logging.getLogger(__name__)

VIEW_ORIGINAL = "Original"
VIEW_RESULT = "Optimiertes Ergebnis"
VIEW_SOFTPROOF = "Softproof"
VIEW_ALPHA_MASK = "Alpha-Maske"
VIEW_WHITE_TEXTILE = "Auf weißem Textil"
VIEW_BLACK_TEXTILE = "Auf schwarzem Textil"
VIEW_REMOVED_PIXELS = "Entfernte Pixel"
VIEW_STRENGTHENED_PIXELS = "Verstärkte Pixel"
VIEW_GAMUT_WARNING = "Gamut-Warnung"
VIEW_WHITE_MASK = "Weißunterlegungsmaske"

# Drei klar getrennte Vorschauzustände (Original / nur Transparenz / Softproof
# eines Druckdienstleister-Presets), damit Transparenzkorrektur und
# Farbkonvertierung nicht miteinander vermischt betrachtet werden.
VIEW_ORIGINAL_SOURCE = "Original – Quellfarbraum"
VIEW_TRANSPARENCY_ONLY = "Transparenzoptimiert – Farben unverändert"
VIEW_DTF_KING_SOFTPROOF = "DTF-King Softproof – ISO Coated v2"

# Vom Benutzer frei wählbares Hauptausgabeformat, unabhängig vom Preset.
OUTPUT_FORMAT_CHOICES = [
    ("PNG (mit Transparenz)", OutputFormat.PNG_RGB),
    ("TIFF (verlustfrei, mit Transparenz)", OutputFormat.TIFF_RGB),
    ("JPEG (ohne Transparenz)", OutputFormat.JPEG_RGB),
    ("PDF (CMYK, druckfertig – erfordert ICC-Zielprofil)", OutputFormat.PDF_CMYK),
]

# Vollständige Liste aller möglichen Bezeichnungen - dient als Grundlage für
# die dynamische Mindestbreite des "Ansicht"-Auswahlfelds (siehe
# _compute_view_combo_min_width), unabhängig davon, welche Einträge im
# aktuellen Zustand tatsächlich angezeigt werden.
ALL_VIEW_MODE_LABELS = [
    VIEW_ORIGINAL,
    VIEW_RESULT,
    VIEW_SOFTPROOF,
    VIEW_ALPHA_MASK,
    VIEW_WHITE_TEXTILE,
    VIEW_BLACK_TEXTILE,
    VIEW_REMOVED_PIXELS,
    VIEW_STRENGTHENED_PIXELS,
    VIEW_GAMUT_WARNING,
    VIEW_WHITE_MASK,
    VIEW_ORIGINAL_SOURCE,
    VIEW_TRANSPARENCY_ONLY,
    VIEW_DTF_KING_SOFTPROOF,
]

# Fallback-Mindestbreite (Prompt-Vorgabe: ca. 190-220px), falls die
# schriftbasierte Messung aus irgendeinem Grund einen zu kleinen Wert liefert.
VIEW_COMBO_FALLBACK_MIN_WIDTH_PX = 220
# Zusätzlicher Platz für Dropdown-Pfeil, Innenabstand und Scrollbar im Popup,
# damit auch das aufgeklappte Dropdown nicht abschneidet.
VIEW_COMBO_EXTRA_WIDTH_PX = 56


def _compute_view_combo_min_width(combo: QComboBox, candidate_labels: list[str]) -> int:
    """Ermittelt eine Mindestbreite, die den längsten Eintrag vollständig anzeigt.

    Verwendet die tatsächlichen (DPI-/skalierungsabhängigen) Schriftmetriken
    des Auswahlfelds, damit die Breite auch bei 100/125/150 % Windows-
    Anzeigeskalierung ausreicht - Qt skaliert Schriftgrößen für solche
    Einstellungen automatisch, `QFontMetrics` misst also bereits die
    tatsächlich auf dem Bildschirm benötigte Breite.
    """
    metrics = QFontMetrics(combo.font())
    longest_text_width = max((metrics.horizontalAdvance(text) for text in candidate_labels), default=0)
    return max(VIEW_COMBO_FALLBACK_MIN_WIDTH_PX, longest_text_width + VIEW_COMBO_EXTRA_WIDTH_PX)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DTF Korrektur")
        self.resize(1280, 800)

        from src.config.paths import get_app_icon_path

        icon_path = get_app_icon_path()
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.controller = MainController()
        self._analysis_thread = None
        self._analysis_worker = None
        self._analysis_request_path: Path | None = None
        self._batch_thread = None
        self._batch_worker = None
        self._current_original_rgba: np.ndarray | None = None
        self._current_result_rgba: np.ndarray | None = None
        self._current_softproof_rgba: np.ndarray | None = None
        self._current_removed_pixels_rgba: np.ndarray | None = None
        self._current_strengthened_pixels_rgba: np.ndarray | None = None
        self._current_gamut_warning_rgba: np.ndarray | None = None
        self._current_white_mask_rgba: np.ndarray | None = None
        self._current_transparency_only_rgba: np.ndarray | None = None
        self._last_reports: dict[str, object] = {}
        self._update_checker = None
        self._latest_release_url: str | None = None
        self._hot_folder_dialog = None

        self._build_ui()
        self._connect_signals()
        self._refresh_output_format_combo()

        if self.controller.startup_warnings:
            QMessageBox.warning(self, "Hinweis zu gespeicherten Einstellungen", "\n".join(self.controller.startup_warnings))

        if self.controller.settings.check_for_updates_enabled:
            self._start_update_check()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)

        self.update_banner = self._build_update_banner()
        root_layout.addWidget(self.update_banner)

        splitter_row = QHBoxLayout()
        root_layout.addLayout(splitter_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter_row.addWidget(splitter)

        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_center_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([260, 700, 320])

    def _build_update_banner(self) -> QWidget:
        """Unaufdringlicher Hinweisstreifen, der nur sichtbar wird, wenn der
        Update-Check (siehe _start_update_check) eine neuere Version findet."""
        banner = QFrame()
        banner.setFrameShape(QFrame.Shape.StyledPanel)
        banner.setStyleSheet("background-color: #fff3cd; border-bottom: 1px solid #ffc107;")
        banner.setVisible(False)
        layout = QHBoxLayout(banner)
        layout.setContentsMargins(10, 6, 10, 6)

        self.update_banner_label = QLabel("")
        self.update_banner_label.setWordWrap(True)
        layout.addWidget(self.update_banner_label, stretch=1)

        self.btn_show_update = QPushButton("Version anzeigen")
        self.btn_dismiss_update = QPushButton("Nicht mehr automatisch prüfen")
        layout.addWidget(self.btn_show_update)
        layout.addWidget(self.btn_dismiss_update)

        return banner

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        self.drop_area = DropArea()
        layout.addWidget(self.drop_area)

        btn_row = QHBoxLayout()
        self.btn_select_file = QPushButton("Bild auswählen")
        self.btn_select_folder = QPushButton("Ordner auswählen")
        btn_row.addWidget(self.btn_select_file)
        btn_row.addWidget(self.btn_select_folder)
        layout.addLayout(btn_row)

        layout.addWidget(QLabel("Ausgewählte Dateien:"))
        self.file_list = DropListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        layout.addWidget(self.file_list, stretch=1)

        list_btn_row = QHBoxLayout()
        self.btn_remove_selected = QPushButton("Ausgewählte entfernen")
        self.btn_clear_list = QPushButton("Liste leeren")
        list_btn_row.addWidget(self.btn_remove_selected)
        list_btn_row.addWidget(self.btn_clear_list)
        layout.addLayout(list_btn_row)

        delete_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self.file_list)
        delete_shortcut.activated.connect(self._on_remove_selected_clicked)

        return panel

    def _build_center_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        view_row = QHBoxLayout()
        view_row.addWidget(QLabel("Ansicht:"))
        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItems([VIEW_ORIGINAL])
        combo_min_width = _compute_view_combo_min_width(self.view_mode_combo, ALL_VIEW_MODE_LABELS)
        self.view_mode_combo.setMinimumWidth(combo_min_width)
        self.view_mode_combo.view().setMinimumWidth(combo_min_width)
        view_row.addWidget(self.view_mode_combo)
        view_row.addStretch(1)
        layout.addLayout(view_row)

        self.preview_tabs = QTabWidget()
        self.preview_view = ZoomableImageView()
        self.compare_view = CompareSliderWidget()

        self.preview_toolbar = ZoomToolbar()
        self.preview_toolbar.bind(self.preview_view)
        preview_tab = QWidget()
        preview_tab_layout = QVBoxLayout(preview_tab)
        preview_tab_layout.setContentsMargins(0, 0, 0, 0)
        preview_tab_layout.addWidget(self.preview_toolbar)
        preview_tab_layout.addWidget(self.preview_view, stretch=1)

        self.compare_toolbar = ZoomToolbar()
        self.compare_toolbar.bind(self.compare_view)

        self.btn_color_picker = QPushButton("Farbpicker")
        self.btn_color_picker.setCheckable(True)
        self.btn_color_picker.setToolTip(
            "Aktivieren, dann auf ein Pixel im Vorher/Nachher-Vergleich klicken, "
            "um dessen Farbcode vorher und nachher anzuzeigen."
        )
        compare_toolbar_layout = self.compare_toolbar.layout()
        assert compare_toolbar_layout is not None
        compare_toolbar_layout.addWidget(self.btn_color_picker)

        self.picker_result_label = QLabel("Farbpicker aktivieren und auf ein Pixel klicken.")
        self.picker_result_label.setTextFormat(Qt.TextFormat.RichText)
        self.picker_result_label.setWordWrap(True)
        self.picker_result_label.setStyleSheet("padding: 4px;")

        compare_tab = QWidget()
        compare_tab_layout = QVBoxLayout(compare_tab)
        compare_tab_layout.setContentsMargins(0, 0, 0, 0)
        compare_tab_layout.addWidget(self.compare_toolbar)
        compare_tab_layout.addWidget(self.compare_view, stretch=1)
        compare_tab_layout.addWidget(self.picker_result_label)

        self.preview_tabs.addTab(preview_tab, "Vorschau")
        self.preview_tabs.addTab(compare_tab, "Vorher / Nachher")
        layout.addWidget(self.preview_tabs, stretch=1)

        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        preset_group = QGroupBox("Druckprofil / Preset")
        preset_layout = QVBoxLayout(preset_group)
        self.preset_combo = QComboBox()
        for preset in PresetName:
            self.preset_combo.addItem(preset.value, preset)
        preset_layout.addWidget(self.preset_combo)

        profile_row = QHBoxLayout()
        self.profile_combo = QComboBox()
        self._reload_profiles()
        self.btn_import_profile = QPushButton("Importieren…")
        profile_row.addWidget(self.profile_combo, stretch=1)
        profile_row.addWidget(self.btn_import_profile)
        preset_layout.addWidget(QLabel("ICC-Zielprofil:"))
        preset_layout.addLayout(profile_row)
        layout.addWidget(preset_group)

        format_group = QGroupBox("Ausgabeformat")
        format_layout = QHBoxLayout(format_group)
        self.output_format_combo = QComboBox()
        for label, fmt in OUTPUT_FORMAT_CHOICES:
            self.output_format_combo.addItem(label, fmt)
        format_layout.addWidget(self.output_format_combo, stretch=1)
        layout.addWidget(format_group)

        output_group = QGroupBox("Ausgabeordner")
        output_layout = QHBoxLayout(output_group)
        self.output_label = QLabel("(wird automatisch neben dem Bild angelegt)")
        self.output_label.setWordWrap(True)
        self.btn_select_output = QPushButton("Wählen…")
        output_layout.addWidget(self.output_label, stretch=1)
        output_layout.addWidget(self.btn_select_output)
        layout.addWidget(output_group)

        layout.addWidget(QLabel("Zusammenfassung:"))
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        layout.addWidget(self.summary_text, stretch=1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        optimize_row = QHBoxLayout()
        self.btn_optimize = QPushButton("Automatisch optimieren")
        self.btn_optimize.setMinimumHeight(48)
        self.btn_optimize.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.btn_cancel = QPushButton("Abbrechen")
        self.btn_cancel.setEnabled(False)
        optimize_row.addWidget(self.btn_optimize, stretch=1)
        optimize_row.addWidget(self.btn_cancel)
        layout.addLayout(optimize_row)

        bottom_row = QHBoxLayout()
        self.btn_advanced = QPushButton("Erweiterte Einstellungen")
        self.btn_open_output = QPushButton("Ergebnisordner öffnen")
        self.btn_open_output.setEnabled(False)
        self.btn_hot_folder = QPushButton("Hot-Folder-Modus…")
        bottom_row.addWidget(self.btn_advanced)
        bottom_row.addWidget(self.btn_open_output)
        bottom_row.addWidget(self.btn_hot_folder)
        layout.addLayout(bottom_row)

        return panel

    def _connect_signals(self) -> None:
        self.drop_area.files_dropped.connect(self._on_files_selected)
        self.file_list.files_dropped.connect(self._on_files_selected)
        self.btn_select_file.clicked.connect(self._on_select_file_clicked)
        self.btn_select_folder.clicked.connect(self._on_select_folder_clicked)
        self.btn_select_output.clicked.connect(self._on_select_output_clicked)
        self.file_list.currentRowChanged.connect(self._on_file_row_changed)
        self.btn_remove_selected.clicked.connect(self._on_remove_selected_clicked)
        self.btn_clear_list.clicked.connect(self._on_clear_list_clicked)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        self.output_format_combo.currentIndexChanged.connect(self._on_output_format_changed)
        self.profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        self.btn_import_profile.clicked.connect(self._on_import_profile_clicked)
        self.view_mode_combo.currentTextChanged.connect(self._on_view_mode_changed)
        self.btn_color_picker.toggled.connect(self.compare_view.set_picker_mode)
        self.compare_view.pixel_picked.connect(self._on_compare_pixel_picked)
        self.btn_optimize.clicked.connect(self._on_optimize_clicked)
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)
        self.btn_advanced.clicked.connect(self._on_advanced_settings_clicked)
        self.btn_open_output.clicked.connect(self._on_open_output_clicked)
        self.btn_show_update.clicked.connect(self._on_show_update_clicked)
        self.btn_dismiss_update.clicked.connect(self._on_dismiss_update_clicked)
        self.btn_hot_folder.clicked.connect(self._on_hot_folder_clicked)

    # ------------------------------------------------------------ Update-Check
    def _start_update_check(self) -> None:
        self._update_checker = AsyncUpdateChecker(APP_VERSION, parent=self)
        self._update_checker.finished.connect(self._on_update_check_finished)
        self._update_checker.start()

    def _on_update_check_finished(self, result: UpdateCheckResult) -> None:
        if not result.update_available or not result.latest_version:
            return
        self._latest_release_url = result.release_url
        self.update_banner_label.setText(
            f"Eine neue Version ist verfügbar: {result.latest_version} (installiert: v{APP_VERSION})."
        )
        self.btn_show_update.setEnabled(self._latest_release_url is not None)
        self.update_banner.setVisible(True)

    def _on_show_update_clicked(self) -> None:
        if self._latest_release_url:
            QDesktopServices.openUrl(QUrl(self._latest_release_url))

    def _on_dismiss_update_clicked(self) -> None:
        self.controller.settings.check_for_updates_enabled = False
        self.controller.persist_settings()
        self.update_banner.setVisible(False)

    def _on_hot_folder_clicked(self) -> None:
        if self._hot_folder_dialog is None:
            from src.app.ui.hot_folder_dialog import HotFolderDialog

            self._hot_folder_dialog = HotFolderDialog(self.controller.settings, self)
        self._hot_folder_dialog.show()
        self._hot_folder_dialog.raise_()
        self._hot_folder_dialog.activateWindow()

    # ------------------------------------------------------------- Helpers
    def _reload_profiles(self) -> None:
        from src.core.color.icc_manager import list_available_profiles

        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItem("Kein Zielprofil", None)
        for info in list_available_profiles():
            self.profile_combo.addItem(info.name, str(info.path))
        self.profile_combo.blockSignals(False)

    def _set_view_modes(self, modes: list[str]) -> None:
        current = self.view_mode_combo.currentText()
        self.view_mode_combo.blockSignals(True)
        self.view_mode_combo.clear()
        self.view_mode_combo.addItems(modes)
        if current in modes:
            self.view_mode_combo.setCurrentText(current)
        self.view_mode_combo.blockSignals(False)
        self._on_view_mode_changed(self.view_mode_combo.currentText())

    # -------------------------------------------------------------- Slots
    def _on_files_selected(self, files: list[Path]) -> None:
        self.controller.set_files(files)
        self.file_list.clear()
        for f in files:
            self.file_list.addItem(str(f))
        self.output_label.setText(str(self.controller.output_dir) if self.controller.output_dir else "-")
        if files:
            self.file_list.setCurrentRow(0)

    def _on_remove_selected_clicked(self) -> None:
        selected_rows = sorted({self.file_list.row(item) for item in self.file_list.selectedItems()}, reverse=True)
        if not selected_rows:
            return
        for row in selected_rows:
            self.file_list.takeItem(row)
            del self.controller.selected_files[row]
        self._after_file_list_changed()

    def _on_clear_list_clicked(self) -> None:
        if self.file_list.count() == 0:
            return
        self.file_list.clear()
        self.controller.selected_files = []
        self._after_file_list_changed()

    def _after_file_list_changed(self) -> None:
        if not self.controller.selected_files:
            self._analysis_request_path = None
            self._current_original_rgba = None
            self._current_result_rgba = None
            self._current_softproof_rgba = None
            self._current_removed_pixels_rgba = None
            self._current_strengthened_pixels_rgba = None
            self._current_gamut_warning_rgba = None
            self._current_white_mask_rgba = None
            self._set_view_modes([VIEW_ORIGINAL])
            self.summary_text.setPlainText("Keine Dateien ausgewählt.")

    def _on_select_file_clicked(self) -> None:
        from src.config.defaults import SUPPORTED_IMPORT_FORMATS

        patterns = " ".join(f"*{ext}" for ext in sorted(SUPPORTED_IMPORT_FORMATS))
        files, _ = QFileDialog.getOpenFileNames(self, "Bild(er) auswählen", "", f"Bilder ({patterns})")
        if files:
            self._on_files_selected([Path(f) for f in files])

    def _on_select_folder_clicked(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Ordner auswählen")
        if folder:
            self._on_files_selected(collect_supported_files([Path(folder)]))

    def _on_select_output_clicked(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Ausgabeordner auswählen")
        if folder:
            self.controller.set_output_dir(Path(folder))
            self.output_label.setText(folder)

    def _on_preset_changed(self) -> None:
        preset = self.preset_combo.currentData()
        if preset is not None:
            self.controller.apply_preset(preset)
            self._refresh_output_format_combo()

    def _refresh_output_format_combo(self) -> None:
        """Hält die Ausgabeformat-Auswahl mit settings.export.output_format synchron,
        z. B. nachdem ein Preset (etwa DTF-King) das Format selbst gesetzt hat."""
        idx = self.output_format_combo.findData(self.controller.settings.export.output_format)
        if idx >= 0:
            self.output_format_combo.blockSignals(True)
            self.output_format_combo.setCurrentIndex(idx)
            self.output_format_combo.blockSignals(False)

    def _on_output_format_changed(self) -> None:
        fmt = self.output_format_combo.currentData()
        if fmt is not None:
            # OutputFormat erbt von str: QComboBox.currentData() liefert dafür
            # in PySide6 mitunter ein reines str-Objekt statt des Enum-Members
            # zurück (derselbe Effekt wie beim RenderingIntent-Absturz in
            # advanced_settings_dialog.py) - explizit re-wrappen.
            self.controller.settings.export.output_format = OutputFormat(fmt)

    def _on_profile_changed(self) -> None:
        path = self.profile_combo.currentData()
        self.controller.settings.color.target_profile_path = path

    def _on_import_profile_clicked(self) -> None:
        from src.core.color.icc_manager import ICCProfileError, import_profile

        file, _ = QFileDialog.getOpenFileName(self, "ICC-Profil importieren", "", "ICC-Profile (*.icc *.icm)")
        if not file:
            return
        try:
            import_profile(Path(file))
            self._reload_profiles()
        except ICCProfileError as exc:
            QMessageBox.warning(self, "Import fehlgeschlagen", str(exc))

    def _on_file_row_changed(self, row: int) -> None:
        if row < 0 or row >= len(self.controller.selected_files):
            return
        path = self.controller.selected_files[row]
        self._start_analysis(path)

    def _start_analysis(self, path: Path) -> None:
        self.summary_text.setPlainText(f"Analysiere {path.name} …")
        self._analysis_request_path = path
        self._analysis_thread, self._analysis_worker = run_analysis_in_thread(path, self.controller.settings)
        # Bewusst eine QObject-gebundene Methode statt einer Lambda (siehe
        # ausführlicher Kommentar in run_analysis_in_thread) - nur so erkennt
        # Qt die Thread-Zugehörigkeit korrekt und liefert das Signal per
        # QueuedConnection im GUI-Thread aus, statt im Worker-Thread
        # abzustürzen.
        self._analysis_worker.finished.connect(self._on_analysis_finished)
        self._analysis_thread.start()

    def _on_analysis_finished(self, result, loaded, error, requested_path: Path) -> None:
        if requested_path != self._analysis_request_path:
            return  # veraltetes Ergebnis einer inzwischen verlassenen Datei - ignorieren
        if error or result is None:
            self.summary_text.setPlainText(f"Fehler bei der Analyse: {error}")
            return
        self._current_original_rgba = loaded.array
        self._current_result_rgba = None
        self._current_softproof_rgba = None
        self._current_removed_pixels_rgba = None
        self._current_strengthened_pixels_rgba = None
        self._current_gamut_warning_rgba = None
        self._current_white_mask_rgba = None
        self._current_transparency_only_rgba = None
        self._set_view_modes([VIEW_ORIGINAL])
        self.summary_text.setPlainText(_format_analysis_summary(result))

    def _on_view_mode_changed(self, mode: str) -> None:
        rgba = None
        if mode == VIEW_ORIGINAL:
            rgba = self._current_original_rgba
        elif mode == VIEW_RESULT:
            rgba = self._current_result_rgba
        elif mode == VIEW_SOFTPROOF:
            rgba = self._current_softproof_rgba
        elif mode == VIEW_ALPHA_MASK and self._current_result_rgba is not None:
            a = self._current_result_rgba[:, :, 3]
            rgba = np.dstack([a, a, a, np.full_like(a, 255)])
        elif mode == VIEW_WHITE_TEXTILE and self._current_result_rgba is not None:
            rgba = composite_over_background(self._current_result_rgba, (255, 255, 255))
        elif mode == VIEW_BLACK_TEXTILE and self._current_result_rgba is not None:
            rgba = composite_over_background(self._current_result_rgba, (20, 20, 20))
        elif mode == VIEW_REMOVED_PIXELS:
            rgba = self._current_removed_pixels_rgba
        elif mode == VIEW_STRENGTHENED_PIXELS:
            rgba = self._current_strengthened_pixels_rgba
        elif mode == VIEW_GAMUT_WARNING:
            rgba = self._current_gamut_warning_rgba
        elif mode == VIEW_WHITE_MASK:
            rgba = self._current_white_mask_rgba
        elif mode == VIEW_ORIGINAL_SOURCE:
            rgba = self._current_original_rgba
        elif mode == VIEW_TRANSPARENCY_ONLY:
            rgba = self._current_transparency_only_rgba
        elif mode == VIEW_DTF_KING_SOFTPROOF:
            rgba = self._current_softproof_rgba

        if rgba is None:
            return
        preview_rgba = downscale_for_preview(rgba, MAX_PREVIEW_DIMENSION_PX)
        self.preview_view.set_pixmap(rgba_array_to_qpixmap(_composite_checkerboard(preview_rgba)))

        if self._current_original_rgba is not None and self._current_result_rgba is not None:
            self.compare_view.set_images(
                rgba_array_to_qpixmap(
                    _composite_checkerboard(downscale_for_preview(self._current_original_rgba, MAX_PREVIEW_DIMENSION_PX))
                ),
                rgba_array_to_qpixmap(
                    _composite_checkerboard(downscale_for_preview(self._current_result_rgba, MAX_PREVIEW_DIMENSION_PX))
                ),
            )

    def _on_compare_pixel_picked(self, fx: float, fy: float) -> None:
        """Zeigt Vorher-/Nachher-Farbcode für die angeklickte Bildposition an.

        `fx`/`fy` sind normiert (0..1) und werden auf die ORIGINAL-/Ergebnis-
        Arrays in voller Auflösung umgerechnet - unabhängig davon, wie stark
        die angezeigte Vorschau herunterskaliert ist, damit der angezeigte
        Farbcode exakt dem tatsächlichen Pixelwert entspricht.
        """
        if self._current_original_rgba is None or self._current_result_rgba is None:
            self.picker_result_label.setText("Kein Vorher/Nachher-Ergebnis verfügbar.")
            return

        before_h, before_w = self._current_original_rgba.shape[:2]
        after_h, after_w = self._current_result_rgba.shape[:2]
        bx = min(before_w - 1, max(0, int(fx * before_w)))
        by = min(before_h - 1, max(0, int(fy * before_h)))
        ax = min(after_w - 1, max(0, int(fx * after_w)))
        ay = min(after_h - 1, max(0, int(fy * after_h)))

        before_px = self._current_original_rgba[by, bx]
        after_px = self._current_result_rgba[ay, ax]
        self.picker_result_label.setText(_format_picker_result(bx, by, before_px, after_px))

    def _on_optimize_clicked(self) -> None:
        if not self.controller.selected_files:
            QMessageBox.information(self, "Keine Dateien", "Bitte zuerst ein oder mehrere Bilder auswählen.")
            return
        if self.controller.output_dir is None:
            QMessageBox.information(self, "Kein Ausgabeordner", "Bitte zuerst einen Ausgabeordner wählen.")
            return

        process_fn = process_image_safe
        if self.controller.settings.export.output_format == OutputFormat.PDF_CMYK:
            dialog = DtfKingExportDialog(self.controller.settings, self.controller.selected_files[0], self)
            if not dialog.exec():
                return  # Benutzer hat abgebrochen - keine Datei wurde geschrieben
            process_fn = process_image_for_dtf_king_pdf_safe

        self.controller.persist_settings()
        self.btn_optimize.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(self.controller.selected_files))
        self.summary_text.setPlainText("Verarbeitung läuft …")

        self._batch_thread, self._batch_worker = run_batch_in_thread(
            self.controller.selected_files, self.controller.settings, self.controller.output_dir, process_fn
        )
        self._batch_worker.progress.connect(self._on_batch_progress)
        self._batch_worker.file_finished.connect(self._on_batch_file_finished)
        self._batch_worker.finished.connect(self._on_batch_finished)
        self._batch_worker.cancelled.connect(self._on_batch_cancelled)
        self._batch_thread.start()

    def _on_cancel_clicked(self) -> None:
        if self._batch_worker is not None:
            self._batch_worker.request_cancel()
            self.btn_cancel.setEnabled(False)

    def _on_batch_cancelled(self) -> None:
        self.btn_optimize.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.summary_text.setPlainText("Verarbeitung abgebrochen.")

    def _on_batch_progress(self, current: int, total: int, filename: str) -> None:
        self.progress_bar.setValue(current)
        self.summary_text.setPlainText(f"Verarbeite {current}/{total}: {filename}")

    def _on_batch_file_finished(self, report) -> None:
        self._last_reports[str(report.source_path)] = report
        if report.output_format == "pdf_cmyk":
            if report.success:
                self.summary_text.append(
                    f"\n{report.source_path.name}: PDF erfolgreich erzeugt und validiert -> {report.output_path.name}"
                )
            else:
                self.summary_text.append(f"\n{report.source_path.name}: Export fehlgeschlagen - {'; '.join(report.errors)}")
                return
        current_row = self.file_list.currentRow()
        if 0 <= current_row < len(self.controller.selected_files):
            if self.controller.selected_files[current_row] == report.source_path and report.success:
                self._load_result_preview(report)

    def _load_result_preview(self, report) -> None:
        try:
            self._current_result_rgba = load_image(report.output_path).array
        except Exception:
            self._current_result_rgba = None

        previews_dir = report.output_path.parent.parent / "previews"
        stem = report.source_path.stem

        softproof_path = previews_dir / f"{stem}_softproof.png"
        self._current_softproof_rgba = self._try_load(softproof_path)

        removed_path = previews_dir / f"{stem}_removed_pixels.png"
        self._current_removed_pixels_rgba = self._try_load(removed_path)

        strengthened_path = previews_dir / f"{stem}_strengthened_pixels.png"
        self._current_strengthened_pixels_rgba = self._try_load(strengthened_path)

        gamut_warning_path = previews_dir / f"{stem}_gamut_warning.png"
        self._current_gamut_warning_rgba = self._try_load(gamut_warning_path)

        transparency_only_path = previews_dir / f"{stem}_transparency_only.png"
        self._current_transparency_only_rgba = self._try_load(transparency_only_path)

        masks_dir = report.output_path.parent.parent / "masks"
        white_mask_path = masks_dir / f"{stem}_white_mask.png"
        self._current_white_mask_rgba = self._try_load(white_mask_path)

        # VIEW_RESULT/ALPHA_MASK/WEISS/SCHWARZ hängen alle an _current_result_rgba
        # (siehe _on_view_mode_changed) - ohne RGB-Ergebnis (z. B. beim
        # DTF-King-PDF-Export, wo das Ergebnis keine RGB-Datei ist) blieben sie
        # sonst als leere, funktionslose Einträge im Auswahlfeld stehen.
        has_rgb_result = self._current_result_rgba is not None
        modes = [VIEW_ORIGINAL]
        if has_rgb_result:
            modes += [VIEW_RESULT, VIEW_ALPHA_MASK, VIEW_WHITE_TEXTILE, VIEW_BLACK_TEXTILE]
        if self._current_softproof_rgba is not None:
            modes.insert(min(2, len(modes)), VIEW_SOFTPROOF)
        if self._current_removed_pixels_rgba is not None:
            modes.append(VIEW_REMOVED_PIXELS)
        if self._current_strengthened_pixels_rgba is not None:
            modes.append(VIEW_STRENGTHENED_PIXELS)
        if self._current_gamut_warning_rgba is not None:
            modes.append(VIEW_GAMUT_WARNING)
        if self._current_white_mask_rgba is not None:
            modes.append(VIEW_WHITE_MASK)
        # Drei klar getrennte, eindeutig benannte Zustände zusätzlich zu den
        # obigen (bestehenden) Ansichten anbieten (Prompt Abschnitt 7).
        modes.append(VIEW_ORIGINAL_SOURCE)
        if self._current_transparency_only_rgba is not None:
            modes.append(VIEW_TRANSPARENCY_ONLY)
        if self._current_softproof_rgba is not None:
            modes.append(VIEW_DTF_KING_SOFTPROOF)
        self._set_view_modes(modes)

        if has_rgb_result:
            self.view_mode_combo.setCurrentText(VIEW_RESULT)
        elif self._current_softproof_rgba is not None:
            self.view_mode_combo.setCurrentText(VIEW_DTF_KING_SOFTPROOF)
        else:
            self.view_mode_combo.setCurrentText(VIEW_ORIGINAL_SOURCE)

    @staticmethod
    def _try_load(path: Path) -> np.ndarray | None:
        if not path.exists():
            return None
        try:
            return load_image(path).array
        except Exception:
            return None

    def _on_batch_finished(self, summary) -> None:
        self.btn_optimize.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.btn_open_output.setEnabled(True)
        self.summary_text.setPlainText(_format_batch_summary(summary))

        if self.controller.output_dir is not None:
            from src.core.reporting.batch_report import write_batch_summary_report

            try:
                write_batch_summary_report(summary, self.controller.output_dir / "reports")
            except OSError:
                logger.exception("Zusammenfassender Abschlussbericht konnte nicht geschrieben werden.")
                self.summary_text.append(
                    "\nHinweis: Der zusammenfassende Abschlussbericht (batch_summary.json) konnte "
                    "nicht gespeichert werden. Die einzelnen Bilder wurden davon nicht beeinflusst."
                )

    def _on_advanced_settings_clicked(self) -> None:
        dialog = AdvancedSettingsDialog(self.controller.settings, self)
        if dialog.exec():
            dialog.apply_to_settings()
            self.controller.persist_settings()

    def _on_open_output_clicked(self) -> None:
        if self.controller.output_dir is None:
            return
        path = str(self.controller.output_dir)
        if sys.platform == "win32":
            os.startfile(path)  # noqa: S606
        else:
            subprocess.Popen(["xdg-open", path])


def _rgba_to_hex(px: np.ndarray) -> str:
    return f"#{int(px[0]):02X}{int(px[1]):02X}{int(px[2]):02X}"


def _color_swatch_html(px: np.ndarray) -> str:
    hex_code = _rgba_to_hex(px)
    return (
        f'<span style="background-color:{hex_code}; border:1px solid #888; '
        f'padding:0 12px; margin-right:4px;">&nbsp;</span>'
    )


def _format_picker_result(x: int, y: int, before_px: np.ndarray, after_px: np.ndarray) -> str:
    before_hex = _rgba_to_hex(before_px)
    after_hex = _rgba_to_hex(after_px)
    return (
        f"<b>Position:</b> ({x}, {y})<br>"
        f"<b>Vorher:</b> {_color_swatch_html(before_px)} {before_hex} &nbsp; "
        f"RGB({before_px[0]}, {before_px[1]}, {before_px[2]}) &nbsp; Alpha={before_px[3]}<br>"
        f"<b>Nachher:</b> {_color_swatch_html(after_px)} {after_hex} &nbsp; "
        f"RGB({after_px[0]}, {after_px[1]}, {after_px[2]}) &nbsp; Alpha={after_px[3]}"
    )


def _composite_checkerboard(rgba: np.ndarray) -> np.ndarray:
    h, w = rgba.shape[:2]
    bg = checkerboard_background(w, h)
    alpha = rgba[:, :, 3:4].astype(np.float32) / 255.0
    out = rgba[:, :, :3].astype(np.float32) * alpha + bg[:, :, :3].astype(np.float32) * (1 - alpha)
    result = np.dstack([out.astype(np.uint8), np.full((h, w), 255, dtype=np.uint8)])
    return result


_TYPE_LABELS = {
    "hard_logo": "Logo oder Schriftzug",
    "illustration": "Illustration/KI-Grafik",
    "photo": "Foto",
    "soft_shadow": "Motiv mit weichem Schatten",
    "unknown": "unbekannter Bildtyp",
}


def _format_analysis_summary(result) -> str:
    type_label = _TYPE_LABELS.get(result.detected_type.value, result.detected_type.value)
    lines = [
        f"Das Bild wurde als {type_label} erkannt.",
        f"Größe: {result.width} x {result.height} px  |  Quellprofil: {result.source_profile}",
        "",
        "Automatisch geplante Verarbeitung:",
    ]
    if result.weak_alpha_count:
        lines.append(f"- {result.weak_alpha_count} Randpixel mit geringer Deckkraft entfernen (bis zum eingestellten Alpha-Wert)")
    if result.semi_transparent_count:
        lines.append(f"- {result.semi_transparent_count} halbtransparente Pixel prüfen und bereinigen")
    if result.likely_soft_shadow:
        lines.append("- Weiche Schatten erkannt - werden beibehalten")
    if result.semi_transparent_mostly_at_edges:
        lines.append("- Farbsäume an den Kanten korrigieren")
    if result.small_pixel_island_count:
        lines.append(f"- {result.small_pixel_island_count} kleine Pixelinseln entfernen")
    if result.small_hole_count:
        lines.append(f"- {result.small_hole_count} kleine transparente Löcher schließen")
    lines.append("- Farben für das gewählte Druckprofil anpassen")
    lines.append("- RGB-PNG mit Transparenz für den DTF-RIP erzeugen")
    lines.append("- Softproof-Vorschau erstellen")

    if result.warnings:
        lines.append("")
        for w in result.warnings:
            lines.append(f"Hinweis: {w.message}")

    lines.append("")
    lines.append("Bereit für 'Automatisch optimieren'.")
    return "\n".join(lines)


def _format_batch_summary(summary) -> str:
    lines = [
        f"Fertig: {summary.succeeded} von {summary.total_files} Dateien erfolgreich optimiert.",
    ]
    if summary.failed:
        lines.append(f"{summary.failed} Datei(en) fehlgeschlagen.")
    lines.append(f"Dauer: {summary.total_duration_seconds:.1f} s")
    lines.append("")
    for report in summary.reports:
        status = "OK" if report.success else "FEHLER"
        lines.append(f"[{status}] {Path(report.source_path).name if report.source_path else '?'}")
        for w in report.warnings:
            lines.append(f"   Hinweis: {w}")
        for e in report.errors:
            lines.append(f"   Fehler: {e}")
    lines.append("")
    lines.append(
        "Hinweis: Diese Bildschirmvorschau ist keine Garantie für das endgültige Druckergebnis. "
        "Das Ergebnis hängt zusätzlich von Drucker, Tinte, Folie/Pulver, RIP, Textil und Pressparametern ab."
    )
    return "\n".join(lines)
