"""Entry filtering and category remapping functions."""

from __future__ import annotations

import re
import unicodedata


# ── Normalization utilities ─────────────────────────────────────────────────

def strip_accents(text: str) -> str:
    """Remove diacritical marks (e.g. 'São' → 'Sao')."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize(text: str) -> str:
    """Full normalization: accents stripped, smart quotes fixed, lowercase."""
    t = strip_accents(text)
    t = t.replace("\u0091", "'").replace("\u0092", "'")
    t = t.replace("\u0093", '"').replace("\u0094", '"')
    t = t.replace("\u2018", "'").replace("\u2019", "'")
    t = t.replace("\u201c", '"').replace("\u201d", '"')
    return t.lower()


# ── Group filtering ────────────────────────────────────────────────────────

def filter_by_group(
    entries: list[tuple[str, str, str]], include_keywords: str | list[str],
) -> list[tuple[str, str, str]]:
    """Keep entries whose *group_title* contains any of *include_keywords*.
    Entries with empty group-title always pass through (files without group-title)."""
    if not include_keywords:
        return entries
    if isinstance(include_keywords, str):
        include_keywords = [include_keywords]
    result: list[tuple[str, str, str]] = []
    removed = 0
    for group_title, name, url in entries:
        if not group_title:
            result.append((group_title, name, url))
        elif any(kw.lower() in group_title.lower() for kw in include_keywords):
            result.append((group_title, name, url))
        else:
            removed += 1
    if removed:
        print(f"[LiveWatch] [-] {removed} grupos ignorados")
    return result


def filter_by_group_exclude(
    entries: list[tuple[str, str, str]], exclude_keywords: list[str]
) -> list[tuple[str, str, str]]:
    """Remove entries whose *group_title* contains any of the *exclude_keywords*."""
    if not exclude_keywords:
        return entries
    result: list[tuple[str, str, str]] = []
    removed = 0
    for group_title, name, url in entries:
        gt = normalize(group_title)
        exclude = any(
            normalize(kw) in gt for kw in exclude_keywords
        )
        if exclude:
            removed += 1
        else:
            result.append((group_title, name, url))
    if removed:
        print(f"[LiveWatch] [-] {removed} grupos excluidos")
    return result


def filter_by_group_keep(
    entries: list[tuple[str, str, str]], group_rules: dict[str, list[str]]
) -> list[tuple[str, str, str]]:
    """
    Within groups matching *group_rules* keys, keep only entries whose name
    matches one of the corresponding patterns.  All other groups pass through.
    """
    if not group_rules:
        return entries
    result: list[tuple[str, str, str]] = []
    removed = 0
    for group_title, name, url in entries:
        keep = True
        for group_key, name_patterns in group_rules.items():
            if group_key.lower() in group_title.lower():
                keep = any(pat.lower() in name.lower() for pat in name_patterns)
                break
        if keep:
            result.append((group_title, name, url))
        else:
            removed += 1
    if removed:
        print(f"[LiveWatch] [-] {removed} canais filtrados (grupo)")
    return result


# ── URL / name filtering ───────────────────────────────────────────────────

def filter_by_url(
    entries: list[tuple[str, str, str]], url_exclude_patterns: list[str]
) -> list[tuple[str, str, str]]:
    """Remove entries whose URL contains any of the *url_exclude_patterns*."""
    if not url_exclude_patterns:
        return entries
    result: list[tuple[str, str, str]] = []
    removed = 0
    for group_title, name, url in entries:
        exclude = any(pat.lower() in url.lower() for pat in url_exclude_patterns)
        if exclude:
            removed += 1
        else:
            result.append((group_title, name, url))
    if removed:
        print(f"[LiveWatch] [-] {removed} URLs bloqueadas")
    return result


def filter_excluded(
    entries: list[tuple[str, str, str]], exclude_keywords: list[str]
) -> list[tuple[str, str, str]]:
    """Remove entries whose *name* contains any of the *exclude_keywords*."""
    if not exclude_keywords:
        return entries
    result: list[tuple[str, str, str]] = []
    removed = 0
    for group_title, name, url in entries:
        name_norm = normalize(name)
        exclude = any(
            normalize(kw) in name_norm for kw in exclude_keywords
        )
        if exclude:
            removed += 1
        else:
            result.append((group_title, name, url))
    if removed:
        print(f"[LiveWatch] [-] {removed} canais indesejados")
    return result


# ── Remapping ──────────────────────────────────────────────────────────────

def remap_by_group(
    entries: list[tuple[str, str, str]],
    group_remap: dict[str, str],
) -> list[tuple[str, str, str]]:
    """Reassign entries to target categories based on group-title keyword matching."""
    if not group_remap:
        return entries
    result: list[tuple[str, str, str]] = []
    remapped = 0
    for group_title, name, url in entries:
        new_group = group_title
        for src_pattern, target_group in group_remap.items():
            if src_pattern.lower() in group_title.lower():
                new_group = target_group
                remapped += 1
                break
        result.append((new_group, name, url))
    if remapped:
        print(f"[LiveWatch] [*] {remapped} grupos remapeados")
    return result


def remap_by_name(
    entries: list[tuple[str, str, str]],
    name_remap: dict[str, list[str]],
    remap_from_groups: list[str] | None = None,
) -> list[tuple[str, str, str]]:
    """Reassign entries to target categories based on channel name patterns."""
    if not name_remap:
        return entries
    result: list[tuple[str, str, str]] = []
    remapped = 0
    for group_title, name, url in entries:
        new_group = group_title
        if remap_from_groups is None or any(
            g.lower() in group_title.lower() for g in remap_from_groups
        ):
            for target_group, patterns in name_remap.items():
                matched = False
                for pat in patterns:
                    if normalize(pat) in normalize(name):
                        new_group = target_group
                        remapped += 1
                        matched = True
                        break
                if matched:
                    break
        result.append((new_group, name, url))
    if remapped:
        print(f"[LiveWatch] [*] {remapped} canais recategorizados")
    return result


# ── Dedup / cleanup ────────────────────────────────────────────────────────

def dedup_by_url(
    entries: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    """Remove duplicate entries (same URL), keeping first occurrence."""
    seen: set[str] = set()
    result: list[tuple[str, str, str]] = []
    removed = 0
    for entry in entries:
        url = entry[2]
        if url not in seen:
            seen.add(url)
            result.append(entry)
        else:
            removed += 1
    if removed:
        print(f"[LiveWatch] [-] {removed} duplicatas URL")
    return result


def rename_duplicates(
    entries: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    """
    Append ``[2]``, ``[3]``, ... suffixes when the same channel name appears
    with multiple different URLs.
    """
    name_counts: dict[str, int] = {}
    renamed = 0
    result: list[tuple[str, str, str]] = []
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
        print(f"[LiveWatch] [*] {renamed} conflitos renomeados")
    return result


def cleanup_channel_names(
    entries: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    """Normalize channel names for consistency and dedup."""
    result: list[tuple[str, str, str]] = []
    for group_title, name, url in entries:
        name = name.strip()
        name = re.sub(r"^[A-Z]{2,3}:\s+", "", name)
        name = re.sub(r"^\d+\s*\|\s*", "", name)
        name = name.upper()
        name = re.sub(r"\b4K\b", "H265", name)
        if "H265" in name and "FHD" in name:
            name = re.sub(r"\bFHD\b", "", name)
        name = re.sub(r"(\bH265\b\s*)+", "H265 ", name)
        name = re.sub(r"\s+", " ", name).strip()
        result.append((group_title, name, url))
    changed = sum(1 for (_, a, _), (_, b, _) in zip(entries, result) if a != b)
    if changed:
        print(f"[LiveWatch] [*] {changed} nomes normalizados")
    return result
