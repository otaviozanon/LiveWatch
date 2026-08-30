# 📁 Playlists e Categorias - LiveWatch

**Estrutura modular com arquivos separados por categoria**

---

## 📂 Estrutura de Arquivos

```
playlists/
├── categories/                    # 26 arquivos JSON separados
│   ├── 24h.json                   # 1.080 canais
│   ├── 24h_infantil.json          # 360 canais
│   ├── abertos.json               # 81 canais
│   ├── ar_livre.json              # 49 canais
│   ├── band.json                  # 2 canais
│   ├── dazn.json                  # 12 canais
│   ├── documentarios.json         # 216 canais
│   ├── dormir_e_relaxar.json      # 1 canal
│   ├── educacao.json              # 58 canais
│   ├── entretenimento.json        # 357 canais
│   ├── esportes.json              # 347 canais
│   ├── estados_unidos.json        # 1 canal
│   ├── filmes_e_series.json       # 721 canais
│   ├── formula_1.json             # 3 canais
│   ├── globo.json                 # 34 canais
│   ├── infantis.json              # 145 canais
│   ├── musicas.json               # 65 canais
│   ├── nba.json                   # 32 canais
│   ├── noticias.json              # 176 canais
│   ├── pay_per_view.json          # 243 canais
│   ├── pluto_tv.json              # 52 canais
│   ├── realities.json             # 3 canais
│   ├── record.json                # 8 canais
│   ├── religiosos.json            # 144 canais
│   ├── sbt.json                   # 1 canal
│   ├── ufc.json                   # 32 canais
│   ├── README.md                  # Guia de uso
│   └── ESTRUTURA.md               # Documentação técnica
│
├── m3u/                           # Playlists M3U
│   ├── LiveWatch-PlaylistAll.m3u
│   ├── LiveWatch-PlaylistBR.m3u
│   ├── LiveWatch-PlaylistIPTVORG.m3u
│   └── LiveWatch-PlaylistManoTV.m3u
│
├── m3u8/                          # Playlists M3U8
│   ├── LiveWatch-PlaylistAll.m3u8
│   ├── LiveWatch-PlaylistBR.m3u8
│   ├── LiveWatch-PlaylistIPTVORG.m3u8
│   └── LiveWatch-PlaylistManoTV.m3u8
│
├── AUDITORIA_CATEGORIAS.md        # Auditoria: visão geral
├── AUDITORIA_DETALHADA.md         # Auditoria: análise profunda
├── LISTA_COMPLETA_CATEGORIAS.md   # Todos os canais listados
├── README_AUDITORIA.md            # Sumário executivo da auditoria
├── SUMARIO_REORGANIZACAO.md       # Resumo da reorganização
├── pipeline.log                   # Log do último merge
└── README.md                      # Este arquivo
```

---

## 📊 Estatísticas

- **26 categorias** organizadas
- **4.223 canais** catalogados
- **0 duplicatas** entre categorias
- **26 arquivos JSON** separados
- **4 perfis** de playlist (ALL, BR, IPTV-ORG, ManoTV)

---

## 🛠️ Como Usar

### Visualizar uma categoria

```bash
# Ver categoria de músicas
cat playlists/categories/musicas.json
```

### Editar uma categoria

```bash
# 1. Abrir arquivo
code playlists/categories/musicas.json

# 2. Editar array "channels"

# 3. Atualizar campo "count"

# 4. Salvar
```

### Carregar todas as categorias (Python)

```python
from scripts.load_categories import load_categories_from_files

# Carregar todas
cats = load_categories_from_files("playlists/categories")

# Acessar categoria específica
print(cats["MUSICAS"])  # Lista de canais musicais
```

### Atualizar uma categoria (Python)

```python
from scripts.load_categories import update_category

# Novos canais
canais = ["MTV", "MTV HITS", "MULTISHOW"]

# Atualizar
update_category("MUSICAS", canais, "playlists/categories")
```

---

## 🔄 Regenerar Categorias

Para atualizar os arquivos JSON a partir do playlist ALL:

```bash
python scripts/export_categories.py
```

Isso irá:
1. Ler `m3u8/LiveWatch-PlaylistAll.m3u8`
2. Extrair categorias e canais
3. Gerar 26 arquivos JSON em `categories/`

---

## 📖 Documentação

- **`categories/README.md`** - Guia completo de uso das categorias
- **`categories/ESTRUTURA.md`** - Documentação técnica da estrutura
- **`AUDITORIA_DETALHADA.md`** - Problemas identificados e sugestões
- **`SUMARIO_REORGANIZACAO.md`** - Resumo da reorganização

---

## ✅ Vantagens da Estrutura Modular

1. **Organização** - Cada categoria em arquivo próprio
2. **Manutenção** - Edição rápida e localizada
3. **Performance** - Carregar apenas categorias necessárias
4. **Git-friendly** - Diffs claros, merges fáceis
5. **Escalabilidade** - Adicionar categorias sem afetar outras

---

## 🚀 Scripts Disponíveis

| Script | Função |
|--------|--------|
| `scripts/export_categories.py` | Gera arquivos JSON separados |
| `scripts/load_categories.py` | Carrega categorias em memória |
| `scripts/audit_categories.py` | Auditoria e validação |
| `scripts/merge.py` | Gera playlists M3U/M3U8 |

---

**Atualizado em:** 2026-08-08
