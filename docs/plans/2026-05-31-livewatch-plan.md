# LiveWatch Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a tool that fetches 5 IPTV raw playlists from GitHub, merges them (filtering only TV channels), deduplicates, and pushes the result back — with a terminal-style frontend on GitHub Pages and a Cloudflare Worker proxy.

**Architecture:** Single repo with 4 components — Python merge script, GitHub Actions workflow, Cloudflare Worker proxy, and vanilla HTML/CSS/JS frontend. The frontend calls the Worker, which triggers the GitHub Action; the Action runs the Python script and pushes the result.

**Tech Stack:** Python 3.11 (requests), GitHub Actions, Cloudflare Workers, vanilla HTML/CSS/JS.

---

### Task 1: Create project directory structure

**Objective:** Set up the folder layout for all components.

**Files:**
- Create: `scripts/merge.py` (empty)
- Create: `scripts/config.json` (empty)
- Create: `.github/workflows/merge.yml` (empty)
- Create: `worker/src/index.js` (empty)
- Create: `worker/wrangler.toml` (empty)
- Create: `frontend/index.html` (empty)
- Create: `frontend/style.css` (empty)
- Create: `frontend/app.js` (empty)

**Step 1: Create directories and empty files**

Run:
```powershell
New-Item -ItemType Directory -Path "scripts" -Force
New-Item -ItemType Directory -Path ".github\workflows" -Force
New-Item -ItemType Directory -Path "worker\src" -Force
New-Item -ItemType Directory -Path "frontend" -Force
New-Item -ItemType File -Path "scripts\merge.py" -Force
New-Item -ItemType File -Path "scripts\config.json" -Force
New-Item -ItemType File -Path ".github\workflows\merge.yml" -Force
New-Item -ItemType File -Path "worker\src\index.js" -Force
New-Item -ItemType File -Path "worker\wrangler.toml" -Force
New-Item -ItemType File -Path "frontend\index.html" -Force
New-Item -ItemType File -Path "frontend\style.css" -Force
New-Item -ItemType File -Path "frontend\app.js" -Force
```

**Step 2: Commit**

```bash
git add scripts/ .github/ worker/ frontend/
git commit -m "chore: create project directory structure"
```

---

### Task 2: Python — parse M3U entries

**Objective:** Write a function that parses an M3U/M3U8 string into a list of `(group_title, name, url)` tuples.

**Files:**
- Modify: `scripts/merge.py`

**Step 1: Write the parse function**

```python
import re


def parse_m3u(text):
    entries = []
    lines = text.strip().splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF"):
            attr_match = re.search(r'group-title="([^"]*)"', line, re.IGNORECASE)
            group_title = attr_match.group(1) if attr_match else ""
            name_match = re.search(r',\s*(.+)$', line)
            name = name_match.group(1).strip() if name_match else ""
            i += 1
            if i < len(lines) and lines[i].strip() and not lines[i].strip().startswith("#"):
                url = lines[i].strip()
                entries.append((group_title, name, url))
        i += 1
    return entries
```

**Step 2: Add a smoke test at the bottom**

```python
if __name__ == "__main__":
    sample = '#EXTINF:-1 group-title="Canais | Globo",GLOBO SP\nhttp://example.com/globo.m3u8\n'
    result = parse_m3u(sample)
    assert len(result) == 1
    assert result[0] == ("Canais | Globo", "GLOBO SP", "http://example.com/globo.m3u8")
    print("parse_m3u: OK")
```

**Step 3: Run and verify**

```powershell
python scripts\merge.py
```

Expected: `parse_m3u: OK`

**Step 4: Commit**

```bash
git add scripts/merge.py
git commit -m "feat: add m3u parser"
```

---

### Task 3: Python — fetch playlists from URLs

**Objective:** Add a function that downloads M3U content from a list of URLs.

**Files:**
- Modify: `scripts/merge.py`

**Step 1: Add fetch function**

```python
import requests


def fetch_playlist(url):
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text
```

**Step 2: Add fetch_all function**

```python
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
```

**Step 3: Commit**

```bash
git add scripts/merge.py
git commit -m "feat: add playlist fetch from URLs"
```

