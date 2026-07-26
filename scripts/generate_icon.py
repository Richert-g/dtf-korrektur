"""Erzeugt das App-Icon programmatisch (kein externes Bildmaterial nötig).

Motiv: ein T-Shirt-Piktogramm (DTF = Direct-to-Film, Textildruck) vor einem
Farbverlauf, mit einem kleinen "Funken" als Symbol für die automatische
Optimierung.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from PIL import Image, ImageDraw

BG_COLOR_1 = (78, 44, 209)   # Violett
BG_COLOR_2 = (33, 140, 245)  # Blau
SHIRT_COLOR = (255, 255, 255)
SHIRT_SHADOW = (223, 231, 250)
SPARK_COLOR = (255, 209, 70)  # Gelb-Gold


def make_gradient(size: tuple[int, int], color1, color2) -> Image.Image:
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w]
    t = ((xx.astype(np.float32) + yy.astype(np.float32)) / (w + h - 2))[:, :, None]
    c1 = np.array(color1, dtype=np.float32)
    c2 = np.array(color2, dtype=np.float32)
    grad = (c1 * (1 - t) + c2 * t).astype(np.uint8)
    return Image.fromarray(grad, mode="RGB")


def rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    img = Image.new("L", size, 0)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=255)
    return img


def shirt_points(cx: float, cy: float, scale: float) -> list[tuple[float, float]]:
    """Vereinfachtes T-Shirt-Polygon (relative Koordinaten, -1..1) um (cx, cy)."""
    raw = [
        (-0.30, -0.62), (-0.30, -0.78), (-0.14, -0.90), (0.14, -0.90),
        (0.30, -0.78), (0.30, -0.62), (0.55, -0.50), (0.62, -0.28),
        (0.42, -0.16), (0.34, -0.28), (0.34, 0.55), (0.30, 0.62),
        (-0.30, 0.62), (-0.34, 0.55), (-0.34, -0.28), (-0.42, -0.16),
        (-0.62, -0.28), (-0.55, -0.50),
    ]
    return [(cx + x * scale, cy + y * scale) for x, y in raw]


def spark_points(cx: float, cy: float, scale: float) -> list[tuple[float, float]]:
    raw = [
        (0.0, -1.0), (0.22, -0.22), (1.0, 0.0), (0.22, 0.22),
        (0.0, 1.0), (-0.22, 0.22), (-1.0, 0.0), (-0.22, -0.22),
    ]
    return [(cx + x * scale, cy + y * scale) for x, y in raw]


def build_icon(size: int = 512) -> Image.Image:
    bg = make_gradient((size, size), BG_COLOR_1, BG_COLOR_2).convert("RGBA")
    mask = rounded_mask((size, size), radius=int(size * 0.22))

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(bg, (0, 0), mask)

    draw = ImageDraw.Draw(canvas)
    shadow = shirt_points(size * 0.5 + size * 0.015, size * 0.52 + size * 0.02, size * 0.34)
    draw.polygon(shadow, fill=SHIRT_SHADOW + (140,))
    shirt = shirt_points(size * 0.5, size * 0.52, size * 0.34)
    draw.polygon(shirt, fill=SHIRT_COLOR + (255,))

    spark = spark_points(size * 0.76, size * 0.26, size * 0.11)
    draw.polygon(spark, fill=SPARK_COLOR + (255,))

    return canvas


def main() -> None:
    out_dir = Path(__file__).resolve().parents[1] / "resources" / "icons"
    out_dir.mkdir(parents=True, exist_ok=True)

    master = build_icon(512)
    master.save(out_dir / "app_icon_preview.png")

    sizes = [16, 24, 32, 48, 64, 128, 256]
    resized = [master.resize((s, s), Image.LANCZOS) for s in sizes]
    resized[-1].save(
        out_dir / "app_icon.ico",
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=resized[:-1],
    )
    print(f"Icon geschrieben: {out_dir / 'app_icon.ico'}")
    print(f"Vorschau-PNG geschrieben: {out_dir / 'app_icon_preview.png'}")


if __name__ == "__main__":
    main()
