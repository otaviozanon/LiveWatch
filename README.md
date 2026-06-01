# LiveWatch

Automated IPTV playlist merger that fetches raw M3U channel lists from GitHub, filters, deduplicates, and publishes merged playlists — all triggered from a terminal-style web dashboard.

## How It Works

1. **Fetch** — Downloads 5 raw `.m3u8`/`.m3u` playlists from a source repository
2. **Filter** — Keeps only channels (`group-title` starts with `"Canais"` for BR, `"CANAL"` for World)
3. **Deduplicate** — Removes duplicate URLs and renames channels with identical names but different URLs
4. **Publish** — Outputs both `.m3u` and `.m3u8` formats in organized folders and pushes back to this repository
5. **Dashboard** — Terminal-style frontend on GitHub Pages with one-click trigger, live progress bar, and PT/EN language toggle

## Architecture

```
[GitHub Pages] ---POST---> [Cloudflare Worker] ---GitHub API---> [GitHub Actions]
                                                                        |
                                                                    [merge.py]
                                                                        |
                                                             [LiveWatch-Playlist*.m3u8]
```

| Component | Technology              | Purpose                                                   |
| --------- | ----------------------- | --------------------------------------------------------- |
| Frontend  | Vanilla HTML/CSS/JS     | Terminal UI, progress bar, logs, PT/EN toggle             |
| Worker    | Cloudflare Workers      | Auth proxy — triggers workflow with profile, proxies logs |
| Pipeline  | Python + GitHub Actions | Fetches, filters, merges, commits                         |
| Hosting   | GitHub Pages            | Serves the dashboard                                      |

## Project Structure

```
LiveWatch/
├── .github/workflows/merge.yml      # CI pipeline (manual + cron every 6h)
├── scripts/
│   ├── merge.py                      # Core logic: fetch, filter, dedup, merge
│   └── config.json                   # Multi-profile playlist configuration
├── worker/
│   ├── src/index.js                  # Cloudflare Worker proxy
│   ├── wrangler.toml
│   └── package.json
├── docs/                             # Frontend (GitHub Pages source)
│   ├── index.html
│   ├── app.js
│   └── style.css
├── playlists/                        # Generated playlists (auto-committed by Actions)
│   ├── m3u/
│   │   ├── LiveWatch-PlaylistBR.m3u
│   │   └── LiveWatch-PlaylistWorld.m3u
│   └── m3u8/
│       ├── LiveWatch-PlaylistBR.m3u8
│       └── LiveWatch-PlaylistWorld.m3u8
└── .gitignore
```

## Profiles

The dashboard includes a dropdown to select between profiles:

| Profile | Sources                  | Filter                               | Output                         |
| ------- | ------------------------ | ------------------------------------ | ------------------------------ |
| Brasil  | `CanaisBR01–05.m3u8`     | `group-title` starts with `"Canais"` | `LiveWatch-PlaylistBR.m3u8`    |
| Global  | `Lista Mundial01–05.m3u` | `group-title` starts with `"CANAL"`  | `LiveWatch-PlaylistWorld.m3u8` |

## Filtering Logic

Duplicate handling:

- **Same URL** — First occurrence kept, rest removed
- **Same name, different URL** — Renamed with `[1]`, `[2]` suffixes

## License

MIT
