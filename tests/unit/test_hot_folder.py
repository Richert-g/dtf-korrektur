from src.config.defaults import ProcessingSettings
from src.core.automation.hot_folder import HotFolderWatcher, run_hot_folder_loop
from src.models.report import ImageProcessingReport


def test_new_stable_file_becomes_ready_on_second_poll(tmp_path):
    (tmp_path / "a.png").write_bytes(b"stable-content")
    watcher = HotFolderWatcher(tmp_path)

    assert watcher.poll() == []  # erster Poll: nur als "pending" gemerkt
    assert watcher.poll() == [tmp_path / "a.png"]  # Größe unverändert -> bereit


def test_growing_file_is_not_returned_until_size_stabilizes(tmp_path):
    path = tmp_path / "a.png"
    path.write_bytes(b"12345")
    watcher = HotFolderWatcher(tmp_path)

    assert watcher.poll() == []
    path.write_bytes(b"1234567890")  # noch am Schreiben -> Größe hat sich geändert
    assert watcher.poll() == []
    assert watcher.poll() == [path]  # jetzt zwei Polls mit gleicher Größe


def test_already_processed_file_is_never_returned_again(tmp_path):
    path = tmp_path / "a.png"
    path.write_bytes(b"stable-content")
    watcher = HotFolderWatcher(tmp_path)

    watcher.poll()
    ready = watcher.poll()
    assert ready == [path]
    watcher.mark_processed(path)

    assert watcher.poll() == []
    assert watcher.poll() == []
    assert watcher.processed_count == 1


def test_unsupported_extension_is_ignored(tmp_path):
    (tmp_path / "notes.txt").write_bytes(b"hello")
    watcher = HotFolderWatcher(tmp_path)

    watcher.poll()
    assert watcher.poll() == []


def test_file_removed_before_stable_is_dropped_without_error(tmp_path):
    path = tmp_path / "a.png"
    path.write_bytes(b"stable-content")
    watcher = HotFolderWatcher(tmp_path)

    watcher.poll()  # als "pending" gemerkt
    path.unlink()
    assert watcher.poll() == []  # verschwindet stillschweigend aus der Merkliste


def test_poll_on_missing_source_dir_returns_empty_list(tmp_path):
    watcher = HotFolderWatcher(tmp_path / "does_not_exist")
    assert watcher.poll() == []


def test_run_hot_folder_loop_processes_ready_file_and_stops(tmp_path):
    source = tmp_path / "in"
    source.mkdir()
    output = tmp_path / "out"
    (source / "a.png").write_bytes(b"stable-content")

    processed_paths = []
    processed_reports = []
    stop_flag = {"stop": False}

    def process_fn(path, settings, output_dir):
        assert output_dir == output
        report = ImageProcessingReport(source_path=path, success=True)
        return report

    def on_file_processed(path, report):
        processed_paths.append(path)
        processed_reports.append(report)
        stop_flag["stop"] = True

    settings = ProcessingSettings()
    run_hot_folder_loop(
        source,
        output,
        settings,
        process_fn,
        should_stop=lambda: stop_flag["stop"],
        on_file_processed=on_file_processed,
        poll_interval=0.01,
    )

    assert processed_paths == [source / "a.png"]
    assert processed_reports[0].success is True


def test_run_hot_folder_loop_stops_immediately_when_should_stop_is_already_true(tmp_path):
    source = tmp_path / "in"
    source.mkdir()
    output = tmp_path / "out"
    (source / "a.png").write_bytes(b"stable-content")

    calls = []
    run_hot_folder_loop(
        source,
        output,
        ProcessingSettings(),
        process_fn=lambda p, s, o: calls.append(p),
        should_stop=lambda: True,
        on_file_processed=lambda p, r: calls.append(p),
    )

    assert calls == []


def test_run_hot_folder_loop_does_not_reprocess_same_file_across_polls(tmp_path):
    """Eine Datei, die zwischen zwei Verarbeitungsrunden weiterhin unveraendert
    im Ordner liegt, darf kein zweites Mal verarbeitet werden."""
    source = tmp_path / "in"
    source.mkdir()
    output = tmp_path / "out"
    (source / "a.png").write_bytes(b"stable-content")

    processed_count = {"n": 0}
    poll_count = {"n": 0}

    def process_fn(path, settings, output_dir):
        processed_count["n"] += 1
        return ImageProcessingReport(source_path=path, success=True)

    def should_stop():
        poll_count["n"] += 1
        return poll_count["n"] > 6  # genug Runden, um eine erneute Verarbeitung zu erlauben, falls fehlerhaft

    run_hot_folder_loop(
        source,
        output,
        ProcessingSettings(),
        process_fn,
        should_stop=should_stop,
        on_file_processed=lambda p, r: None,
        poll_interval=0.01,
    )

    assert processed_count["n"] == 1
