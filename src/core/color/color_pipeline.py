"""Orchestriert ICC-Farbmanagement, Gamut-Analyse, Rendering-Intent und Farboptimierung.

Siehe Prompt Abschnitt 9 (ICC-Farbmanagement) und Abschnitt 10 (automatische Farboptimierung).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms

from src.config.defaults import ProcessingSettings
from src.core.analysis.image_loader import LoadedImage
from src.core.color.delta_e import delta_e_cie76, rgb_array_to_lab
from src.core.color.icc_manager import (
    get_srgb_icc_bytes,
    get_srgb_profile,
    load_icc_profile,
    load_icc_profile_from_bytes,
    profile_color_space,
    profile_description,
)
from src.core.color.rendering_intent import select_rendering_intent
from src.core.color.saturation_optimizer import reduce_saturation_pass
from src.models.report import ImageProcessingReport

logger = logging.getLogger(__name__)

_INTENT_TO_CMS = {
    "perceptual": ImageCms.Intent.PERCEPTUAL,
    "relative_colorimetric": ImageCms.Intent.RELATIVE_COLORIMETRIC,
    "saturation": ImageCms.Intent.SATURATION,
    "absolute_colorimetric": ImageCms.Intent.ABSOLUTE_COLORIMETRIC,
}


@dataclass
class ColorProcessingInfo:
    source_profile_name: str
    target_profile_name: str
    target_icc_bytes: bytes | None
    softproof_rgba: np.ndarray | None = None
    target_profile: object | None = None
    rendering_intent_cms: object | None = None
    has_valid_target_profile: bool = False


def _cms_intent(intent) -> ImageCms.Intent:
    return _INTENT_TO_CMS[intent.value]


def _round_trip(rgb: np.ndarray, source_profile, target_profile, target_mode: str, cms_intent, bpc: bool) -> np.ndarray:
    flags = ImageCms.Flags.BLACKPOINTCOMPENSATION if bpc else ImageCms.Flags.NONE
    t1 = ImageCms.buildTransform(source_profile, target_profile, "RGB", target_mode, renderingIntent=cms_intent, flags=flags)
    t2 = ImageCms.buildTransform(target_profile, source_profile, target_mode, "RGB", renderingIntent=cms_intent, flags=flags)
    img_rgb = Image.fromarray(np.ascontiguousarray(rgb), mode="RGB")
    img_target = ImageCms.applyTransform(img_rgb, t1)
    img_back = ImageCms.applyTransform(img_target, t2)
    return np.array(img_back)


def optimize_colors(
    rgba: np.ndarray,
    loaded: LoadedImage,
    settings: ProcessingSettings,
    report: ImageProcessingReport,
) -> tuple[np.ndarray, ColorProcessingInfo]:
    color_cfg = settings.color
    gamut_cfg = settings.gamut

    # --- Quellprofil ---
    source_profile = None
    if loaded.icc_profile_bytes:
        source_profile = load_icc_profile_from_bytes(loaded.icc_profile_bytes)
        if source_profile is None:
            report.warnings.append(
                "Das eingebettete Quellprofil ist beschädigt oder inkompatibel. Es wird sRGB angenommen."
            )
    if source_profile is None:
        source_profile = get_srgb_profile()
        source_name = "sRGB (angenommen)"
    else:
        source_name = profile_description(source_profile)
    report.source_profile = source_name

    # --- Zielprofil ---
    target_profile = None
    no_target_selected = True
    if color_cfg.target_profile_path:
        target_profile = load_icc_profile(Path(color_cfg.target_profile_path))
        if target_profile is None:
            report.warnings.append(
                f"Das gewählte Zielprofil konnte nicht geladen werden: {Path(color_cfg.target_profile_path).name}. "
                "Es wurde keine Farbraum-Anpassung vorgenommen."
            )
        else:
            no_target_selected = False

    if no_target_selected:
        report.target_profile = "kein Zielprofil ausgewählt"
        if color_cfg.target_profile_path is None:
            report.warnings.append(
                "Kein ICC-Zielprofil ausgewählt. Es wurde keine Farbraum-Anpassung an ein Druckprofil vorgenommen."
            )
        info = ColorProcessingInfo(source_name, report.target_profile, None, None)
        return rgba, info

    target_name = profile_description(target_profile)
    report.target_profile = target_name
    target_color_space = profile_color_space(target_profile)
    target_mode = "CMYK" if target_color_space.startswith("CMYK") else "RGB"

    rgb = rgba[:, :, :3]
    alpha = rgba[:, :, 3]
    visible_mask = alpha > 0
    if not visible_mask.any():
        info = ColorProcessingInfo(
            source_name, target_name, target_profile.tobytes(), target_profile=target_profile, has_valid_target_profile=True
        )
        return rgba, info

    try:
        rt_relcol = _round_trip(
            rgb, source_profile, target_profile, target_mode, ImageCms.Intent.RELATIVE_COLORIMETRIC, color_cfg.black_point_compensation
        )
    except Exception:
        logger.exception("ICC-Transformation fehlgeschlagen, Zielprofil evtl. inkompatibel.")
        report.warnings.append(
            "Die Farbraum-Transformation mit dem gewählten Zielprofil ist fehlgeschlagen. Es wurde keine Farbanpassung vorgenommen."
        )
        info = ColorProcessingInfo(source_name, target_name, None)
        return rgba, info

    lab_orig = rgb_array_to_lab(rgb)
    lab_rt = rgb_array_to_lab(rt_relcol)
    delta = delta_e_cie76(lab_orig, lab_rt)

    visible_delta = delta[visible_mask]
    out_of_gamut_before_pct = float((visible_delta > gamut_cfg.delta_e_out_of_gamut).sum() / visible_delta.size * 100)

    intent, reason = select_rendering_intent(report.detected_type, out_of_gamut_before_pct, color_cfg, gamut_cfg)
    report.rendering_intent = intent

    if intent.value == "relative_colorimetric":
        working_rgb = rt_relcol
        working_delta = delta
    else:
        try:
            working_rgb = _round_trip(
                rgb, source_profile, target_profile, target_mode, _cms_intent(intent), color_cfg.black_point_compensation
            )
            working_delta = delta_e_cie76(lab_orig, rgb_array_to_lab(working_rgb))
        except Exception:
            logger.exception("ICC-Transformation mit perzeptivem Intent fehlgeschlagen.")
            working_rgb = rt_relcol
            working_delta = delta

    optimized_rgb = rgb.copy()
    total_adjusted = 0
    total_yellow_orange = 0
    prev_mean_delta = float(working_delta[visible_mask].mean())

    for _ in range(gamut_cfg.max_optimization_iterations):
        out_of_gamut_mask = (working_delta > gamut_cfg.delta_e_out_of_gamut) & visible_mask
        if not out_of_gamut_mask.any():
            break
        result = reduce_saturation_pass(optimized_rgb, working_delta, out_of_gamut_mask, gamut_cfg)
        optimized_rgb = result.rgb
        total_adjusted += result.adjusted_pixel_count
        total_yellow_orange += result.yellow_orange_adjusted_count

        try:
            working_rgb = _round_trip(
                optimized_rgb, source_profile, target_profile, target_mode, _cms_intent(intent), color_cfg.black_point_compensation
            )
            working_delta = delta_e_cie76(rgb_array_to_lab(optimized_rgb), rgb_array_to_lab(working_rgb))
        except Exception:
            break

        new_mean_delta = float(working_delta[visible_mask].mean())
        improvement = prev_mean_delta - new_mean_delta
        prev_mean_delta = new_mean_delta
        if improvement < gamut_cfg.min_improvement_delta_e:
            break

    visible_final_delta = working_delta[visible_mask]
    out_of_gamut_after_pct = float((visible_final_delta > gamut_cfg.delta_e_out_of_gamut).sum() / visible_final_delta.size * 100)

    report.out_of_gamut_before = out_of_gamut_before_pct
    report.out_of_gamut_after = out_of_gamut_after_pct
    report.mean_delta_e = float(visible_final_delta.mean())
    report.max_delta_e = float(visible_final_delta.max())

    report.add_step(
        "color_optimization",
        f"Farben für das Druckprofil '{target_name}' angepasst ({reason})",
    )
    if total_adjusted > 0:
        report.add_step(
            "saturation_reduction",
            f"Sättigung von {total_adjusted} Pixeln außerhalb des Farbraums gezielt reduziert.",
            pixels_affected=total_adjusted,
        )
    if color_cfg.show_gamut_warning:
        if out_of_gamut_before_pct > 0:
            report.warnings.append(
                f"{out_of_gamut_before_pct:.1f}% der Farben lagen außerhalb des druckbaren Farbraums und wurden angepasst "
                f"(davor Ø ΔE {float(visible_delta.mean()):.2f}, danach Ø ΔE {report.mean_delta_e:.2f})."
            )
    if total_yellow_orange > 0:
        report.warnings.append(
            f"{total_yellow_orange} gelb-/orangefarbene Pixel wurden angepasst - Gelbtöne bitte gesondert prüfen."
        )

    out_rgba = rgba.copy()
    out_rgba[:, :, :3] = np.clip(optimized_rgb, 0, 255).astype(np.uint8)

    softproof_rgba = None
    if settings.export.write_softproof_preview:
        try:
            flags = ImageCms.Flags.SOFTPROOFING
            if color_cfg.black_point_compensation:
                flags = flags | ImageCms.Flags.BLACKPOINTCOMPENSATION
            proof_transform = ImageCms.buildProofTransform(
                source_profile,
                source_profile,
                target_profile,
                "RGB",
                "RGB",
                renderingIntent=_cms_intent(intent),
                proofRenderingIntent=ImageCms.Intent.RELATIVE_COLORIMETRIC,
                flags=flags,
            )
            proof_img = ImageCms.applyTransform(Image.fromarray(np.ascontiguousarray(out_rgba[:, :, :3]), "RGB"), proof_transform)
            softproof_rgba = np.dstack([np.array(proof_img), alpha])
        except Exception:
            logger.exception("Softproof-Vorschau konnte nicht erzeugt werden.")
            report.warnings.append("Softproof-Vorschau konnte nicht erzeugt werden.")

    target_icc_bytes = get_srgb_icc_bytes()  # Hauptausgabe bleibt RGB -> sRGB-Profil einbetten
    info = ColorProcessingInfo(
        source_profile_name=source_name,
        target_profile_name=target_name,
        target_icc_bytes=target_icc_bytes,
        softproof_rgba=softproof_rgba,
        target_profile=target_profile,
        rendering_intent_cms=_cms_intent(intent),
        has_valid_target_profile=True,
    )
    return out_rgba, info
