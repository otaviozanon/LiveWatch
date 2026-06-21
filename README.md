# LiveWatch

Automated IPTV playlist merger — discovers sources via GitHub API, fetches M3U/JSON playlists, filters unwanted content, deduplicates, and publishes merged playlists. Triggered from a terminal-style web dashboard or cron.

https://ozlivewatch.pages.dev

## Quick Start (Windows)

1. Install **Simple M3U Player** from the Microsoft Store.
2. Open Simple M3U Player.
3. From the LiveWatch dashboard, copy the URL of the desired playlist (`.m3u` or `.m3u8`) — **Brasil**, **Global**, **IPTV-ORG**, or **Todos**.
4. In Simple M3U Player, add a new playlist and paste the LiveWatch URL.
5. Save and watch channels kept up to date by LiveWatch.

## Quick Links

| Resource | URL |
|---|---|
| Dashboard | https://ozlivewatch.pages.dev |
| Playlist BR | https://ozlivewatch.pages.dev/p/brasil.m3u8 |
| Playlist Global | https://ozlivewatch.pages.dev/p/global.m3u8 |
| Playlist IPTV-ORG | https://ozlivewatch.pages.dev/p/iptv-org.m3u8 |
| Playlist All | https://ozlivewatch.pages.dev/p/all.m3u8 |
| EPG BR | https://ozlivewatch.pages.dev/e/BR |
| EPG US | https://ozlivewatch.pages.dev/e/US |

## How It Works

1. **Discover** — Auto-discovers source files from GitHub repos via API (no manual URL maintenance)
2. **Fetch** — Downloads M3U playlists and JSON APIs (iptv-org channels + streams)
3. **Filter** — Keeps only channel entries, excludes adult content, radios, and unwanted keywords
4. **Deduplicate** — Same URL = kept once; same name/different URL = renamed with `[2]`, `[3]` suffixes
5. **Sort** — Alphabetical order by channel name, single unified group-title per profile
6. **Publish** — Outputs both `.m3u` and `.m3u8` in organized folders, committed back to the repo
7. **Dashboard** — Terminal-style frontend with one-click trigger, live progress, PT/EN toggle, LOGS and EPG tabs

## Architecture

```
[Cloudflare Pages] ---POST---> [GitHub API] ---> [GitHub Actions]
       |                                                  |
  frontend + API                                    [merge.py]
  (_worker.js)                                          |
                                                   [Playlists]
```

| Component | Technology | Purpose |
| --------- | ---------- | ------- |
| Frontend + API | Cloudflare Pages + Functions | Serves dashboard and proxies all API calls (trigger, logs, playlists, EPG) |
| Pipeline | Python + GitHub Actions | Fetches, filters, merges, commits |

## Project Structure

```
LiveWatch/
├── .github/workflows/merge.yml         # CI pipeline (manual + cron every 6h)
├── scripts/
│   ├── merge.py                         # Core logic: discover, fetch, filter, dedup, merge
│   ├── epg.py                           # EPG channel ID matching
│   └── config.json                      # Multi-profile config (M3U, iptv_api, merge_all)
├── docs/                                # Frontend + Pages Worker
│   ├── _worker.js                       # Cloudflare Pages Functions (API + static serving)
│   ├── index.html
│   ├── app.js
│   └── style.css
├── playlists/                           # Generated playlists (auto-committed by Actions)
│   ├── m3u/
│   └── m3u8/
└── .gitignore
```

## Profiles

| Profile  | Type      | Sources                                            | Output                           |
| -------- | --------- | -------------------------------------------------- | -------------------------------- |
| Brasil   | M3U       | `CanaisBR*.m3u8` (auto-discovered from GitHub)     | `LiveWatch-PlaylistBR.m3u8`      |
| Global   | M3U       | `Lista Mundial*.m3u` (auto-discovered from GitHub) | `LiveWatch-PlaylistWorld.m3u8`   |
| IPTV-ORG | iptv_api  | iptv-org channels.json + streams.json (BR only)    | `LiveWatch-PlaylistIPTVORG.m3u8` |
| Todos    | merge_all | Merges all profiles above into a single playlist   | `LiveWatch-PlaylistAll.m3u8`     |

Sources are auto-discovered via GitHub API, so new files added to the source repo are picked up automatically — no manual config updates needed.

## Filtering

**Duplicate handling:**

- Same URL → first occurrence kept, rest removed
- Same name, different URL → renamed with `[2]`, `[3]`, etc.

**Content filtering:**

- Adult/NSFW channels
- Radio stations
- Explicit keywords in channel names

## License

MIT
