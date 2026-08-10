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
from typing import Any

from core.fetcher import discover_github_sources, fetch_all, fetch_json
from core.filters import (
    cleanup_channel_names,
    dedup_by_url,
    filter_by_group,
    filter_by_group_exclude,
    filter_by_group_keep,
    filter_by_url,
    filter_excluded,
    remap_by_group,
    remap_by_name,
    rename_duplicates,
)
from core.output import (
    CATEGORY_TRANSLATION,
    category_sort_key,
    generate_playlist,
    normalize_group_title,
)

try:
    from . import epg
    from .load_config import load_config
except ImportError:
    import epg
    from load_config import load_config


# ── IPTV API processing ────────────────────────────────────────────────────

def process_iptv_api(
    channels_url: str, streams_url: str, country: str
) -> list[tuple[str, str, str]]:
    """Fetch channel + stream data from an IPTV API and build entry list."""
    import re

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


# ── Profile pipeline ───────────────────────────────────────────────────────

def fetch_profile_entries(p: dict[str, Any]) -> list[tuple[str, str, str]]:
    """
    Fetch, filter, and remap entries for a single profile configuration.

    Pipeline:
    1. Fetch from GitHub M3U or IPTV API
    2. Filter by group keyword inclusion
    3. Remap source group titles to target categories
    4. Exclude by URL pattern
    5. Exclude by channel name
    6. Remap categories by channel name
    7. Exclude by group title
    8. Keep/remove within specific groups
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

    entries = remap_by_group(entries, p.get("group_remap", {}))
    entries = filter_by_url(entries, p.get("url_exclude", []))
    entries = filter_excluded(entries, p.get("name_exclude", []))
    entries = remap_by_name(entries, p.get("name_remap", {}), p.get("remap_from"))
    entries = filter_by_group_exclude(entries, p.get("group_exclude", []))
    entries = filter_by_group_keep(entries, p.get("group_keep", {}))
    return entries


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    """Entry point.  Reads profile config and generates playlists."""
    parser = argparse.ArgumentParser(description="LiveWatch playlist generator")
    parser.add_argument(
        "--profile", default="brasil", help="Which playlist profile to use"
    )
    args = parser.parse_args()
    profile: str = args.profile

    # Carregar config de arquivos separados
    config: dict[str, Any] = load_config()
    script_dir = os.path.dirname(os.path.abspath(__file__))

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
