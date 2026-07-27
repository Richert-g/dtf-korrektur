"""Erweiterte Einstellungen (Prompt Abschnitt 13) - optionaler Expertenbereich."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.config.defaults import AlphaThresholds, ProcessingSettings
from src.models.enums import AlphaMode, RenderingIntent


class AdvancedSettingsDialog(QDialog):
    # 255 ist bewusst nicht wählbar: alpha <= threshold wird gelöscht, bei 255
    # würden dadurch auch vollständig deckende Pixel entfernt.
    WEAK_ALPHA_THRESHOLD_MIN = 0
    WEAK_ALPHA_THRESHOLD_MAX = 254
    # Zentral in AlphaThresholds gepflegt, hier nur wiederverwendet.
    WEAK_ALPHA_THRESHOLD_WARNING_FROM = AlphaThresholds.weak_alpha_threshold_warning_from

    def __init__(self, settings: ProcessingSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Erweiterte Einstellungen")
        self.resize(480, 560)
        self.settings = settings

        layout = QVBoxLayout(self)
        tabs = QTabWidget(self)
        layout.addWidget(tabs)

        tabs.addTab(self._build_alpha_tab(), "Transparenz")
        tabs.addTab(self._build_halo_tab(), "Farbsaum")
        tabs.addTab(self._build_color_tab(), "Farbe")
        tabs.addTab(self._build_export_tab(), "Export")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_alpha_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        a = self.settings.alpha

        self.alpha_mode_combo = QComboBox()
        for mode in AlphaMode:
            self.alpha_mode_combo.addItem(mode.value, mode)
        self.alpha_mode_combo.setCurrentIndex(list(AlphaMode).index(self.settings.alpha_mode))
        self.alpha_mode_combo.setToolTip("AUTO wählt den Modus automatisch anhand des erkannten Bildtyps.")
        form.addRow("Alpha-Modus", self.alpha_mode_combo)

        weak_container = QWidget()
        weak_layout = QVBoxLayout(weak_container)
        weak_layout.setContentsMargins(0, 0, 0, 0)
        weak_layout.setSpacing(2)

        self.weak_threshold = self._spin(
            self.WEAK_ALPHA_THRESHOLD_MIN,
            self.WEAK_ALPHA_THRESHOLD_MAX,
            a.weak_alpha_threshold,
            "Alle Pixel mit Alpha 0 bis einschließlich diesem Wert werden vollständig transparent "
            "(0 = vollständig transparent, 255 = vollständig deckend).",
        )
        weak_layout.addWidget(self.weak_threshold)

        weak_help = QLabel(
            "Alle Pixel mit einem Alpha-Wert von 0 bis einschließlich des eingestellten Werts werden "
            "vollständig transparent.\n0 = vollständig transparent, 255 = vollständig deckend"
        )
        weak_help.setWordWrap(True)
        weak_layout.addWidget(weak_help)

        self.weak_threshold_percent_label = QLabel()
        self.weak_threshold_percent_label.setWordWrap(True)
        weak_layout.addWidget(self.weak_threshold_percent_label)

        self.weak_threshold_warning_label = QLabel()
        self.weak_threshold_warning_label.setWordWrap(True)
        self.weak_threshold_warning_label.setStyleSheet("color: #a15c00; font-weight: bold;")
        weak_layout.addWidget(self.weak_threshold_warning_label)

        self.weak_threshold.valueChanged.connect(self._update_weak_threshold_info)
        self._update_weak_threshold_info(self.weak_threshold.value())

        form.addRow("Pixel löschen bis Alpha-Wert", weak_container)

        strengthen_container = QWidget()
        strengthen_layout = QVBoxLayout(strengthen_container)
        strengthen_layout.setContentsMargins(0, 0, 0, 0)
        strengthen_layout.setSpacing(2)

        self.near_opaque_threshold = self._spin(
            0,
            255,
            a.near_opaque_threshold,
            "Alle Pixel mit Alpha ab einschließlich diesem Wert werden auf volle Deckkraft (255) gesetzt.",
        )
        strengthen_layout.addWidget(self.near_opaque_threshold)

        strengthen_help = QLabel(
            "Alle Pixel mit einem Alpha-Wert ab einschließlich des eingestellten Werts werden auf volle "
            "Deckkraft gesetzt.\n0 = vollständig transparent, 255 = vollständig deckend"
        )
        strengthen_help.setWordWrap(True)
        strengthen_layout.addWidget(strengthen_help)

        self.near_opaque_percent_label = QLabel()
        self.near_opaque_percent_label.setWordWrap(True)
        strengthen_layout.addWidget(self.near_opaque_percent_label)

        self.near_opaque_threshold.valueChanged.connect(self._update_near_opaque_info)
        self._update_near_opaque_info(self.near_opaque_threshold.value())

        form.addRow("Pixel ab Alpha-Wert auf volle Deckkraft setzen", strengthen_container)

        self.min_island = self._spin(0, 500, a.min_island_size_px, "Pixelinseln kleiner als dieser Wert werden entfernt.")
        form.addRow("Min. Inselgröße (px)", self.min_island)

        self.max_hole = self._spin(0, 2000, a.max_hole_fill_size_px, "Löcher bis zu dieser Größe werden geschlossen.")
        form.addRow("Max. Lochgröße (px)", self.max_hole)

        self.edge_choke = self._double_spin(0, 10, a.edge_choke_px, "Kantenrücknahme in Pixeln (0 = aus).")
        form.addRow("Kantenrücknahme (px)", self.edge_choke)

        self.edge_feather = self._double_spin(0, 10, a.edge_feather_radius, "Weichzeichnungsradius der Kante nach der Bereinigung.")
        form.addRow("Kantenglättung", self.edge_feather)

        return w

    def _update_weak_threshold_info(self, value: int) -> None:
        percent = value / 255 * 100
        self.weak_threshold_percent_label.setText(
            f"{value} von 255 – Pixel bis etwa {percent:.1f} % Deckkraft werden gelöscht"
        )
        if value >= self.WEAK_ALPHA_THRESHOLD_WARNING_FROM:
            self.weak_threshold_warning_label.setText(
                "Hoher Wert: Weiche Schatten, Rauch, Glow und geglättete Kanten können entfernt werden."
            )
            self.weak_threshold_warning_label.show()
        else:
            self.weak_threshold_warning_label.hide()

    def _update_near_opaque_info(self, value: int) -> None:
        percent = value / 255 * 100
        self.near_opaque_percent_label.setText(
            f"{value} von 255 – Pixel ab etwa {percent:.1f} % Deckkraft werden voll deckend gemacht"
        )

    def _build_halo_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        h = self.settings.halo

        self.halo_enabled = QCheckBox("Farbsaum-/Halo-Korrektur aktiv")
        self.halo_enabled.setChecked(h.enabled)
        self.halo_enabled.setToolTip("Entfernt weiße/graue/schwarze Farbsäume an halbtransparenten Kanten.")
        form.addRow(self.halo_enabled)

        self.halo_strength = self._double_spin(0, 1, h.strength, "Stärke der Farbsaum-Korrektur (0-1).", step=0.05)
        form.addRow("Stärke", self.halo_strength)

        self.halo_radius = self._spin(1, 30, h.search_radius_px, "Suchradius für benachbarte deckende Pixel.")
        form.addRow("Suchradius (px)", self.halo_radius)

        return w

    def _build_color_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        c = self.settings.color
        g = self.settings.gamut

        self.target_profile_edit = QLineEdit(c.target_profile_path or "")
        self.target_profile_edit.setToolTip("Pfad zum ICC-Zielprofil (leer = kein Zielprofil, keine Farbanpassung).")
        form.addRow("ICC-Zielprofil", self.target_profile_edit)

        self.auto_intent = QCheckBox("Rendering Intent automatisch wählen")
        self.auto_intent.setChecked(c.auto_select_intent)
        form.addRow(self.auto_intent)

        self.intent_combo = QComboBox()
        for intent in RenderingIntent:
            self.intent_combo.addItem(intent.value, intent)
        self.intent_combo.setCurrentIndex(list(RenderingIntent).index(c.rendering_intent))
        self.intent_combo.setToolTip("Nur wirksam, wenn 'automatisch wählen' deaktiviert ist.")
        form.addRow("Rendering Intent", self.intent_combo)

        self.bpc = QCheckBox("Schwarzpunktkompensation")
        self.bpc.setChecked(c.black_point_compensation)
        form.addRow(self.bpc)

        self.gamut_warning = QCheckBox("Gamut-Warnung anzeigen")
        self.gamut_warning.setChecked(c.show_gamut_warning)
        form.addRow(self.gamut_warning)

        self.max_saturation = self._double_spin(
            0, 1, g.max_auto_saturation_reduction, "Maximale automatische Sättigungsreduktion.", step=0.05
        )
        form.addRow("Max. Sättigungsreduktion", self.max_saturation)

        return w

    def _build_export_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        e = self.settings.export

        self.write_alpha_mask = QCheckBox("Alpha-Maske exportieren")
        self.write_alpha_mask.setChecked(e.write_alpha_mask)
        form.addRow(self.write_alpha_mask)

        self.write_white_mask = QCheckBox("Weißunterlegungs-Vorschau exportieren")
        self.write_white_mask.setChecked(e.write_white_mask)
        self.write_white_mask.setToolTip("Nur eine Vorschau/Hilfsdatei - die Weißkanalsteuerung erfolgt im DTF-RIP.")
        form.addRow(self.write_white_mask)

        self.write_cmyk = QCheckBox("CMYK-TIFF-Vorschau exportieren")
        self.write_cmyk.setChecked(e.write_cmyk_tiff)
        self.write_cmyk.setToolTip("Erfordert ein gültiges ICC-Zielprofil.")
        form.addRow(self.write_cmyk)

        self.keep_metadata = QCheckBox("Metadaten beibehalten")
        self.keep_metadata.setChecked(e.keep_metadata)
        form.addRow(self.keep_metadata)

        self.overwrite = QCheckBox("Bestehende Dateien überschreiben")
        self.overwrite.setChecked(e.overwrite_existing)
        form.addRow(self.overwrite)

        self.suffix_edit = QLineEdit(e.filename_suffix_optimized)
        form.addRow("Dateinamenssuffix", self.suffix_edit)

        return w

    @staticmethod
    def _spin(lo: int, hi: int, value: int, tooltip: str) -> QSpinBox:
        s = QSpinBox()
        s.setRange(lo, hi)
        s.setValue(value)
        s.setToolTip(tooltip)
        return s

    @staticmethod
    def _double_spin(lo: float, hi: float, value: float, tooltip: str, step: float = 0.1) -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setSingleStep(step)
        s.setValue(value)
        s.setToolTip(tooltip)
        return s

    def apply_to_settings(self) -> None:
        a = self.settings.alpha
        # AlphaMode/RenderingIntent erben von str: QComboBox.currentData() liefert
        # dafuer in PySide6 mitunter ein reines str-Objekt statt des Enum-Members
        # zurueck (die Enum-Identitaet geht bei der QVariant-Rueckkonvertierung
        # verloren). Explizit re-wrappen, damit spaeteres .value nicht crasht.
        self.settings.alpha_mode = AlphaMode(self.alpha_mode_combo.currentData())
        a.weak_alpha_threshold = self.weak_threshold.value()
        a.near_opaque_threshold = self.near_opaque_threshold.value()
        a.min_island_size_px = self.min_island.value()
        a.max_hole_fill_size_px = self.max_hole.value()
        a.edge_choke_px = self.edge_choke.value()
        a.edge_feather_radius = self.edge_feather.value()

        h = self.settings.halo
        h.enabled = self.halo_enabled.isChecked()
        h.strength = self.halo_strength.value()
        h.search_radius_px = self.halo_radius.value()

        c = self.settings.color
        c.target_profile_path = self.target_profile_edit.text().strip() or None
        c.auto_select_intent = self.auto_intent.isChecked()
        c.rendering_intent = RenderingIntent(self.intent_combo.currentData())
        c.black_point_compensation = self.bpc.isChecked()
        c.show_gamut_warning = self.gamut_warning.isChecked()
        self.settings.gamut.max_auto_saturation_reduction = self.max_saturation.value()

        e = self.settings.export
        e.write_alpha_mask = self.write_alpha_mask.isChecked()
        e.write_white_mask = self.write_white_mask.isChecked()
        e.write_cmyk_tiff = self.write_cmyk.isChecked()
        e.keep_metadata = self.keep_metadata.isChecked()
        e.overwrite_existing = self.overwrite.isChecked()
        e.filename_suffix_optimized = self.suffix_edit.text().strip() or "_dtf_optimized"
