import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from src.config.defaults import ProcessingSettings
from src.core.pipeline import process_image, process_image_safe
from tests.fixtures.synthetic_images import (
    make_logo_with_white_halo,
    make_no_alpha_image,
)


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_full_pipeline_creates_expected_outputs_and_preserves_original(tmp_path: Path):
    src_dir = tmp_path / "input"
    src_dir.mkdir()
    src_path = src_dir / "logo.png"
    make_logo_with_white_halo().save(src_path)
    original_hash = _hash_file(src_path)

    output_root = tmp_path / "output"
    settings = ProcessingSettings()

    report = process_image(src_path, settings, output_root)

    assert report.success is True
    assert report.output_path is not None
    assert report.output_path.exists()

    # Original darf nicht verändert werden
    assert _hash_file(src_path) == original_hash

    # Ausgabe ist ein gültiges RGBA-PNG
    with Image.open(report.output_path) as out_img:
        assert out_img.mode == "RGBA"
        assert out_img.size == (64, 64)
        assert "icc_profile" in out_img.info

    report_json_path = output_root / "reports" / "logo_report.json"
    report_html_path = output_root / "reports" / "logo_report.html"
    assert report_json_path.exists()
    assert report_html_path.exists()

    data = json.loads(report_json_path.read_text(encoding="utf-8"))
    assert data["detected_type"] == "hard_logo"
    assert data["success"] is True


def test_pipeline_handles_corrupted_file_without_crashing(tmp_path: Path):
    output_root = tmp_path / "output"
    bad_file = tmp_path / "broken.png"
    bad_file.write_bytes(b"not a real image")

    settings = ProcessingSettings()
    report = process_image_safe(bad_file, settings, output_root)

    assert report.success is False
    assert len(report.errors) > 0


def test_pipeline_no_alpha_image_gets_full_opacity_output(tmp_path: Path):
    src_path = tmp_path / "flat.png"
    make_no_alpha_image().save(src_path)

    output_root = tmp_path / "output"
    settings = ProcessingSettings()
    report = process_image(src_path, settings, output_root)

    with Image.open(report.output_path) as out_img:
        arr = np.array(out_img.convert("RGBA"))
        assert (arr[:, :, 3] == 255).all()


def test_pipeline_respects_overwrite_setting(tmp_path: Path):
    src_path = tmp_path / "logo.png"
    make_logo_with_white_halo().save(src_path)
    output_root = tmp_path / "output"

    settings = ProcessingSettings()
    settings.export.overwrite_existing = False

    report1 = process_image(src_path, settings, output_root)
    report2 = process_image(src_path, settings, output_root)

    assert report1.output_path != report2.output_path
    assert report1.output_path.exists()
    assert report2.output_path.exists()
