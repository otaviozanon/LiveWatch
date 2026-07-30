"""Playlist and data fetching utilities."""

from __future__ import annotations

import re
from typing import Any

import requests


def fetch_playlist(url: str) -> str:
    """Download an M3U playlist from *url* and return its raw text."""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def fetch_all(urls: list[str]) -> dict[str, list[tuple[str, str, str]]]:
    """Download and parse multiple M3U playlist URLs."""
    from .parser import parse_m3u

    results: dict[str, list[tuple[str, str, str]]] = {}
    for i, url in enumerate(urls, 1):
        try:
            text = fetch_playlist(url)
            entries = parse_m3u(text)
            results[url] = entries
            print(f"[LiveWatch] [+] {url.rsplit('/', 1)[-1]} ({i}/{len(urls)})")
            print(f"[LiveWatch]    {len(entries)} entradas ({len(text.splitlines())} linhas)")
        except Exception as e:
            print(f"[LiveWatch] [!] {e}")
            results[url] = []
    return results


def fetch_json(url: str) -> Any:
    """Download and parse a JSON endpoint."""
    print(f"[LiveWatch] [+] {url.rsplit('/', 1)[-1]}")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    print(f"[LiveWatch]    {len(data)} registros")
    return data


def discover_github_sources(repo: str, pattern: str) -> list[str]:
    """List files in a GitHub repo matching *pattern* and return download URLs."""
    api_url = f"https://api.github.com/repos/{repo}/contents/"
    print(f"[LiveWatch] [+] Buscando {repo}")
    resp = requests.get(api_url, timeout=30)
    resp.raise_for_status()
    files = resp.json()
    regex = re.compile(pattern)
    matched = sorted(
        [f["download_url"] for f in files
         if f["type"] == "file" and regex.search(f["name"])],
        key=lambda u: u,
    )
    print(f"[LiveWatch]    {len(matched)} listas encontradas")
    return matched
