"""Vorab-Dialog für den DTF-King-PDF-Export (Prompt Abschnitte 4, 5, 9, 10).

Zeigt: welches konkrete ICC-Profil verwendet wird (Datei + Beschreibung) bzw.
eine klare Fehlermeldung, falls keines/ein ungeeignetes gewählt ist; Eingabe
von Breite/Höhe/dpi mit Live-Neuberechnung der effektiven Auflösung inkl.
Warnung unterhalb 300 dpi; eine vollständige Zusammenfassung vor dem Export.
Der "Exportieren"-Button ist deaktiviert, solange das Zielprofil ungültig ist.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from src.config.defaults import ProcessingSettings
from src.core.export.dtf_king_export import DtfKingExportError, DtfKingExportSummary, build_export_summary


class DtfKingExportDialog(QDialog):
    def __init__(self, settings: ProcessingSettings, reference_file: Path, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.reference_file = reference_file
        self.setWindowTitle("DTF-King Export – ISO Coated v2 (ECI)")
        self.resize(560, 620)

        layout = QVBoxLayout(self)

        self.profile_label = QLabel()
        self.profile_label.setWordWrap(True)
        layout.addWidget(self.profile_label)

        size_group = QGroupBox("Druckgröße")
        form = QFormLayout(size_group)

        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(1.0, 10000.0)
        self.width_spin.setSuffix(" mm")
        self.width_spin.setDecimals(1)
        form.addRow("Breite", self.width_spin)

        self.manual_height_check = QCheckBox("Höhe manuell festlegen (statt proportional)")
        form.addRow(self.manual_height_check)

        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(1.0, 10000.0)
        self.height_spin.setSuffix(" mm")
        self.height_spin.setDecimals(1)
        self.height_spin.setEnabled(False)
        form.addRow("Höhe", self.height_spin)

        self.dpi_spin = QDoubleSpinBox()
        self.dpi_spin.setRange(1.0, 2400.0)
        self.dpi_spin.setDecimals(0)
        self.dpi_spin.setValue(settings.export.pdf_target_dpi or 300.0)
        form.addRow("Ziel-Auflösung", self.dpi_spin)

        self.allow_upscale_check = QCheckBox("Fehlende Bildpixel künstlich hochskalieren, falls nötig")
        self.allow_upscale_check.setChecked(settings.export.pdf_allow_upscale)
        form.addRow(self.allow_upscale_check)

        layout.addWidget(size_group)

        self.dpi_warning_label = QLabel()
        self.dpi_warning_label.setWordWrap(True)
        self.dpi_warning_label.setStyleSheet("color: #a15c00; font-weight: bold;")
        self.dpi_warning_label.hide()
        layout.addWidget(self.dpi_warning_label)

        layout.addWidget(QLabel("Zusammenfassung vor dem Export:"))
        self.summary_table = QTableWidget(0, 2)
        self.summary_table.horizontalHeader().setVisible(False)
        self.summary_table.verticalHeader().setVisible(False)
        self.summary_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.summary_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.summary_table, stretch=1)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Exportieren")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self._initializing = True
        self._init_size_defaults()
        self._initializing = False

        self.width_spin.valueChanged.connect(self._on_size_changed)
        self.height_spin.valueChanged.connect(self._on_size_changed)
        self.dpi_spin.valueChanged.connect(self._on_size_changed)
        self.allow_upscale_check.toggled.connect(self._on_size_changed)
        self.manual_height_check.toggled.connect(self._on_manual_height_toggled)

        self._refresh()

    def _init_size_defaults(self) -> None:
        export = self.settings.export
        try:
            summary = build_export_summary(self.reference_file, self.settings)
            width_mm, height_mm = summary.page_size_mm
        except DtfKingExportError:
            width_mm, height_mm = export.pdf_width_mm or 100.0, export.pdf_height_mm or 100.0
        self.width_spin.setValue(export.pdf_width_mm or width_mm)
        self.height_spin.setValue(export.pdf_height_mm or height_mm)
        self.manual_height_check.setChecked(export.pdf_height_mm is not None)
        self.height_spin.setEnabled(export.pdf_height_mm is not None)

    def _on_manual_height_toggled(self, checked: bool) -> None:
        self.height_spin.setEnabled(checked)
        self._on_size_changed()

    def _on_size_changed(self) -> None:
        if self._initializing:
            return
        self._refresh()

    def _refresh(self) -> None:
        export = self.settings.export
        export.pdf_width_mm = self.width_spin.value()
        export.pdf_height_mm = self.height_spin.value() if self.manual_height_check.isChecked() else None
        export.pdf_target_dpi = self.dpi_spin.value()
        export.pdf_allow_upscale = self.allow_upscale_check.isChecked()

        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        try:
            summary = build_export_summary(self.reference_file, self.settings)
        except DtfKingExportError as exc:
            self.profile_label.setText(f"✗ {exc}")
            self.profile_label.setStyleSheet("color: #b00020; font-weight: bold;")
            self.summary_table.setRowCount(0)
            self.dpi_warning_label.hide()
            ok_button.setEnabled(False)
            return

        profile_path = self.settings.color.target_profile_path
        profile_file = Path(profile_path).name if profile_path else "-"
        self.profile_label.setText(f"✓ ICC-Zielprofil: {summary.target_profile}  ({profile_file})")
        self.profile_label.setStyleSheet("color: #1a7f37; font-weight: bold;")

        if summary.dpi_warning:
            self.dpi_warning_label.setText(summary.dpi_warning)
            self.dpi_warning_label.show()
        else:
            self.dpi_warning_label.hide()

        self._populate_summary(summary)
        ok_button.setEnabled(True)

    def _populate_summary(self, summary: DtfKingExportSummary) -> None:
        rows = [
            ("Preset", summary.preset_name),
            ("Quellprofil", summary.source_profile),
            ("Zielprofil", summary.target_profile),
            ("ICC-Konvertierung durchgeführt", "Ja" if summary.icc_conversion_performed else "Nein"),
            ("Zielprofil eingebettet", "Ja" if summary.icc_profile_embedded else "Nein"),
            ("Ausgabefarbraum", summary.output_color_space),
            ("Rendering Intent", summary.rendering_intent),
            ("Schwarzpunktkompensation", "aktiviert" if summary.black_point_compensation else "deaktiviert"),
            ("Zusätzliche Sättigungsreduktion", "Ja" if summary.additional_saturation_reduction else "Nein"),
            ("Zusätzliche Gamut-Korrektur", "Ja" if summary.additional_gamut_correction else "Nein"),
            ("Transparenz vorhanden", "Ja" if summary.has_transparency else "Nein"),
            ("Hintergrund transparent", "Ja" if summary.background_transparent else "Nein"),
            ("Seitengröße", f"{summary.page_size_mm[0]:.1f} x {summary.page_size_mm[1]:.1f} mm"),
            ("Effektive dpi", f"{summary.effective_dpi:.0f}"),
            ("Zielauflösung erreicht (≥{:.0f} dpi)".format(self.dpi_spin.value()), "Ja" if summary.meets_target_dpi else "Nein"),
            ("Spiegelung", "Ja" if summary.mirrored else "Nein"),
            ("Dateiformat", summary.file_format),
        ]
        self.summary_table.setRowCount(len(rows))
        for i, (key, value) in enumerate(rows):
            self.summary_table.setItem(i, 0, QTableWidgetItem(key))
            self.summary_table.setItem(i, 1, QTableWidgetItem(str(value)))
        self.summary_table.resizeColumnsToContents()
