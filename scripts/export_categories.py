"""Exporta categorias a partir da playlist ALL gerada.

Uso: python scripts/export_categories.py

Gera APENAS arquivos JSON separados por categoria em playlists/categories/
NÃO gera mais o categories.json gigante.
Usado como referencia para saber o que ja esta mapeado.
"""
import re, os, json
from pathlib import Path

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

# Criar diretório para categorias separadas
cat_dir = Path(project_dir) / 'playlists' / 'categories'
cat_dir.mkdir(exist_ok=True)

# Salvar arquivo individual para cada categoria
for category, channels in cats.items():
    filename = category.lower().replace(' ', '_').replace('|', '').strip()
    filepath = cat_dir / f"{filename}.json"

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump({
            "name": category,
            "channels": channels,
            "count": len(channels)
        }, f, ensure_ascii=False, indent=2)

total_channels = sum(len(v) for v in cats.values())
print(f"[LiveWatch] ✅ {len(cats)} categorias exportadas")
print(f"[LiveWatch] 📊 {total_channels} canais organizados")
print(f"[LiveWatch] 📁 Arquivos separados: playlists/categories/*.json")
