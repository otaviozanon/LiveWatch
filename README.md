# LiveWatch

Automated IPTV playlist merger that fetches 5 raw M3U channel lists from GitHub, filters, deduplicates, and publishes a single merged playlist — all triggered from a terminal-style web dashboard.

## How It Works

1. **Fetch** — Downloads 5 raw `.m3u8` playlists from a source repository
2. **Filter** — Keeps only channels (entries whose `group-title` starts with `"Canais"`)
3. **Deduplicate** — Removes duplicate URLs and renames channels with identical names but different URLs
4. **Publish** — Outputs `LiveWatch-Playlist.m3u8` and pushes it back to this repository
5. **Dashboard** — Terminal-style frontend on GitHub Pages with a one-click trigger and live progress bar

## Architecture

```
[GitHub Pages] ---POST---> [Cloudflare Worker] ---GitHub API---> [GitHub Actions]
                                                                       |
                                                                [merge.py]
                                                                       |
                                                              [LiveWatch-Playlist.m3u8]
```

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Frontend | Vanilla HTML/CSS/JS | Terminal UI, progress bar, logs |
| Worker | Cloudflare Workers | Auth proxy — triggers workflow, proxies logs |
| Pipeline | Python + GitHub Actions | Fetches, filters, merges, commits |
| Hosting | GitHub Pages | Serves the dashboard |

## Project Structure

```
LiveWatch/
├── .github/workflows/merge.yml      # CI pipeline (manual + cron every 6h)
├── scripts/
│   ├── merge.py                      # Core logic: fetch, filter, dedup, merge
│   └── config.json                   # Source playlist URLs
├── worker/
│   ├── src/index.js                  # Cloudflare Worker proxy
│   ├── wrangler.toml
│   └── package.json
├── docs/                             # Frontend (GitHub Pages source)
│   ├── index.html
│   ├── app.js
│   └── style.css
├── LiveWatch-Playlist.m3u8           # Merged output (auto-committed by Actions)
└── .gitignore
```

## Quick Start

### 1. Clone

```bash
git clone https://github.com/otaviozanon/LiveWatch.git
cd LiveWatch
```

### 2. Configure sources

Edit `scripts/config.json` with your 5 raw playlist URLs:

```json
{
  "sources": [
    "https://raw.githubusercontent.com/.../lista1.m3u8",
    "https://raw.githubusercontent.com/.../lista2.m3u8",
    "https://raw.githubusercontent.com/.../lista3.m3u8",
    "https://raw.githubusercontent.com/.../lista4.m3u8",
    "https://raw.githubusercontent.com/.../lista5.m3u8"
  ],
  "filter_group": "Canais"
}
```

### 3. Run locally

```bash
pip install requests
python scripts/merge.py
```

### 4. GitHub Actions

Create a repository secret `PAT_GH` (Personal Access Token) with `contents` and `workflows` scopes. The workflow:

- **Manual**: Triggered via the dashboard button
- **Automatic**: Runs every 6 hours via cron

### 5. Cloudflare Worker

```bash
cd worker
npm install
npx wrangler deploy
npx wrangler secret put GITHUB_PAT
npx wrangler secret put GITHUB_OWNER
npx wrangler secret put GITHUB_REPO
npx wrangler secret put WORKFLOW_ID
```

### 6. GitHub Pages

Enable Pages in repository Settings → Pages:
- Source: `main` branch
- Folder: `/docs`

### 7. Update frontend config

Edit `docs/app.js` with your Worker URL if different from the default.

## Trigger Interval

The default cron schedule in `.github/workflows/merge.yml` is every 6 hours:

```yaml
schedule:
  - cron: "0 */6 * * *"
```

Adjust the cron expression to change the interval.

## Filtering Logic

The merger only includes entries where `group-title` starts with `"Canais"` (case-insensitive). To change this, edit the `filter_group` value in `scripts/config.json`.

Duplicate handling:

- **Same URL** — First occurrence kept, rest removed
- **Same name, different URL** — Renamed with `[1]`, `[2]` suffixes

## License

MIT
