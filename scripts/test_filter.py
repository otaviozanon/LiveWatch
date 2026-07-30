"""
Test filter pipeline on a single M3U file.
Usage: python scripts/test_filter.py CanaisBR01.m3u8
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(__file__))
from core.parser import parse_m3u
from core.fetcher import fetch_playlist
from core.filters import (
    filter_by_group, filter_by_url, filter_excluded,
    remap_by_name, remap_by_group,
    filter_by_group_exclude, filter_by_group_keep,
    cleanup_channel_names, dedup_by_url, rename_duplicates,
)
from core.output import normalize_group_title, category_sort_key

def main():
    """Download and run the full filter pipeline on a single M3U file."""
    if len(sys.argv) < 2:
        print("Uso: python test_filter.py <arquivo.m3u8>")
        return

    filename = sys.argv[1]
    url = f"https://raw.githubusercontent.com/Ramys/Iptv-Brasil-2026/master/{filename}"

    # Load config
    script_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(script_dir, "config.json"), "r", encoding="utf-8") as f:
        config = json.load(f)
    p = config["profiles"]["brasil"]

    print(f"\n=== {filename} ===")
    text = fetch_playlist(url)
    entries = parse_m3u(text)
    print(f"Total entradas: {len(entries)}")

    # Step 1: filter by group
    if p.get("filter_group"):
        # Show which groups are being removed
        ignored_groups = {}
        for g, n, u in entries:
            keep = not g or any(kw.lower() in g.lower() for kw in p["filter_group"])
            if not keep:
                if g not in ignored_groups:
                    ignored_groups[g] = 0
                ignored_groups[g] += 1
        if ignored_groups:
            print(f"\nGrupos ignorados por filter_group:")
            for grp, cnt in sorted(ignored_groups.items(), key=lambda x: -x[1]):
                safe = grp.encode('ascii','replace').decode('ascii')
                print(f"  [{cnt:3d}] {safe}")
            print()
        e1 = filter_by_group(entries, p["filter_group"])
        print(f"Apos filter_by_group: {len(e1)} (removidos: {len(entries)-len(e1)})")
    else:
        e1 = entries

    # Step 2: remap groups
    if p.get("group_remap"):
        e2 = remap_by_group(e1, p.get("group_remap", {}))
    else:
        e2 = e1

    # Step 3: URL exclude
    e3 = filter_by_url(e2, p.get("url_exclude", []))

    # Step 4: name exclude
    e4 = filter_excluded(e3, p.get("name_exclude", []))

    # Step 5: name remap
    e5 = remap_by_name(e4, p.get("name_remap", {}), p.get("remap_from"))

    # Step 6: group exclude
    e6 = filter_by_group_exclude(e5, p.get("group_exclude", []))

    # Step 7: group keep
    e7 = filter_by_group_keep(e6, p.get("group_keep", {}))

    # Cleanup
    e8 = cleanup_channel_names(e7)
    e9 = dedup_by_url(e8)
    e10 = rename_duplicates(e9)

    # Normalize
    prefix = p.get("group_prefix", "BR")
    result = []
    for g, n, u in e10:
        result.append((normalize_group_title(g, prefix), n, u))

    # Sort
    result.sort(key=category_sort_key)

    print(f"\n=== Resultado final: {len(result)} canais ===")

    # Group summary
    groups = {}
    for g, n, u in result:
        cat = g.split("|")[-1].strip()
        if cat not in groups:
            groups[cat] = []
        if len(groups[cat]) < 10:
            groups[cat].append(n)

    for cat in sorted(groups.keys()):
        print(f"\n{cat} ({len([1 for g2,_,_ in result if cat in g2])}):")
        for ch in groups[cat][:10]:
            print(f"  {ch}")
        if len(groups[cat]) == 10:
            more = len([1 for g2,_,_ in result if cat in g2]) - 10
            if more > 0:
                print(f"  ... +{more}")

if __name__ == "__main__":
    main()