---

### Task 4: Python — filter by group-title

**Objective:** Filter entries where `group-title` starts with a given prefix.

**Files:**
- Modify: `scripts/merge.py`

**Step 1: Add filter function**

```python
def filter_by_group(entries, prefix):
    filtered = [(g, n, u) for g, n, u in entries if g.lower().startswith(prefix.lower())]
    return filtered
```

**Step 2: Add smoke test (temporary, appended to `__main__`)**

```python
    e = [("Canais | Globo", "GLOBO SP", "http://x"), ("Filmes", "Filme A", "http://y")]
    r = filter_by_group(e, "Canais")
    assert len(r) == 1
    assert r[0][0] == "Canais | Globo"
    print("filter_by_group: OK")
```

**Step 3: Run and verify**

```powershell
python scripts\merge.py
```

Expected: both smoke tests pass.

**Step 4: Commit**

```bash
git add scripts/merge.py
git commit -m "feat: add group-title filter"
```

---

### Task 5: Python — deduplicate by URL

**Objective:** Remove entries with identical URLs, keeping the first occurrence.

**Files:**
- Modify: `scripts/merge.py`

**Step 1: Add dedup_by_url function**

```python
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
```

**Step 2: Add smoke test**

```python
    e = [("A", "X", "http://same"), ("B", "Y", "http://same")]
    r = dedup_by_url(e)
    assert len(r) == 1
    print("dedup_by_url: OK")
```

**Step 3: Run and verify, then Commit**

```bash
python scripts\merge.py
git add scripts/merge.py
git commit -m "feat: add URL deduplication"
```

---

### Task 6: Python — rename duplicate names

**Objective:** For entries with the same name but different URLs, append ` [1]`, ` [2]` suffixes.

**Files:**
- Modify: `scripts/merge.py`

**Step 1: Add rename_duplicates function**

```python
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
```

**Note:** The counts are per-name, so the first occurrence keeps the original name, the second gets `[2]`, third gets `[3]`, etc.

**Step 2: Add smoke test**

```python
    e = [("C", "GLOBO SP", "http://a"), ("C", "GLOBO SP", "http://b")]
    r = rename_duplicates(e)
    assert r[0][1] == "GLOBO SP"
    assert r[1][1] == "GLOBO SP [2]"
    print("rename_duplicates: OK")
```

**Step 3: Run and verify, then Commit**

```bash
python scripts\merge.py
git add scripts/merge.py
git commit -m "feat: add duplicate name renaming"
```

---

### Task 7: Python — generate output M3U8

**Objective:** Write the final merged playlist to `playlist.m3u8`.

**Files:**
- Modify: `scripts/merge.py`

**Step 1: Add generate_playlist function**

```python
def generate_playlist(entries, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for group_title, name, url in entries:
            f.write(f'#EXTINF:-1 group-title="{group_title}",{name}\n')
            f.write(f"{url}\n")
    print(f"[LiveWatch] playlist.m3u8 gerada: {len(entries)} canais")
```

**Step 2: Add smoke test**

```python
    import os
    e = [("Canais | Globo", "GLOBO SP", "http://x")]
    generate_playlist(e, "test_out.m3u8")
    assert os.path.exists("test_out.m3u8")
    os.remove("test_out.m3u8")
    print("generate_playlist: OK")
```

**Step 3: Run and verify, then Commit**

```bash
python scripts\merge.py
git add scripts/merge.py
git commit -m "feat: add m3u8 output generator"
```

---

### Task 8: Python — wire together main()

**Objective:** Build the `main()` function that orchestrates fetch, filter, dedup, rename, and generate. Read config from `scripts/config.json`.

**Files:**
- Modify: `scripts/merge.py`

**Step 1: Replace the temporary `__main__` block with the real main**

```python
import json
import os


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    output_path = os.path.join(os.path.dirname(script_dir), "playlist.m3u8")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    all_results = fetch_all(config["sources"])
    
    all_entries = []
    for entries in all_results.values():
        all_entries.extend(entries)

    filtered = []
    for entries in all_results.values():
        filtered.extend(filter_by_group(entries, config["filter_group"]))

    print(f"[LiveWatch] Total canais (pos-filtro): {len(filtered)}")
    
    filtered = dedup_by_url(filtered)
    filtered = rename_duplicates(filtered)

    print(f"[LiveWatch] Total final: {len(filtered)} canais")
    generate_playlist(filtered, output_path)
    print("[LiveWatch] Playlist salva e pronta para commit!")


if __name__ == "__main__":
    main()
```

