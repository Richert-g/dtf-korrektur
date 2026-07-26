from pathlib import Path
from unittest.mock import patch

import pytest

from src.utils.fs_utils import ensure_dir


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
