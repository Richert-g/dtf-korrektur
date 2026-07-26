from pathlib import Path
from unittest.mock import patch

import pytest

from src.utils.fs_utils import ensure_dir, retry_on_oserror


def test_ensure_dir_creates_new_directory(tmp_path: Path):
    target = tmp_path / "a" / "b" / "c"
    result = ensure_dir(target)
    assert target.exists()
    assert result == target


def test_ensure_dir_idempotent_on_existing_directory(tmp_path: Path):
    target = tmp_path / "existing"
    target.mkdir()
    ensure_dir(target)  # darf nicht werfen
    assert target.exists()


def test_ensure_dir_retries_transient_failure(tmp_path: Path):
    target = tmp_path / "flaky"
    call_count = {"n": 0}
    real_mkdir = Path.mkdir

    def flaky_mkdir(self, *args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise OSError(2, "Das System kann die angegebene Datei nicht finden")
        return real_mkdir(self, *args, **kwargs)

    with patch("pathlib.Path.mkdir", flaky_mkdir), patch("time.sleep", lambda s: None):
        ensure_dir(target, retries=5, delay_seconds=0)

    assert target.exists()
    assert call_count["n"] == 3


def test_ensure_dir_raises_after_exhausting_retries(tmp_path: Path):
    target = tmp_path / "always_fails"

    def always_fail(self, *args, **kwargs):
        raise OSError(3, "Das System kann den angegebenen Pfad nicht finden")

    with patch("pathlib.Path.mkdir", always_fail), patch("time.sleep", lambda s: None):
        with pytest.raises(OSError):
            ensure_dir(target, retries=3, delay_seconds=0)


def test_ensure_dir_retries_when_mkdir_succeeds_but_not_yet_visible(tmp_path: Path):
    """Simuliert Cloud-Sync-Race: mkdir() wirft nichts, is_dir() sieht es aber erst später."""
    target = tmp_path / "not_yet_visible"
    real_mkdir = Path.mkdir
    call_count = {"n": 0}

    def fake_mkdir(self, *args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] < 2:
            return  # "erfolgreicher" Aufruf, der aber nichts anlegt
        return real_mkdir(self, *args, **kwargs)

    with patch("pathlib.Path.mkdir", fake_mkdir), patch("time.sleep", lambda s: None):
        ensure_dir(target, retries=5, delay_seconds=0)

    assert target.exists()
    assert call_count["n"] == 2


def test_retry_on_oserror_succeeds_after_transient_failures():
    call_count = {"n": 0}

    def flaky():
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise OSError(9, "Bad file descriptor")
        return "ok"

    with patch("time.sleep", lambda s: None):
        result = retry_on_oserror(flaky, retries=5, delay_seconds=0)

    assert result == "ok"
    assert call_count["n"] == 3


def test_retry_on_oserror_raises_after_exhausting_retries():
    def always_fail():
        raise OSError(2, "Das System kann die angegebene Datei nicht finden")

    with patch("time.sleep", lambda s: None):
        with pytest.raises(OSError):
            retry_on_oserror(always_fail, retries=3, delay_seconds=0)


def test_retry_on_oserror_passes_through_return_value():
    result = retry_on_oserror(lambda: 42)
    assert result == 42
