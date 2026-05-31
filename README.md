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

## Filtering Logic

The merger only includes entries where `group-title` starts with `"Canais"` (case-insensitive). To change this, edit the `filter_group` value in `scripts/config.json`.

Duplicate handling:

- **Same URL** — First occurrence kept, rest removed
- **Same name, different URL** — Renamed with `[1]`, `[2]` suffixes

## License

MIT
