"""
LiveWatch playlist generator.

Fetches channel lists from GitHub-hosted M3U sources and IPTV APIs,
filters, remaps categories, enriches with EPG metadata, and outputs
clean M3U/M3U8 playlists organized by profile.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
from typing import Any, Callable

import requests

try:
    from . import epg
except ImportError:
    import epg


# ── M3U parsing ───────────────────────────────────────────────────────────

def parse_m3u(text: str) -> list[tuple[str, str, str]]:
    """Parse raw M3U/M3U8 text into ``[(group_title, name, url), ...]``."""
    entries: list[tuple[str, str, str]] = []
    lines = text.strip().splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF"):
            attr_match = re.search(r'group-title="([^"]*)"', line, re.IGNORECASE)
            group_title = attr_match.group(1) if attr_match else ""
            name_match = re.search(r",\s*(.+)$", line)
            name = name_match.group(1).strip() if name_match else ""
            name = re.sub(r"[¹²³]+", "", name)
            i += 1
            if i < len(lines) and lines[i].strip() and not lines[i].strip().startswith("#"):
                url = lines[i].strip()
                entries.append((group_title, name, url))
        i += 1
    return entries


# ── Data fetching ─────────────────────────────────────────────────────────

def fetch_playlist(url: str) -> str:
    """Download an M3U playlist from *url* and return its raw text."""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def fetch_all(urls: list[str]) -> dict[str, list[tuple[str, str, str]]]:
    """Download and parse multiple M3U playlist URLs."""
    results: dict[str, list[tuple[str, str, str]]] = {}
    for i, url in enumerate(urls, 1):
        try:
            text = fetch_playlist(url)
            entries = parse_m3u(text)
            results[url] = entries
            print(f"[LiveWatch] [+] {url.rsplit('/', 1)[-1]} ({i}/{len(urls)})")
            print(f"[LiveWatch]    {len(entries)} entradas ({len(text.splitlines())} linhas)")
        except Exception as e:
            print(f"[LiveWatch] [!] {e}")
            results[url] = []
    return results


def fetch_json(url: str) -> Any:
    """Download and parse a JSON endpoint."""
    print(f"[LiveWatch] [+] {url.rsplit('/', 1)[-1]}")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    print(f"[LiveWatch]    {len(data)} registros")
    return data


def discover_github_sources(repo: str, pattern: str) -> list[str]:
    """List files in a GitHub repo matching *pattern* and return download URLs."""
    api_url = f"https://api.github.com/repos/{repo}/contents/"
    print(f"[LiveWatch] [+] Buscando {repo}")
    resp = requests.get(api_url, timeout=30)
    resp.raise_for_status()
    files = resp.json()
    regex = re.compile(pattern)
    matched = sorted(
        [f["download_url"] for f in files
         if f["type"] == "file" and regex.search(f["name"])],
        key=lambda u: u,
    )
    print(f"[LiveWatch]    {len(matched)} listas encontradas")
    return matched


# ── Filtering & remapping ─────────────────────────────────────────────────

def filter_by_group(
    entries: list[tuple[str, str, str]], prefix: str
) -> list[tuple[str, str, str]]:
    """Keep only entries whose *group_title* starts with *prefix*."""
    return [(g, n, u) for g, n, u in entries if g.lower().startswith(prefix.lower())]


def _strip_accents(text: str) -> str:
    """Remove diacritical marks (e.g. 'São' → 'Sao')."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _normalize(text: str) -> str:
    """Full normalization: accents stripped, smart quotes fixed, lowercase."""
    t = _strip_accents(text)
    t = t.replace("\u0091", "'").replace("\u0092", "'")
    t = t.replace("\u0093", '"').replace("\u0094", '"')
    t = t.replace("\u2018", "'").replace("\u2019", "'")
    t = t.replace("\u201c", '"').replace("\u201d", '"')
    return t.lower()


def filter_by_group_exclude(
    entries: list[tuple[str, str, str]], exclude_keywords: list[str]
) -> list[tuple[str, str, str]]:
    """Remove entries whose *group_title* contains any of the *exclude_keywords*."""
    if not exclude_keywords:
        return entries
    result: list[tuple[str, str, str]] = []
    removed = 0
    for group_title, name, url in entries:
        gt = _normalize(group_title)
        exclude = any(
            _normalize(kw) in gt for kw in exclude_keywords
        )
        if exclude:
            removed += 1
        else:
            result.append((group_title, name, url))
    if removed:
        print(f"[LiveWatch] [-] {removed} grupos excluidos")
    return result


