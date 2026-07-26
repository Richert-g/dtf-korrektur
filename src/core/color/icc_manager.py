"""ICC-Profilverwaltung: lokal, robust gegen defekte Profile (Prompt Abschnitt 9)."""
from __future__ import annotations

import io
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import ImageCms

from src.config.paths import get_user_profiles_dir, get_profiles_dir

logger = logging.getLogger(__name__)

_ICC_EXTENSIONS = {".icc", ".icm"}


class ICCProfileError(Exception):
    """Wird bei defekten oder inkompatiblen ICC-Profilen ausgelöst."""


@dataclass
class ProfileInfo:
    name: str
    path: Path


_srgb_profile_cache: ImageCms.ImageCmsProfile | None = None
_srgb_bytes_cache: bytes | None = None


def get_srgb_profile() -> ImageCms.ImageCmsProfile:
    global _srgb_profile_cache
    if _srgb_profile_cache is None:
        _srgb_profile_cache = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
    return _srgb_profile_cache


def get_srgb_icc_bytes() -> bytes:
    global _srgb_bytes_cache
    if _srgb_bytes_cache is None:
        _srgb_bytes_cache = get_srgb_profile().tobytes()
    return _srgb_bytes_cache


def load_icc_profile_from_bytes(data: bytes) -> ImageCms.ImageCmsProfile | None:
    try:
        profile = ImageCms.ImageCmsProfile(io.BytesIO(data))
        # Zugriff erzwingen, um defekte Profile frühzeitig zu erkennen
        ImageCms.getProfileDescription(profile)
        return profile
    except Exception:
        logger.warning("ICC-Profil aus Bilddaten ist defekt oder inkompatibel.", exc_info=True)
        return None


def load_icc_profile(path: Path) -> ImageCms.ImageCmsProfile | None:
    try:
        profile = ImageCms.ImageCmsProfile(str(path))
        ImageCms.getProfileDescription(profile)
        return profile
    except Exception:
        logger.warning("ICC-Profil konnte nicht geladen werden: %s", path, exc_info=True)
        return None


def profile_description(profile: ImageCms.ImageCmsProfile) -> str:
    try:
        return ImageCms.getProfileDescription(profile).strip() or "Unbenanntes Profil"
    except Exception:
        return "Unbenanntes Profil"


def profile_color_space(profile: ImageCms.ImageCmsProfile) -> str:
    try:
        return (profile.profile.xcolor_space or "RGB").strip().upper()
    except Exception:
        return "RGB"


def list_available_profiles() -> list[ProfileInfo]:
    """Listet alle verfügbaren ICC-Profile auf (mitgelieferte + vom Benutzer importierte).

    Durchsucht Unterordner rekursiv, damit z. B. eine CMYK/RGB-Ordnerstruktur bei den
    mitgelieferten Profilen (`resources/profiles`) erkannt wird. Der Ordnername wird,
    falls vorhanden, der Anzeigebezeichnung als Kategorie vorangestellt.
    """
    profiles: list[ProfileInfo] = []
    seen_paths: set[Path] = set()
    for base_dir in {get_profiles_dir(), get_user_profiles_dir()}:
        if not base_dir.exists():
            continue
        files = [f for f in base_dir.rglob("*") if f.is_file() and f.suffix.lower() in _ICC_EXTENSIONS]
        for file in sorted(files, key=lambda f: (str(f.relative_to(base_dir).parent), f.name)):
            if file in seen_paths:
                continue
            profile = load_icc_profile(file)
            display_name = profile_description(profile) if profile else file.stem
            category = file.relative_to(base_dir).parent
            if str(category) not in (".", ""):
                display_name = f"{category}: {display_name}"
            profiles.append(ProfileInfo(name=display_name, path=file))
            seen_paths.add(file)
    return profiles


def import_profile(source_path: Path, display_name: str | None = None) -> ProfileInfo:
    """Kopiert ein vom Benutzer gewähltes ICC-Profil lokal in den Profilordner.

    Validiert das Profil vorher, damit keine defekten Dateien importiert werden
    (Prompt Abschnitt 9: 'Defekte oder inkompatible Profile dürfen die Anwendung
    nicht zum Absturz bringen').
    """
    source_path = Path(source_path)
    if source_path.suffix.lower() not in _ICC_EXTENSIONS:
        raise ICCProfileError(f"Keine gültige ICC-Profildatei: {source_path.name}")

    profile = load_icc_profile(source_path)
    if profile is None:
        raise ICCProfileError(f"Das Profil ist defekt oder inkompatibel: {source_path.name}")

    target_dir = get_user_profiles_dir()
    target_name = f"{display_name or source_path.stem}{source_path.suffix.lower()}"
    target_path = target_dir / target_name
    counter = 1
    while target_path.exists():
        target_path = target_dir / f"{display_name or source_path.stem}_{counter}{source_path.suffix.lower()}"
        counter += 1

    shutil.copy2(source_path, target_path)
    return ProfileInfo(name=display_name or profile_description(profile), path=target_path)
