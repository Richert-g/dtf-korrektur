"""Erweiterte Einstellungen (Prompt Abschnitt 13) - optionaler Expertenbereich."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.config.defaults import AlphaThresholds, ProcessingSettings
from src.models.enums import AlphaMode, AlphaThresholdOrder, RenderingIntent, WeakAlphaAction

ALPHA_THRESHOLD_ORDER_LABELS = {
    AlphaThresholdOrder.REMOVE_FIRST: "Zuerst bearbeiten, dann volldeckend setzen",
    AlphaThresholdOrder.STRENGTHEN_FIRST: "Zuerst volldeckend setzen, dann bearbeiten",
}

WEAK_ALPHA_ACTION_LABELS = {
    WeakAlphaAction.SET_TRANSPARENT: "Transparenz auf 0 setzen",
    WeakAlphaAction.DELETE_PIXEL: "Pixel vollständig löschen",
}


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
        weak_layout.setContentsMargins(0, 4, 0, 4)
        weak_layout.setSpacing(2)

        self.weak_enabled_checkbox = QCheckBox("Pixel mit geringer Deckkraft bearbeiten")
        self.weak_enabled_checkbox.setChecked(a.weak_alpha_threshold_enabled)
        self.weak_enabled_checkbox.setToolTip(
            "Bearbeitet Pixel mit geringer Deckkraft gemäß der gewählten Verarbeitungsmethode. Bei "
            "Deaktivierung bleiben Schwellenwert und Methode erhalten, der Verarbeitungsschritt wird "
            "aber übersprungen."
        )
        weak_layout.addWidget(self.weak_enabled_checkbox)

        weak_action_row = QHBoxLayout()
        weak_action_row.setContentsMargins(20, 0, 0, 0)
        weak_action_row.addWidget(QLabel("Verarbeitungsmethode:"))
        self.weak_action_combo = QComboBox()
        for action in WeakAlphaAction:
            self.weak_action_combo.addItem(WEAK_ALPHA_ACTION_LABELS[action], action)
        self.weak_action_combo.setCurrentIndex(list(WeakAlphaAction).index(a.weak_alpha_action))
        self.weak_action_combo.setToolTip(
            "'Transparenz auf 0 setzen': Pixel bleibt erhalten, nur der Alpha-Wert wird 0.\n"
            "'Pixel vollständig löschen': Pixel wird vollständig entfernt, es bleiben keine "
            "Farbinformationen (RGB) zurück."
        )
        weak_action_row.addWidget(self.weak_action_combo)
        weak_action_row.addStretch(1)
        weak_layout.addLayout(weak_action_row)

        weak_action_help = QLabel(
            "„Transparenz auf 0 setzen“: Der Pixel bleibt erhalten, erhält jedoch einen Alpha-Wert von 0.\n"
            "„Pixel vollständig löschen“: Der Pixel wird vollständig entfernt und enthält keine "
            "Farbinformationen mehr."
        )
        weak_action_help.setWordWrap(True)
        weak_action_help.setContentsMargins(20, 0, 0, 0)
        weak_layout.addWidget(weak_action_help)

        weak_threshold_row = QHBoxLayout()
        weak_threshold_row.setContentsMargins(20, 0, 0, 0)
        weak_threshold_row.addWidget(QLabel("Schwellenwert:"))
        self.weak_threshold = self._spin(
            self.WEAK_ALPHA_THRESHOLD_MIN,
            self.WEAK_ALPHA_THRESHOLD_MAX,
            a.weak_alpha_threshold,
            "Alle Pixel mit Alpha 0 bis einschließlich diesem Wert werden bearbeitet, alle Pixel mit "
            "einem höheren Alpha-Wert bleiben unverändert (0 = vollständig transparent, "
            "255 = vollständig deckend).",
        )
        weak_threshold_row.addWidget(self.weak_threshold)
        weak_threshold_row.addStretch(1)
        weak_layout.addLayout(weak_threshold_row)

        weak_help = QLabel(
            "Alle Pixel mit einem Alpha-Wert von 0 bis einschließlich des eingestellten Werts werden "
            "bearbeitet. Alle Pixel mit einem Alpha-Wert ÜBER dem Schwellenwert bleiben unverändert.\n"
            "0 = vollständig transparent, 255 = vollständig deckend"
        )
        weak_help.setWordWrap(True)
        weak_help.setContentsMargins(20, 0, 0, 0)
        weak_layout.addWidget(weak_help)

        self.weak_threshold_percent_label = QLabel()
        self.weak_threshold_percent_label.setWordWrap(True)
        self.weak_threshold_percent_label.setContentsMargins(20, 0, 0, 0)
        weak_layout.addWidget(self.weak_threshold_percent_label)

        self.weak_threshold_warning_label = QLabel()
        self.weak_threshold_warning_label.setWordWrap(True)
        self.weak_threshold_warning_label.setStyleSheet("color: #a15c00; font-weight: bold;")
        self.weak_threshold_warning_label.setContentsMargins(20, 0, 0, 0)
        weak_layout.addWidget(self.weak_threshold_warning_label)

        self.weak_threshold.valueChanged.connect(self._update_weak_threshold_info)
        self.weak_action_combo.currentIndexChanged.connect(self._on_weak_action_changed)
        self._update_weak_threshold_info(self.weak_threshold.value())
        self.weak_enabled_checkbox.toggled.connect(self.weak_threshold.setEnabled)
        self.weak_enabled_checkbox.toggled.connect(self.weak_action_combo.setEnabled)
        self.weak_threshold.setEnabled(a.weak_alpha_threshold_enabled)
        self.weak_action_combo.setEnabled(a.weak_alpha_threshold_enabled)

        form.addRow(weak_container)

        strengthen_container = QWidget()
        strengthen_layout = QVBoxLayout(strengthen_container)
        strengthen_layout.setContentsMargins(0, 4, 0, 4)
        strengthen_layout.setSpacing(2)

        self.near_opaque_enabled_checkbox = QCheckBox("Pixel mit hoher Deckkraft vollständig deckend setzen")
        self.near_opaque_enabled_checkbox.setChecked(a.near_opaque_threshold_enabled)
        self.near_opaque_enabled_checkbox.setToolTip(
            "Setzt Pixel mit hoher Deckkraft auf volle Deckkraft (255). Bei Deaktivierung bleibt der "
            "eingestellte Schwellenwert erhalten, der Verarbeitungsschritt wird aber übersprungen."
        )
        strengthen_layout.addWidget(self.near_opaque_enabled_checkbox)

        strengthen_threshold_row = QHBoxLayout()
        strengthen_threshold_row.setContentsMargins(20, 0, 0, 0)
        strengthen_threshold_row.addWidget(QLabel("Schwellenwert:"))
        self.near_opaque_threshold = self._spin(
            0,
            255,
            a.near_opaque_threshold,
            "Alle Pixel mit Alpha ab einschließlich diesem Wert werden auf volle Deckkraft (255) gesetzt.",
        )
        strengthen_threshold_row.addWidget(self.near_opaque_threshold)
        strengthen_threshold_row.addStretch(1)
        strengthen_layout.addLayout(strengthen_threshold_row)

        strengthen_help = QLabel(
            "Alle Pixel mit einem Alpha-Wert ab einschließlich des eingestellten Werts werden auf volle "
            "Deckkraft gesetzt.\n0 = vollständig transparent, 255 = vollständig deckend"
        )
        strengthen_help.setWordWrap(True)
        strengthen_help.setContentsMargins(20, 0, 0, 0)
        strengthen_layout.addWidget(strengthen_help)

        self.near_opaque_percent_label = QLabel()
        self.near_opaque_percent_label.setWordWrap(True)
        self.near_opaque_percent_label.setContentsMargins(20, 0, 0, 0)
        strengthen_layout.addWidget(self.near_opaque_percent_label)

        self.near_opaque_threshold.valueChanged.connect(self._update_near_opaque_info)
        self._update_near_opaque_info(self.near_opaque_threshold.value())
        self.near_opaque_enabled_checkbox.toggled.connect(self.near_opaque_threshold.setEnabled)
        self.near_opaque_threshold.setEnabled(a.near_opaque_threshold_enabled)

        form.addRow(strengthen_container)

        self.threshold_order_combo = QComboBox()
        for order in AlphaThresholdOrder:
            self.threshold_order_combo.addItem(ALPHA_THRESHOLD_ORDER_LABELS[order], order)
        self.threshold_order_combo.setCurrentIndex(list(AlphaThresholdOrder).index(a.threshold_order))
        self.threshold_order_combo.setToolTip(
            "Legt fest, welche der beiden obigen Funktionen zuerst läuft. Wirkt sich nur aus, wenn "
            "sich die beiden Schwellenwerte überschneiden (unüblich) - sonst liefern beide "
            "Reihenfolgen dasselbe Ergebnis."
        )
        form.addRow("Reihenfolge bei Überschneidung", self.threshold_order_combo)

        self.min_island = self._spin(0, 500, a.min_island_size_px, "Pixelinseln kleiner als dieser Wert werden entfernt.")
        form.addRow("Min. Inselgröße (px)", self.min_island)

        self.max_hole = self._spin(0, 2000, a.max_hole_fill_size_px, "Löcher bis zu dieser Größe werden geschlossen.")
        form.addRow("Max. Lochgröße (px)", self.max_hole)

        self.edge_choke = self._double_spin(0, 10, a.edge_choke_px, "Kantenrücknahme in Pixeln (0 = aus).")
        form.addRow("Kantenrücknahme (px)", self.edge_choke)

        self.edge_feather = self._double_spin(0, 10, a.edge_feather_radius, "Weichzeichnungsradius der Kante nach der Bereinigung.")
        form.addRow("Kantenglättung", self.edge_feather)

        return w

    def _on_weak_action_changed(self) -> None:
        self._update_weak_threshold_info(self.weak_threshold.value())

    def _update_weak_threshold_info(self, value: int) -> None:
        # WeakAlphaAction erbt von str: QComboBox.currentData() liefert dafür in
        # PySide6 mitunter ein reines str-Objekt statt des Enum-Members zurück -
        # ueber WeakAlphaAction(...) re-wrappen statt z. B. per == zu vergleichen.
        action = WeakAlphaAction(self.weak_action_combo.currentData())
        verb = "vollständig gelöscht" if action == WeakAlphaAction.DELETE_PIXEL else "transparent gemacht"
        percent = value / 255 * 100
        self.weak_threshold_percent_label.setText(
            f"{value} von 255 – Pixel bis etwa {percent:.1f} % Deckkraft werden {verb}"
        )
        if value >= self.WEAK_ALPHA_THRESHOLD_WARNING_FROM:
            self.weak_threshold_warning_label.setText(
                "Hoher Wert: Weiche Schatten, Rauch, Glow und geglättete Kanten können betroffen sein."
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
        a.weak_alpha_threshold_enabled = self.weak_enabled_checkbox.isChecked()
        a.weak_alpha_action = WeakAlphaAction(self.weak_action_combo.currentData())
        a.near_opaque_threshold = self.near_opaque_threshold.value()
        a.near_opaque_threshold_enabled = self.near_opaque_enabled_checkbox.isChecked()
        a.threshold_order = AlphaThresholdOrder(self.threshold_order_combo.currentData())
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
