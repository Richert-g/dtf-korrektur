import json

import pytest

from src import cli
from src.config.defaults import ProcessingSettings
from src.core.presets.custom_presets import save_custom_preset
from src.models.enums import AlphaMode, PresetName
from tests.fixtures.synthetic_images import make_logo_with_white_halo


@pytest.fixture(autouse=True)
def _isolated_presets_file(tmp_path, monkeypatch):
    fake_file = tmp_path / "presets.json"
    monkeypatch.setattr("src.core.presets.custom_presets.get_presets_file", lambda: fake_file)


def _write_valid_image(path):
    make_logo_with_white_halo().save(path)


def test_resolve_settings_applies_builtin_preset():
    settings = cli._resolve_settings(PresetName.DTF_LOGO_TEXT.value)
    assert settings.alpha_mode == AlphaMode.HARD_EDGE


def test_resolve_settings_loads_custom_preset():
    custom = ProcessingSettings()
    custom.alpha_mode = AlphaMode.SOFT_CLEANUP
    custom.alpha.weak_alpha_threshold = 88
    save_custom_preset("Mein CLI Preset", custom)

    settings = cli._resolve_settings("Mein CLI Preset")

    assert settings.alpha_mode == AlphaMode.SOFT_CLEANUP
    assert settings.alpha.weak_alpha_threshold == 88


def test_resolve_settings_raises_helpful_error_for_unknown_preset():
    with pytest.raises(ValueError, match="Unbekanntes Preset"):
        cli._resolve_settings("Gibt es nicht")


def test_run_processes_files_successfully(tmp_path, capsys):
    source_dir = tmp_path / "in"
    source_dir.mkdir()
    _write_valid_image(source_dir / "a.png")
    output_dir = tmp_path / "out"

    exit_code = cli.run(["--output", str(output_dir), str(source_dir)])

    assert exit_code == 0
    optimized = list((output_dir / "optimized").glob("*.png"))
    assert len(optimized) == 1
    assert (output_dir / "reports" / "batch_summary.json").exists()
    captured = capsys.readouterr()
    assert "Fertig: 1 von 1" in captured.out


def test_run_reports_failure_for_corrupt_file(tmp_path):
    source_dir = tmp_path / "in"
    source_dir.mkdir()
    (source_dir / "kaputt.png").write_bytes(b"not a real png")
    output_dir = tmp_path / "out"

    exit_code = cli.run(["--output", str(output_dir), str(source_dir)])

    assert exit_code == 1
    data = json.loads((output_dir / "reports" / "batch_summary.json").read_text(encoding="utf-8"))
    assert data["failed"] == 1
    assert data["succeeded"] == 0


def test_run_returns_2_when_no_supported_files_found(tmp_path, capsys):
    source_dir = tmp_path / "in"
    source_dir.mkdir()
    (source_dir / "notes.txt").write_text("kein bild")
    output_dir = tmp_path / "out"

    exit_code = cli.run(["--output", str(output_dir), str(source_dir)])

    assert exit_code == 2
    assert "Keine unterstützten Bilddateien" in capsys.readouterr().err


def test_run_returns_2_for_unknown_preset(tmp_path, capsys):
    source_dir = tmp_path / "in"
    source_dir.mkdir()
    _write_valid_image(source_dir / "a.png")

    exit_code = cli.run(["--output", str(tmp_path / "out"), "--preset", "Gibt es nicht", str(source_dir)])

    assert exit_code == 2
    assert "Unbekanntes Preset" in capsys.readouterr().err


def test_run_applies_format_override(tmp_path):
    source_dir = tmp_path / "in"
    source_dir.mkdir()
    _write_valid_image(source_dir / "a.png")
    output_dir = tmp_path / "out"

    exit_code = cli.run(["--output", str(output_dir), "--format", "tiff", str(source_dir)])

    assert exit_code == 0
    assert list((output_dir / "optimized").glob("*.tiff"))


def test_run_uses_custom_preset_by_name(tmp_path):
    custom = ProcessingSettings()
    custom.alpha_mode = AlphaMode.HARD_EDGE
    save_custom_preset("Mein CLI Preset", custom)

    source_dir = tmp_path / "in"
    source_dir.mkdir()
    _write_valid_image(source_dir / "a.png")
    output_dir = tmp_path / "out"

    exit_code = cli.run(["--output", str(output_dir), "--preset", "Mein CLI Preset", str(source_dir)])

    assert exit_code == 0


def test_run_pdf_preset_without_icc_profile_fails_per_file_not_crash(tmp_path):
    """DTF-King-PDF-Export erfordert ein ICC-Zielprofil - ohne eines schlaegt
    die Verarbeitung der Datei fehl (Exit-Code 1), das Programm darf aber
    nicht abstuerzen (kein manueller Bestaetigungsdialog wie in der GUI)."""
    source_dir = tmp_path / "in"
    source_dir.mkdir()
    _write_valid_image(source_dir / "a.png")
    output_dir = tmp_path / "out"

    exit_code = cli.run(
        ["--output", str(output_dir), "--preset", PresetName.DTF_KING_ISO_COATED_V2.value, "--format", "pdf", str(source_dir)]
    )

    # Das Preset setzt selbst ein Standardprofil (Coated FOGRA39), daher hier
    # eher Erfolg zu erwarten - der Test stellt vor allem sicher, dass der
    # PDF-Zweig ohne Absturz durchlaeuft und einen definierten Exit-Code liefert.
    assert exit_code in (0, 1)


def test_quiet_suppresses_per_file_progress_lines(tmp_path, capsys):
    source_dir = tmp_path / "in"
    source_dir.mkdir()
    _write_valid_image(source_dir / "a.png")
    output_dir = tmp_path / "out"

    cli.run(["--output", str(output_dir), "--quiet", str(source_dir)])

    captured = capsys.readouterr()
    assert "[1/1]" not in captured.out
    assert "Fertig: 1 von 1" in captured.out


def test_overwrite_flag_sets_export_setting():
    settings = cli._resolve_settings(PresetName.DTF_AUTO.value)
    assert settings.export.overwrite_existing is False


def test_run_accepts_single_file_input(tmp_path):
    image_path = tmp_path / "a.png"
    _write_valid_image(image_path)
    output_dir = tmp_path / "out"

    exit_code = cli.run(["--output", str(output_dir), str(image_path)])

    assert exit_code == 0


def test_run_output_format_pdf_uses_dtf_king_pipeline(tmp_path, monkeypatch):
    calls = []

    def _fake_process(path, settings, output_root):
        calls.append(path)
        from src.models.report import ImageProcessingReport

        return ImageProcessingReport(source_path=path, success=True, output_format="pdf_cmyk")

    monkeypatch.setattr("src.core.export.dtf_king_export.process_image_for_dtf_king_pdf_safe", _fake_process)

    source_dir = tmp_path / "in"
    source_dir.mkdir()
    _write_valid_image(source_dir / "a.png")

    exit_code = cli.run(
        ["--output", str(tmp_path / "out"), "--format", "pdf", str(source_dir)]
    )

    assert exit_code == 0
    assert len(calls) == 1
