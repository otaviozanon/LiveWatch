"""
LiveWatch dead-channel filter.

Reads the unfiltered ``LiveWatch-PlaylistAll`` playlists, tests every stream
URL with an HTTP liveness check (ported from IPTVChecker's
``src-tauri/src/engine/checker.rs``), and rewrites the *same* files keeping
only the channels that respond. Dead channels are dropped in place — no new
playlist is created.

The liveness check follows HTTP redirects and HLS/DASH playlists, reads a
minimum amount of stream data (500KB direct / 128KB segment), and classifies
each channel as Alive / Geoblocked / Keep / Dead.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import time
from urllib.parse import urljoin, urlparse

import requests


# ── Constants (ported from IPTVChecker checker.rs) ─────────────────────────

MIN_DATA_THRESHOLD = 1024 * 500           # direct streams must deliver 500KB
PLAYLIST_SEGMENT_THRESHOLD = 1024 * 128   # HLS segments need only 128KB
MAX_PLAYLIST_DEPTH = 4
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
RETRYABLE_HTTP_STATUSES = {408, 425, 429, 500, 502, 503, 504}
GEOBLOCK_STATUSES = {403, 423, 426, 451}

VERDICT_ALIVE = "alive"
VERDICT_DEAD = "dead"
VERDICT_GEOBLOCKED = "geoblocked"
VERDICT_KEEP = "keep"  # untestable scheme (rtsp/rtmp) — keep conservatively

KEEP_VERDICTS = {VERDICT_ALIVE, VERDICT_GEOBLOCKED, VERDICT_KEEP}

USER_AGENT = "TiviMate/5.1.6 (Android 12)"

DEFAULT_BASE_NAME = "LiveWatch-PlaylistAll"


# ── URL classification helpers ─────────────────────────────────────────────

def _is_manifest(url: str, content_type: str) -> bool:
    path = urlparse(url).path.lower()
    ct = content_type.lower()
    return path.endswith(".m3u8") or "mpegurl" in ct


def _is_dash_manifest(url: str, content_type: str) -> bool:
    path = urlparse(url).path.lower()
    ct = content_type.lower()
    return path.endswith(".mpd") or "dash+xml" in ct or "xml+dash" in ct


def _classify_non_ok(status: int) -> tuple[str, str]:
    reason = f"HTTP {status}"
    if status in GEOBLOCK_STATUSES:
        return VERDICT_GEOBLOCKED, reason
    if status in RETRYABLE_HTTP_STATUSES:
        return "retry", reason
    return VERDICT_DEAD, reason


def _summarize_error(err: requests.exceptions.RequestException) -> str:
    if isinstance(err, requests.exceptions.Timeout):
        return "Timeout"
    low = str(err).lower()
    if "connection refused" in low:
        return "Connection refused"
    if "name or service not known" in low or "dns" in low:
        return "DNS failure"
    if "ssl" in low or "tls" in low or "certificate" in low:
        return "SSL/TLS error"
    if "too many redirects" in low or "redirect loop" in low:
        return "Redirect loop"
    return str(err)[:200]


def _is_retryable(err: requests.exceptions.RequestException) -> bool:
    return isinstance(
        err,
        (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.ChunkedEncodingError,
        ),
    )


# ── HLS manifest parsing ───────────────────────────────────────────────────

def _parse_variant_score(attrs: str) -> tuple[int, int, int]:
    resolution_pixels = 0
    average_bandwidth = 0
    bandwidth = 0
    for raw in attrs.split(","):
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip().upper()
        value = value.strip().strip('"').strip("'")
        if key == "RESOLUTION" and "x" in value:
            w, h = value.split("x", 1)
            if w.strip().isdigit() and h.strip().isdigit():
                resolution_pixels = int(w.strip()) * int(h.strip())
        elif key == "AVERAGE-BANDWIDTH" and value.isdigit():
            average_bandwidth = int(value)
        elif key == "BANDWIDTH" and value.isdigit():
            bandwidth = int(value)
    return resolution_pixels, average_bandwidth, bandwidth


def _extract_next_url(base_url: str, body: str) -> str | None:
    variants: list[tuple[tuple[int, int, int], str]] = []
    pending_score: tuple[int, int, int] | None = None
    first_uri: str | None = None

    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#EXT-X-STREAM-INF:"):
            pending_score = _parse_variant_score(line[len("#EXT-X-STREAM-INF:"):])
            continue
        if line.startswith("#"):
            continue
        resolved = urljoin(base_url, line)
        if pending_score is not None:
            variants.append((pending_score, resolved))
            pending_score = None
            continue
        if first_uri is None:
            first_uri = resolved

    if variants:
        variants.sort(key=lambda v: v[0])
        return variants[-1][1]
    return first_uri


# ── Stream verification ────────────────────────────────────────────────────

def _read_capped(resp: requests.Response, cap: int) -> bytes | None:
    """Read up to ``cap`` bytes. Returns None when the body exceeds the cap."""
    buf = bytearray()
    try:
        for chunk in resp.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            buf.extend(chunk)
            if len(buf) > cap:
                return None
    except requests.exceptions.RequestException:
        return b""
    return bytes(buf)


def _read_stream(resp: requests.Response, min_bytes: int) -> tuple[str, str | None]:
    bytes_read = 0
    try:
        for chunk in resp.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            bytes_read += len(chunk)
            if bytes_read >= min_bytes:
                resp.close()
                return VERDICT_ALIVE, None
    except requests.exceptions.RequestException as err:
        resp.close()
        return "retry", f"Stream read interrupted: {_summarize_error(err)}"
    resp.close()

    fallback = (
        min_bytes if min_bytes >= MIN_DATA_THRESHOLD else max(32768, min_bytes // 2)
    )
    if bytes_read >= fallback:
        return VERDICT_ALIVE, None
    return VERDICT_DEAD, f"No data (insufficient stream data: {bytes_read} bytes)"


def _verify(
    session: requests.Session,
    url: str,
    timeout: float,
    deadline: float,
    depth: int,
    visited: set[str],
) -> tuple[str, str | None]:
    if depth > MAX_PLAYLIST_DEPTH:
        return VERDICT_DEAD, "Playlist recursion limit exceeded"

    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return VERDICT_DEAD, "Timeout"
    effective_timeout = min(timeout, remaining)

    normalized = url.split("#", 1)[0]
    if normalized in visited:
        return VERDICT_DEAD, "Redirect loop"
    visited.add(normalized)

    try:
        resp = session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=(5, effective_timeout),
            stream=True,
            allow_redirects=True,
        )
    except requests.exceptions.RequestException as err:
        if _is_retryable(err):
            return "retry", _summarize_error(err)
        return VERDICT_DEAD, _summarize_error(err)

    status = resp.status_code
    if status != 200:
        resp.close()
        return _classify_non_ok(status)

    content_type = resp.headers.get("content-type", "")
    final_url = resp.url

    if _is_manifest(final_url, content_type) or _is_dash_manifest(final_url, content_type):
        body = _read_capped(resp, MAX_MANIFEST_BYTES)
        resp.close()
        if body is None:
            return VERDICT_DEAD, "Manifest body exceeded 8 MiB cap"
        if body == b"":
            return "retry", "Failed to read manifest body"
        text = body.decode("utf-8", errors="replace")
        if not text.strip():
            return "retry", "Empty manifest body"
        if _is_manifest(final_url, content_type) and not _is_dash_manifest(final_url, content_type):
            next_url = _extract_next_url(final_url, text)
            if next_url is None:
                return "retry", "No playable URI found in playlist"
            return _verify(session, next_url, timeout, deadline, depth + 1, visited)
        # DASH manifest present → alive
        return VERDICT_ALIVE, None

    min_bytes = MIN_DATA_THRESHOLD if depth == 0 else PLAYLIST_SEGMENT_THRESHOLD
    return _read_stream(resp, min_bytes)


def _run_attempts(
    session: requests.Session, url: str, timeout: float, retries: int
) -> tuple[str, str | None]:
    last_reason: str | None = None
    for _ in range(retries + 1):
        deadline = time.monotonic() + timeout * 3
        visited: set[str] = set()
        verdict, reason = _verify(session, url, timeout, deadline, 0, visited)
        if verdict in (VERDICT_ALIVE, VERDICT_GEOBLOCKED):
            return verdict, reason
        if verdict == "retry":
            last_reason = reason
            continue
        # Dead is final within an attempt loop (matches IPTVChecker).
        return VERDICT_DEAD, reason
    return VERDICT_DEAD, last_reason


def check_stream(
    url: str,
    timeout: float = 10.0,
    extended_timeout: float = 20.0,
    retries: int = 1,
) -> tuple[str, str | None, int]:
    scheme = urlparse(url).scheme.lower()
    if scheme not in ("http", "https"):
        return VERDICT_KEEP, "Unsupported scheme", 0

    started = time.monotonic()
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    try:
        verdict, reason = _run_attempts(session, url, timeout, retries)
        if verdict == VERDICT_DEAD and extended_timeout:
            second, second_reason = _run_attempts(
                session, url, extended_timeout, retries
            )
            if second != VERDICT_DEAD:
                verdict, reason = second, second_reason
            elif second_reason:
                reason = second_reason
    finally:
        session.close()

    latency_ms = int((time.monotonic() - started) * 1000)
    return verdict, reason, latency_ms


# ── Playlist parsing / rendering ───────────────────────────────────────────

def _parse_file(text: str) -> tuple[list[str], list[tuple[str, str, str, str, str]]]:
    """Return ``(header_lines, entries)``.

    Each entry is ``(extinf_line, url_line, group, name, url)`` with original
    lines preserved verbatim so attributes (tvg-id, tvg-name, …) survive.
    """
    lines = text.split("\n")
    header: list[str] = []
    entries: list[tuple[str, str, str, str, str]] = []
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("#EXTINF"):
            break
        if stripped:
            header.append(lines[i])
        i += 1

    while i < len(lines):
        line = lines[i].rstrip("\r")
        stripped = line.strip()
        if stripped.startswith("#EXTINF"):
            group = ""
            m = re.search(r'group-title="([^"]*)"', stripped, re.IGNORECASE)
            if m:
                group = m.group(1)
            name = ""
            m = re.search(r",\s*(.+)$", stripped)
            if m:
                name = m.group(1).strip()

            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if j < len(lines):
                url_line = lines[j].rstrip("\r")
                url = url_line.strip()
                if url and not url.startswith("#"):
                    entries.append((line, url_line, group, name, url))
                    i = j
        i += 1

    return header, entries


def _render(header: list[str], kept: list[tuple[str, str]]) -> str:
    parts = list(header) + [f"{extinf}\n{url}" for extinf, url in kept]
    return "\n".join(parts) + "\n"


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Filter dead channels from a playlist")
    parser.add_argument("--base-name", default=DEFAULT_BASE_NAME)
    parser.add_argument("--workers", type=int, default=64)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--extended-timeout", type=float, default=20.0)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--force", action="store_true", help="re-test even if unchanged")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(script_dir)
    playlists_dir = os.path.join(root, "playlists")
    base_name = args.base_name
    m3u_path = os.path.join(playlists_dir, "m3u", f"{base_name}.m3u")
    m3u8_path = os.path.join(playlists_dir, "m3u8", f"{base_name}.m3u8")
    # State lives OUTSIDE the repo (GitHub Actions cache) so it survives between
    # CI runs without polluting git history.
    state_dir = os.environ.get("FILTER_STATE_DIR", os.path.join(root, ".github", "filter-state"))
    os.makedirs(state_dir, exist_ok=True)
    state_path = os.path.join(state_dir, f"{base_name}.filter_state.json")
    report_path = os.path.join(state_dir, f"{base_name}.filter_report.csv")
    log_path = os.path.join(state_dir, f"{base_name}.filter.log")

    if not os.path.exists(m3u_path) or not os.path.exists(m3u8_path):
        print(f"[Filter] [!] Playlists not found, skipping", flush=True)
        return

    with open(m3u_path, encoding="utf-8") as f:
        m3u_text = f.read()
    with open(m3u8_path, encoding="utf-8") as f:
        m3u8_text = f.read()

    # Idempotency: skip re-testing an already-filtered list.
    state: dict = {}
    if os.path.exists(state_path):
        try:
            with open(state_path, encoding="utf-8") as f:
                state = json.load(f)
        except (ValueError, OSError):
            state = {}

    current_hash = hashlib.sha256(m3u8_text.encode("utf-8")).hexdigest()
    if not args.force and state.get("last_filtered_hash") == current_hash:
        print("[Filter] [i] Playlist unchanged since last filter, skipping", flush=True)
        return

    header_m3u, entries_m3u = _parse_file(m3u_text)
    header_m3u8, entries_m3u8 = _parse_file(m3u8_text)

    all_entries = entries_m3u + entries_m3u8
    unique_urls = list(dict.fromkeys(e[4] for e in all_entries))
    print(f"[Filter] [i] {len(entries_m3u)} entradas no .m3u, {len(entries_m3u8)} no .m3u8", flush=True)
    print(f"[Filter] [i] {len(unique_urls)} URLs únicas para testar", flush=True)

    results: dict[str, tuple[str, str | None, int]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(
                check_stream, u, args.timeout, args.extended_timeout, args.retries
            ): u
            for u in unique_urls
        }
        done = 0
        for fut in concurrent.futures.as_completed(futures):
            url = futures[fut]
            try:
                results[url] = fut.result()
            except Exception as err:  # noqa: BLE001 - keep the batch alive
                results[url] = (VERDICT_DEAD, f"Error: {err}", 0)
            done += 1
            if done % 250 == 0 or done == len(unique_urls):
                alive = sum(1 for v in results.values() if v[0] in KEEP_VERDICTS)
                print(f"[Filter] {done}/{len(unique_urls)} testados, {alive} vivos", flush=True)

    def apply(entries: list[tuple[str, str, str, str, str]]) -> tuple[list[tuple[str, str]], int]:
        kept: list[tuple[str, str]] = []
        dropped = 0
        for extinf, url_line, _group, _name, url in entries:
            verdict, _reason, _lat = results.get(url, (VERDICT_DEAD, "untested", 0))
            if verdict in KEEP_VERDICTS:
                kept.append((extinf, url_line))
            else:
                dropped += 1
        return kept, dropped

    kept_m3u, dropped_m3u = apply(entries_m3u)
    kept_m3u8, dropped_m3u8 = apply(entries_m3u8)

    new_m3u = _render(header_m3u, kept_m3u)
    new_m3u8 = _render(header_m3u8, kept_m3u8)

    with open(m3u_path, "w", encoding="utf-8") as f:
        f.write(new_m3u)
    with open(m3u8_path, "w", encoding="utf-8") as f:
        f.write(new_m3u8)

    state = {
        "last_filtered_hash": hashlib.sha256(new_m3u8.encode("utf-8")).hexdigest(),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total": len(entries_m3u),
        "kept": len(kept_m3u),
        "dropped": dropped_m3u,
    }
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    # Report CSV: one row per channel with its verdict + reason.
    with open(report_path, "w", encoding="utf-8", newline="") as f:
        f.write("Status,Group,Channel Name,URL,Reason,LatencyMs\n")
        for extinf, _url_line, group, name, url in entries_m3u:
            verdict, reason, lat = results.get(url, (VERDICT_DEAD, "untested", 0))
            label = "Alive" if verdict == VERDICT_ALIVE else verdict.capitalize()
            f.write(f'{label},"{group}","{name}","{url}","{reason or ""}",{lat}\n')

    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"total={state['total']} kept={state['kept']} dropped={state['dropped']}\n")

    print(f"[Filter] [+] Total: {len(entries_m3u)} | Vivos: {len(kept_m3u)} | Removidos: {dropped_m3u}", flush=True)
    print("[Filter] [+] Playlists filtradas salvas no lugar", flush=True)


if __name__ == "__main__":
    main()
