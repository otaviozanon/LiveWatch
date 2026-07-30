"""M3U/M3U8 playlist parser."""

import re


def parse_m3u(text: str) -> list[tuple[str, str, str]]:
    """Parse raw M3U/M3U8 text into ``[(group_title, name, url), ...]``."""
    entries: list[tuple[str, str, str]] = []
    lines = text.strip().splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF"):
            attr_match = re.search(r'group-title="([^"]*)"', line, re.IGNORECASE)
            group_title = attr_match.group(1) if attr_match else ""
            name_match = re.search(r",\s*(.+)$", line)
            name = name_match.group(1).strip() if name_match else ""
            name = re.sub(r"[¹²³]+", "", name)
            name = re.sub(r"^[A-Z]{2,3}:\s+", "", name)
            i += 1
            if i < len(lines) and lines[i].strip() and not lines[i].strip().startswith("#"):
                url = lines[i].strip()
                if name:
                    entries.append((group_title, name, url))
        i += 1
    return entries
