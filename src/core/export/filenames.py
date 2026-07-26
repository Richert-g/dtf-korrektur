"""Dateinamens- und Ausgabeordnerlogik (Prompt Abschnitt 15 & 17)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.config.defaults import ExportSettings
from src.utils.fs_utils import ensure_dir


@dataclass
class OutputPaths:
    optimized_png: Path
    softproof_png: Path
    alpha_mask_png: Path
    white_mask_png: Path
    removed_pixels_png: Path
    strengthened_pixels_png: Path
    report_json: Path
    report_html: Path
    cmyk_tiff: Path


def build_output_dirs(output_root: Path) -> dict[str, Path]:
    dirs = {
        "optimized": output_root / "optimized",
        "previews": output_root / "previews",
        "reports": output_root / "reports",
        "masks": output_root / "masks",
    }
    for d in dirs.values():
        ensure_dir(d)
    return dirs


def build_output_paths(source_path: Path, output_root: Path, export: ExportSettings) -> OutputPaths:
    dirs = build_output_dirs(output_root)
    stem = source_path.stem
    return OutputPaths(
        optimized_png=dirs["optimized"] / f"{stem}{export.filename_suffix_optimized}.png",
        softproof_png=dirs["previews"] / f"{stem}{export.filename_suffix_softproof}.png",
        alpha_mask_png=dirs["masks"] / f"{stem}{export.filename_suffix_alpha_mask}.png",
        white_mask_png=dirs["masks"] / f"{stem}{export.filename_suffix_white_mask}.png",
        removed_pixels_png=dirs["previews"] / f"{stem}{export.filename_suffix_removed_pixels}.png",
        strengthened_pixels_png=dirs["previews"] / f"{stem}{export.filename_suffix_strengthened_pixels}.png",
        report_json=dirs["reports"] / f"{stem}{export.filename_suffix_report_json}",
        report_html=dirs["reports"] / f"{stem}{export.filename_suffix_report_html}",
        cmyk_tiff=dirs["optimized"] / f"{stem}_dtf_cmyk_preview.tiff",
    )


def avoid_collision(path: Path, overwrite_allowed: bool) -> Path:
    """Verhindert ungefragtes Überschreiben: hängt bei Bedarf einen Zähler an."""
    if overwrite_allowed or not path.exists():
        return path
    counter = 1
    stem, suffix = path.stem, path.suffix
    while True:
        candidate = path.with_name(f"{stem}_{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1