def filter_by_url(
    entries: list[tuple[str, str, str]], url_exclude_patterns: list[str]
) -> list[tuple[str, str, str]]:
    """Remove entries whose URL contains any of the *url_exclude_patterns*."""
    if not url_exclude_patterns:
        return entries
    result: list[tuple[str, str, str]] = []
    removed = 0
    for group_title, name, url in entries:
        exclude = any(pat.lower() in url.lower() for pat in url_exclude_patterns)
        if exclude:
            removed += 1
        else:
            result.append((group_title, name, url))
    if removed:
        print(f"[LiveWatch] [-] {removed} URLs bloqueadas")
    return result


def filter_excluded(
    entries: list[tuple[str, str, str]], exclude_keywords: list[str]
) -> list[tuple[str, str, str]]:
    """Remove entries whose *name* contains any of the *exclude_keywords*."""
    if not exclude_keywords:
        return entries
    result: list[tuple[str, str, str]] = []
    removed = 0
    for group_title, name, url in entries:
        name_norm = _normalize(name)
        exclude = any(
            _normalize(kw) in name_norm for kw in exclude_keywords
        )
        if exclude:
            removed += 1
        else:
            result.append((group_title, name, url))
    if removed:
        print(f"[LiveWatch] [-] {removed} canais indesejados")
    return result


def remap_by_name(
    entries: list[tuple[str, str, str]],
    name_remap: dict[str, list[str]],
    remap_from_groups: list[str] | None = None,
) -> list[tuple[str, str, str]]:
    """Reassign entries to target categories based on channel name patterns."""
    if not name_remap:
        return entries
    result: list[tuple[str, str, str]] = []
    remapped = 0
    for group_title, name, url in entries:
        new_group = group_title
        if remap_from_groups is None or any(
            g.lower() in group_title.lower() for g in remap_from_groups
        ):
            for target_group, patterns in name_remap.items():
                for pat in patterns:
                    if _normalize(pat) in _normalize(name):
                        new_group = target_group
                        remapped += 1
                        break
                if new_group != group_title:
                    break
        result.append((new_group, name, url))
    if remapped:
        print(f"[LiveWatch] [*] {remapped} canais recategorizados")
    return result


def filter_by_group_keep(
    entries: list[tuple[str, str, str]], group_rules: dict[str, list[str]]
) -> list[tuple[str, str, str]]:
    """
    Within groups matching *group_rules* keys, keep only entries whose name
    matches one of the corresponding patterns.  All other groups pass through.
    """
    if not group_rules:
        return entries
    result: list[tuple[str, str, str]] = []
    removed = 0
    for group_title, name, url in entries:
        keep = True
        for group_key, name_patterns in group_rules.items():
            if group_key.lower() in group_title.lower():
                keep = any(pat.lower() in name.lower() for pat in name_patterns)
                break
        if keep:
            result.append((group_title, name, url))
        else:
            removed += 1
    if removed:
        print(f"[LiveWatch] [-] {removed} canais filtrados (grupo)")
    return result