**Step 2: Run and verify structure only (no network)**

Run: `python scripts\merge.py`

Expected: fails because `config.json` is empty — this is OK for now. We'll create the config next.

**Step 3: Commit**

```bash
git add scripts/merge.py
git commit -m "feat: wire main() orchestration"
```

---

### Task 9: Create config.json

**Objective:** Create the configuration file with the 5 source URLs.

**Files:**
- Create: `scripts/config.json`

**Step 1: Write config.json**

```json
{
  "sources": [
    "https://raw.githubusercontent.com/REPO_OWNER/REPO_NAME/main/lista1.m3u",
    "https://raw.githubusercontent.com/REPO_OWNER/REPO_NAME/main/lista2.m3u",
    "https://raw.githubusercontent.com/REPO_OWNER/REPO_NAME/main/lista3.m3u",
    "https://raw.githubusercontent.com/REPO_OWNER/REPO_NAME/main/lista4.m3u",
    "https://raw.githubusercontent.com/REPO_OWNER/REPO_NAME/main/lista5.m3u"
  ],
  "filter_group": "Canais"
}
```

**Step 2: Commit**

```bash
git add scripts/config.json
git commit -m "chore: add playlist config template"
```

---

### Task 10: GitHub Actions workflow

**Objective:** Create the `merge.yml` workflow that runs on `workflow_dispatch` and schedule (6h).

**Files:**
- Modify: `.github/workflows/merge.yml`

**Step 1: Write the workflow**

```yaml
name: Merge Playlists

on:
  workflow_dispatch:
  schedule:
    - cron: "0 */6 * * *"

jobs:
  merge:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install requests

      - name: Run merge script
        run: python scripts/merge.py

      - name: Commit and push
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add playlist.m3u8
          if git diff --staged --quiet; then
            echo "No changes to commit"
          else
            git commit -m "chore: auto update playlist $(date -u +%Y-%m-%dT%H:%M:%SZ)"
            git push
          fi
```

**Step 2: Commit**

```bash
git add .github/workflows/merge.yml
git commit -m "feat: add GitHub Actions merge workflow"
```

---

### Task 11: Cloudflare Worker — wrangler config

**Objective:** Create the Wrangler configuration for the Worker.

**Files:**
- Modify: `worker/wrangler.toml`

**Step 1: Write wrangler.toml**

```toml
name = "livewatch-trigger"
main = "src/index.js"
compatibility_date = "2025-01-01"
```

**Step 2: Commit**

```bash
git add worker/wrangler.toml
git commit -m "feat: add Worker wrangler config"
```

---

### Task 12: Cloudflare Worker — trigger endpoint

**Objective:** Write the Worker that receives a POST, reads secrets, and dispatches the GitHub Actions workflow.

**Files:**
- Modify: `worker/src/index.js`

**Step 1: Write the Worker**

```javascript
export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type",
        },
      });
    }

    if (request.method !== "POST") {
      return new Response(JSON.stringify({ ok: false, error: "Use POST" }), {
        status: 405,
        headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      });
    }

    try {
      const url = `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/workflows/${env.WORKFLOW_ID}/dispatches`;
      const resp = await fetch(url, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${env.GITHUB_PAT}`,
          Accept: "application/vnd.github+json",
          "User-Agent": "LiveWatch",
        },
        body: JSON.stringify({ ref: "main" }),
      });

      if (resp.ok) {
        return new Response(JSON.stringify({ ok: true }), {
          headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
        });
      } else {
        const err = await resp.text();
        return new Response(JSON.stringify({ ok: false, error: err }), {
          status: 502,
          headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
        });
      }
    } catch (e) {
      return new Response(JSON.stringify({ ok: false, error: e.message }), {
        status: 500,
        headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      });
    }
  },
};
```

**Step 2: Commit**

```bash
git add worker/src/index.js
git commit -m "feat: add Worker trigger endpoint"
```

---

### Task 13: Frontend — HTML structure

**Objective:** Create the terminal-style page with the button and log container.

**Files:**
- Modify: `frontend/index.html`

**Step 1: Write index.html**

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LiveWatch</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div class="terminal">
    <div class="terminal-header">LiveWatch — Merge Playlist</div>
    <div class="terminal-body" id="logs">
      <div class="log info">[LiveWatch] Sistema pronto.</div>
      <div class="log dim">[LiveWatch] Aguardando acao...</div>
    </div>
    <div class="terminal-footer">
      <button class="btn" id="btn-update">&gt; ATUALIZAR PLAYLIST</button>
      <span class="hint">(ou aguarde o cron de 6h)</span>
    </div>
  </div>
  <script src="app.js"></script>
</body>
</html>
```

