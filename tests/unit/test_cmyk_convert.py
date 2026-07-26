from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageCms

from src.core.color.cmyk_convert import CmykConversionError, convert_rgba_to_output_cmyk
from src.core.color.icc_manager import get_srgb_profile, load_icc_profile
from src.models.enums import RenderingIntent

_FOGRA39 = Path("resources/profiles/CMYK/CoatedFOGRA39.icc")


def _target_profile():
    profile = load_icc_profile(_FOGRA39)
    assert profile is not None
    return profile


def test_alpha_is_returned_unchanged():
    rgba = np.zeros((5, 5, 4), dtype=np.uint8)
    rgba[:, :, :3] = [30, 200, 60]
    rgba[:, :, 3] = 255
    rgba[0, 0, 3] = 0
    rgba[1, 1, 3] = 128

    result = convert_rgba_to_output_cmyk(
        rgba, get_srgb_profile(), _target_profile(), RenderingIntent.RELATIVE_COLORIMETRIC, True
    )
    assert np.array_equal(result.alpha, rgba[:, :, 3])


def test_output_is_genuine_4_channel_cmyk_uint8():
    rgba = np.zeros((4, 4, 4), dtype=np.uint8)
    rgba[:, :, :3] = [200, 30, 30]
    rgba[:, :, 3] = 255

    result = convert_rgba_to_output_cmyk(
        rgba, get_srgb_profile(), _target_profile(), RenderingIntent.RELATIVE_COLORIMETRIC, True
    )
    assert result.cmyk.shape == (4, 4, 4)
    assert result.cmyk.dtype == np.uint8


def test_matches_direct_littlecms_transform_no_extra_correction():
    """Die Funktion darf keine eigene Näherungsformel verwenden - das Ergebnis
    muss exakt einer direkten LittleCMS-Transformation entsprechen."""
    rgba = np.zeros((3, 3, 4), dtype=np.uint8)
    rgba[:, :, :3] = [30, 200, 60]
    rgba[:, :, 3] = 255

    target = _target_profile()
    result = convert_rgba_to_output_cmyk(rgba, get_srgb_profile(), target, RenderingIntent.RELATIVE_COLORIMETRIC, True)

    transform = ImageCms.buildTransform(
        get_srgb_profile(),
        target,
        "RGB",
        "CMYK",
        renderingIntent=ImageCms.Intent.RELATIVE_COLORIMETRIC,
        flags=ImageCms.Flags.BLACKPOINTCOMPENSATION,
    )
    expected_img = ImageCms.applyTransform(Image.fromarray(np.ascontiguousarray(rgba[:, :, :3]), "RGB"), transform)
    expected = np.array(expected_img, dtype=np.uint8)

    assert np.array_equal(result.cmyk, expected)


def test_rejects_non_rgba_array():
    rgb_only = np.zeros((4, 4, 3), dtype=np.uint8)
    with pytest.raises(CmykConversionError):
        convert_rgba_to_output_cmyk(
            rgb_only, get_srgb_profile(), _target_profile(), RenderingIntent.RELATIVE_COLORIMETRIC, True
        )