def dedup_by_url(
    entries: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    """Remove duplicate entries (same URL), keeping first occurrence."""
    seen: set[str] = set()
    result: list[tuple[str, str, str]] = []
    removed = 0
    for entry in entries:
        url = entry[2]
        if url not in seen:
            seen.add(url)
            result.append(entry)
        else:
            removed += 1
    if removed:
        print(f"[LiveWatch] [-] {removed} duplicatas URL")
    return result


def rename_duplicates(
    entries: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    """
    Append ``[2]``, ``[3]``, ... suffixes when the same channel name appears
    with multiple different URLs.
    """
    name_counts: dict[str, int] = {}
    renamed = 0
    result: list[tuple[str, str, str]] = []
    for group_title, name, url in entries:
        key = name.lower()
        if key not in name_counts:
            name_counts[key] = 1
            result.append((group_title, name, url))
        else:
            name_counts[key] += 1
            new_name = f"{name} [{name_counts[key]}]"
            result.append((group_title, new_name, url))
            renamed += 1
    if renamed:
        print(f"[LiveWatch] [*] {renamed} conflitos renomeados")
    return result


# ── Channel name cleanup ──────────────────────────────────────────────────

def cleanup_channel_names(
    entries: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    """Normalize channel names for consistency and dedup."""
    result: list[tuple[str, str, str]] = []
    for group_title, name, url in entries:
        name = name.strip().upper()
        name = re.sub(r"\b4K\b", "H265", name)
        if "H265" in name and "FHD" in name:
            name = re.sub(r"\bFHD\b", "", name)
        name = re.sub(r"(\bH265\b\s*)+", "H265 ", name)
        name = re.sub(r"\s+", " ", name).strip()
        result.append((group_title, name, url))
    changed = sum(1 for (_, a, _), (_, b, _) in zip(entries, result) if a != b)
    if changed:
        print(f"[LiveWatch] [*] {changed} nomes normalizados")
    return result


# ── Category normalization ────────────────────────────────────────────────

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

# Translation table used by process_iptv_api
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
    """
    Sort key: category order first, then accent-insensitive alphabetical.
    """
    group_title, name, _ = entry
    cat = re.sub(r"^[A-Z]{2}\s*\|\s*", "", group_title)
    try:
        cat_order = CATEGORY_ORDER.index(cat)
    except ValueError:
        cat_order = len(CATEGORY_ORDER)
    name_sort = unicodedata.normalize("NFKD", name.lower())
    name_sort = "".join(c for c in name_sort if not unicodedata.combining(c))
    return (cat_order, name_sort)


def process_iptv_api(
    channels_url: str, streams_url: str, country: str
) -> list[tuple[str, str, str]]:
    """Fetch channel + stream data from an IPTV API and build entry list."""
    channels_data = fetch_json(channels_url)

    br_channels = [c for c in channels_data if c.get("country") == country]
    print(f"[LiveWatch]    {len(br_channels)} canais BR")

    channel_map: dict[str, dict] = {}
    for c in br_channels:
        if not c.get("is_nsfw", False) and "xxx" not in [
            x.lower() for x in c.get("categories", [])
        ]:
            channel_map[c["id"]] = c

    print(f"[LiveWatch]    {len(channel_map)} canais validos")

    streams_data = fetch_json(streams_url)

    entries: list[tuple[str, str, str]] = []
    for s in streams_data:
        ch_id = s.get("channel")
        if not ch_id or ch_id not in channel_map:
            continue

        ch = channel_map[ch_id]
        url = s.get("url")
        if not url:
            continue

        title = s.get("title") or ch.get("name", "Unnamed")
        title = re.sub(r"[¹²³]+", "", title)
        cats = ch.get("categories", ["general"])
        category = cats[0] if cats else "general"
        group_title = CATEGORY_TRANSLATION.get(category.lower(), category.upper())

        entries.append((group_title, title, url))

    print(f"[LiveWatch]    {len(entries)} streams")
    return entries


def fetch_profile_entries(p: dict[str, Any]) -> list[tuple[str, str, str]]:
    """
    Fetch, filter, and remap entries for a single profile configuration.

    Pipeline:
    1. Fetch from GitHub M3U or IPTV API
    2. Exclude by URL pattern
    3. Exclude by channel name
    4. Remap categories by channel name
    5. Exclude by group title
    6. Keep/remove within specific groups
    """
    if p.get("type") == "iptv_api":
        entries = process_iptv_api(
            p["sources"][0], p["sources"][1], p.get("country", "BR")
        )
    else:
        github_repo: str | None = p.get("github_repo")
        sources: list[str] = p.get("sources", [])
        if github_repo:
            sources = discover_github_sources(github_repo, p.get("source_pattern", ""))
        all_results = fetch_all(sources)
        entries = []
        for e_list in all_results.values():
            if p.get("filter_group"):
                e_list = filter_by_group(e_list, p["filter_group"])
            entries.extend(e_list)

    entries = filter_by_url(entries, p.get("url_exclude", []))
    entries = filter_excluded(entries, p.get("name_exclude", []))
    entries = remap_by_name(entries, p.get("name_remap", {}), p.get("remap_from"))
    entries = filter_by_group_exclude(entries, p.get("group_exclude", []))
    entries = filter_by_group_keep(entries, p.get("group_keep", {}))
    return entries


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

    # Normalize tvg_url to list
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
                f.write(f'#EXTINF:-1 {extras},{name}\n{url}\n')
        print(f"[LiveWatch] [+] {base_name}.{ext} ({len(entries)} canais)")


def main() -> None:
    """Entry point.  Reads profile config and generates playlists."""
    parser = argparse.ArgumentParser(
        description="LiveWatch playlist generator"
    )
    parser.add_argument(
        "--profile", default="brasil", help="Which playlist profile to use"
    )
    args = parser.parse_args()
    profile: str = args.profile

    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")

    with open(config_path, "r", encoding="utf-8") as f:
        config: dict[str, Any] = json.load(f)

    if profile not in config.get("profiles", {}):
        print(f"[LiveWatch] [!] Perfil '{profile}' nao encontrado")
        return

    p: dict[str, Any] = config["profiles"][profile]
    base_name: str = p["output"].replace(".m3u8", "").replace(".m3u", "")
    output_dir: str = os.path.dirname(script_dir)

    # --- EPG integration ---
    epg_config: dict[str, Any] = config.get("epg", {})
    tvg_mapper = None
    tvg_url: list[str] | None = None
    if epg_config.get("enabled", False):
        try:
            epg_countries: list[str] = epg_config.get("countries", ["BR"])
            epgshare_urls, globetv_urls, extra_urls = (
                epg.get_epg_sources_for_countries(epg_countries)
            )
            print(f"[LiveWatch] [i] EPG: {len(epgshare_urls)}+{len(globetv_urls)} fontes")
            tvg_mapper = epg.build_channel_mapper(
                sources=epgshare_urls,
                globetv_sources=globetv_urls,
            )
            primary_url: str = epg_config.get("tvg_url", "")
            tvg_url = [
                u for u in [primary_url] + epgshare_urls + globetv_urls + extra_urls
                if u
            ]
            if tvg_mapper:
                print("[LiveWatch] [i] EPG ativado")
        except Exception as e:
            print(f"[LiveWatch] [!] EPG: {e}")

    if p.get("type") == "merge_all":
        all_entries: list[tuple[str, str, str]] = []
        sub_profiles: list[str] = p.get(
            "include", [k for k in config["profiles"] if k != profile]
        )
        for sp_name in sub_profiles:
            if sp_name not in config["profiles"]:
                print(f"\n[LiveWatch] [!] Sub-perfil '{sp_name}' nao encontrado")
                continue
            print(f"\n[LiveWatch] --- {sp_name} ---")
            sp: dict[str, Any] = config["profiles"][sp_name]
            entries = fetch_profile_entries(sp)
            prefix: str = sp.get("group_prefix", sp_name.upper())
            for group_title, name, url in entries:
                all_entries.append(
                    (normalize_group_title(group_title, prefix), name, url)
                )

        print(f"\n[LiveWatch] [i] Total combinado: {len(all_entries)}")
        all_entries = cleanup_channel_names(all_entries)
        # Final exclusion pass using combined excludes from all sub-profiles
        combined_exclude: list[str] = []
        for sp_name in sub_profiles:
            sp_cfg = config["profiles"].get(sp_name, {})
            combined_exclude.extend(sp_cfg.get("name_exclude", []))
        combined_exclude = list(dict.fromkeys(combined_exclude))
        if combined_exclude:
            all_entries = filter_excluded(all_entries, combined_exclude)
        all_entries = dedup_by_url(all_entries)
        all_entries = rename_duplicates(all_entries)
        all_entries.sort(key=category_sort_key)

        print(f"[LiveWatch] [+] Final: {len(all_entries)} canais")
        generate_playlist(all_entries, base_name, output_dir, tvg_mapper, tvg_url)
        print("[LiveWatch] [+] Playlist salva!")
        return

    filtered = fetch_profile_entries(p)
    print(f"[LiveWatch] [i] Total pos-filtro: {len(filtered)}")

    filtered = cleanup_channel_names(filtered)
    filtered = dedup_by_url(filtered)
    filtered = rename_duplicates(filtered)

    prefix = p.get("group_prefix", profile.upper())
    normalized: list[tuple[str, str, str]] = []
    for group_title, name, url in filtered:
        normalized.append((normalize_group_title(group_title, prefix), name, url))
    filtered = normalized
    filtered.sort(key=category_sort_key)

    print(f"[LiveWatch] [+] Final: {len(filtered)} canais")
    generate_playlist(filtered, base_name, output_dir, tvg_mapper, tvg_url)
    print("[LiveWatch] [+] Playlist salva!")


if __name__ == "__main__":
    main()

