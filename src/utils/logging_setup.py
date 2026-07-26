"""Zentrale Logging-Konfiguration. Schreibt lokal in %LOCALAPPDATA% - keine Cloud."""
from __future__ import annotations

import logging
import sys

from src.config.paths import get_user_data_dir


def setup_logging(level: int = logging.INFO) -> None:
    log_dir = get_user_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "dtf_korrektur.log"

    root = logging.getLogger()
    if root.handlers:
        return  # bereits konfiguriert

    root.setLevel(level)
    fmt = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)
    root.addHandler(console_handler)
