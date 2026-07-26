from pathlib import Path

import numpy as np
from PIL import Image

from src.core.export.raster_export import export_rgb_jpeg, export_rgba_tiff


def _sample_rgba(w=8, h=6):
    arr = np.zeros((h, w, 4), dtype=np.uint8)
    arr[:, :, 0] = 200
    arr[:, :, 1] = 40
    arr[:, :, 2] = 40
    arr[:, :, 3] = 255
    arr[0, 0, 3] = 0  # transparentes Eckpixel
    return arr


def test_tiff_export_preserves_alpha_channel(tmp_path: Path):
    rgba = _sample_rgba()
    out = tmp_path / "out.tiff"
    export_rgba_tiff(rgba, out)

    assert out.exists()
    with Image.open(out) as img:
        assert img.mode == "RGBA"
        loaded = np.array(img)
        assert np.array_equal(loaded, rgba)


def test_tiff_export_embeds_icc_profile(tmp_path: Path):
    from src.core.color.icc_manager import get_srgb_icc_bytes

    rgba = _sample_rgba()
    out = tmp_path / "out.tiff"
    export_rgba_tiff(rgba, out, icc_profile_bytes=get_srgb_icc_bytes())

    with Image.open(out) as img:
        assert "icc_profile" in img.info


def test_jpeg_export_has_no_alpha_and_flattens_on_background(tmp_path: Path):
    rgba = _sample_rgba()
    out = tmp_path / "out.jpg"
    export_rgb_jpeg(rgba, out, background_rgb=(255, 255, 255), quality=90)

    assert out.exists()
    with Image.open(out) as img:
        assert img.mode == "RGB"
        loaded = np.array(img)
        # das urspruenglich transparente Eckpixel muss jetzt (annaehernd) weiss
        # sein - JPEG-DCT-Blockartefakte an einem einzelnen Randpixel neben
        # einer starken Farbkante erlauben keine exakte Gleichheit, daher eine
        # großzügigere, aber immer noch aussagekräftige Toleranz.
        assert all(c > 200 for c in loaded[0, 0].tolist())
        # ein deckendes Pixel behaelt ungefaehr seine Farbe (JPEG ist verlustbehaftet)
        assert abs(int(loaded[3, 3, 0]) - 200) < 15


def test_jpeg_export_embeds_icc_profile(tmp_path: Path):
    from src.core.color.icc_manager import get_srgb_icc_bytes

    rgba = _sample_rgba()
    out = tmp_path / "out.jpg"
    export_rgb_jpeg(rgba, out, icc_profile_bytes=get_srgb_icc_bytes())

    with Image.open(out) as img:
        assert "icc_profile" in img.info
