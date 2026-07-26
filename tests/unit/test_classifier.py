import numpy as np

from src.config.defaults import AlphaThresholds, ClassificationThresholds
from src.core.analysis.alpha_analysis import analyze_alpha_channel
from src.core.classification.classifier import classify_image
from src.models.enums import ImageType
from tests.fixtures.synthetic_images import (
    make_large_soft_shadow,
    make_logo_with_white_halo,
    make_no_alpha_image,
)

ALPHA_THRESH = AlphaThresholds()
CLASS_THRESH = ClassificationThresholds()


def _classify(img):
    arr = np.array(img.convert("RGBA"))
    stats = analyze_alpha_channel(arr, ALPHA_THRESH)
    return classify_image(arr, stats, CLASS_THRESH)


def test_logo_classified_as_hard_logo():
    result = _classify(make_logo_with_white_halo())
    assert result.image_type == ImageType.HARD_LOGO
    assert len(result.reasons) > 0


def test_soft_shadow_classified_correctly():
    result = _classify(make_large_soft_shadow())
    assert result.image_type == ImageType.SOFT_SHADOW


def test_flat_opaque_image_classified_as_hard_logo():
    result = _classify(make_no_alpha_image())
    assert result.image_type == ImageType.HARD_LOGO


def test_photo_like_gradient_not_soft_shadow():
    # großflächiges opakes Bild mit vielen Farben -> darf nicht als Schatten erkannt werden
    w, h = 128, 128
    yy, xx = np.mgrid[0:h, 0:w]
    rgb = np.stack(
        [
            (xx * 2) % 256,
            (yy * 2) % 256,
            ((xx + yy)) % 256,
        ],
        axis=-1,
    ).astype(np.uint8)
    arr = np.dstack([rgb, np.full((h, w), 255, dtype=np.uint8)])
    stats = analyze_alpha_channel(arr, ALPHA_THRESH)
    result = classify_image(arr, stats, CLASS_THRESH)
    assert result.image_type != ImageType.SOFT_SHADOW
