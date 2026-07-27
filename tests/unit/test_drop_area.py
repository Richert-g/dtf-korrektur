from pathlib import Path

from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QApplication

from src.app.ui.drop_area import DropListWidget, collect_supported_files


def _app():
    return QApplication.instance() or QApplication([])


def test_collect_supported_files_filters_extensions(tmp_path: Path):
    png = tmp_path / "a.png"
    png.write_bytes(b"x")
    txt = tmp_path / "b.txt"
    txt.write_bytes(b"x")

    result = collect_supported_files([png, txt])
    assert result == [png]


def test_collect_supported_files_recurses_into_folders(tmp_path: Path):
    sub = tmp_path / "sub"
    sub.mkdir()
    img1 = tmp_path / "a.jpg"
    img1.write_bytes(b"x")
    img2 = sub / "b.png"
    img2.write_bytes(b"x")

    result = collect_supported_files([tmp_path])
    assert set(result) == {img1, img2}


# QMimeData ist kein QObject - PySide6 haelt dafuer keine automatische
# Referenz, wenn es nur lokal in einer Hilfsfunktion erzeugt wird. Ohne
# diese Keepalive-Liste gibt Python das Objekt frei, bevor der native
# QDropEvent noch darauf zugreift, was zu einer echten Access Violation
# fuehrt (reproduziert) - nicht im Produktivcode, sondern rein im Testaufbau.
_mime_keepalive: list[QMimeData] = []


def _make_drop_event(paths: list[Path]) -> QDropEvent:
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
    _mime_keepalive.append(mime)
    return QDropEvent(
        QPointF(1, 1), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier
    )


def test_drop_list_widget_emits_files_dropped_on_url_drop(tmp_path: Path):
    _app()
    png = tmp_path / "a.png"
    png.write_bytes(b"x")

    widget = DropListWidget()
    received = []
    widget.files_dropped.connect(lambda files: received.append(files))

    widget.dropEvent(_make_drop_event([png]))

    assert len(received) == 1
    assert received[0] == [png]


def test_drop_list_widget_ignores_drop_without_supported_files(tmp_path: Path):
    _app()
    txt = tmp_path / "b.txt"
    txt.write_bytes(b"x")

    widget = DropListWidget()
    received = []
    widget.files_dropped.connect(lambda files: received.append(files))

    widget.dropEvent(_make_drop_event([txt]))

    assert received == []


def test_drop_list_widget_accepts_drops():
    _app()
    widget = DropListWidget()
    assert widget.acceptDrops() is True
