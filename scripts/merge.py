import argparse
import json
import os
import re

import requests


def parse_m3u(text):
    entries = []
    lines = text.strip().splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF"):
            attr_match = re.search(r'group-title="([^"]*)"', line, re.IGNORECASE)
            group_title = attr_match.group(1) if attr_match else ""
            name_match = re.search(r",\s*(.+)$", line)
            name = name_match.group(1).strip() if name_match else ""
            i += 1
            if i < len(lines) and lines[i].strip() and not lines[i].strip().startswith("#"):
                url = lines[i].strip()
                entries.append((group_title, name, url))
        i += 1
    return entries


def fetch_playlist(url):
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def fetch_all(urls):
    results = {}
    for i, url in enumerate(urls, 1):
        try:
            text = fetch_playlist(url)
            entries = parse_m3u(text)
            results[url] = entries
            print(f"[LiveWatch] Extraindo lista {i}/{len(urls)}: {url.rsplit('/', 1)[-1]}")
            print(f"[LiveWatch]   Encontrados: {len(text.splitlines())} linhas -> {len(entries)} entradas")
        except Exception as e:
            print(f"[LiveWatch]   ERRO: {e}")
            results[url] = []
    return results


def filter_by_group(entries, prefix):
    return [(g, n, u) for g, n, u in entries if g.lower().startswith(prefix.lower())]


def filter_excluded(entries, exclude_keywords):
    if not exclude_keywords:
        return entries
    result = []
    removed = 0
    for group_title, name, url in entries:
        exclude = False
        for kw in exclude_keywords:
            if kw.lower() in name.lower():
                exclude = True
                break
        if exclude:
            removed += 1
        else:
            result.append((group_title, name, url))
    if removed:
        print(f"[LiveWatch] Removendo canais indesejados: {removed} removidos")
    return result


def dedup_by_url(entries):
    seen = set()
    result = []
    removed = 0
    for entry in entries:
        url = entry[2]
        if url not in seen:
            seen.add(url)
            result.append(entry)
        else:
            removed += 1
    if removed:
        print(f"[LiveWatch] Removendo duplicados por URL: {removed} removidos")
    return result


def rename_duplicates(entries):
    name_counts = {}
    renamed = 0
    result = []
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
        print(f"[LiveWatch] Renomeando conflitos: {renamed} canais ajustados")
    return result


def generate_playlist(entries, base_name, output_dir):
    # Cria as pastas m3u e m3u8
    m3u_dir = os.path.join(output_dir, "playlists", "m3u")
    m3u8_dir = os.path.join(output_dir, "playlists", "m3u8")

    os.makedirs(m3u_dir, exist_ok=True)
    os.makedirs(m3u8_dir, exist_ok=True)

    # Gera ambos os formatos
    for ext, folder in [("m3u", m3u_dir), ("m3u8", m3u8_dir)]:
        output_path = os.path.join(folder, f"{base_name}.{ext}")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for group_title, name, url in entries:
                f.write(f'#EXTINF:-1 group-title="{group_title}",{name}\n')
                f.write(f"{url}\n")
        print(f"[LiveWatch] {base_name}.{ext} gerada: {len(entries)} canais")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="brasil", help="Which playlist profile to use")
    args = parser.parse_args()
    profile = args.profile

    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    if profile not in config.get("profiles", {}):
        print(f"[LiveWatch] ERRO: Perfil '{profile}' nao encontrado no config.json")
        return

    p = config["profiles"][profile]
    base_name = p["output"].replace(".m3u8", "").replace(".m3u", "")
    output_dir = os.path.dirname(script_dir)

    all_results = fetch_all(p["sources"])

    filtered = []
    for entries in all_results.values():
        filtered.extend(filter_by_group(entries, p["filter_group"]))

    print(f"[LiveWatch] Total canais (pos-filtro): {len(filtered)}")

    filtered = filter_excluded(filtered, p.get("name_exclude", []))
    filtered = dedup_by_url(filtered)
    filtered = rename_duplicates(filtered)

    print(f"[LiveWatch] Total final: {len(filtered)} canais")
    generate_playlist(filtered, base_name, output_dir)
    print("[LiveWatch] Playlist salva com sucesso!")


if __name__ == "__main__":
    main()
