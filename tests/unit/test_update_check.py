import json
import urllib.error

from src.core.update.update_check import check_for_update, is_newer_version


def test_is_newer_version_detects_patch_bump():
    assert is_newer_version("v1.0.13", "1.0.12") is True


def test_is_newer_version_detects_minor_and_major_bump():
    assert is_newer_version("v1.1.0", "1.0.99") is True
    assert is_newer_version("v2.0.0", "1.99.99") is True


def test_is_newer_version_false_when_equal_or_older():
    assert is_newer_version("v1.0.13", "1.0.13") is False
    assert is_newer_version("v1.0.12", "1.0.13") is False


def test_is_newer_version_tolerates_missing_v_prefix_and_suffixes():
    assert is_newer_version("1.0.14", "1.0.13") is True
    assert is_newer_version("v1.0.14-beta", "1.0.13") is True


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_check_for_update_reports_available_update(monkeypatch):
    payload = {"tag_name": "v1.0.14", "html_url": "https://github.com/Richert-g/dtf-korrektur/releases/tag/v1.0.14"}
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: _FakeResponse(payload))

    result = check_for_update("1.0.13")

    assert result.update_available is True
    assert result.latest_version == "v1.0.14"
    assert result.release_url == "https://github.com/Richert-g/dtf-korrektur/releases/tag/v1.0.14"
    assert result.error is None


def test_check_for_update_reports_no_update_when_current():
    def _fake_urlopen(*args, **kwargs):
        return _FakeResponse({"tag_name": "v1.0.13", "html_url": "https://github.com/Richert-g/dtf-korrektur/releases/tag/v1.0.13"})

    import urllib.request

    orig = urllib.request.urlopen
    urllib.request.urlopen = _fake_urlopen
    try:
        result = check_for_update("1.0.13")
    finally:
        urllib.request.urlopen = orig

    assert result.update_available is False
    assert result.latest_version == "v1.0.13"


def test_check_for_update_never_raises_on_network_error(monkeypatch):
    def _raise(*args, **kwargs):
        raise urllib.error.URLError("kein Internet")

    monkeypatch.setattr("urllib.request.urlopen", _raise)

    result = check_for_update("1.0.13")

    assert result.update_available is False
    assert result.error is not None


def test_check_for_update_never_raises_on_malformed_json(monkeypatch):
    class _BadResponse(_FakeResponse):
        def read(self) -> bytes:
            return b"not json"

    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: _BadResponse({}))

    result = check_for_update("1.0.13")

    assert result.update_available is False
    assert result.error is not None


def test_check_for_update_rejects_untrusted_release_url(monkeypatch):
    """Selbst wenn die GitHub-API kompromittiert waere/eine ungewoehnliche
    Antwort liefert, wird nur ein echter github.com-Link zum Oeffnen angeboten."""
    payload = {"tag_name": "v1.0.14", "html_url": "https://evil.example.com/phish"}
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: _FakeResponse(payload))

    result = check_for_update("1.0.13")

    assert result.update_available is True
    assert result.release_url is None


def test_check_for_update_missing_tag_name_reports_error(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: _FakeResponse({}))

    result = check_for_update("1.0.13")

    assert result.update_available is False
    assert result.error is not None
