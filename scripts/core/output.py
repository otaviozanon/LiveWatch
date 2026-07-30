"""Category constants, normalization, and playlist generation."""

from __future__ import annotations

import os
import re
import unicodedata
from typing import Callable


# ── Category constants ─────────────────────────────────────────────────────

GT_REMAP: dict[str, str] = {
    "85 BRAZILIAN CHANNELS": "VARIEDADES",
    "INFANTIL": "INFANTIS",
    "FILMES & SERIES": "FILMES E SERIES",
    "REALITY SHOW": "REALITIES",
    "UFC FIGHT PASS": "UFC",
    "UFC FIGHT": "UFC",
    "MUSICA": "MUSICAS",
    "USA": "ESTADOS UNIDOS",
    "ESTADOS UNIDOS US": "ESTADOS UNIDOS",
    "GERAL": "DIVERSOS",
    "GLOBO SUL": "GLOBO",
    "FILMES": "FILMES E SERIES",
    "SERIES": "FILMES E SERIES",
    "COMEDIA": "ENTRETENIMENTO",
    "ANIMACAO": "INFANTIS",
    "RECORDTV": "RECORD",
    "AGENDA ESPORTIVA": "ESPORTES DO DIA",
    "MAX": "FILMES E SERIES",
    "TNT": "FILMES E SERIES",
    "HBO": "FILMES E SERIES",
    "ESPN": "ESPORTES",
    "SPORTV": "ESPORTES",
    "NBA LEAGUE PASS": "NBA",
    "BRASILEIRAO": "PAY PER VIEW",
    "PREMIERE": "PAY PER VIEW",
    "NBA": "NBA",
    "ESTADUAIS": "PAY PER VIEW",
    "FUTSAL": "PAY PER VIEW",
    "TELECINE": "FILMES E SERIES",
    "24H VARIADOS": "24H",
    "ESPORTES ESTADUAIS": "PAY PER VIEW",
    "ESPORTES PPV": "PAY PER VIEW",
    "VARIEDADES": "ENTRETENIMENTO",
}

CATEGORY_ORDER: tuple[str, ...] = (
    "NOVOS",
    "24H", "24H INFANTIL", "REALITIES", "4K",
    "GLOBO", "SBT", "BAND", "RECORD", "ABERTOS",
    "FILMES E SERIES", "DOCUMENTARIOS", "ESPORTES",
    "ENTRETENIMENTO", "PAY PER VIEW", "NOTICIAS",
    "MUSICAS", "DORMIR E RELAXAR", "UFC", "NBA",
    "FORMULA 1", "DAZN", "DUAL AUDIO", "PLUTO TV",
    "INFANTIS", "EDUCACAO", "AR LIVRE", "RELIGIOSOS",
    "ESTADOS UNIDOS", "ESPORTES DO DIA",
)

CATEGORY_TRANSLATION: dict[str, str] = {
    "general": "GERAL",
    "news": "NOTICIAS",
    "entertainment": "ENTRETENIMENTO",
    "sports": "ESPORTES",
    "religious": "RELIGIOSOS",
    "education": "EDUCACAO",
    "legislative": "LEGISLATIVO",
    "kids": "INFANTIS",
    "outdoor": "AR LIVRE",
    "movies": "FILMES",
    "animation": "ANIMACAO",
    "culture": "CULTURA",
    "comedy": "COMEDIA",
    "public": "PUBLICO",
    "series": "SERIES",
    "travel": "VIAGEM",
    "shop": "COMPRAS",
    "classic": "CLASSICOS",
    "music": "MUSICA",
    "family": "FAMILIA",
}


# ── Normalization ──────────────────────────────────────────────────────────

def _strip_accents(text: str) -> str:
    """Remove diacritical marks (e.g. 'São' → 'Sao')."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_group_title(group_title: str, prefix: str) -> str:
    """Clean up a raw group title and prepend the profile prefix."""
    gt = group_title.strip()
    gt = re.sub(r"^CANAIS\s*\|\s*", "", gt, flags=re.IGNORECASE)
    gt = re.sub(r"^CANAL\s+\W+(?=\s*\w)", "", gt, flags=re.IGNORECASE)
    gt = gt.strip().upper()
    gt = _strip_accents(gt)
    gt = GT_REMAP.get(gt, gt)
    if gt not in CATEGORY_ORDER:
        gt = "NOVOS"
    return f"{prefix} | {gt}"


def category_sort_key(entry: tuple[str, str, str]) -> tuple[int, str]:
    """Sort key: category order first, then accent-insensitive alphabetical."""
    group_title, name, _ = entry
    cat = re.sub(r"^[A-Z]{2}\s*\|\s*", "", group_title)
    try:
        cat_order = CATEGORY_ORDER.index(cat)
    except ValueError:
        cat_order = len(CATEGORY_ORDER)
    name_sort = unicodedata.normalize("NFKD", name.lower())
    name_sort = "".join(c for c in name_sort if not unicodedata.combining(c))
    return (cat_order, name_sort)


# ── Playlist generation ────────────────────────────────────────────────────

def generate_playlist(
    entries: list[tuple[str, str, str]],
    base_name: str,
    output_dir: str,
    tvg_mapper: Callable[[str], str | None] | None = None,
    tvg_url: str | list[str] | None = None,
) -> None:
    """Write a sorted entry list to M3U and M3U8 playlist files."""
    m3u_dir = os.path.join(output_dir, "playlists", "m3u")
    m3u8_dir = os.path.join(output_dir, "playlists", "m3u8")
    os.makedirs(m3u_dir, exist_ok=True)
    os.makedirs(m3u8_dir, exist_ok=True)

    if isinstance(tvg_url, str):
        tvg_urls = [tvg_url]
    elif tvg_url:
        tvg_urls = list(tvg_url)
    else:
        tvg_urls: list[str] = []

    for ext, folder in [("m3u", m3u_dir), ("m3u8", m3u8_dir)]:
        output_path = os.path.join(folder, f"{base_name}.{ext}")
        with open(output_path, "w", encoding="utf-8") as f:
            header = "#EXTM3U"
            for url in tvg_urls:
                header += f' x-tvg-url="{url}"'
            f.write(header + "\n")
            for group_title, name, url in entries:
                extras = f'group-title="{group_title}"'
                if tvg_mapper:
                    tvg_id = tvg_mapper(name)
                    if tvg_id:
                        extras += f' tvg-id="{tvg_id}" tvg-name="{name}"'
                f.write(f"#EXTINF:-1 {extras},{name}\n{url}\n")
        print(f"[LiveWatch] [+] {base_name}.{ext} ({len(entries)} canais)")
