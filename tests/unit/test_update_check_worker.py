import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from src.app.workers.update_check_worker import UpdateCheckWorker
from src.core.update.update_check import UpdateCheckResult


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_worker_emits_finished_with_check_result(qapp, monkeypatch):
    fake_result = UpdateCheckResult(update_available=True, latest_version="v9.9.9", release_url="https://github.com/x")
    monkeypatch.setattr(
        "src.app.workers.update_check_worker.check_for_update", lambda current_version: fake_result
    )

    worker = UpdateCheckWorker("1.0.13")
    received = []
    worker.finished.connect(received.append)

    worker.run()

    assert received == [fake_result]
