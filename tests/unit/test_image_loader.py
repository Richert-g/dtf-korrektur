from pathlib import Path

import pytest

from src.core.analysis.image_loader import ImageLoadError, load_image
from tests.fixtures.synthetic_images import make_fully_opaque, make_no_alpha_image


def test_load_png_without_alpha(tmp_path: Path):
    img = make_no_alpha_image()
    p = tmp_path / "no_alpha.png"
    img.save(p)

    loaded = load_image(p)
    assert loaded.array.shape[2] == 4
    assert loaded.had_alpha is False
    assert loaded.array[:, :, 3].min() == 255


def test_load_png_with_alpha(tmp_path: Path):
    img = make_fully_opaque()
    p = tmp_path / "opaque.png"
    img.save(p)

    loaded = load_image(p)
    assert loaded.had_alpha is True
    assert loaded.array.shape == (32, 32, 4)


def test_load_corrupted_file_raises(tmp_path: Path):
    p = tmp_path / "broken.png"
    p.write_bytes(b"this is not a real png file")

    with pytest.raises(ImageLoadError):
        load_image(p)


def test_load_missing_file_raises(tmp_path: Path):
    with pytest.raises(ImageLoadError):
        load_image(tmp_path / "does_not_exist.png")


def test_load_unsupported_extension_raises(tmp_path: Path):
    p = tmp_path / "file.xyz"
    p.write_bytes(b"data")
    with pytest.raises(ImageLoadError):
        load_image(p)


@pytest.mark.parametrize("ext,fmt", [(".jpg", "JPEG"), (".bmp", "BMP"), (".tif", "TIFF"), (".webp", "WEBP")])
def test_load_various_formats(tmp_path: Path, ext, fmt):
    img = make_no_alpha_image()
    p = tmp_path / f"img{ext}"
    img.save(p, format=fmt)
    loaded = load_image(p)
    assert loaded.array.shape[2] == 4
