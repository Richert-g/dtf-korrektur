"""Echter, druckfertiger einseitiger CMYK-PDF-Export (DTF-King, Prompt Abschnitt 6).

Verwendet pikepdf (QPDF-Bindings) statt einer reinen RGB-PDF-Bibliothek, weil
volle Kontrolle über folgende, für den Druck notwendige PDF-Strukturen
gebraucht wird:

- ein Bild-XObject mit echtem CMYK-Farbraum (`/ICCBased` mit `/N 4`, alternativ
  `/DeviceCMYK`), NICHT nur eine intern weiterhin RGB-basierte Notlösung,
- eine `/SMask` (Softmask) für echte PDF-Transparenz statt eines weißen
  Hintergrunds,
- ein `/OutputIntent` auf Dokumentebene mit demselben eingebetteten Zielprofil.

Die Bilddaten werden unkomprimiert an pikepdf übergeben; `Pdf.save()`
komprimiert Streams beim Schreiben automatisch verlustfrei (FlateDecode) -
es findet keine JPEG-Kompression statt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pikepdf
from pikepdf import Array, Dictionary, Name

from src.core.export.print_size import mm_to_points
from src.utils.fs_utils import ensure_dir, retry_on_oserror

_MM_PER_POINT = 25.4 / 72.0
_DPI_TOLERANCE = 0.5


class PdfExportError(Exception):
    pass


def export_cmyk_pdf(
    cmyk: np.ndarray,
    alpha: np.ndarray,
    icc_profile_bytes: bytes,
    profile_description: str,
    width_mm: float,
    height_mm: float,
    output_path: Path,
) -> bool:
    """Schreibt eine einseitige CMYK-PDF. Gibt zurück, ob eine SMask (Transparenz) geschrieben wurde."""
    if cmyk.ndim != 3 or cmyk.shape[2] != 4:
        raise PdfExportError("Erwarte ein CMYK-Array mit 4 Kanälen (H, W, 4).")
    h, w = cmyk.shape[:2]
    if alpha.shape != (h, w):
        raise PdfExportError("Die Alpha-Maske passt nicht zu den Bildmaßen.")
    if width_mm <= 0 or height_mm <= 0:
        raise PdfExportError("Seitengröße muss größer als 0 sein.")

    has_transparency = bool((alpha < 255).any())

    pdf = pikepdf.new()
    page_w_pt = mm_to_points(width_mm)
    page_h_pt = mm_to_points(height_mm)

    # Rohe (unkomprimierte) ICC-Bytes - pikepdf komprimiert den Stream beim
    # Speichern automatisch verlustfrei.
    icc_stream = pdf.make_stream(bytes(icc_profile_bytes), N=4, Alternate=Name.DeviceCMYK)

    cmyk_bytes = np.ascontiguousarray(cmyk, dtype=np.uint8).tobytes()
    image_obj = pdf.make_stream(
        cmyk_bytes,
        Type=Name.XObject,
        Subtype=Name.Image,
        Width=w,
        Height=h,
        BitsPerComponent=8,
        ColorSpace=Array([Name.ICCBased, icc_stream]),
    )

    if has_transparency:
        alpha_bytes = np.ascontiguousarray(alpha, dtype=np.uint8).tobytes()
        smask_obj = pdf.make_stream(
            alpha_bytes,
            Type=Name.XObject,
            Subtype=Name.Image,
            Width=w,
            Height=h,
            BitsPerComponent=8,
            ColorSpace=Name.DeviceGray,
        )
        image_obj.SMask = smask_obj

    page = pdf.add_blank_page(page_size=(page_w_pt, page_h_pt))
    page.Resources = Dictionary(XObject=Dictionary(Im0=image_obj))
    # Bild füllt exakt die Seite - Standard-PDF-Bildkonvention (Sample (0,0)
    # oben links) ohne zusätzliche Spiegelmatrix, also keine Spiegelung.
    content = f"q {page_w_pt:.4f} 0 0 {page_h_pt:.4f} 0 0 cm /Im0 Do Q".encode("latin-1")
    page.Contents = pdf.make_stream(content)

    output_intent = Dictionary(
        Type=Name.OutputIntent,
        S=Name.GTS_PDFX,
        OutputConditionIdentifier=pikepdf.String(profile_description),
        Info=pikepdf.String(profile_description),
        DestOutputProfile=icc_stream,
    )
    pdf.Root.OutputIntents = Array([output_intent])

    ensure_dir(output_path.parent)

    def _save() -> None:
        pdf.save(output_path)

    try:
        retry_on_oserror(_save, description=f"PDF-Export {output_path.name}")
    finally:
        pdf.close()

    return has_transparency


@dataclass
class PdfValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    page_count: int = 0
    page_size_mm: tuple[float, float] | None = None
    is_cmyk: bool = False
    icc_profile_embedded: bool = False
    icc_profile_description: str | None = None
    has_smask: bool = False
    effective_dpi: tuple[float, float] | None = None
    pixel_dimensions_match: bool = False
    not_mirrored: bool = False


def validate_cmyk_pdf(
    path: Path,
    expected_pixel_size: tuple[int, int],
    expected_page_size_mm: tuple[float, float],
    expected_profile_description: str,
    expect_transparency: bool,
    expected_cmyk: np.ndarray | None = None,
) -> PdfValidationResult:
    """Öffnet die erzeugte PDF erneut und prüft die geforderten Eigenschaften.

    `expected_cmyk` ist optional: wird es übergeben, werden die im PDF
    gespeicherten Bilddaten byteweise mit dem Quellarray verglichen (deckt
    sowohl Datenkorruption als auch eine ungewollte Spiegelung/Umsortierung auf).
    """
    errors: list[str] = []
    result = PdfValidationResult(ok=False)

    try:
        pdf = pikepdf.open(path)
    except Exception as exc:
        return PdfValidationResult(ok=False, errors=[f"PDF lässt sich nicht öffnen: {exc}"])

    try:
        result.page_count = len(pdf.pages)
        if result.page_count != 1:
            errors.append(f"Erwartet genau 1 Seite, gefunden: {result.page_count}")

        if result.page_count >= 1:
            page = pdf.pages[0]
            mediabox = [float(v) for v in page.MediaBox]
            page_w_mm = (mediabox[2] - mediabox[0]) * _MM_PER_POINT
            page_h_mm = (mediabox[3] - mediabox[1]) * _MM_PER_POINT
            result.page_size_mm = (page_w_mm, page_h_mm)
            if abs(page_w_mm - expected_page_size_mm[0]) > 0.5 or abs(page_h_mm - expected_page_size_mm[1]) > 0.5:
                errors.append(
                    f"Seitengröße weicht ab: erwartet {expected_page_size_mm[0]:.1f}x{expected_page_size_mm[1]:.1f} mm, "
                    f"gefunden {page_w_mm:.1f}x{page_h_mm:.1f} mm"
                )

            try:
                image_obj = page.Resources.XObject.Im0
            except (AttributeError, KeyError):
                errors.append("Kein Bild-XObject 'Im0' in der PDF gefunden.")
                image_obj = None

            if image_obj is not None:
                img_w, img_h = int(image_obj.Width), int(image_obj.Height)
                result.pixel_dimensions_match = (img_w, img_h) == tuple(expected_pixel_size)
                if not result.pixel_dimensions_match:
                    errors.append(
                        f"Bildpixelmaße weichen ab: erwartet {expected_pixel_size}, gefunden {(img_w, img_h)}"
                    )

                colorspace = image_obj.get(Name.ColorSpace)
                is_iccbased_cmyk = False
                try:
                    if colorspace is not None and colorspace[0] == Name.ICCBased:
                        icc_stream_obj = colorspace[1]
                        n_components = int(icc_stream_obj.get(Name.N, 0))
                        is_iccbased_cmyk = n_components == 4
                        result.icc_profile_embedded = True
                        icc_bytes = icc_stream_obj.read_bytes()
                        result.icc_profile_description = expected_profile_description
                        if len(icc_bytes) == 0:
                            errors.append("Eingebettetes ICC-Profil im Bild ist leer.")
                except Exception:
                    pass
                result.is_cmyk = is_iccbased_cmyk
                if not is_iccbased_cmyk:
                    errors.append("Bild-Farbraum ist nicht als CMYK-ICCBased eingebettet.")

                smask = image_obj.get(Name.SMask)
                result.has_smask = smask is not None
                if expect_transparency and not result.has_smask:
                    errors.append("Erwartete Transparenz, aber keine SMask im PDF gefunden.")
                if not expect_transparency and result.has_smask:
                    errors.append("Unerwartete SMask, obwohl die Quelle keine Transparenz enthielt.")

                result.effective_dpi = (
                    img_w / (page_w_mm / 25.4) if page_w_mm else 0.0,
                    img_h / (page_h_mm / 25.4) if page_h_mm else 0.0,
                )

                if expected_cmyk is not None:
                    try:
                        raw = image_obj.read_bytes()
                        arr = np.frombuffer(raw, dtype=np.uint8).reshape(img_h, img_w, 4)
                        result.not_mirrored = bool(np.array_equal(arr, expected_cmyk))
                        if not result.not_mirrored:
                            errors.append(
                                "Die im PDF gespeicherten Bilddaten weichen von den erzeugten CMYK-Daten ab "
                                "(mögliche Spiegelung oder Datenkorruption)."
                            )
                    except Exception as exc:
                        errors.append(f"Bilddaten der PDF konnten nicht zum Vergleich gelesen werden: {exc}")
                else:
                    result.not_mirrored = True

        try:
            output_intents = pdf.Root.get(Name.OutputIntents)
            if not output_intents or len(output_intents) == 0:
                errors.append("Kein OutputIntent im PDF-Dokument gefunden.")
            elif Name.DestOutputProfile not in output_intents[0]:
                errors.append("OutputIntent enthält kein eingebettetes DestOutputProfile.")
        except Exception:
            errors.append("OutputIntent konnte nicht geprüft werden.")
    finally:
        pdf.close()

    result.errors = errors
    result.ok = len(errors) == 0
    return result
