from pathlib import Path

from PIL import Image

from src.config.defaults import ProcessingSettings
from src.core.pipeline import process_image
from tests.fixtures.synthetic_images import make_logo_with_white_halo


def test_diff_overlay_files_created_for_logo(tmp_path: Path):
    src_path = tmp_path / "logo.png"
    make_logo_with_white_halo().save(src_path)
    output_root = tmp_path / "output"

    settings = ProcessingSettings()  # write_diff_overlays ist standardmäßig aktiv
    report = process_image(src_path, settings, output_root)

    removed_path = output_root / "previews" / "logo_removed_pixels.png"
    strengthened_path = output_root / "previews" / "logo_strengthened_pixels.png"
    assert removed_path.exists()
    assert strengthened_path.exists()

    with Image.open(removed_path) as img:
        assert img.mode == "RGBA"
        assert img.size == (64, 64)

    assert any("Diff-Vorschau" in s.description for s in report.applied_steps)


def test_diff_overlays_skipped_when_disabled(tmp_path: Path):
    src_path = tmp_path / "logo.png"
    make_logo_with_white_halo().save(src_path)
    output_root = tmp_path / "output"

    settings = ProcessingSettings()
    settings.export.write_diff_overlays = False
    process_image(src_path, settings, output_root)

    removed_path = output_root / "previews" / "logo_removed_pixels.png"
    assert not removed_path.exists()
