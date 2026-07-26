"""Zentrale Verarbeitungspipeline: Analyse -> Klassifizierung -> Alpha -> Halo -> Farbe -> Export -> Bericht.

Diese Datei orchestriert alle core-Module. Sie wird schrittweise erweitert:
Phase 1: Laden, Analysieren, unveränderter RGB-PNG-Export, Bericht.
Phase 2: Klassifizierung, Alpha-Bereinigung, Halo-Korrektur, Inseln/Löcher.
Phase 3: ICC-Farbmanagement, Softproof, Gamut, Farboptimierung.
Phase 4: Weißmaske, Presets, Hintergrundsimulation (Batch-Ebene in workers/).
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

from src.config.defaults import ProcessingSettings
from src.core.analysis.alpha_analysis import analyze_alpha_channel
from src.core.analysis.image_loader import ImageLoadError, load_image
from src.core.color.icc_manager import get_srgb_icc_bytes
from src.core.export.filenames import avoid_collision, build_output_paths
from src.core.export.png_export import export_alpha_mask_png, export_rgba_png
from src.core.reporting.report_writer import write_html_report, write_json_report
from src.models.enums import OutputFormat
from src.models.report import ImageProcessingReport
from src.utils.fs_utils import ensure_dir

logger = logging.getLogger(__name__)

_OUTPUT_FORMAT_EXTENSIONS = {
    OutputFormat.PNG_RGB: ".png",
    OutputFormat.TIFF_RGB: ".tiff",
    OutputFormat.JPEG_RGB: ".jpg",
    OutputFormat.PDF_CMYK: ".pdf",
}


def _export_primary_pdf(array, color_info, settings: ProcessingSettings, optimized_path: Path, report: ImageProcessingReport) -> bool:
    """Verpackt das bereits farboptimierte RGB-Ergebnis als druckfertige CMYK-PDF.

    Nutzt dieselben Bausteine wie der DTF-King-Export (echte, einmalige ICC-
    Konvertierung, keine eigene Näherungsformel), respektiert dabei aber die
    AKTUELL aktiven Farbeinstellungen (Rendering Intent, Schwarzpunkt-
    kompensation) statt sie wie das DTF-King-Preset fest vorzugeben. Gibt
    False zurück, wenn kein gültiges CMYK-Zielprofil vorliegt - dann wird
    NICHT stillschweigend eine andere Datei erzeugt.
    """
    from src.core.color.cmyk_convert import CmykConversionError, convert_rgba_to_output_cmyk
    from src.core.color.profile_validation import validate_cmyk_output_profile
    from src.core.export.pdf_export import PdfExportError, export_cmyk_pdf, validate_cmyk_pdf
    from src.core.export.print_size import compute_print_size

    color = settings.color
    export = settings.export

    if not color.target_profile_path:
        report.errors.append(
            "Ausgabeformat PDF gewählt, aber kein ICC-Zielprofil ausgewählt. Es wurde keine PDF erzeugt."
        )
        return False

    validation = validate_cmyk_output_profile(Path(color.target_profile_path))
    if not validation.ok:
        report.errors.append(validation.error or "ICC-Zielprofil ist ungültig.")
        return False

    if color_info is None or color_info.source_profile is None or color_info.target_profile is None:
        report.errors.append("Quell- oder Zielprofil konnte nicht ermittelt werden - keine PDF erzeugt.")
        return False

    size = compute_print_size(
        pixel_width=array.shape[1],
        pixel_height=array.shape[0],
        target_dpi=export.pdf_target_dpi,
        width_mm=export.pdf_width_mm,
        height_mm=export.pdf_height_mm,
    )
    if size.warning:
        report.warnings.append(size.warning)

    try:
        cmyk_result = convert_rgba_to_output_cmyk(
            array, color_info.source_profile, color_info.target_profile, report.rendering_intent, color.black_point_compensation
        )
    except CmykConversionError as exc:
        report.errors.append(str(exc))
        return False

    report.black_point_compensation = color.black_point_compensation
    report.additional_saturation_reduction_applied = False
    report.mirrored = False

    try:
        has_smask = export_cmyk_pdf(
            cmyk_result.cmyk,
            cmyk_result.alpha,
            color_info.target_profile.tobytes(),
            validation.description or Path(color.target_profile_path).name,
            size.width_mm,
            size.height_mm,
            optimized_path,
        )
    except PdfExportError as exc:
        report.errors.append(f"PDF-Export fehlgeschlagen: {exc}")
        return False

    report.output_path = optimized_path
    report.pdf_has_transparency_smask = has_smask
    report.pdf_icc_output_intent_embedded = True
    report.pdf_page_size_mm = (size.width_mm, size.height_mm)
    report.add_step(
        "export_pdf",
        f"Einseitige CMYK-PDF mit eingebettetem ICC-Profil '{validation.description}' erzeugt.",
    )

    pdf_validation = validate_cmyk_pdf(
        optimized_path,
        expected_pixel_size=(array.shape[1], array.shape[0]),
        expected_page_size_mm=(size.width_mm, size.height_mm),
        expected_profile_description=validation.description or "",
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
        report.errors.append("PDF-Validierung fehlgeschlagen: " + "; ".join(pdf_validation.errors))
        return False

    return True


def process_image(path: Path, settings: ProcessingSettings, output_root: Path) -> ImageProcessingReport:
    start = time.perf_counter()
    report = ImageProcessingReport(source_path=path)

    loaded = load_image(path)
    array = loaded.array.copy()
    report.width, report.height = array.shape[1], array.shape[0]
    report.file_format = loaded.file_format

    if loaded.icc_profile_description:
        report.source_profile = loaded.icc_profile_description
    else:
        report.source_profile = "sRGB (angenommen)"
        report.assumed_profiles.append("sRGB (kein eingebettetes Profil gefunden)")
        report.warnings.append("Diese Datei enthält kein eingebettetes Farbprofil. Es wird sRGB angenommen.")

    alpha_stats = analyze_alpha_channel(array, settings.alpha)
    report.transparent_pixel_count = alpha_stats.fully_transparent_count
    report.semi_transparent_pixel_count = alpha_stats.semi_transparent_count

    # --- Klassifizierung (Phase 2) ---
    from src.core.classification.classifier import classify_image

    classification = classify_image(array, alpha_stats, settings.classification)
    report.detected_type = classification.image_type
    report.classification_reasons = [f"{r.signal}: {r.value}" for r in classification.reasons]

    # --- Halo-/Farbsaumkorrektur (Phase 2) ---
    # Muss VOR der Alpha-Bereinigung laufen, solange die halbtransparenten
    # Randpixel noch existieren (Prompt Abschnitt 7 "Harte Kante" & Abschnitt 8).
    from src.core.halo.halo_correction import correct_halo

    array, halo_pixels = correct_halo(array, settings.halo, report)
    report.halo_corrected_pixel_count = halo_pixels

    # --- Alpha-Bereinigung (Phase 2) ---
    from src.core.alpha.alpha_cleanup import clean_alpha

    alpha_before_cleanup = array[:, :, 3].copy()
    alpha_result = clean_alpha(array, classification.image_type, settings, report)
    array = alpha_result.rgba
    alpha_after_cleanup = array[:, :, 3]
    transparency_only_rgba = array.copy()

    # --- Farboptimierung / ICC (Phase 3) ---
    from src.core.color.color_pipeline import optimize_colors

    array, color_info = optimize_colors(array, loaded, settings, report)

    # --- Export ---
    export = settings.export
    # OutputFormat erbt von str: je nach Herkunft (z. B. QComboBox.currentData()
    # in PySide6) kann hier ein reines str-Objekt statt des Enum-Members
    # ankommen - defensiv erneut wrappen, damit .value weiter unten nicht crasht.
    output_format = OutputFormat(export.output_format)
    paths = build_output_paths(path, output_root, export)
    optimized_path = avoid_collision(
        paths.optimized_png.with_suffix(_OUTPUT_FORMAT_EXTENSIONS[output_format]), export.overwrite_existing
    )
    report.output_format = output_format.value

    if export.write_transparency_only_preview:
        transparency_only_path = avoid_collision(paths.transparency_only_png, export.overwrite_existing)
        export_rgba_png(transparency_only_rgba, transparency_only_path, icc_profile_bytes=get_srgb_icc_bytes())
        report.add_step(
            "export_transparency_only",
            "Vorschau 'Transparenzoptimiert - Farben unverändert' erzeugt (Zustand nach Alpha-/"
            "Halo-Korrektur, vor jeder Farbkonvertierung).",
        )

    icc_bytes = color_info.target_icc_bytes if color_info else None

    if output_format == OutputFormat.PDF_CMYK:
        pdf_ok = _export_primary_pdf(array, color_info, settings, optimized_path, report)
        if not pdf_ok:
            report.success = False
            report.processing_duration_seconds = time.perf_counter() - start
            return report
    elif output_format == OutputFormat.TIFF_RGB:
        from src.core.export.raster_export import export_rgba_tiff

        export_rgba_tiff(array, optimized_path, icc_profile_bytes=icc_bytes)
        report.output_path = optimized_path
        report.add_step("export_tiff", "Verlustfreies RGB-TIFF mit Transparenz erzeugt.")
    elif output_format == OutputFormat.JPEG_RGB:
        from src.core.export.raster_export import export_rgb_jpeg

        export_rgb_jpeg(
            array,
            optimized_path,
            icc_profile_bytes=icc_bytes,
            quality=export.jpeg_quality,
            background_rgb=export.jpeg_background_rgb,
        )
        report.output_path = optimized_path
        report.warnings.append(
            "JPEG unterstützt keine Transparenz - der Hintergrund wurde auf eine Volltonfarbe geflacht."
        )
        report.add_step("export_jpeg", f"RGB-JPEG (Qualität {export.jpeg_quality}) ohne Transparenz erzeugt.")
    else:
        export_rgba_png(array, optimized_path, icc_profile_bytes=icc_bytes)
        report.output_path = optimized_path
        report.add_step(
            "export_png",
            "RGB-PNG mit Transparenz für den DTF-RIP erzeugt.",
        )

    if export.write_alpha_mask:
        mask_path = avoid_collision(paths.alpha_mask_png, export.overwrite_existing)
        export_alpha_mask_png(array, mask_path)
        report.add_step("export_alpha_mask", "Alpha-Maske als eigenständige PNG-Datei exportiert.")

    if export.write_diff_overlays:
        from src.core.export.diff_overlay import (
            REMOVED_HIGHLIGHT_COLOR,
            STRENGTHENED_HIGHLIGHT_COLOR,
            compute_removed_pixels_mask,
            compute_strengthened_pixels_mask,
            generate_diff_overlay,
        )

        removed_mask = compute_removed_pixels_mask(alpha_before_cleanup, alpha_after_cleanup)
        strengthened_mask = compute_strengthened_pixels_mask(alpha_before_cleanup, alpha_after_cleanup)

        removed_overlay = generate_diff_overlay(loaded.array, removed_mask, REMOVED_HIGHLIGHT_COLOR)
        removed_path = avoid_collision(paths.removed_pixels_png, export.overwrite_existing)
        export_rgba_png(removed_overlay, removed_path, icc_profile_bytes=get_srgb_icc_bytes())

        strengthened_overlay = generate_diff_overlay(loaded.array, strengthened_mask, STRENGTHENED_HIGHLIGHT_COLOR)
        strengthened_path = avoid_collision(paths.strengthened_pixels_png, export.overwrite_existing)
        export_rgba_png(strengthened_overlay, strengthened_path, icc_profile_bytes=get_srgb_icc_bytes())

        report.add_step(
            "export_diff_overlays",
            f"Diff-Vorschau erzeugt: {int(removed_mask.sum())} entfernte, "
            f"{int(strengthened_mask.sum())} verstärkte Pixel farbig markiert.",
            pixels_affected=int(removed_mask.sum() + strengthened_mask.sum()),
        )

    if export.write_gamut_warning and color_info is not None and color_info.out_of_gamut_mask is not None:
        from src.core.export.diff_overlay import GAMUT_WARNING_HIGHLIGHT_COLOR, generate_diff_overlay

        gamut_mask = color_info.out_of_gamut_mask
        if gamut_mask.any():
            gamut_overlay = generate_diff_overlay(loaded.array, gamut_mask, GAMUT_WARNING_HIGHLIGHT_COLOR)
            gamut_path = avoid_collision(paths.gamut_warning_png, export.overwrite_existing)
            export_rgba_png(gamut_overlay, gamut_path, icc_profile_bytes=get_srgb_icc_bytes())
            report.add_step(
                "export_gamut_warning",
                f"Gamut-Warnung erzeugt: {int(gamut_mask.sum())} Pixel lagen außerhalb des Zielfarbraums.",
                pixels_affected=int(gamut_mask.sum()),
            )

    if export.write_white_mask:
        from src.core.export.white_mask import generate_white_mask, recommend_choke_px

        choke = export.white_mask_choke_px or recommend_choke_px(report.width, report.height)
        white_mask = generate_white_mask(array, choke)
        white_mask_path = avoid_collision(paths.white_mask_png, export.overwrite_existing)
        from PIL import Image as _Image

        ensure_dir(white_mask_path.parent)
        _Image.fromarray(white_mask, mode="L").save(white_mask_path, format="PNG")
        report.add_step(
            "export_white_mask",
            f"Weißunterlegungs-Vorschau erzeugt (Choke {choke:.1f}px). "
            "Hinweis: Die endgültige Weißkanalsteuerung erfolgt im DTF-RIP.",
        )

    if export.write_cmyk_tiff:
        if color_info and color_info.has_valid_target_profile:
            from src.core.export.cmyk_export import CmykExportError, export_cmyk_tiff_preview

            try:
                export_cmyk_tiff_preview(
                    array,
                    color_info.target_profile,
                    color_info.rendering_intent_cms,
                    settings.color.black_point_compensation,
                    avoid_collision(paths.cmyk_tiff, export.overwrite_existing),
                )
                report.add_step(
                    "export_cmyk_tiff",
                    "Optionale CMYK-TIFF-Vorschau mit dem gewählten Zielprofil erzeugt.",
                )
            except CmykExportError as exc:
                report.warnings.append(str(exc))
        else:
            report.warnings.append(
                "CMYK-TIFF-Export übersprungen: Ohne gültiges ICC-Zielprofil wird keine "
                "angeblich druckfertige CMYK-Datei erzeugt."
            )

    if export.write_softproof_preview and color_info and color_info.softproof_rgba is not None:
        from src.core.export.png_export import export_rgba_png as _export_softproof

        softproof_path = avoid_collision(paths.softproof_png, export.overwrite_existing)
        _export_softproof(color_info.softproof_rgba, softproof_path, icc_profile_bytes=get_srgb_icc_bytes())
        report.add_step("export_softproof", "Softproof-Vorschau (Simulation auf dem Zielprofil) erzeugt.")

    if export.write_json_report:
        write_json_report(report, avoid_collision(paths.report_json, True))
    if export.write_html_report:
        write_html_report(report, avoid_collision(paths.report_html, True))

    report.processing_duration_seconds = time.perf_counter() - start
    report.success = True
    return report


def process_image_safe(path: Path, settings: ProcessingSettings, output_root: Path) -> ImageProcessingReport:
    """Fehlertolerante Variante: eine fehlerhafte Datei darf die Stapelverarbeitung nicht stoppen."""
    try:
        return process_image(path, settings, output_root)
    except ImageLoadError as exc:
        logger.warning("Verarbeitung fehlgeschlagen für %s: %s", path, exc)
        report = ImageProcessingReport(source_path=path, success=False)
        report.errors.append(str(exc))
        return report
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unerwarteter Fehler bei der Verarbeitung von %s", path)
        report = ImageProcessingReport(source_path=path, success=False)
        report.errors.append(f"Unerwarteter Fehler: {exc}")
        return report
