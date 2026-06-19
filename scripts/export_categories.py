"""Exporta categories.json a partir da playlist ALL gerada.

Uso: python scripts/export_categories.py

Gera playlists/categories.json com todas as categorias e canais do ALL.
Usado como referencia para saber o que ja esta mapeado.
Novos canais/categorias vao automaticamente para "NOVOS" no merge.py.
"""
import re, os, json

script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
playlist_path = os.path.join(project_dir, 'playlists', 'm3u8', 'LiveWatch-PlaylistAll.m3u8')

with open(playlist_path, encoding='utf-8') as f:
    content = f.read()

lines = content.splitlines()
cats = {}

for i in range(len(lines)):
    m = re.match(r'#EXTINF:.*group-title="BR \| ([^"]+)"', lines[i])
    if m:
        cat = m.group(1)
        name = re.sub(r'.*,', '', lines[i]).strip()
        if cat not in cats:
            cats[cat] = []
        if name not in cats[cat]:
            cats[cat].append(name)

for cat in cats:
    cats[cat].sort()

json_path = os.path.join(project_dir, 'playlists', 'categories.json')
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(cats, f, ensure_ascii=False, indent=2)

print(f"[LiveWatch] categories.json gerado: {len(cats)} categorias, {sum(len(v) for v in cats.values())} canais")
