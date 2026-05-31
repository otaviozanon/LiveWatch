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
            name_match = re.search(r",\s*(.+)$", line)
            name = name_match.group(1).strip() if name_match else ""
            i += 1
            if i < len(lines) and lines[i].strip() and not lines[i].strip().startswith("#"):
                url = lines[i].strip()
                entries.append((group_title, name, url))
        i += 1
    return entries


if __name__ == "__main__":
    sample = '#EXTINF:-1 group-title="Canais | Globo",GLOBO SP\nhttp://example.com/globo.m3u8\n'
    result = parse_m3u(sample)
    assert len(result) == 1
    assert result[0] == ("Canais | Globo", "GLOBO SP", "http://example.com/globo.m3u8")
    print("parse_m3u: OK")
