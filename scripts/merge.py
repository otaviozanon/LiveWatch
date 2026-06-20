import argparse
import json
import os
import re
import unicodedata

import requests

try:
    from . import epg
except ImportError:
    import epg


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


def discover_github_sources(repo, pattern):
    api_url = f"https://api.github.com/repos/{repo}/contents/"
    print(f"[LiveWatch] Descobrindo sources: {api_url}")
    resp = requests.get(api_url, timeout=30)
    resp.raise_for_status()
    files = resp.json()
    regex = re.compile(pattern)
    matched = sorted(
        [f["download_url"] for f in files
         if f["type"] == "file" and regex.search(f["name"])],
        key=lambda u: u
    )
    print(f"[LiveWatch]   Pattern '{pattern}' -> {len(matched)} arquivos encontrados")
    for u in matched:
        print(f"[LiveWatch]     {u.rsplit('/', 1)[-1]}")
    return matched


def filter_by_group(entries, prefix):
    return [(g, n, u) for g, n, u in entries if g.lower().startswith(prefix.lower())]


def strip_accents(text):
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def filter_by_group_exclude(entries, exclude_keywords):
    if not exclude_keywords:
        return entries
    result = []
    removed = 0
    for group_title, name, url in entries:
        gt = strip_accents(group_title.lower())
        exclude = False
        for kw in exclude_keywords:
            if strip_accents(kw.lower()) in gt:
                exclude = True
                break
        if exclude:
            removed += 1
        else:
            result.append((group_title, name, url))
    if removed:
        print(f"[LiveWatch] Removendo por grupo excluido: {removed} removidos")
    return result


