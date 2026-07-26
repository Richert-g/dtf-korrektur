"""Verbindet die Oberfläche mit der Kernlogik (Analyse, Verarbeitung, Presets)."""
from __future__ import annotations

import logging
from pathlib import Path

from src.config.config_manager import load_settings, save_settings
from src.config.defaults import ProcessingSettings
from src.config.paths import get_default_output_root
from src.models.enums import PresetName
from src.utils.fs_utils import ensure_dir

logger = logging.getLogger(__name__)


class MainController:
    def __init__(self) -> None:
        self.settings: ProcessingSettings = load_settings()
        self.current_preset: PresetName = PresetName.DTF_AUTO
        self.selected_files: list[Path] = []
        self.output_dir: Path | None = None
        self.startup_warnings: list[str] = self._validate_loaded_icc_path()

    def _validate_loaded_icc_path(self) -> list[str]:
        """Prüft beim Programmstart, ob ein gespeichertes ICC-Zielprofil noch
        existiert und gültig ist (RGB- oder CMYK-Profil - dieses Feld wird
        von allen Presets gemeinsam genutzt, nicht nur DTF-King). Ungültige/
        fehlende Pfade werden erkannt und zurückgesetzt, statt unbemerkt eine
        defekte Einstellung zu behalten.
        """
        path_str = self.settings.color.target_profile_path
        if not path_str:
            return []
        path = Path(path_str)
        if not path.exists():
            logger.warning("Gespeichertes ICC-Zielprofil nicht mehr vorhanden: %s", path)
            self.settings.color.target_profile_path = None
            return [f"Das zuletzt verwendete ICC-Zielprofil wurde nicht gefunden: {path}"]

        from src.core.color.icc_manager import load_icc_profile

        if load_icc_profile(path) is None:
            logger.warning("Gespeichertes ICC-Zielprofil ist defekt/ungültig geworden: %s", path)
            self.settings.color.target_profile_path = None
            return [f"Das zuletzt verwendete ICC-Zielprofil ist beschädigt oder ungültig: {path.name}"]
        return []

    def set_files(self, files: list[Path]) -> None:
        self.selected_files = files
        if self.output_dir is None and files:
            self.output_dir = get_default_output_root(files[0])

    def set_output_dir(self, path: Path) -> None:
        self.output_dir = path

    def apply_preset(self, preset: PresetName) -> None:
        from src.core.presets.presets import apply_preset as _apply_preset

        self.current_preset = preset
        _apply_preset(self.settings, preset)

    def persist_settings(self) -> None:
        save_settings(self.settings)

    def process_all(self, progress_cb=None) -> list:
        """Verarbeitet alle ausgewählten Dateien synchron (wird i.d.R. im Worker-Thread aufgerufen)."""
        from src.core.pipeline import process_image_safe

        if self.output_dir is None:
            raise ValueError("Kein Ausgabeordner gewählt.")
        ensure_dir(self.output_dir)

        reports = []
        for idx, path in enumerate(self.selected_files, start=1):
            if progress_cb:
                progress_cb(idx, len(self.selected_files), path.name)
            report = process_image_safe(path, self.settings, self.output_dir)
            reports.append(report)
        return reports
