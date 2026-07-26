"""Einstiegspunkt der DTF-Korrektur-Anwendung."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ermöglicht den Start sowohl als Modul (`python -m src.app.main`) als auch
# per PyInstaller-EXE, bei der `src` ggf. nicht automatisch im Pfad liegt.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from src.config.paths import get_app_icon_path
from src.utils.logging_setup import setup_logging

logger = logging.getLogger(__name__)


def main() -> int:
    setup_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("DTF Korrektur")
    app.setOrganizationName("DTF Korrektur")

    icon_path = get_app_icon_path()
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    else:
        logger.warning("App-Icon nicht gefunden unter %s", icon_path)

    def handle_exception(exc_type, exc_value, exc_traceback):
        logger.critical("Unbehandelte Ausnahme", exc_info=(exc_type, exc_value, exc_traceback))
        QMessageBox.critical(
            None,
            "Unerwarteter Fehler",
            f"Ein unerwarteter Fehler ist aufgetreten:\n{exc_value}\n\nDetails wurden protokolliert.",
        )

    sys.excepthook = handle_exception

    from src.app.ui.main_window import MainWindow

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
