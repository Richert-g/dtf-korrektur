"""Erstellt technische (JSON) und verständliche (HTML) Berichte (Prompt Abschnitt 18)."""
from __future__ import annotations

import json
from pathlib import Path

from src.models.report import ImageProcessingReport
from src.utils.fs_utils import ensure_dir, retry_on_oserror

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>DTF-Optimierungsbericht: {title}</title>
<style>
body {{ font-family: Segoe UI, Arial, sans-serif; margin: 2rem; color: #222; background: #fafafa; }}
h1 {{ font-size: 1.4rem; }}
h2 {{ font-size: 1.1rem; margin-top: 1.5rem; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 0.5rem; }}
td, th {{ border: 1px solid #ddd; padding: 6px 10px; text-align: left; font-size: 0.92rem; }}
th {{ background: #eee; }}
.warn {{ color: #a15c00; }}
.err {{ color: #b00020; }}
.ok {{ color: #1a7f37; }}
.steps li {{ margin-bottom: 4px; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; background: #e6f4ea; color: #1a7f37; font-size: 0.85rem; }}
</style>
</head>
<body>
<h1>Optimierungsbericht: {title}</h1>
<p><span class="badge">{status}</span></p>

<h2>Übersicht</h2>
<table>
<tr><th>Quelldatei</th><td>{source_path}</td></tr>
<tr><th>Zieldatei</th><td>{output_path}</td></tr>
<tr><th>Bildgröße</th><td>{width} x {height} px</td></tr>
<tr><th>Dateiformat</th><td>{file_format}</td></tr>
<tr><th>Erkannter Bildtyp</th><td>{detected_type}</td></tr>
<tr><th>Quellprofil</th><td>{source_profile}</td></tr>
<tr><th>Zielprofil</th><td>{target_profile}</td></tr>
<tr><th>Rendering Intent</th><td>{rendering_intent}</td></tr>
<tr><th>Verarbeitungsdauer</th><td>{duration:.2f} s</td></tr>
</table>

<h2>Was wurde automatisch geändert?</h2>
<ul class="steps">
{steps_html}
</ul>

<h2>Transparenz</h2>
<table>
<tr><th>Transparente Pixel</th><td>{transparent}</td></tr>
<tr><th>Halbtransparente Pixel</th><td>{semi_transparent}</td></tr>
<tr><th>Entfernte Pixel</th><td>{removed}</td></tr>
<tr><th>Verstärkte Pixel</th><td>{strengthened}</td></tr>
<tr><th>Korrigierte Farbsaum-Pixel</th><td>{halo_corrected}</td></tr>
<tr><th>Entfernte Pixelinseln</th><td>{islands}</td></tr>
<tr><th>Geschlossene Löcher</th><td>{holes}</td></tr>
</table>

<h2>Farbe</h2>
<table>
<tr><th>Außerhalb Farbraum (vorher)</th><td>{gamut_before:.1f}%</td></tr>
<tr><th>Außerhalb Farbraum (nachher)</th><td>{gamut_after:.1f}%</td></tr>
<tr><th>Durchschnittliche Farbabweichung</th><td>{mean_de:.2f}</td></tr>
<tr><th>Maximale Farbabweichung</th><td>{max_de:.2f}</td></tr>
</table>

<h2>Hinweise</h2>
{warnings_html}
{errors_html}

{pdf_section_html}

<p style="margin-top:2rem;font-size:0.85rem;color:#666;">
Diese Bildschirmvorschau ist keine Garantie für das endgültige Druckergebnis.
Das Ergebnis hängt zusätzlich von Drucker, Tinte, Folie/Pulver, RIP, Textil und Pressparametern ab.
</p>
</body>
</html>
"""


def _steps_to_html(report: ImageProcessingReport) -> str:
    if not report.applied_steps:
        return "<li>Keine Änderungen notwendig.</li>"
    return "\n".join(f"<li>{s.description}</li>" for s in report.applied_steps)


def _warnings_to_html(items: list[str], css_class: str, empty_text: str) -> str:
    if not items:
        return f'<p class="ok">{empty_text}</p>'
    lis = "\n".join(f'<li class="{css_class}">{w}</li>' for w in items)
    return f"<ul>{lis}</ul>"


def _pdf_section_to_html(report: ImageProcessingReport) -> str:
    if report.output_format != "pdf_cmyk":
        return ""
    page_mm = report.pdf_page_size_mm
    dpi = report.pdf_effective_dpi
    validated_class = "ok" if report.pdf_validated else "err"
    validated_text = "Ja" if report.pdf_validated else "Nein"
    dpi_class = "" if report.pdf_meets_target_dpi else "warn"
    validation_errors_html = (
        _warnings_to_html(report.pdf_validation_errors, "err", "") if report.pdf_validation_errors else ""
    )
    return f"""
<h2>PDF-Export (Druckdienstleister-Preset)</h2>
<table>
<tr><th>Ausgabeformat</th><td>{report.output_format}</td></tr>
<tr><th>Seiten</th><td>{report.pdf_page_count}</td></tr>
<tr><th>Seitengröße</th><td>{f"{page_mm[0]:.1f} x {page_mm[1]:.1f} mm" if page_mm else "-"}</td></tr>
<tr><th>Effektive dpi</th><td class="{dpi_class}">{f"{dpi[0]:.0f} x {dpi[1]:.0f}" if dpi else "-"}</td></tr>
<tr><th>Zielauflösung erreicht (≥300 dpi)</th><td>{"Ja" if report.pdf_meets_target_dpi else "Nein"}</td></tr>
<tr><th>ICC-Profil als OutputIntent eingebettet</th><td>{"Ja" if report.pdf_icc_output_intent_embedded else "Nein"}</td></tr>
<tr><th>Transparenz-Softmask vorhanden</th><td>{"Ja" if report.pdf_has_transparency_smask else "Nein"}</td></tr>
<tr><th>Zusätzliche Sättigungsreduktion</th><td>{"Ja" if report.additional_saturation_reduction_applied else "Nein"}</td></tr>
<tr><th>Zusätzliche Gamut-Korrektur</th><td>{"Ja" if report.additional_gamut_correction_applied else "Nein"}</td></tr>
<tr><th>Spiegelung</th><td>{"Ja" if report.mirrored else "Nein"}</td></tr>
<tr><th>Schwarzpunktkompensation</th><td>{"aktiviert" if report.black_point_compensation else "deaktiviert"}</td></tr>
<tr><th>PDF-Validierung erfolgreich</th><td class="{validated_class}">{validated_text}</td></tr>
</table>
{validation_errors_html}
"""


def write_html_report(report: ImageProcessingReport, output_path: Path) -> None:
    status = "Erfolgreich" if report.success else "Fehlgeschlagen"
    html = _HTML_TEMPLATE.format(
        title=report.source_path.name if report.source_path else "?",
        status=status,
        source_path=report.source_path,
        output_path=report.output_path or "-",
        width=report.width,
        height=report.height,
        file_format=report.file_format,
        detected_type=report.detected_type.value,
        source_profile=report.source_profile,
        target_profile=report.target_profile or "-",
        rendering_intent=report.rendering_intent.value,
        duration=report.processing_duration_seconds,
        steps_html=_steps_to_html(report),
        transparent=report.transparent_pixel_count,
        semi_transparent=report.semi_transparent_pixel_count,
        removed=report.removed_pixel_count,
        strengthened=report.strengthened_pixel_count,
        halo_corrected=report.halo_corrected_pixel_count,
        islands=report.removed_islands,
        holes=report.closed_holes,
        gamut_before=report.out_of_gamut_before,
        gamut_after=report.out_of_gamut_after,
        mean_de=report.mean_delta_e,
        max_de=report.max_delta_e,
        warnings_html=_warnings_to_html(report.warnings, "warn", "Keine Warnungen."),
        errors_html=_warnings_to_html(report.errors, "err", ""),
        pdf_section_html=_pdf_section_to_html(report),
    )
    ensure_dir(output_path.parent)
    retry_on_oserror(lambda: output_path.write_text(html, encoding="utf-8"), description=f"HTML-Bericht {output_path.name}")


def _write_json(report: ImageProcessingReport, output_path: Path) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)


def write_json_report(report: ImageProcessingReport, output_path: Path) -> None:
    ensure_dir(output_path.parent)
    retry_on_oserror(lambda: _write_json(report, output_path), description=f"JSON-Bericht {output_path.name}")
