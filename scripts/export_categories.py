"""Exporta categorias a partir da playlist ALL gerada.

Uso: python scripts/export_categories.py

Le os arquivos de categoria existentes, adiciona canais novos encontrados
na playlist, e preserva os canais ja curados manualmente.
"""
import re, os, json
from pathlib import Path

script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
playlist_path = os.path.join(project_dir, 'playlists', 'm3u8', 'LiveWatch-PlaylistAll.m3u8')

with open(playlist_path, encoding='utf-8') as f:
    content = f.read()

lines = content.splitlines()
cats: dict[str, set] = {}

# Extrair categorias de TODOS os perfis (nao so BR)
for i in range(len(lines)):
    m = re.match(r'#EXTINF:.*group-title="[^|\u2013]+[\|\u2013] ([^"]+)"', lines[i])
    if not m:
        m = re.match(r'#EXTINF:.*group-title="([^"]+)"', lines[i])
    if m:
        cat = m.group(1).strip()
        name = re.sub(r'.*,', '', lines[i]).strip()
        if cat not in cats:
            cats[cat] = set()
        cats[cat].add(name)

cat_dir = Path(project_dir) / 'playlists' / 'categories'
cat_dir.mkdir(exist_ok=True)

added_total = 0
kept_total = 0

for category, new_channels in cats.items():
    filename = category.lower().replace(' ', '_').replace('|', '').strip()
    filepath = cat_dir / f"{filename}.json"

    existing_channels: list[str] = []
    if filepath.exists():
        with open(filepath, encoding='utf-8') as f:
            data = json.load(f)
            existing_channels = data.get('channels', [])

    merged = list(existing_channels)
    existing_set = set(existing_channels)
    for ch in sorted(new_channels):
        if ch not in existing_set:
            merged.append(ch)
            added_total += 1

    kept_total += len(existing_channels)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump({
            "name": category,
            "channels": merged,
            "count": len(merged)
        }, f, ensure_ascii=False, indent=2)

print(f"[LiveWatch] categorias: {len(cats)} arquivos")
if kept_total:
    print(f"[LiveWatch] canais mantidos (curados): {kept_total}")
if added_total:
    print(f"[LiveWatch] canais novos adicionados: {added_total}")
