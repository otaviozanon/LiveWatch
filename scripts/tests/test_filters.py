"""Unit tests for the core filter pipeline."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.filters import (
    cleanup_channel_names,
    dedup_by_url,
    filter_by_group,
    filter_by_group_exclude,
    filter_by_group_keep,
    filter_by_url,
    filter_excluded,
    normalize,
    remap_by_group,
    remap_by_name,
    rename_duplicates,
    strip_accents,
)
from core.parser import parse_m3u
from core.output import normalize_group_title


class TestNormalization(unittest.TestCase):
    def test_strip_accents(self):
        self.assertEqual(strip_accents("São Paulo"), "Sao Paulo")
        self.assertEqual(strip_accents("Câmeras Escondidas"), "Cameras Escondidas")

    def test_normalize_case_and_accents(self):
        self.assertEqual(normalize("A&E HD"), "a&e hd")
        self.assertEqual(normalize("GloboSat"), "globosat")
        self.assertEqual(normalize("Câmeras"), "cameras")


class TestParseM3U(unittest.TestCase):
    def test_parse_standard_entry(self):
        text = '#EXTM3U\n#EXTINF:-1 group-title="CANAIS | ESPORTES",ESPN HD\nhttp://example.com/stream.ts'
        entries = parse_m3u(text)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0], ("CANAIS | ESPORTES", "ESPN HD", "http://example.com/stream.ts"))

    def test_parse_entry_without_group(self):
        text = '#EXTM3U\n#EXTINF:-1,A&E 4K\nhttp://example.com/stream.ts'
        entries = parse_m3u(text)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0], ("", "A&E 4K", "http://example.com/stream.ts"))

    def test_parse_strips_br_prefix(self):
        text = '#EXTM3U\n#EXTINF:-1 group-title="LAME | BRAZIL VIP",BR: A&E\nhttp://example.com/stream.ts'
        entries = parse_m3u(text)
        self.assertEqual(entries[0][1], "A&E")

    def test_parse_strips_unicode_superscript(self):
        text = '#EXTM3U\n#EXTINF:-1,TV Globo\u00b2\nhttp://example.com/stream.ts'
        entries = parse_m3u(text)
        self.assertEqual(entries[0][1], "TV Globo")


class TestFilters(unittest.TestCase):
    def setUp(self):
        self.entries = [
            ("CANAIS | ESPORTES", "ESPN HD", "http://a.com/1.ts"),
            ("CANAIS | FILMES", "HBO HD", "http://a.com/2.ts"),
            ("", "Globo SP FHD", "http://b.com/3.ts"),  # no group
            ("ADULTOS", "XXX HD", "http://bad.com/1.ts"),
            ("CANAIS | GLOBO", "RPC CURITIBA", "http://a.com/4.ts"),
            ("CANAIS | SBT", "SBT NORDESTE", "http://a.com/5.ts"),
        ]

    def test_filter_by_group_list(self):
        result = filter_by_group(self.entries, ["CANAIS"])
        self.assertEqual(len(result), 5)
        self.assertNotIn(("ADULTOS", "XXX HD", "http://bad.com/1.ts"), result)

    def test_filter_by_group_exclude(self):
        result = filter_by_group_exclude(self.entries, ["ADULTOS"])
        self.assertEqual(len(result), 5)

    def test_filter_by_url(self):
        result = filter_by_url(self.entries, ["bad.com"])
        self.assertEqual(len(result), 5)

    def test_filter_excluded(self):
        result = filter_excluded(self.entries, ["XXX"])
        self.assertEqual(len(result), 5)
        names = {n for _, n, _ in result}
        self.assertNotIn("XXX HD", names)

    def test_filter_by_group_keep(self):
        rules = {"GLOBO": ["RPC"], "SBT": ["SBT"]}
        result = filter_by_group_keep(self.entries, rules)
        # RPC CURITIBA in GLOBO group is kept
        # SBT NORDESTE in SBT group is NOT kept ("SBT" pattern — "sbt nordeste" contains "sbt")
        self.assertIn(("CANAIS | GLOBO", "RPC CURITIBA", "http://a.com/4.ts"), result)

    def test_remap_by_group(self):
        group_remap = {"ESPORTES": "ESPORTES", "FILMES": "FILMES E SERIES"}
        result = remap_by_group(self.entries, group_remap)
        groups = {g for g, _, _ in result}
        self.assertIn("FILMES E SERIES", groups)
        self.assertIn("ESPORTES", groups)

    def test_remap_by_name(self):
        name_remap = {"NOTICIAS": ["Globo News", "CNN"]}
        entries = [("CANAIS | VARIEDADES", "GLOBO NEWS HD", "http://a.com/1.ts")]
        result = remap_by_name(entries, name_remap)
        self.assertEqual(result[0][0], "NOTICIAS")

    def test_remap_by_name_first_match_wins(self):
        name_remap = {"BAND": ["BAND"], "ABERTOS": ["TV C"]}
        entries = [("CANAIS | BAND", "BAND TV CAPIXABA ES HD", "http://a.com/1.ts")]
        result = remap_by_name(entries, name_remap)
        self.assertEqual(result[0][0], "BAND")

    def test_dedup_by_url(self):
        entries = [
            ("A", "Canal 1", "http://dup.com/1.ts"),
            ("B", "Canal 1", "http://dup.com/1.ts"),  # same URL
            ("C", "Canal 2", "http://dup.com/2.ts"),
        ]
        result = dedup_by_url(entries)
        self.assertEqual(len(result), 2)

    def test_rename_duplicates(self):
        entries = [
            ("A", "CANAL", "http://a.com/1.ts"),
            ("B", "CANAL", "http://a.com/2.ts"),
        ]
        result = rename_duplicates(entries)
        self.assertEqual(result[1][1], "CANAL [2]")

    def test_cleanup_channel_names(self):
        entries = [("A", "10 | CANAL BRASIL HD", "http://a.com/1.ts")]
        result = cleanup_channel_names(entries)
        self.assertEqual(result[0][1], "CANAL BRASIL HD")


class TestOutput(unittest.TestCase):
    def test_normalize_group_title(self):
        self.assertEqual(normalize_group_title("CANAIS | ESPORTES", "BR"), "BR | ESPORTES")
        self.assertEqual(normalize_group_title("UNKNOWN CATEGORY", "BR"), "BR | NOVOS")
        self.assertEqual(normalize_group_title("", "BR"), "BR | NOVOS")

    def test_normalize_group_title_remap(self):
        # FILMES & SERIES → FILMES E SERIES
        self.assertEqual(normalize_group_title("CANAIS | FILMES & SERIES", "BR"), "BR | FILMES E SERIES")


class TestPipelineIntegration(unittest.TestCase):
    """End-to-end test loading real config and running through pipeline."""

    @classmethod
    def setUpClass(cls):
        config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            cls.config = json.load(f)
        cls.profile = cls.config["profiles"]["brasil"]

    def test_config_loads(self):
        self.assertIn("filter_group", self.profile)
        self.assertIn("group_remap", self.profile)
        self.assertIn("name_remap", self.profile)

    def test_config_no_empty_patterns(self):
        for cat, patterns in self.profile["name_remap"].items():
            for pat in patterns:
                self.assertTrue(pat.strip(), f"Empty pattern in category {cat}")

    def test_config_group_remap_keys_ordered(self):
        remap = self.profile["group_remap"]
        # Specific patterns should come before generic
        keys = list(remap.keys())
        if "Globo" in keys and "Globos Regionais" in keys:
            self.fail("Should use 'Globo' to match both, not separate keys")

    def test_run_pipeline_on_sample(self):
        """Run the full fetch_profile_entries on a small sample to catch crashes."""
        from merge import fetch_profile_entries

        entries = fetch_profile_entries(self.profile)
        self.assertGreater(len(entries), 0, "Pipeline returned zero entries!")


if __name__ == "__main__":
    unittest.main()
