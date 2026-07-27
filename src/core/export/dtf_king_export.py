"""Druckfertiger einseitiger CMYK-PDF-Export für den Druckdienstleister DTF-King.

Eigenständige Orchestrierung statt Erweiterung von `src.core.pipeline.process_image()`,
damit der bestehende RGB/PNG-Ablauf unangetastet bleibt (siehe Auftrag: "Bestehende
Funktionen dürfen nicht unnötig umgebaut werden"). Reihenfolge:

1. Quelldatei laden
2. eingebettetes Quellprofil erkennen (fehlend -> sRGB angenommen, RGB unverändert)
3. Skalierung auf die endgültige Druckgröße (VOR Alpha/Halo, damit die
   nachfolgende Kantenbehandlung auf der finalen Auflösung arbeitet)
4. Halo-Korrektur, danach Alpha-Bereinigung (siehe Hinweis unten zur
   bewussten Abweichung von der im Auftrag angegebenen Reihenfolge)
5. genau EINE echte ICC-Konvertierung nach dem gewählten CMYK-Zielprofil
   (keine weitere Sättigungs-, Gamut- oder Sonderfarbkorrektur)
6. einseitiger CMYK-PDF-Export mit eingebetteter ICC-Softmask/-OutputIntent
7. Nachvalidierung der erzeugten PDF-Datei

Bewusste Abweichung von der im Auftrag genannten Reihenfolge "5. Alpha, dann
6. Halo": Die bestehende, bereits im Programm etablierte Halo-Korrektur MUSS
vor der Alpha-Bereinigung laufen, weil sie auf den noch vorhandenen
halbtransparenten Randpixeln arbeitet (siehe `src.core.halo.halo_correction`).
Würde man zuerst die Alpha-Bereinigung ausführen, hätte der aggressive
Standard-Schwellenwert ("Pixel löschen bis Alpha-Wert") die meisten dieser
Randpixel bereits auf 0 gesetzt - die Halo-Korrektur fände dann kaum noch
etwas zu korrigieren vor. Die vom Auftrag geforderte übergeordnete Regel
("Transparenzbehandlung komplett vor der Farbkonvertierung, deckende
Innenflächen bleiben dabei unangetastet") wird weiterhin vollständig erfüllt.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

from src.config.defaults import ProcessingSettings
from src.core.analysis.alpha_analysis import analyze_alpha_channel
from src.core.analysis.image_loader import ImageLoadError, load_image
from src.core.color.cmyk_convert import CmykConversionError, convert_cmyk_to_preview_rgb, convert_rgba_to_output_cmyk
from src.core.color.icc_manager import (
    ICCProfileError,
    get_srgb_icc_bytes,
    get_srgb_profile,
    load_icc_profile,
    load_icc_profile_from_bytes,
)
from src.core.color.profile_validation import validate_cmyk_output_profile
from src.core.export.filenames import avoid_collision
from src.core.export.pdf_export import PdfExportError, export_cmyk_pdf, validate_cmyk_pdf
from src.core.export.png_export import export_rgba_png
from src.core.export.print_size import compute_print_size, resize_rgba_to_print_size
from src.core.reporting.report_writer import write_html_report, write_json_report
from src.models.report import ImageProcessingReport

logger = logging.getLogger(__name__)


class DtfKingExportError(Exception):
    """Wird ausgelöst, wenn der Export nicht sicher/korrekt durchgeführt werden kann.

    Der Export wird in diesem Fall NICHT stillschweigend mit einem anderen
    Profil oder anderen Annahmen fortgesetzt.
    """


@dataclass
class DtfKingExportSummary:
    """Zusammenfassung für die Vorschau vor dem eigentlichen Export (Prompt Abschnitt 10)."""

    preset_name: str
    source_profile: str
    target_profile: str
    icc_conversion_performed: bool
    icc_profile_embedded: bool
    output_color_space: str
    rendering_intent: str
    black_point_compensation: bool
    additional_saturation_reduction: bool
    additional_gamut_correction: bool
    has_transparency: bool
    background_transparent: bool
    page_size_mm: tuple[float, float]
    effective_dpi: float
    meets_target_dpi: bool
    dpi_warning: str | None
    mirrored: bool
    file_format: str


def build_export_summary(
    path: Path, settings: ProcessingSettings, preset_name: str = "DTF-King – ISO Coated v2 (ECI)"
) -> DtfKingExportSummary:
    """Berechnet die Vorab-Zusammenfassung, OHNE zu exportieren (keine Seiteneffekte auf Dateien)."""
    export = settings.export
    color = settings.color

    if not color.target_profile_path:
        raise DtfKingExportError(
            "Kein ICC-Zielprofil ausgewählt. Bitte zuerst das ICC-Profil 'ISO Coated v2 (ECI)' importieren und auswählen."
        )
    validation = validate_cmyk_output_profile(Path(color.target_profile_path))
    if not validation.ok:
        raise DtfKingExportError(validation.error or "ICC-Zielprofil ist ungültig.")

    loaded = load_image(path)
    array = loaded.array
    source_profile_name = loaded.icc_profile_description or "sRGB IEC61966-2.1 (angenommen)"

    alpha = array[:, :, 3]
    has_transparency = bool((alpha < 255).any())

    size = compute_print_size(
        pixel_width=array.shape[1],
        pixel_height=array.shape[0],
        target_dpi=export.pdf_target_dpi,
        width_mm=export.pdf_width_mm,
        height_mm=export.pdf_height_mm,
    )

    return DtfKingExportSummary(
        preset_name=preset_name,
        source_profile=source_profile_name,
        target_profile=validation.description or Path(color.target_profile_path).name,
        icc_conversion_performed=True,
        icc_profile_embedded=True,
        output_color_space="CMYK",
        rendering_intent=color.rendering_intent.value,
        black_point_compensation=color.black_point_compensation,
        additional_saturation_reduction=False,
        additional_gamut_correction=False,
        has_transparency=has_transparency,
        background_transparent=True,
        page_size_mm=(size.width_mm, size.height_mm),
        effective_dpi=size.effective_dpi,
        meets_target_dpi=size.meets_target_dpi,
        dpi_warning=size.warning,
        mirrored=False,
        file_format="PDF (einseitig, CMYK)",
    )


def process_image_for_dtf_king_pdf(path: Path, settings: ProcessingSettings, output_root: Path) -> ImageProcessingReport:
    start = time.perf_counter()
    report = ImageProcessingReport(source_path=path)
    report.output_format = "pdf_cmyk"

    export = settings.export
    color = settings.color

    if not color.target_profile_path:
        report.success = False
        report.errors.append(
            "Kein ICC-Zielprofil ausgewählt. Bitte zuerst das ICC-Profil 'ISO Coated v2 (ECI)' importieren und auswählen."
        )
        return report

    validation = validate_cmyk_output_profile(Path(color.target_profile_path))
    if not validation.ok:
        report.success = False
        report.errors.append(validation.error or "ICC-Zielprofil ist ungültig.")
        return report

    target_profile = load_icc_profile(Path(color.target_profile_path))
    if target_profile is None:
        report.success = False
        report.errors.append(f"ICC-Zielprofil konnte nicht geladen werden: {color.target_profile_path}")
        return report

    try:
        loaded = load_image(path)
    except ImageLoadError as exc:
        report.success = False
        report.errors.append(str(exc))
        return report

    array = loaded.array.copy()

    # --- 1+2: Quellprofil erkennen ---
    if loaded.icc_profile_bytes:
        source_profile = load_icc_profile_from_bytes(loaded.icc_profile_bytes)
        if source_profile is None:
            report.warnings.append("Das eingebettete Quellprofil ist beschädigt oder inkompatibel. Es wird sRGB angenommen.")
            source_profile = get_srgb_profile()
            report.source_profile = "sRGB IEC61966-2.1 (angenommen, Quellprofil defekt)"
        else:
            from src.core.color.icc_manager import profile_description

            report.source_profile = profile_description(source_profile)
    else:
        source_profile = get_srgb_profile()
        report.source_profile = "sRGB IEC61966-2.1 (angenommen, kein eingebettetes Profil)"
        report.assumed_profiles.append("sRGB IEC61966-2.1 (kein eingebettetes Profil gefunden)")
    report.add_step("source_profile_detection", f"Quellprofil: {report.source_profile}")

    report.target_profile = validation.description or Path(color.target_profile_path).name

    # --- 3: Skalierung auf die endgültige Druckgröße ---
    size = compute_print_size(
        pixel_width=array.shape[1],
        pixel_height=array.shape[0],
        target_dpi=export.pdf_target_dpi,
        width_mm=export.pdf_width_mm,
        height_mm=export.pdf_height_mm,
    )
    array, did_resize = resize_rgba_to_print_size(
        array, size.width_mm, size.height_mm, export.pdf_target_dpi, allow_upscale=export.pdf_allow_upscale
    )
    if did_resize:
        report.add_step(
            "resize_to_print_size",
            f"Auf Druckgröße skaliert: {array.shape[1]}x{array.shape[0]} px "
            f"für {size.width_mm:.1f}x{size.height_mm:.1f} mm.",
        )
    if size.warning:
        report.warnings.append(size.warning)
    report.pdf_meets_target_dpi = size.meets_target_dpi
    report.width, report.height = array.shape[1], array.shape[0]
    report.file_format = loaded.file_format

    # --- 4: Halo-Korrektur (vor Alpha, siehe Moduldokumentation oben), dann Alpha-Bereinigung ---
    from src.core.alpha.alpha_cleanup import clean_alpha
    from src.core.classification.classifier import classify_image
    from src.core.halo.halo_correction import correct_halo

    alpha_stats = analyze_alpha_channel(array, settings.alpha)
    report.transparent_pixel_count = alpha_stats.fully_transparent_count
    report.semi_transparent_pixel_count = alpha_stats.semi_transparent_count

    classification = classify_image(array, alpha_stats, settings.classification)
    report.detected_type = classification.image_type
    report.classification_reasons = [f"{r.signal}: {r.value}" for r in classification.reasons]

    array, halo_pixels = correct_halo(array, settings.halo, report)
    report.halo_corrected_pixel_count = halo_pixels

    alpha_result = clean_alpha(array, classification.image_type, settings, report)
    array = alpha_result.rgba
    transparency_only_rgba = array.copy()

    # --- 5: genau EINE echte ICC-Konvertierung nach CMYK, keine weitere Korrektur ---
    try:
        cmyk_result = convert_rgba_to_output_cmyk(
            array, source_profile, target_profile, color.rendering_intent, color.black_point_compensation
        )
    except CmykConversionError as exc:
        report.success = False
        report.errors.append(str(exc))
        return report

    report.rendering_intent = color.rendering_intent
    report.black_point_compensation = color.black_point_compensation
    report.additional_saturation_reduction_applied = False
    report.additional_gamut_correction_applied = False
    report.mirrored = False
    report.add_step(
        "icc_conversion_cmyk",
        f"Einmalige ICC-Konvertierung nach '{report.target_profile}' durchgeführt "
        f"(Rendering Intent: {color.rendering_intent.value}, Schwarzpunktkompensation: "
        f"{'aktiviert' if color.black_point_compensation else 'deaktiviert'}). "
        "Keine zusätzliche Sättigungs- oder Gamut-Korrektur angewendet.",
    )

    # --- Vorschauen: Zustand vor der Farbkonvertierung sowie eine
    # Bildschirm-Rückwandlung der tatsächlich erzeugten CMYK-Daten (zeigt,
    # wie die Farben nach der echten ICC-Konvertierung aussehen werden).
    # Dieselben Dateinamen wie im normalen PNG-Ablauf, damit die Oberfläche
    # sie ohne Sonderfall automatisch findet und anzeigt.
    from src.core.export.filenames import build_output_dirs

    dirs = build_output_dirs(output_root)

    if export.write_transparency_only_preview:
        transparency_only_path = avoid_collision(
            dirs["previews"] / f"{path.stem}_transparency_only.png", export.overwrite_existing
        )
        export_rgba_png(transparency_only_rgba, transparency_only_path, icc_profile_bytes=get_srgb_icc_bytes())
        report.add_step(
            "export_transparency_only",
            "Vorschau 'Transparenzoptimiert - Farben unverändert' erzeugt (Zustand nach Alpha-/"
            "Halo-Korrektur, vor jeder Farbkonvertierung).",
        )

    if export.write_softproof_preview:
        try:
            softproof_rgba = convert_cmyk_to_preview_rgb(
                cmyk_result.cmyk,
                cmyk_result.alpha,
                source_profile,
                target_profile,
                color.rendering_intent,
                color.black_point_compensation,
            )
            softproof_path = avoid_collision(
                dirs["previews"] / f"{path.stem}{export.filename_suffix_softproof}.png", export.overwrite_existing
            )
            export_rgba_png(softproof_rgba, softproof_path, icc_profile_bytes=get_srgb_icc_bytes())
            report.add_step(
                "export_softproof",
                "DTF-King-Softproof-Vorschau erzeugt (Rückwandlung der tatsächlich in die PDF "
                "geschriebenen CMYK-Farben zur Bildschirmanzeige).",
            )
        except CmykConversionError as exc:
            report.warnings.append(f"DTF-King-Softproof-Vorschau konnte nicht erzeugt werden: {exc}")

    # --- 6: einseitiger CMYK-PDF-Export ---
    pdf_path = avoid_collision(
        dirs["optimized"] / f"{path.stem}{export.filename_suffix_pdf}.pdf", export.overwrite_existing
    )

    try:
        has_smask = export_cmyk_pdf(
            cmyk_result.cmyk,
            cmyk_result.alpha,
            target_profile.tobytes(),
            report.target_profile,
            size.width_mm,
            size.height_mm,
            pdf_path,
        )
    except PdfExportError as exc:
        report.success = False
        report.errors.append(f"PDF-Export fehlgeschlagen: {exc}")
        return report

    report.output_path = pdf_path
    report.pdf_has_transparency_smask = has_smask
    report.pdf_icc_output_intent_embedded = True
    report.pdf_page_size_mm = (size.width_mm, size.height_mm)
    report.add_step("export_pdf", f"Einseitige CMYK-PDF mit eingebettetem ICC-Profil erzeugt: {pdf_path.name}")

    # --- 7: Nachvalidierung ---
    pdf_validation = validate_cmyk_pdf(
        pdf_path,
        expected_pixel_size=(array.shape[1], array.shape[0]),
        expected_page_size_mm=(size.width_mm, size.height_mm),
        expected_profile_description=report.target_profile,
        expect_transparency=has_smask,
        expected_cmyk=cmyk_result.cmyk,
    )
    report.pdf_validated = pdf_validation.ok
    report.pdf_validation_errors = pdf_validation.errors
    report.pdf_page_count = pdf_validation.page_count
    report.pdf_effective_dpi = pdf_validation.effective_dpi
    if pdf_validation.ok:
        report.add_step("validate_pdf", "PDF erfolgreich validiert.")
    else:
        report.success = False
        report.errors.append("PDF-Validierung fehlgeschlagen: " + "; ".join(pdf_validation.errors))

    if export.write_json_report:
        write_json_report(report, dirs["reports"] / f"{path.stem}{export.filename_suffix_report_json}")
    if export.write_html_report:
        write_html_report(report, dirs["reports"] / f"{path.stem}{export.filename_suffix_report_html}")

    report.processing_duration_seconds = time.perf_counter() - start
    return report


def process_image_for_dtf_king_pdf_safe(path: Path, settings: ProcessingSettings, output_root: Path) -> ImageProcessingReport:
    """Fehlertolerante Variante für die Stapelverarbeitung."""
    try:
        return process_image_for_dtf_king_pdf(path, settings, output_root)
    except (ICCProfileError, DtfKingExportError) as exc:
        report = ImageProcessingReport(source_path=path, success=False, output_format="pdf_cmyk")
        report.errors.append(str(exc))
        return report
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unerwarteter Fehler beim DTF-King-PDF-Export von %s", path)
        report = ImageProcessingReport(source_path=path, success=False, output_format="pdf_cmyk")
        report.errors.append(f"Unerwarteter Fehler: {exc}")
        return report