**Step 2: Commit**

```bash
git add frontend/index.html
git commit -m "feat: add frontend HTML structure"
```

---

### Task 14: Frontend — CSS terminal theme

**Objective:** Style the page with a dark terminal look using monospace font and log colors.

**Files:**
- Modify: `frontend/style.css`

**Step 1: Write style.css**

```css
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  background: #0d1117;
  color: #c9d1d9;
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
}

.terminal {
  width: 90%;
  max-width: 900px;
  border: 1px solid #30363d;
  border-radius: 8px;
  overflow: hidden;
  background: #0d1117;
}

.terminal-header {
  background: #161b22;
  padding: 10px 16px;
  font-weight: bold;
  color: #58a6ff;
  border-bottom: 1px solid #30363d;
}

.terminal-body {
  padding: 16px;
  min-height: 400px;
  max-height: 60vh;
  overflow-y: auto;
}

.terminal-footer {
  padding: 12px 16px;
  border-top: 1px solid #30363d;
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn {
  background: #238636;
  color: #fff;
  border: none;
  padding: 10px 24px;
  border-radius: 6px;
  font-family: inherit;
  font-size: 13px;
  cursor: pointer;
  font-weight: bold;
}

.btn:hover { background: #2ea043; }
.btn:disabled { background: #21262d; color: #484f58; cursor: not-allowed; }

.hint { color: #484f58; font-size: 11px; }

.log { padding: 2px 0; line-height: 1.6; }
.log.success { color: #3fb950; }
.log.info { color: #58a6ff; }
.log.warn { color: #f0883e; }
.log.action { color: #d2a8ff; }
.log.dim { color: #8b949e; }
.log.error { color: #f85149; }
```

**Step 2: Commit**

```bash
git add frontend/style.css
git commit -m "feat: add terminal CSS theme"
```

---

### Task 15: Frontend — JavaScript logic

**Objective:** Wire the button to the Worker, poll GitHub Actions logs, and render them in the terminal with colors.

**Files:**
- Modify: `frontend/app.js`

**Step 1: Write app.js**

```javascript
const WORKER_URL = "https://REPLACE_ME.workers.dev/trigger";
const GH_OWNER = "REPLACE_ME";
const GH_REPO = "REPLACE_ME";

const logsEl = document.getElementById("logs");
const btnEl = document.getElementById("btn-update");

function log(msg, cls = "info") {
  const div = document.createElement("div");
  div.className = `log ${cls}`;
  div.textContent = `[LiveWatch] ${msg}`;
  logsEl.appendChild(div);
  logsEl.scrollTop = logsEl.scrollHeight;
}

async function triggerWorkflow() {
  btnEl.disabled = true;
  log("Disparando workflow...", "action");

  try {
    const resp = await fetch(WORKER_URL, { method: "POST" });
    const data = await resp.json();

    if (!data.ok) {
      log(`Erro ao disparar: ${data.error}`, "error");
      btnEl.disabled = false;
      return;
    }

    log("Workflow iniciado. Aguardando inicio da action...", "success");
    await pollLogs();
  } catch (e) {
    log(`Falha: ${e.message}`, "error");
    btnEl.disabled = false;
  }
}

async function pollLogs() {
  let found = false;
  const maxAttempts = 120;
  const delay = 3000;

  for (let i = 0; i < maxAttempts; i++) {
    await sleep(delay);

    try {
      const runsResp = await fetch(
        `https://api.github.com/repos/${GH_OWNER}/${GH_REPO}/actions/runs?per_page=3`
      );
      const runsData = await runsResp.json();
      const run = runsData.workflow_runs[0];

      if (!run) continue;

      if (!found) {
        log(`Run ID: #${run.id} — Status: ${run.status}`, "dim");
        found = true;
      }

      if (run.status === "completed") {
        await fetchAndDisplayLogs(run.id);
        log(`Concluido. Sistema pronto para proxima acao.`, "success");
        btnEl.disabled = false;
        return;
      }
    } catch (e) {
      log(`Erro no polling: ${e.message}`, "error");
    }
  }

  log("Timeout — a action pode ainda estar rodando.", "warn");
  btnEl.disabled = false;
}

