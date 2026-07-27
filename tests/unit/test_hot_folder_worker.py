import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from src.app.workers.hot_folder_worker import HotFolderWorker
from src.config.defaults import ProcessingSettings
from src.models.report import ImageProcessingReport


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_worker_emits_file_processed_and_stopped(qapp, tmp_path):
    source = tmp_path / "in"
    source.mkdir()
    output = tmp_path / "out"
    (source / "a.png").write_bytes(b"data")

    def process_fn(path, settings, output_dir):
        return ImageProcessingReport(source_path=path, success=True)

    worker = HotFolderWorker(source, output, ProcessingSettings(), process_fn, poll_interval=0.01)

    received = []
    stopped = []
    worker.file_processed.connect(lambda path, report: received.append((path, report)))
    worker.file_processed.connect(lambda *_: worker.request_stop())
    worker.stopped.connect(lambda: stopped.append(True))

    worker.run()

    assert len(received) == 1
    assert received[0][0] == source / "a.png"
    assert stopped == [True]


def test_request_stop_before_run_exits_immediately(qapp, tmp_path):
    source = tmp_path / "in"
    source.mkdir()
    output = tmp_path / "out"

    worker = HotFolderWorker(source, output, ProcessingSettings(), process_fn=lambda p, s, o: None)
    worker.request_stop()

    stopped = []
    worker.stopped.connect(lambda: stopped.append(True))
    worker.run()

    assert stopped == [True]
