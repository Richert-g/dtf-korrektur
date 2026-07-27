import pytest

pytest.importorskip("PySide6")

from PySide6.QtNetwork import QNetworkReply
from PySide6.QtWidgets import QApplication

from src.app.workers.update_check_async import AsyncUpdateChecker


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class _FakeReplyData:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def data(self) -> bytes:
        return self._body


class _FakeReply:
    """Duck-typed Ersatz für QNetworkReply, ohne echten Netzwerkzugriff -
    _on_finished() liest nur error()/errorString()/readAll(), das reicht aus,
    um die Auswertungslogik isoliert zu testen (siehe test_update_check.py
    für die reine Parsing-Logik selbst)."""

    def __init__(
        self,
        body: bytes,
        error=QNetworkReply.NetworkError.NoError,
        error_string: str = "",
        finished: bool = True,
    ) -> None:
        self._body = body
        self._error = error
        self._error_string = error_string
        self._finished = finished
        self.delete_later_called = False
        self.abort_called = False

    def error(self):
        return self._error

    def errorString(self) -> str:
        return self._error_string

    def readAll(self) -> _FakeReplyData:
        return _FakeReplyData(self._body)

    def deleteLater(self) -> None:
        self.delete_later_called = True

    def isFinished(self) -> bool:
        return self._finished

    def abort(self) -> None:
        self.abort_called = True


def test_on_finished_parses_successful_response(qapp):
    checker = AsyncUpdateChecker("1.0.13")
    checker._reply = _FakeReply(b'{"tag_name": "v1.0.14", "html_url": "https://github.com/x/y"}')

    received = []
    checker.finished.connect(received.append)
    checker._on_finished()

    assert len(received) == 1
    assert received[0].update_available is True
    assert received[0].latest_version == "v1.0.14"
    assert received[0].release_url == "https://github.com/x/y"


def test_on_finished_handles_network_error(qapp):
    checker = AsyncUpdateChecker("1.0.13")
    checker._reply = _FakeReply(b"", error=QNetworkReply.NetworkError.HostNotFoundError, error_string="kein Internet")

    received = []
    checker.finished.connect(received.append)
    checker._on_finished()

    assert received[0].update_available is False
    assert received[0].error == "kein Internet"


def test_on_finished_handles_malformed_json(qapp):
    checker = AsyncUpdateChecker("1.0.13")
    checker._reply = _FakeReply(b"not json")

    received = []
    checker.finished.connect(received.append)
    checker._on_finished()

    assert received[0].update_available is False
    assert received[0].error is not None


def test_on_finished_clears_reply_reference_and_deletes_it(qapp):
    checker = AsyncUpdateChecker("1.0.13")
    fake_reply = _FakeReply(b'{"tag_name": "v1.0.13"}')
    checker._reply = fake_reply

    checker._on_finished()

    assert checker._reply is None
    assert fake_reply.delete_later_called is True


def test_on_finished_without_reply_does_nothing(qapp):
    checker = AsyncUpdateChecker("1.0.13")
    checker._reply = None

    received = []
    checker.finished.connect(received.append)
    checker._on_finished()  # darf nicht werfen

    assert received == []


def test_on_timeout_aborts_unfinished_reply(qapp):
    checker = AsyncUpdateChecker("1.0.13")
    fake_reply = _FakeReply(b"", finished=False)
    checker._reply = fake_reply

    checker._on_timeout()

    assert fake_reply.abort_called is True


def test_on_timeout_does_not_abort_already_finished_reply(qapp):
    checker = AsyncUpdateChecker("1.0.13")
    fake_reply = _FakeReply(b"", finished=True)
    checker._reply = fake_reply

    checker._on_timeout()

    assert fake_reply.abort_called is False
