from pathlib import Path

from src.config.defaults import ProcessingSettings
from src.core.analysis.analyzer import analyze_image, analyze_image_safe
from src.models.enums import ImageType
from tests.fixtures.synthetic_images import make_logo_with_white_halo


def test_analyze_image_includes_classification(tmp_path: Path):
    p = tmp_path / "logo.png"
    make_logo_with_white_halo().save(p)

    result, loaded = analyze_image(p, ProcessingSettings())
    assert result.detected_type == ImageType.HARD_LOGO
    assert len(result.classification_reasons) > 0
    assert loaded.array.shape == (64, 64, 4)


def test_analyze_image_safe_handles_broken_file(tmp_path: Path):
    p = tmp_path / "broken.png"
    p.write_bytes(b"not an image")

    result, loaded, error = analyze_image_safe(p, ProcessingSettings())
    assert result is None
    assert loaded is None
    assert error is not None
