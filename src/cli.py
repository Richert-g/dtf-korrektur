"""Kommandozeilen-/Automatisierungsmodus: Batch-Verarbeitung ohne Oberfläche,
z. B. für den Windows-Taskplaner, Linux-cron oder macOS launchd (siehe
README, Abschnitt "Kommandozeilen-/Automatisierungsmodus").

Bewusst OHNE jede Abhängigkeit von PySide6/Qt (im Unterschied zu
app.main.py) - dadurch kann unter Windows ein eigenständiger, deutlich
kleinerer Konsolen-Build erzeugt werden (siehe scripts/build_windows.ps1:
DTF-Korrektur-CLI.exe). Die normale GUI-EXE wird mit --windowed gebaut und
hat gar kein Konsolenfenster, liefert also weder stdout-Ausgaben noch
zuverlässige Exit-Codes an einen Taskplaner zurück - genau dafür ist dieser
zweite Build gedacht.

Exit-Codes:
    0 - alle Dateien erfolgreich verarbeitet
    1 - mindestens eine Datei fehlgeschlagen
    2 - ungültige Aufrufparameter (z. B. unbekanntes Preset, keine Dateien gefunden)
"""
from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Ermöglicht den Start sowohl als Modul (`python -m src.cli`) als auch per
# PyInstaller-Konsolen-EXE, bei der `src` ggf. nicht automatisch im Pfad liegt
# (siehe app/main.py für dasselbe Muster).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.defaults import DEFAULT_MAX_PARALLEL_WORKERS, ProcessingSettings
from src.core.presets.custom_presets import load_custom_presets
from src.core.presets.presets import apply_preset
from src.core.reporting.batch_report import format_batch_summary_text, write_batch_summary_report
from src.models.enums import OutputFormat, PresetName
from src.models.report import BatchSummary, ImageProcessingReport
from src.utils.file_collection import collect_supported_files
from src.utils.fs_utils import ensure_dir
from src.utils.logging_setup import setup_logging

_FORMAT_CHOICES: dict[str, OutputFormat] = {
    "png": OutputFormat.PNG_RGB,
    "tiff": OutputFormat.TIFF_RGB,
    "jpeg": OutputFormat.JPEG_RGB,
    "pdf": OutputFormat.PDF_CMYK,
}


def _build_arg_parser() -> argparse.ArgumentParser:
    builtin_names = ", ".join(p.value for p in PresetName)
    parser = argparse.ArgumentParser(
        prog="dtf-korrektur-cli",
        description=(
            "DTF Korrektur - Kommandozeilen-/Automatisierungsmodus. "
            "Verarbeitet Bilddateien im Batch ohne Oberfläche, z. B. für Taskplaner/cron."
        ),
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="Eine oder mehrere Bilddateien oder Ordner (Ordner werden rekursiv nach unterstützten Bildformaten durchsucht).",
    )
    parser.add_argument("--output", "-o", required=True, type=Path, help="Ausgabeordner.")
    parser.add_argument(
        "--preset",
        "-p",
        default=PresetName.DTF_AUTO.value,
        help=(
            f"Name eines eingebauten Presets ({builtin_names}) oder eines gespeicherten "
            f"benutzerdefinierten Presets. Standard: '{PresetName.DTF_AUTO.value}'."
        ),
    )
    parser.add_argument(
        "--format",
        choices=sorted(_FORMAT_CHOICES),
        help="Überschreibt das vom Preset gewählte Ausgabeformat (png/tiff/jpeg/pdf).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_MAX_PARALLEL_WORKERS,
        help=f"Maximale Anzahl paralleler Verarbeitungen (Standard: {DEFAULT_MAX_PARALLEL_WORKERS}).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Bestehende Ausgabedateien überschreiben statt automatisch einen neuen Dateinamen zu wählen.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Nur die Abschlusszusammenfassung ausgeben, keine Fortschrittszeile pro Datei.",
    )
    return parser


def _resolve_settings(preset_name: str) -> ProcessingSettings:
    """Löst einen Preset-Namen (eingebaut oder benutzerdefiniert) zu einem
    vollständigen, eigenständigen ProcessingSettings-Objekt auf. Anders als
    MainController.apply_preset()/apply_custom_preset() (die ein bereits
    bestehendes "lebendes" Settings-Objekt in-place verändern) gibt es im CLI-
    Kontext kein solches Objekt - hier wird stets bei den Standardwerten
    begonnen."""
    settings = ProcessingSettings()
    try:
        builtin = PresetName(preset_name)
    except ValueError:
        builtin = None
    if builtin is not None:
        apply_preset(settings, builtin)
        return settings

    custom = load_custom_presets().get(preset_name)
    if custom is not None:
        return custom

    available_builtin = ", ".join(p.value for p in PresetName)
    available_custom = ", ".join(sorted(load_custom_presets())) or "(keine)"
    raise ValueError(
        f"Unbekanntes Preset: '{preset_name}'.\n"
        f"Eingebaute Presets: {available_builtin}\n"
        f"Benutzerdefinierte Presets: {available_custom}"
    )


def run(argv: list[str] | None = None) -> int:
    setup_logging()
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    try:
        settings = _resolve_settings(args.preset)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.format:
        settings.export.output_format = _FORMAT_CHOICES[args.format]
    if args.overwrite:
        settings.export.overwrite_existing = True

    files = collect_supported_files(args.inputs)
    if not files:
        print("Keine unterstützten Bilddateien gefunden.", file=sys.stderr)
        return 2

    output_dir: Path = args.output
    ensure_dir(output_dir)

    if settings.export.output_format == OutputFormat.PDF_CMYK:
        from src.core.export.dtf_king_export import process_image_for_dtf_king_pdf_safe as process_fn
    else:
        from src.core.pipeline import process_image_safe as process_fn

    summary = BatchSummary(total_files=len(files))
    start = time.perf_counter()
    max_workers = max(1, args.workers)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {executor.submit(process_fn, path, settings, output_dir): path for path in files}
        completed = 0
        for future in as_completed(future_to_path):
            path = future_to_path[future]
            completed += 1
            try:
                report: ImageProcessingReport = future.result()
            except Exception as exc:  # noqa: BLE001 - eine Datei darf den Batch nicht stoppen
                report = ImageProcessingReport(source_path=path, success=False)
                report.errors.append(str(exc))
            summary.reports.append(report)
            if report.success:
                summary.succeeded += 1
            else:
                summary.failed += 1
            if not args.quiet:
                status = "OK" if report.success else "FEHLER"
                print(f"[{completed}/{len(files)}] {status}: {path.name}")

    summary.total_duration_seconds = time.perf_counter() - start

    print()
    print(format_batch_summary_text(summary))

    try:
        write_batch_summary_report(summary, output_dir / "reports")
    except OSError:
        print(
            "Hinweis: Zusammenfassender Abschlussbericht (batch_summary.json) konnte nicht gespeichert werden.",
            file=sys.stderr,
        )

    return 0 if summary.failed == 0 else 1


def main() -> int:
    return run()


if __name__ == "__main__":
    sys.exit(main())
