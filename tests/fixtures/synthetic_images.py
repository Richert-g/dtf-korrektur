"""Erzeugt synthetische Testbilder, damit keine urheberrechtlich fragwürdigen
Beispieldateien benötigt werden (Prompt Abschnitt 23).

Alle Funktionen geben PIL.Image im Modus RGBA zurück (sofern nicht anders benannt).
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageCms, ImageDraw


def _blank_rgba(w: int, h: int) -> np.ndarray:
    return np.zeros((h, w, 4), dtype=np.uint8)


def make_no_alpha_image(w: int = 64, h: int = 64) -> Image.Image:
    """Vollständig deckendes RGB-Bild ohne Alphakanal."""
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    arr[:, :] = [200, 60, 60]
    arr[h // 4 : 3 * h // 4, w // 4 : 3 * w // 4] = [60, 120, 200]
    return Image.fromarray(arr, mode="RGB")


def make_fully_transparent(w: int = 32, h: int = 32) -> Image.Image:
    arr = _blank_rgba(w, h)
    return Image.fromarray(arr, mode="RGBA")


def make_fully_opaque(w: int = 32, h: int = 32) -> Image.Image:
    arr = _blank_rgba(w, h)
    arr[:, :, :3] = [10, 180, 90]
    arr[:, :, 3] = 255
    return Image.fromarray(arr, mode="RGBA")


def make_single_semi_transparent_edge_pixel(w: int = 32, h: int = 32) -> Image.Image:
    arr = _blank_rgba(w, h)
    arr[8:24, 8:24, :3] = [10, 10, 10]
    arr[8:24, 8:24, 3] = 255
    # ein einzelnes halbtransparentes Randpixel
    arr[8, 16, 3] = 120
    return Image.fromarray(arr, mode="RGBA")


def make_large_soft_shadow(w: int = 128, h: int = 128) -> Image.Image:
    """Hartes Motiv in der Mitte, darunter ein weicher, großflächiger Schattenverlauf."""
    arr = _blank_rgba(w, h)
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w * 0.5, h * 0.65
    dist = np.sqrt((xx - cx) ** 2 + ((yy - cy) * 0.6) ** 2)
    radius = w * 0.42
    shadow_alpha = np.clip(1.0 - dist / radius, 0, 1) ** 1.5 * 140
    arr[:, :, 3] = shadow_alpha.astype(np.uint8)
    arr[:, :, :3] = 20

    motif_cx, motif_cy, motif_r = w * 0.5, h * 0.35, w * 0.2
    mdist = np.sqrt((xx - motif_cx) ** 2 + (yy - motif_cy) ** 2)
    motif_mask = mdist < motif_r
    arr[motif_mask, 3] = 255
    arr[motif_mask, 0:3] = [30, 30, 200]
    return Image.fromarray(arr, mode="RGBA")


def make_logo_with_white_halo(w: int = 64, h: int = 64) -> Image.Image:
    """Schwarzer Kreis auf transparentem Hintergrund mit weißem Halo an der Kante."""
    arr = _blank_rgba(w, h)
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w / 2, h / 2
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    r = w * 0.35

    core = dist < r
    halo = (dist >= r) & (dist < r + 3)
    fade = (dist >= r + 3) & (dist < r + 6)

    arr[core, 0:3] = [0, 0, 0]
    arr[core, 3] = 255
    arr[halo, 0:3] = [255, 255, 255]
    arr[halo, 3] = 200
    fade_alpha = np.clip(255 - (dist - r - 3) / 3 * 255, 0, 255)
    arr[fade, 0:3] = [255, 255, 255]
    arr[fade, 3] = fade_alpha[fade].astype(np.uint8)
    return Image.fromarray(arr, mode="RGBA")


def make_black_motif_gray_edge(w: int = 64, h: int = 64) -> Image.Image:
    """Schwarzes Motiv mit grauem Rand (z. B. durch schlechtes Freistellen)."""
    arr = _blank_rgba(w, h)
    draw_img = Image.fromarray(arr, mode="RGBA")
    draw = ImageDraw.Draw(draw_img)
    draw.rectangle([16, 16, 48, 48], fill=(0, 0, 0, 255))
    arr = np.array(draw_img)
    yy, xx = np.mgrid[0:h, 0:w]
    edge_ring = (xx >= 14) & (xx <= 50) & (yy >= 14) & (yy <= 50) & (
        (xx < 16) | (xx > 48) | (yy < 16) | (yy > 48)
    )
    arr[edge_ring, 0:3] = [128, 128, 128]
    arr[edge_ring, 3] = 160
    return Image.fromarray(arr, mode="RGBA")


def make_thin_text(w: int = 96, h: int = 32) -> Image.Image:
    """Dünne, textähnliche Linien (Erosionsempfindlichkeit testen)."""
    arr = _blank_rgba(w, h)
    img = Image.fromarray(arr, mode="RGBA")
    draw = ImageDraw.Draw(img)
    for i in range(4):
        x = 8 + i * 20
        draw.line([(x, 6), (x, 26)], fill=(0, 0, 0, 255), width=2)
    draw.line([(8, 16), (86, 16)], fill=(0, 0, 0, 255), width=1)
    return img


def make_small_islands(w: int = 64, h: int = 64) -> Image.Image:
    """Hauptform plus mehrere isolierte 1-3-Pixel-Inseln."""
    arr = _blank_rgba(w, h)
    arr[20:44, 20:44, :3] = [200, 30, 30]
    arr[20:44, 20:44, 3] = 255
    for (x, y) in [(2, 2), (5, 60), (60, 3), (61, 61), (10, 50)]:
        arr[y : y + 2, x : x + 2, :3] = [200, 30, 30]
        arr[y : y + 2, x : x + 2, 3] = 255
    return Image.fromarray(arr, mode="RGBA")


def make_transparent_holes(w: int = 64, h: int = 64) -> Image.Image:
    """Deckende Fläche mit kleinen transparenten Löchern innen."""
    arr = _blank_rgba(w, h)
    arr[8:56, 8:56, :3] = [30, 130, 200]
    arr[8:56, 8:56, 3] = 255
    arr[20:24, 20:24, 3] = 0
    arr[30:33, 40:43, 3] = 0
    return Image.fromarray(arr, mode="RGBA")


def make_srgb_icc_bytes() -> bytes:
    profile = ImageCms.createProfile("sRGB")
    cms_profile = ImageCms.ImageCmsProfile(profile)
    return cms_profile.tobytes()


def make_invalid_icc_bytes() -> bytes:
    return b"NOT_A_VALID_ICC_PROFILE_" + b"\x00" * 32


def make_illustration_soft_edge(w: int = 96, h: int = 96) -> Image.Image:
    """Farbige Illustration mit weich ausgefranster Außenkante (kein harter Halo)."""
    arr = _blank_rgba(w, h)
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w / 2, h / 2
    dist = np.sqrt(((xx - cx) / 1.1) ** 2 + ((yy - cy) / 0.8) ** 2)
    r = w * 0.32
    feather = 8.0
    alpha = np.clip((r + feather - dist) / feather, 0, 1) * 255
    arr[:, :, 3] = alpha.astype(np.uint8)
    # bunter Farbverlauf statt einfarbig
    arr[:, :, 0] = np.clip(120 + (xx - cx), 0, 255).astype(np.uint8)
    arr[:, :, 1] = np.clip(120 + (yy - cy), 0, 255).astype(np.uint8)
    arr[:, :, 2] = 200
    return Image.fromarray(arr, mode="RGBA")


def make_saturated_out_of_gamut(w: int = 64, h: int = 64) -> Image.Image:
    """Sehr stark gesättigte Neonfarben, die typischerweise außerhalb von CMYK liegen."""
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    arr[:, : w // 3] = [0, 255, 0]
    arr[:, w // 3 : 2 * w // 3] = [255, 0, 255]
    arr[:, 2 * w // 3 :] = [255, 255, 0]
    return Image.fromarray(arr, mode="RGB")
