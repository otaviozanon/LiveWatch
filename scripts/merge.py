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
            print(f"[LiveWatch] Extracting playlist {i}/{len(urls)}: {url.rsplit('/', 1)[-1]}")
            print(f"[LiveWatch]   Found: {len(text.splitlines())} lines -> {len(entries)} entries")
        except Exception as e:
            print(f"[LiveWatch]   ERROR: {e}")
            results[url] = []
    return results


def fetch_json(url: str) -> Any:
    """Download and parse a JSON endpoint."""
    print(f"[LiveWatch] Downloading JSON: {url.rsplit('/', 1)[-1]}")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    print(f"[LiveWatch]   Records: {len(data)}")
    return data


def discover_github_sources(repo: str, pattern: str) -> list[str]:
    """List files in a GitHub repo matching *pattern* and return download URLs."""
    api_url = f"https://api.github.com/repos/{repo}/contents/"
    print(f"[LiveWatch] Discovering sources: {api_url}")
    resp = requests.get(api_url, timeout=30)
    resp.raise_for_status()
    files = resp.json()
    regex = re.compile(pattern)
    matched = sorted(
        [f["download_url"] for f in files
         if f["type"] == "file" and regex.search(f["name"])],
        key=lambda u: u,
    )
    print(f"[LiveWatch]   Pattern '{pattern}' -> {len(matched)} files found")
    for u in matched:
        print(f"[LiveWatch]     {u.rsplit('/', 1)[-1]}")
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


def filter_by_group_exclude(
    entries: list[tuple[str, str, str]], exclude_keywords: list[str]
) -> list[tuple[str, str, str]]:
    """Remove entries whose *group_title* contains any of the *exclude_keywords*."""
    if not exclude_keywords:
        return entries
    result: list[tuple[str, str, str]] = []
    removed = 0
    for group_title, name, url in entries:
        gt = _strip_accents(group_title.lower())
        exclude = any(
            _strip_accents(kw.lower()) in gt for kw in exclude_keywords
        )
        if exclude:
            removed += 1
        else:
            result.append((group_title, name, url))
    if removed:
        print(f"[LiveWatch] Removing by excluded group: {removed} removed")
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
        print(f"[LiveWatch] Removing by URL: {removed} removed")
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
        exclude = any(kw.lower() in name.lower() for kw in exclude_keywords)
        if exclude:
            removed += 1
        else:
            result.append((group_title, name, url))
    if removed:
        print(f"[LiveWatch] Removing unwanted channels: {removed} removed")
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
                    if pat.lower() in name.lower():
                        new_group = target_group
                        remapped += 1
                        break
                if new_group != group_title:
                    break
        result.append((new_group, name, url))
    if remapped:
        print(f"[LiveWatch] Redistributing channels by name: {remapped} remapped")
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
        print(f"[LiveWatch] Filtering by group+channel: {removed} removed")
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
        print(f"[LiveWatch] Removing duplicates by URL: {removed} removed")
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
        print(f"[LiveWatch] Renaming conflicts: {renamed} channels adjusted")
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
    "NBA LEAGUE PASS": "PAY PER VIEW",
    "BRASILEIRAO": "PAY PER VIEW",
    "PREMIERE": "PAY PER VIEW",
    "NBA": "PAY PER VIEW",
    "ESTADUAIS": "PAY PER VIEW",
    "FUTSAL": "PAY PER VIEW",
    "TELECINE": "FILMES E SERIES",
    "24H VARIADOS": "24H",
    "ESPORTES ESTADUAIS": "PAY PER VIEW",
    "ESPORTES PPV": "PAY PER VIEW",
}

CATEGORY_ORDER: tuple[str, ...] = (
    "NOVOS",
    "24H", "24H INFANTIL", "REALITIES", "4K",
    "GLOBO", "SBT", "BAND", "RECORD", "ABERTOS",
    "FILMES E SERIES", "DOCUMENTARIOS", "ESPORTES",
    "ENTRETENIMENTO", "PAY PER VIEW", "NOTICIAS",
    "MUSICAS", "DORMIR E RELAXAR", "UFC",
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
    print(f"[LiveWatch] Channels with country={country}: {len(br_channels)}")

    channel_map: dict[str, dict] = {}
    for c in br_channels:
        if not c.get("is_nsfw", False) and "xxx" not in [
            x.lower() for x in c.get("categories", [])
        ]:
            channel_map[c["id"]] = c

    print(f"[LiveWatch] Valid channels (non-NSFW): {len(channel_map)}")

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

    print(f"[LiveWatch] Streams matched for {country}: {len(entries)}")
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
        print(f"[LiveWatch] {base_name}.{ext} generated: {len(entries)} channels")


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
        print(f"[LiveWatch] ERROR: Profile '{profile}' not found in config.json")
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
            print(
                f"[LiveWatch] EPG countries: {epg_countries} "
                f"({len(epgshare_urls)} epgshare + {len(globetv_urls)} globetv sources)"
            )
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
                print("[LiveWatch] EPG enabled - mapping ready")
        except Exception as e:
            print(f"[LiveWatch] WARNING: EPG failed: {e}")

    if p.get("type") == "merge_all":
        all_entries: list[tuple[str, str, str]] = []
        sub_profiles: list[str] = p.get(
            "include", [k for k in config["profiles"] if k != profile]
        )
        for sp_name in sub_profiles:
            if sp_name not in config["profiles"]:
                print(
                    f"[LiveWatch] WARNING: Sub-profile '{sp_name}' not found,"
                    f" skipping"
                )
                continue
            print(f"\n[LiveWatch] ====== Profile: {sp_name} ======")
            sp: dict[str, Any] = config["profiles"][sp_name]
            entries = fetch_profile_entries(sp)
            prefix: str = sp.get("group_prefix", sp_name.upper())
            for group_title, name, url in entries:
                all_entries.append(
                    (normalize_group_title(group_title, prefix), name, url)
                )

        print(f"\n[LiveWatch] Total combined channels: {len(all_entries)}")
        all_entries = dedup_by_url(all_entries)
        all_entries = rename_duplicates(all_entries)
        all_entries.sort(key=category_sort_key)

        print(f"[LiveWatch] Final total: {len(all_entries)} channels")
        generate_playlist(all_entries, base_name, output_dir, tvg_mapper, tvg_url)
        print("[LiveWatch] Playlist saved successfully!")
        return

    filtered = fetch_profile_entries(p)
    print(f"[LiveWatch] Total channels (post-filter): {len(filtered)}")

    filtered = dedup_by_url(filtered)
    filtered = rename_duplicates(filtered)

    prefix = p.get("group_prefix", profile.upper())
    normalized: list[tuple[str, str, str]] = []
    for group_title, name, url in filtered:
        normalized.append((normalize_group_title(group_title, prefix), name, url))
    filtered = normalized
    filtered.sort(key=category_sort_key)

    print(f"[LiveWatch] Final total: {len(filtered)} channels")
    generate_playlist(filtered, base_name, output_dir, tvg_mapper, tvg_url)
    print("[LiveWatch] Playlist saved successfully!")


if __name__ == "__main__":
    main()

