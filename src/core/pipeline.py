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
from src.models.report import ImageProcessingReport
from src.utils.fs_utils import ensure_dir

logger = logging.getLogger(__name__)


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
    paths = build_output_paths(path, output_root, export)
    optimized_path = avoid_collision(paths.optimized_png, export.overwrite_existing)

    if export.write_transparency_only_preview:
        transparency_only_path = avoid_collision(paths.transparency_only_png, export.overwrite_existing)
        export_rgba_png(transparency_only_rgba, transparency_only_path, icc_profile_bytes=get_srgb_icc_bytes())
        report.add_step(
            "export_transparency_only",
            "Vorschau 'Transparenzoptimiert - Farben unverändert' erzeugt (Zustand nach Alpha-/"
            "Halo-Korrektur, vor jeder Farbkonvertierung).",
        )

    icc_bytes = color_info.target_icc_bytes if color_info else None
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
