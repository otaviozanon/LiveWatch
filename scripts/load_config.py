"""Carrega a configuracao a partir dos arquivos separados em scripts/config/."""

import json
import re
import unicodedata
from pathlib import Path
from typing import Any


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _normalize(text: str) -> str:
    t = _strip_accents(text)
    t = t.replace("\u0091", "'").replace("\u0092", "'")
    return t.strip().lower()


def load_config() -> dict[str, Any]:
    config_dir = Path(__file__).parent / "config"

    with open(config_dir / "epg.json", encoding="utf-8") as f:
        epg = json.load(f)

    profiles: dict[str, Any] = {}
    profiles_dir = config_dir / "profiles"
    for path in sorted(profiles_dir.glob("*.json")):
        name = path.stem
        with open(path, encoding="utf-8") as f:
            profiles[name] = json.load(f)

    return {"epg": epg, "profiles": profiles}


def _strip_variants(name: str) -> str:
    name = re.sub(r"^\d+[\s|\-\.]+", "", name)
    name = re.sub(r"\s*\[H265\s*\]", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*\[4K\s*\]", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*\[\d+\]", "", name)
    name = re.sub(r"\s+(HD|FHD|SD|H265|4K|HEVC)(\s|$)", " ", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+$", "", name)
    return name.strip()


def load_category_name_remap() -> dict[str, list[str]]:
    project_dir = Path(__file__).parent.parent
    cat_dir = project_dir / "playlists" / "categories"

    remap: dict[str, list[str]] = {}
    for path in sorted(cat_dir.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        category = data.get("name", "")
        if not category:
            continue
        base_names = set()
        for ch in data.get("channels", []):
            base = _strip_variants(_normalize(ch))
            if base:
                base_names.add(base)
        if base_names:
            remap[category] = sorted(base_names)

    return remap
