import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox

from src.app.ui.custom_preset_manager_dialog import CustomPresetManagerDialog
from src.config.defaults import ProcessingSettings
from src.core.presets.custom_presets import load_custom_presets, save_custom_preset


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def _isolated_presets_file(tmp_path, monkeypatch):
    fake_file = tmp_path / "presets.json"
    monkeypatch.setattr("src.core.presets.custom_presets.get_presets_file", lambda: fake_file)


def test_dialog_lists_existing_presets_sorted(qapp):
    save_custom_preset("Zebra", ProcessingSettings())
    save_custom_preset("Apfel", ProcessingSettings())

    dlg = CustomPresetManagerDialog()

    items = [dlg.list_widget.item(i).text() for i in range(dlg.list_widget.count())]
    assert items == ["Apfel", "Zebra"]


def test_rename_without_selection_shows_info_and_does_nothing(qapp, monkeypatch):
    shown = []
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **kw: shown.append(a))

    dlg = CustomPresetManagerDialog()
    dlg._on_rename_clicked()

    assert len(shown) == 1
    assert dlg.changed is False


def test_delete_without_selection_shows_info_and_does_nothing(qapp, monkeypatch):
    shown = []
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **kw: shown.append(a))

    dlg = CustomPresetManagerDialog()
    dlg._on_delete_clicked()

    assert len(shown) == 1
    assert dlg.changed is False


def test_rename_success_updates_list_and_marks_changed(qapp, monkeypatch):
    save_custom_preset("Alt", ProcessingSettings())
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **kw: ("Neu", True)))

    dlg = CustomPresetManagerDialog()
    dlg.list_widget.setCurrentRow(0)
    dlg._on_rename_clicked()

    assert dlg.changed is True
    items = [dlg.list_widget.item(i).text() for i in range(dlg.list_widget.count())]
    assert items == ["Neu"]
    assert "Neu" in load_custom_presets()


def test_rename_cancelled_by_user_does_nothing(qapp, monkeypatch):
    save_custom_preset("Alt", ProcessingSettings())
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **kw: ("Neu", False)))

    dlg = CustomPresetManagerDialog()
    dlg.list_widget.setCurrentRow(0)
    dlg._on_rename_clicked()

    assert dlg.changed is False
    assert "Alt" in load_custom_presets()


def test_rename_collision_shows_warning_and_keeps_original(qapp, monkeypatch):
    save_custom_preset("A", ProcessingSettings())
    save_custom_preset("B", ProcessingSettings())
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **kw: ("B", True)))
    warned = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **kw: warned.append(a))

    dlg = CustomPresetManagerDialog()
    dlg.list_widget.setCurrentRow(0)  # "A"
    dlg._on_rename_clicked()

    assert len(warned) == 1
    assert set(load_custom_presets()) == {"A", "B"}


def test_delete_confirmed_removes_preset(qapp, monkeypatch):
    save_custom_preset("Weg", ProcessingSettings())
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.StandardButton.Yes)

    dlg = CustomPresetManagerDialog()
    dlg.list_widget.setCurrentRow(0)
    dlg._on_delete_clicked()

    assert dlg.changed is True
    assert load_custom_presets() == {}


def test_delete_cancelled_keeps_preset(qapp, monkeypatch):
    save_custom_preset("Bleibt", ProcessingSettings())
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.StandardButton.No)

    dlg = CustomPresetManagerDialog()
    dlg.list_widget.setCurrentRow(0)
    dlg._on_delete_clicked()

    assert dlg.changed is False
    assert "Bleibt" in load_custom_presets()
