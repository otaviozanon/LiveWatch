# LiveWatch

Automated IPTV playlist merger — fetches, filters, categorizes and publishes playlists from multiple sources. Triggered via web dashboard or cron.

<p align="center">
  <a href="https://ozlivewatch.pages.dev/"><strong>Live Watch</strong></a>
</p>

## Quick Start

1. Install **Simple M3U Player** (Microsoft Store)
2. Copy a playlist URL from the [dashboard](https://ozlivewatch.pages.dev)
3. Add to Simple M3U Player and save

## Quick Links

| Resource          | URL                                           |
| ----------------- | --------------------------------------------- |
| Dashboard         | https://ozlivewatch.pages.dev                 |
| Playlist BR       | https://ozlivewatch.pages.dev/p/brasil.m3u8   |
| Playlist IPTV-ORG | https://ozlivewatch.pages.dev/p/iptv-org.m3u8 |
| Playlist Todos    | https://ozlivewatch.pages.dev/p/all.m3u8      |
| EPG BR            | https://ozlivewatch.pages.dev/e/BR            |
| EPG US            | https://ozlivewatch.pages.dev/e/US            |

## Profiles

| Profile  | Type      | Sources                      | Output                           |
| -------- | --------- | ---------------------------- | -------------------------------- |
| Brasil   | M3U       | `CanaisBR*.m3u8` (GitHub)    | `LiveWatch-PlaylistBR.m3u8`      |
| IPTV-ORG | iptv_api  | iptv-org API (BR only)       | `LiveWatch-PlaylistIPTVORG.m3u8` |
| ManoTV   | M3U       | `ManoTV.m3u`                 | `LiveWatch-PlaylistManoTV.m3u8`  |
| Todos    | merge_all | Merges all profiles above    | `LiveWatch-PlaylistAll.m3u8`     |

## Filtering

- 26 categories with automatic channel remapping
- Adult/NSFW, radios, series episodes, movie/series streams removed
- Duplicates: same URL → first kept; same name + different URL → `[2]`, `[3]` suffix
- Sul-only broadcast affiliates (RPC, RBS, NSC, PR/RS/SC)

## License

GPL-3.0
