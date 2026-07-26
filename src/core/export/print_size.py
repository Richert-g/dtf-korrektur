"""Druckgrößen- und DPI-Berechnung für den PDF-Export (DTF-King, Prompt Abschnitt 9).

Die Anwendung skaliert Bilder NIE ohne Hinweis künstlich hoch. Reicht die
native Pixelanzahl für die gewünschte Druckgröße bei der Zielauflösung nicht
aus, wird das als Warnung gemeldet - eine tatsächliche Hochskalierung
passiert nur, wenn sie ausdrücklich aktiviert wird.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image

MM_PER_INCH = 25.4
POINTS_PER_INCH = 72.0


def mm_to_points(mm: float) -> float:
    return mm / MM_PER_INCH * POINTS_PER_INCH


@dataclass
class PrintSizeResult:
    pixel_width: int
    pixel_height: int
    width_mm: float
    height_mm: float
    target_dpi: float
    effective_dpi_x: float
    effective_dpi_y: float
    effective_dpi: float  # der begrenzende (kleinere) der beiden Werte
    meets_target_dpi: bool
    warning: str | None


def compute_print_size(
    pixel_width: int,
    pixel_height: int,
    target_dpi: float = 300.0,
    width_mm: float | None = None,
    height_mm: float | None = None,
) -> PrintSizeResult:
    """Berechnet Druckgröße und effektive dpi.

    - Sind weder Breite noch Höhe angegeben, wird die native Größe bei
      `target_dpi` verwendet (effektive dpi entsprechen dann exakt `target_dpi`).
    - Ist nur eine der beiden Angaben gesetzt, wird die andere proportional
      zu den Bildpixeln berechnet.
    - Sind beide gesetzt, werden sie unverändert übernommen (können bei
      abweichendem Seitenverhältnis zu unterschiedlichen effektiven dpi in
      X- und Y-Richtung führen).
    """
    if pixel_width <= 0 or pixel_height <= 0:
        raise ValueError("Bildmaße müssen größer als 0 sein.")
    if target_dpi <= 0:
        raise ValueError("Zielauflösung (dpi) muss größer als 0 sein.")

    resolved_width_mm: float
    resolved_height_mm: float

    if width_mm is None and height_mm is None:
        resolved_width_mm = pixel_width / target_dpi * MM_PER_INCH
        resolved_height_mm = pixel_height / target_dpi * MM_PER_INCH
    elif width_mm is not None and height_mm is None:
        if width_mm <= 0:
            raise ValueError("Breite muss größer als 0 sein.")
        resolved_width_mm = width_mm
        resolved_height_mm = width_mm * pixel_height / pixel_width
    elif height_mm is not None and width_mm is None:
        if height_mm <= 0:
            raise ValueError("Höhe muss größer als 0 sein.")
        resolved_height_mm = height_mm
        resolved_width_mm = height_mm * pixel_width / pixel_height
    else:
        assert width_mm is not None and height_mm is not None
        if width_mm <= 0 or height_mm <= 0:
            raise ValueError("Breite und Höhe müssen größer als 0 sein.")
        resolved_width_mm = width_mm
        resolved_height_mm = height_mm

    width_mm = resolved_width_mm
    height_mm = resolved_height_mm

    effective_dpi_x = pixel_width / (width_mm / MM_PER_INCH)
    effective_dpi_y = pixel_height / (height_mm / MM_PER_INCH)
    effective_dpi = min(effective_dpi_x, effective_dpi_y)
    meets_target_dpi = effective_dpi >= target_dpi - 1e-6

    warning = None
    if not meets_target_dpi:
        width_cm = width_mm / 10
        warning = (
            f"Die Datei erreicht bei {width_cm:.1f} cm Breite nur {effective_dpi:.0f} dpi. "
            f"Für den empfohlenen Mindestwert von {target_dpi:.0f} dpi fehlen Bildpixel."
        )

    return PrintSizeResult(
        pixel_width=pixel_width,
        pixel_height=pixel_height,
        width_mm=width_mm,
        height_mm=height_mm,
        target_dpi=target_dpi,
        effective_dpi_x=effective_dpi_x,
        effective_dpi_y=effective_dpi_y,
        effective_dpi=effective_dpi,
        meets_target_dpi=meets_target_dpi,
        warning=warning,
    )


def required_pixel_dimensions(width_mm: float, height_mm: float, target_dpi: float) -> tuple[int, int]:
    """Pixelmaße, die für die gewünschte Druckgröße bei `target_dpi` nötig wären."""
    width_px = int(round(width_mm / MM_PER_INCH * target_dpi))
    height_px = int(round(height_mm / MM_PER_INCH * target_dpi))
    return max(1, width_px), max(1, height_px)


def resize_rgba_to_print_size(
    rgba: np.ndarray,
    width_mm: float,
    height_mm: float,
    target_dpi: float,
    allow_upscale: bool = False,
) -> tuple[np.ndarray, bool]:
    """Skaliert ein RGBA-Array auf die für die Druckgröße nötigen Pixelmaße.

    Verkleinern (die Datei hat mehr Pixel als für `target_dpi` nötig) passiert
    immer. Vergrößern (die Datei hat WENIGER Pixel als nötig) passiert nur,
    wenn `allow_upscale=True` explizit gesetzt ist - sonst bleibt das Array
    unverändert und der Aufrufer muss über `compute_print_size().warning`
    informieren.

    Gibt (Array, wurde_skaliert) zurück.
    """
    h, w = rgba.shape[:2]
    required_w, required_h = required_pixel_dimensions(width_mm, height_mm, target_dpi)

    if required_w == w and required_h == h:
        return rgba, False

    needs_upscale = required_w > w or required_h > h
    if needs_upscale and not allow_upscale:
        return rgba, False

    img = Image.fromarray(np.ascontiguousarray(rgba), mode="RGBA")
    resized = img.resize((required_w, required_h), resample=Image.Resampling.LANCZOS)
    return np.array(resized, dtype=np.uint8), True
