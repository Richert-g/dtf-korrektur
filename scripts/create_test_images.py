"""Erzeugt Beispielbilder in resources/sample_images (rein synthetisch, keine
urheberrechtlich problematischen Dateien - Prompt Abschnitt 23)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.fixtures.synthetic_images import (  # noqa: E402
    make_black_motif_gray_edge,
    make_fully_opaque,
    make_fully_transparent,
    make_illustration_soft_edge,
    make_large_soft_shadow,
    make_logo_with_white_halo,
    make_no_alpha_image,
    make_saturated_out_of_gamut,
    make_small_islands,
    make_thin_text,
    make_transparent_holes,
)


def main() -> None:
    out_dir = Path(__file__).resolve().parents[1] / "resources" / "sample_images"
    out_dir.mkdir(parents=True, exist_ok=True)

    images = {
        "logo_mit_weissem_halo.png": make_logo_with_white_halo(256, 256),
        "schwarzes_motiv_grauer_rand.png": make_black_motif_gray_edge(256, 256),
        "weicher_schatten.png": make_large_soft_shadow(400, 400),
        "illustration_weiche_kante.png": make_illustration_soft_edge(300, 300),
        "duenne_schrift.png": make_thin_text(400, 120),
        "kleine_pixelinseln.png": make_small_islands(200, 200),
        "transparente_loecher.png": make_transparent_holes(200, 200),
        "ohne_alphakanal.png": make_no_alpha_image(200, 200),
        "voll_deckend.png": make_fully_opaque(200, 200),
        "voll_transparent.png": make_fully_transparent(100, 100),
        "stark_gesaettigt.png": make_saturated_out_of_gamut(300, 200),
    }

    for filename, img in images.items():
        img.save(out_dir / filename)
        print(f"geschrieben: {out_dir / filename}")

    print(f"\n{len(images)} Beispielbilder erzeugt in {out_dir}")


if __name__ == "__main__":
    main()
