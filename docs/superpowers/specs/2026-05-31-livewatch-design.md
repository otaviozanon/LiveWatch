# LiveWatch — Design Spec

**Date:** 2026-05-31  
**Status:** Approved

---

## 1. Overview

LiveWatch e uma ferramenta que extrai 5 playlists IPTV raw do GitHub, mescla em uma unica playlist m3u8 (filtrando apenas canais), e publica o resultado de volta no GitHub. O frontend e uma interface estilo terminal com logs em tempo real, hospedada no GitHub Pages. Um botao manual dispara o processamento; um cron a cada 6h executa automaticamente.

## 2. Architecture

```
[GitHub Pages] --POST--> [Cloudflare Worker] --workflow_dispatch--> [GitHub Actions]
                                                                          |
                                                                   [Python merge.py]
                                                                          |
                                                                   [git push playlist.m3u8]
```

### Repos

| Repo | Proposito | Visibilidade |
|------|-----------|--------------|
| Repo Origem (X) | Contem as 5 playlists raw | Leitura anonima (raw URL) |
| Repo Processamento | Script Python + workflow + playlist gerada | Publico (PAT em Secrets) |
| Repo Frontend | HTML/CSS/JS + GitHub Pages | Publico |

### Flow

1. Usuario clica "ATUALIZAR PLAYLIST" no frontend
2. Frontend chama `POST /trigger` no Cloudflare Worker
3. Worker le o PAT dos secrets e dispara `workflow_dispatch` no repo de processamento
4. GitHub Actions inicia, roda `merge.py`, gera `playlist.m3u8`, da push
5. Frontend consulta `GET /repos/{owner}/{repo}/actions/runs/{id}/logs` a cada 3s e exibe os logs no terminal

### Auto-update

Cron: `0 */6 * * *` no workflow YAML. Executa o mesmo pipeline automaticamente.

## 3. Python Script (`merge.py`)

### Entrada

Arquivo `config.json` no repo de processamento:

```json
{
  "sources": [
    "https://raw.githubusercontent.com/user/repo/main/lista1.m3u",
    "https://raw.githubusercontent.com/user/repo/main/lista2.m3u",
    "https://raw.githubusercontent.com/user/repo/main/lista3.m3u",
    "https://raw.githubusercontent.com/user/repo/main/lista4.m3u",
    "https://raw.githubusercontent.com/user/repo/main/lista5.m3u"
  ],
  "filter_group": "Canais"
}
```

### Processamento

1. **Fetch**: Baixa cada URL raw via `requests.get()`
2. **Parse**: Extrai pares `(group-title, nome, url)` de cada playlist
3. **Filter**: Mantem apenas entradas cujo `group-title` comeca com `"Canais"`
4. **Dedup por URL**: Remove entradas com URL identica (mantem a primeira ocorrencia)
5. **Dedup por nome**: Para nomes iguais com URLs diferentes, renomeia adicionando sufixo ` [1]`, ` [2]`, etc.
6. **Generate**: Escreve `playlist.m3u8` com header `#EXTM3U` e entradas `#EXTINF` + URL

### Dependencias

- `requests` (unica dependencia externa)
- Instalado via `pip install requests` na action

### Logs

Cada etapa imprime uma linha no stdout formatada:
```
[LiveWatch] Extraindo lista 1/5: lista-canais.m3u
[LiveWatch]   Encontrados: 342 entradas -> 187 canais (filtro)
[LiveWatch] Removendo duplicados por URL: 23 removidos
[LiveWatch] Total final: 822 canais
[LiveWatch] playlist.m3u8 gerada e enviada ao GitHub!
```

## 4. GitHub Actions Workflow

Arquivo: `.github/workflows/merge.yml` (no repo de processamento)

### Triggers

- `workflow_dispatch` — manual via frontend
- `schedule` — cron `0 */6 * * *`

### Steps

| Step | Acao |
|------|------|
| Checkout | `actions/checkout@v4` |
| Python | `actions/setup-python@v5` com Python 3.11 |
| Install | `pip install requests` |
| Merge | `python merge.py` |
| Commit | `git add playlist.m3u8 && git diff --staged --quiet \|\| git commit -m "Atualizacao automatica $(date -u +%Y-%m-%dT%H:%M:%SZ)"` |
| Push | `git push` autenticado com o PAT do Secrets |