async function fetchAndDisplayLogs(runId) {
  try {
    const logsResp = await fetch(
      `https://api.github.com/repos/${GH_OWNER}/${GH_REPO}/actions/runs/${runId}/logs`
    );

    if (!logsResp.ok) {
      log("Nao foi possivel buscar logs (talvez ainda nao estejam disponiveis).", "warn");
      return;
    }

    const text = await logsResp.text();
    const lines = text.split("\n");

    for (const line of lines) {
      if (!line.trim()) continue;
      if (line.includes("[LiveWatch]")) {
        const msg = line.substring(line.indexOf("[LiveWatch]") + 12).trim();
        if (msg.includes("ERRO") || msg.includes("Falha")) {
          log(msg, "error");
        } else if (msg.includes("Removendo") || msg.includes("Renomeando") || msg.includes("Total")) {
          log(msg, "warn");
        } else if (msg.includes("gerada") || msg.includes("salva") || msg.includes("Concluido")) {
          log(msg, "success");
        } else if (msg.includes("Extraindo") || msg.includes("Encontrados")) {
          log(msg, "info");
        } else {
          log(msg, "dim");
        }
      }
    }
  } catch (e) {
    log(`Erro ao buscar logs: ${e.message}`, "error");
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

btnEl.addEventListener("click", triggerWorkflow);
```

**Step 2: Commit**

```bash
git add frontend/app.js
git commit -m "feat: add frontend JS logic"
```

---

### Task 16: Add .gitignore

**Objective:** Prevent committing temporary and environment-specific files.

**Files:**
- Create: `.gitignore`

**Step 1: Write .gitignore**

```
__pycache__/
*.pyc
.venv/
.env
.superpowers/
node_modules/
wrangler.toml
```

**Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: add .gitignore"
```

---

## Execution Order

```
Task 1   → Create directory structure
Task 2   → Python: parse M3U entries
Task 3   → Python: fetch playlists
Task 4   → Python: filter by group-title
Task 5   → Python: deduplicate by URL
Task 6   → Python: rename duplicate names
Task 7   → Python: generate output M3U8
Task 8   → Python: wire main()
Task 9   → Create config.json
Task 10  → GitHub Actions workflow
Task 11  → Worker: wrangler config
Task 12  → Worker: trigger endpoint
Task 13  → Frontend: HTML
Task 14  → Frontend: CSS
Task 15  → Frontend: JS
Task 16  → Add .gitignore
```

Total: 16 tasks. Dependencies are sequential within each component phase, but Python (2-9), Actions (10), Worker (11-12), and Frontend (13-15) are independent of each other and can be parallelized.

---

## Post-Implementation Setup

After all tasks are implemented and pushed to GitHub:

1. Enable GitHub Pages in repo Settings → Pages → Source: `main` branch, folder `/frontend`
2. Deploy Worker: `cd worker && npx wrangler secret put GITHUB_PAT` (plus owner, repo, workflow_id)
3. Deploy Worker: `npx wrangler deploy`
4. Update `frontend/app.js` with the real `WORKER_URL`, `GH_OWNER`, `GH_REPO`
5. Fill in real URLs in `scripts/config.json`
6. Add `PAT_GH` secret in repo Settings → Secrets → Actions
