"""Validierung von ICC-Zielprofilen für den CMYK-Druckexport (DTF-King).

Prüft ein vom Benutzer gewähltes .icc/.icm-Profil, BEVOR es als Zielprofil
verwendet wird. Bei einem ungeeigneten Profil wird der Export nicht
stillschweigend mit einem anderen Profil fortgesetzt - der Aufrufer erhält
stattdessen ein Ergebnis mit `ok=False` und einer verständlichen Fehlermeldung.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import ImageCms

from src.core.color.icc_manager import profile_color_space

_ICC_EXTENSIONS = {".icc", ".icm"}

# ICC-Geräteklassen-Signaturen (Header "Profile/Device Class") -> lesbare Bezeichnung.
_DEVICE_CLASS_LABELS = {
    "scnr": "Scanner-Eingabeprofil",
    "mntr": "Monitor-/Anzeigeprofil",
    "prtr": "Druckausgabeprofil",
    "link": "DeviceLink-Profil",
    "abst": "Abstract-Profil",
    "spac": "Farbraum-Konvertierungsprofil",
    "nmcl": "Named-Color-Profil",
}


@dataclass
class ProfileValidationResult:
    ok: bool
    path: Path
    error: str | None = None
    description: str | None = None
    color_space: str | None = None
    device_class: str | None = None
    device_class_label: str | None = None


def validate_cmyk_output_profile(path: Path) -> ProfileValidationResult:
    """Validiert eine ICC-Profildatei als CMYK-Ausgabeprofil.

    Prüft der Reihe nach: Existenz, Dateiendung, Ladbarkeit (defekt/beschädigt?),
    Farbraum (muss CMYK sein) und liest Beschreibung/Profilklasse aus, soweit
    verfügbar. Gibt bei jedem Fehlschlag sofort ein `ok=False`-Ergebnis mit
    präziser Fehlermeldung zurück - der Aufrufer darf daraufhin NICHT
    automatisch ein anderes, ähnlich benanntes Profil verwenden.
    """
    path = Path(path)

    if not path.exists():
        return ProfileValidationResult(ok=False, path=path, error=f"Die Datei wurde nicht gefunden: {path}")

    if path.suffix.lower() not in _ICC_EXTENSIONS:
        return ProfileValidationResult(
            ok=False, path=path, error=f"Keine gültige ICC-Profildatei (Endung .icc/.icm erwartet): {path.name}"
        )

    try:
        profile = ImageCms.ImageCmsProfile(str(path))
        # Erzwingt das Parsen des Profilheaders - deckt beschädigte Dateien auf.
        description = ImageCms.getProfileDescription(profile).strip() or path.stem
    except Exception as exc:
        return ProfileValidationResult(
            ok=False, path=path, error=f"Das Profil ist beschädigt oder kein gültiges ICC-Profil: {path.name} ({exc})"
        )

    color_space = profile_color_space(profile)
    if color_space != "CMYK":
        return ProfileValidationResult(
            ok=False,
            path=path,
            description=description,
            color_space=color_space,
            error=(
                f"Das Profil '{description}' hat den Farbraum {color_space}, nicht CMYK. "
                "Es kann nicht als CMYK-Ausgabeprofil für den Druck verwendet werden."
            ),
        )

    device_class = None
    device_class_label = None
    try:
        raw_class = getattr(profile.profile, "device_class", None)
        if raw_class:
            device_class = str(raw_class).strip().lower()
            device_class_label = _DEVICE_CLASS_LABELS.get(device_class, f"Unbekannte Geräteklasse ({device_class})")
    except Exception:
        pass

    if device_class is not None and device_class not in ("prtr", "spac", "link"):
        return ProfileValidationResult(
            ok=False,
            path=path,
            description=description,
            color_space=color_space,
            device_class=device_class,
            device_class_label=device_class_label,
            error=(
                f"Das Profil '{description}' ist kein Druckausgabeprofil (Geräteklasse: "
                f"{device_class_label}). Bitte ein echtes CMYK-Druckausgabeprofil auswählen."
            ),
        )

    return ProfileValidationResult(
        ok=True,
        path=path,
        description=description,
        color_space=color_space,
        device_class=device_class,
        device_class_label=device_class_label,
    )


def find_profile_by_description_fragment(candidates: list[Path], fragment: str) -> Path | None:
    """Sucht unter bereits importierten/mitgelieferten Profilen eines, dessen
    Beschreibung `fragment` enthält (case-insensitive). Liefert None, wenn
    keines oder mehrere unterschiedliche Kandidaten gefunden werden - es wird
    NIEMALS automatisch ein ähnlich benanntes Profil geraten.
    """
    fragment_lower = fragment.lower()
    matches: list[Path] = []
    for candidate in candidates:
        result = validate_cmyk_output_profile(candidate)
        if result.ok and result.description and fragment_lower in result.description.lower():
            matches.append(candidate)
    if len(matches) == 1:
        return matches[0]
    return None