### Secrets

- `PAT_GH`: GitHub Personal Access Token com permissoes `contents` (push) e `workflows` (dispatch). Um unico token com ambas as permissoes e usado tanto na Action quanto no Worker.

### Observacao

O commit so ocorre se `playlist.m3u8` foi alterada (evita commits vazios).

## 5. Cloudflare Worker

### Endpoint

`POST https://<worker>.workers.dev/trigger`

### Secrets (via `wrangler secret put`)

- `GITHUB_PAT` — token com permissoes `workflow`
- `GITHUB_OWNER` — nome do usuario/proprietario do repo
- `GITHUB_REPO` — nome do repo de processamento
- `WORKFLOW_ID` — nome do arquivo YAML (`merge.yml`)

### Comportamento

1. Recebe POST do frontend (body pode ser vazio)
2. Adiciona headers CORS (`Access-Control-Allow-Origin: *`)
3. Chama `POST https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches` com ref `main`
4. Retorna JSON: `{ "ok": true }` ou `{ "ok": false, "error": "..." }`

### Seguranca

O Worker nao exige autenticacao propria. A URL nao e publicamente listada. O PAT esta apenas nos secrets do Worker, nunca exposto ao browser.

## 6. Frontend (GitHub Pages)

### Tecnologia

Vanilla HTML + CSS + JS. Zero dependencias.

### Arquivos

| Arquivo | Responsabilidade |
|---------|-----------------|
| `index.html` | Estrutura base, botao "ATUALIZAR PLAYLIST", container do terminal |
| `style.css` | Tema escuro (fundo `#0d1117`), fonte monospace, scroll automatico |
| `app.js` | Logica de disparo (POST para Worker), polling de logs (cada 3s), renderizacao dos logs no terminal |

### Interface

- Fundo escuro com texto monospace (estilo terminal)
- Cabecalho: "LiveWatch — Merge Playlist"
- Botao verde: `> ATUALIZAR PLAYLIST`
- Apos clique: logs aparecem linha por linha, com scroll automatico

### Cores dos logs

| Cor | Significado | Exemplo |
|-----|-------------|---------|
| Verde (`#3fb950`) | Sucesso / conclusao | "Total final: 822 canais" |
| Azul (`#58a6ff`) | Informacao / progresso | "Extraindo lista 1/5" |
| Laranja (`#f0883e`) | Aviso / processamento | "Removendo duplicados por URL" |
| Roxo (`#d2a8ff`) | Acao do sistema | "Disparando workflow..." |
| Cinza (`#8b949e`) | Status / espera | "Aguardando inicio da action..." |
| Vermelho (`#f85149`) | Erro | "Falha ao extrair lista 3/5" |

### Polling

Apos o Worker retornar sucesso, o frontend:
1. Busca a ultima action run via `GET /repos/{owner}/{repo}/actions/runs?status=in_progress&per_page=1`
2. A cada 3 segundos, busca logs via `GET /repos/{owner}/{repo}/actions/runs/{id}/logs`
3. Quando o status muda para `completed`, busca os logs finais e exibe "Concluido em Xs"

### Repo de processamento publico

O repo de processamento deve ser publico para que o frontend (sem autenticacao) possa consultar os logs da action via API do GitHub. O PAT fica protegido nos Secrets, nunca exposto no codigo ou no historico.

## 7. Error Handling

| Cenario | Comportamento |
|---------|--------------|
| URL raw offline | Loga erro e continua com as demais listas |
| Playlist vazia ou mal formatada | Loga warning e continua |
| GitHub API rate limit | Frontend exibe mensagem de erro e sugere esperar |
| Workflow ja em execucao | Worker retorna erro; frontend exibe "Workflow ja esta rodando, aguarde" |
| Push falha (token sem permissao) | Action falha; logs mostram o erro |

## 8. Configuracao Inicial (one-time setup)

1. Criar repo de processamento (publico) com o script Python e workflow
2. Criar repo de frontend com GitHub Pages habilitado
3. Gerar PAT com permissoes `contents` e `workflows`
4. Adicionar PAT como secret `PAT_GH` no repo de processamento
5. Deploy do Cloudflare Worker com `wrangler secret put` para os 4 secrets
6. Configurar `config.json` com as 5 URLs raw
7. Atualizar `app.js` com a URL do Worker e o nome do repo de processamento
