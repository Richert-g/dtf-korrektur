"""Erzeugt/überschreibt die Referenzbilder für die visuellen Regressionstests
(tests/visual_regression/test_golden_images.py).

NUR manuell ausführen, wenn eine Änderung an der Bildverarbeitung bewusst
und geprüft ist - das Skript vertraut blind der aktuellen Pipeline-Ausgabe.
Nach dem Ausführen die veränderten Dateien unter tests/fixtures/golden/ von
Auge prüfen (z. B. im Diff-Viewer oder direkt öffnen), bevor sie committet
werden.

Aufruf (aus dem Projektstamm):
    python scripts/update_golden_images.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image

from tests.visual_regression.golden_utils import GOLDEN_DIR, GOLDEN_SCENARIOS, golden_path, run_scenario


def main() -> None:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for name in GOLDEN_SCENARIOS:
            scenario_dir = tmp_path / name
            scenario_dir.mkdir()
            result = run_scenario(name, scenario_dir)
            path = golden_path(name)
            Image.fromarray(result, mode="RGBA").save(path)
            print(f"geschrieben: {path}")


if __name__ == "__main__":
    main()
