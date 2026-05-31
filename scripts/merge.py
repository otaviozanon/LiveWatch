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


def generate_playlist(entries, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for group_title, name, url in entries:
            f.write(f'#EXTINF:-1 group-title="{group_title}",{name}\n')
            f.write(f"{url}\n")
    print(f"[LiveWatch] playlist.m3u8 gerada: {len(entries)} canais")


if __name__ == "__main__":
    sample = '#EXTINF:-1 group-title="Canais | Globo",GLOBO SP\nhttp://example.com/globo.m3u8\n'
    result = parse_m3u(sample)
    assert len(result) == 1
    assert result[0] == ("Canais | Globo", "GLOBO SP", "http://example.com/globo.m3u8")
    print("parse_m3u: OK")

    e = [("Canais | Globo", "GLOBO SP", "http://x"), ("Filmes", "Filme A", "http://y")]
    r = filter_by_group(e, "Canais")
    assert len(r) == 1
    assert r[0][0] == "Canais | Globo"
    print("filter_by_group: OK")

    e = [("A", "X", "http://same"), ("B", "Y", "http://same")]
    r = dedup_by_url(e)
    assert len(r) == 1
    print("dedup_by_url: OK")

    e = [("C", "GLOBO SP", "http://a"), ("C", "GLOBO SP", "http://b")]
    r = rename_duplicates(e)
    assert r[0][1] == "GLOBO SP"
    assert r[1][1] == "GLOBO SP [2]"
    print("rename_duplicates: OK")

    import os
    e = [("Canais | Globo", "GLOBO SP", "http://x")]
    generate_playlist(e, "test_out.m3u8")
    assert os.path.exists("test_out.m3u8")
    os.remove("test_out.m3u8")
    print("generate_playlist: OK")
