"""Verwaltungsdialog für benutzerdefinierte Presets: umbenennen und löschen.
Speichern eines neuen Presets erfolgt direkt im Hauptfenster (Button "Als
Preset speichern…"), da dort bereits die aktuellen Einstellungen vorliegen.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.presets.custom_presets import (
    CustomPresetError,
    delete_custom_preset,
    load_custom_presets,
    rename_custom_preset,
)


class CustomPresetManagerDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Benutzerdefinierte Presets verwalten")
        self.resize(380, 320)
        self.changed = False

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Gespeicherte, benutzerdefinierte Presets:"))

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget, stretch=1)
        self._reload_list()

        btn_row = QHBoxLayout()
        self.btn_rename = QPushButton("Umbenennen…")
        self.btn_delete = QPushButton("Löschen")
        btn_row.addWidget(self.btn_rename)
        btn_row.addWidget(self.btn_delete)
        layout.addLayout(btn_row)

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        self.btn_close = QPushButton("Schließen")
        close_row.addWidget(self.btn_close)
        layout.addLayout(close_row)

        self.btn_rename.clicked.connect(self._on_rename_clicked)
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        self.btn_close.clicked.connect(self.accept)

    def _reload_list(self) -> None:
        self.list_widget.clear()
        for name in sorted(load_custom_presets()):
            self.list_widget.addItem(name)

    def _selected_name(self) -> str | None:
        item = self.list_widget.currentItem()
        return item.text() if item is not None else None

    def _on_rename_clicked(self) -> None:
        name = self._selected_name()
        if name is None:
            QMessageBox.information(self, "Kein Preset ausgewählt", "Bitte zuerst ein Preset in der Liste auswählen.")
            return
        new_name, ok = QInputDialog.getText(self, "Preset umbenennen", "Neuer Name:", text=name)
        if not ok or not new_name.strip():
            return
        try:
            rename_custom_preset(name, new_name)
        except CustomPresetError as exc:
            QMessageBox.warning(self, "Umbenennen nicht möglich", str(exc))
            return
        self.changed = True
        self._reload_list()

    def _on_delete_clicked(self) -> None:
        name = self._selected_name()
        if name is None:
            QMessageBox.information(self, "Kein Preset ausgewählt", "Bitte zuerst ein Preset in der Liste auswählen.")
            return
        answer = QMessageBox.question(
            self,
            "Preset löschen?",
            f"Benutzerdefiniertes Preset '{name}' wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            delete_custom_preset(name)
        except CustomPresetError as exc:
            QMessageBox.warning(self, "Löschen nicht möglich", str(exc))
            return
        self.changed = True
        self._reload_list()