GT_REMAP = {
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


def normalize_group_title(group_title, prefix):
    gt = group_title.strip()
    gt = re.sub(r"^CANAIS\s*\|\s*", "", gt, flags=re.IGNORECASE)
    gt = re.sub(r"^CANAL\s+\W+(?=\s*\w)", "", gt, flags=re.IGNORECASE)
    gt = gt.strip().upper()
    gt = strip_accents(gt)

    gt = GT_REMAP.get(gt, gt)

    if gt not in CATEGORY_ORDER:
        gt = "NOVOS"

    return f"{prefix} | {gt}"


CATEGORY_ORDER = (
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


def category_sort_key(entry):
    group_title, name, _ = entry
    cat = group_title.replace("BR | ", "")
    try:
        cat_order = CATEGORY_ORDER.index(cat)
    except ValueError:
        cat_order = len(CATEGORY_ORDER)
    return (cat_order, name.lower())


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


def fetch_json(url):
    print(f"[LiveWatch] Baixando JSON: {url.rsplit('/', 1)[-1]}")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    print(f"[LiveWatch]   Registros: {len(data)}")
    return data


def process_iptv_api(channels_url, streams_url, country):
    CATEGORY_TRANSLATION = {
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

    channels_data = fetch_json(channels_url)

    br_channels = [c for c in channels_data if c.get("country") == country]
    print(f"[LiveWatch] Canais com country={country}: {len(br_channels)}")

    channel_map = {}
    for c in br_channels:
        if not c.get("is_nsfw", False) and "xxx" not in [x.lower() for x in c.get("categories", [])]:
            channel_map[c["id"]] = c

    print(f"[LiveWatch] Canais validos (sem NSFW): {len(channel_map)}")

    streams_data = fetch_json(streams_url)

    entries = []
    for s in streams_data:
        ch_id = s.get("channel")
        if not ch_id or ch_id not in channel_map:
            continue

        ch = channel_map[ch_id]
        url = s.get("url")
        if not url:
            continue

        title = s.get("title") or ch.get("name", "Sem Nome")
        cats = ch.get("categories", ["general"])
        category = cats[0] if cats else "general"
        group_title = CATEGORY_TRANSLATION.get(category.lower(), category.upper())

        entries.append((group_title, title, url))

    print(f"[LiveWatch] Streams com match para {country}: {len(entries)}")
    return entries


def fetch_profile_entries(p):
    if p.get("type") == "iptv_api":
        entries = process_iptv_api(p["sources"][0], p["sources"][1], p.get("country", "BR"))
    else:
        github_repo = p.get("github_repo")
        sources = p.get("sources", [])
        if github_repo:
            sources = discover_github_sources(github_repo, p.get("source_pattern", ""))
        all_results = fetch_all(sources)
        entries = []
        for e_list in all_results.values():
            if p.get("filter_group"):
                e_list = filter_by_group(e_list, p["filter_group"])
            entries.extend(e_list)

    entries = filter_excluded(entries, p.get("name_exclude", []))
    entries = remap_by_name(entries, p.get("name_remap", {}), p.get("remap_from"))
    entries = filter_by_group_exclude(entries, p.get("group_exclude", []))
    entries = filter_by_group_keep(entries, p.get("group_keep", {}))
    return entries


def remap_by_name(entries, name_remap, remap_from_groups=None):
    if not name_remap:
        return entries
    result = []
    remapped = 0
    for group_title, name, url in entries:
        new_group = group_title
        if remap_from_groups is None or any(g.lower() in group_title.lower() for g in remap_from_groups):
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
        print(f"[LiveWatch] Redistribuindo canais por nome: {remapped} remapeados")
    return result


def filter_by_group_keep(entries, group_rules):
    if not group_rules:
        return entries
    result = []
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
        print(f"[LiveWatch] Filtrando por grupo+canal: {removed} removidos")
    return result


def generate_playlist(entries, base_name, output_dir, tvg_mapper=None, tvg_url=None):
    # Cria as pastas m3u e m3u8
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
        tvg_urls = []

    # Gera ambos os formatos
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

    # â”€â”€ EPG integration â”€â”€
    epg_config = config.get("epg", {})
    tvg_mapper = None
    tvg_url = None
    if epg_config.get("enabled", False):
        try:
            epg_countries = epg_config.get("countries", ["BR"])
            epgshare_urls, globetv_urls, extra_urls = epg.get_epg_sources_for_countries(epg_countries)
            print(f"[LiveWatch] EPG paises: {epg_countries} ({len(epgshare_urls)} epgshare + {len(globetv_urls)} globetv fontes)")
            tvg_mapper = epg.build_channel_mapper(
                sources=epgshare_urls,
                globetv_sources=globetv_urls,
            )
            primary_url = epg_config.get("tvg_url", "")
            tvg_url = [u for u in [primary_url] + epgshare_urls + globetv_urls + extra_urls if u]
            if tvg_mapper:
                print("[LiveWatch] EPG habilitado - mapeamento pronto")
        except Exception as e:
            print(f"[LiveWatch] AVISO: EPG falhou: {e}")

    if p.get("type") == "merge_all":
        all_entries = []
        sub_profiles = p.get("include", [k for k in config["profiles"] if k != profile])
        for sp_name in sub_profiles:
            if sp_name not in config["profiles"]:
                print(f"[LiveWatch] AVISO: Sub-perfil '{sp_name}' nao encontrado, pulando")
                continue
            print(f"\n[LiveWatch] ====== Perfil: {sp_name} ======")
            sp = config["profiles"][sp_name]
            entries = fetch_profile_entries(sp)
            prefix = sp.get("group_prefix", sp_name.upper())
            for group_title, name, url in entries:
                all_entries.append((normalize_group_title(group_title, prefix), name, url))

        print(f"\n[LiveWatch] Total canais combinados: {len(all_entries)}")
        all_entries = dedup_by_url(all_entries)
        all_entries = rename_duplicates(all_entries)
        all_entries.sort(key=category_sort_key)

        print(f"[LiveWatch] Total final: {len(all_entries)} canais")
        generate_playlist(all_entries, base_name, output_dir, tvg_mapper, tvg_url)
        print("[LiveWatch] Playlist salva com sucesso!")
        return

    filtered = fetch_profile_entries(p)
    print(f"[LiveWatch] Total canais (pos-filtro): {len(filtered)}")

    filtered = dedup_by_url(filtered)
    filtered = rename_duplicates(filtered)

    prefix = p.get("group_prefix", profile.upper())
    normalized = []
    for group_title, name, url in filtered:
        normalized.append((normalize_group_title(group_title, prefix), name, url))
    filtered = normalized
    filtered.sort(key=category_sort_key)

    print(f"[LiveWatch] Total final: {len(filtered)} canais")
    generate_playlist(filtered, base_name, output_dir, tvg_mapper, tvg_url)
    print("[LiveWatch] Playlist salva com sucesso!")


if __name__ == "__main__":
    main()

