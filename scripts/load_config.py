"""Carrega a configuracao a partir dos arquivos separados em scripts/config/."""

import json
import os
from pathlib import Path
from typing import Any


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
