"""
EPG module for LiveWatch.
Downloads EPG channel IDs from epgshare01.online and provides
fuzzy matching to map LiveWatch channel names to XMLTV tvg-id values.

Does NOT modify the existing merge pipeline - used as an optional enrichment step.
"""
import gzip
import re
import unicodedata
from io import BytesIO
from xml.etree import ElementTree as ET

import requests

# ── EPG data sources ──────────────────────────────────────────────────────
EPG_BASE = "https://epgshare01.online/epgshare01"
GLOBETV_BASE = "https://raw.githubusercontent.com/globetvapp/epg/main"

# Country code → list of epgshare01 file names
EPG_COUNTRY_SOURCES = {
    "BR": ["epg_ripper_BR1.xml.gz", "epg_ripper_BR2.xml.gz"],
    "US": ["epg_ripper_US2.xml.gz"],
}

# Country code → list of globetvapp/epg file paths (relative to repo root)
GLOBETV_COUNTRY_SOURCES = {
    "BR": [
        "Brazil/brazil1.xml.gz",
        "Brazil/brazil2.xml.gz",
        "Brazil/brazil3.xml.gz",
        "Brazil/brazil4.xml.gz",
    ],
    "US": [
        "Usa/usa1.xml.gz",
        "Usa/usa2.xml.gz",
        "Usa/usa3.xml.gz",
        "Usa/usa4.xml.gz",
    ],
}

# Alternative EPG URLs for x-tvg-url header (not used for ID matching)
# These are listed in the M3U header so IPTV apps can use them as fallback.
EXTRA_EPG_URLS = {
    "BR": [
        "https://www.free-epg.de/api/epg?country=BR",
    ],
    "US": [
        "https://www.free-epg.de/api/epg?country=US",
    ],
}

# Default EPG sources used when no specific countries are configured
EPG_SOURCES_DEFAULT = [
    f"{EPG_BASE}/{f}" for f in EPG_COUNTRY_SOURCES["BR"]
]

# ── Manual mapping: LiveWatch canonical name → EPG tvg-id ──────────────────
# These are the definitive mappings for the most important channels.
# The EPG IDs come from epgshare01.online (BR1/BR2).
MANUAL_TVG_MAP = {
    # ─── TV Aberta ───
    "GLOBO": "São.Paulo/SP..Globo.br",
    "SBT": "São.Paulo/SP..SBT.br",
    "RECORD": "São.Paulo/SP..Record.br",
    "BAND": "São.Paulo/SP..Band.br",
    "REDE TV": "São.Paulo/SP..Rede.TV.br",
    "CULTURA": "São.Paulo/SP..Cultura.br",
    "GAZETA": "São.Paulo/SP..Gazeta.br",
    "FUTURA": "São.Paulo/SP..Futura.br",
    "REDE BRASIL": "Rede.Brasil.HD.br",
    "REDE VIDA": "São.Paulo/SP..Rede.Vida.br",
    "REDE GOSPEL": "São.Paulo/SP..Rede.Gospel.br",
    "TV BRASIL": "São.Paulo/SP..TV.Brasil.br",
    "TV CAMARA": "São.Paulo/SP..TV.Câmara.br",
    "TV SENADO": "São.Paulo/SP..TV.Senado.br",
    "TV JUSTICA": "São.Paulo/SP..TV.Justiça.br",
    "TV ESCOLA": "São.Paulo/SP..TV.Escola.br",
    "TV APARECIDA": "São.Paulo/SP...TV.Aparecida.(espelho).br",
    "CANAL DO BOI": "São.Paulo/SP..Canal.do.Boi.br",
    "CANAL RURAL": "São.Paulo/SP..Canal.Rural.br",
    "TERRA VIVA": "São.Paulo/SP..Terra.Viva.br",
    "RECORD NEWS": "São.Paulo/SP.Record.News.br",
    "REDE 21": "São.Paulo/SP..Rede.21.br",
    "MEGA TV": "São.Paulo/SP..Mega.TV.br",
    "PLAY TV": "São.Paulo/SP..Play.TV.br",
    "RIT TV": "São.Paulo/SP..RIT.TV.br",
    "TV GAZETA": "São.Paulo/SP..Gazeta.br",
    "TV PAI ETERNO": "São.Paulo/SP..TV.Pai.Eterno.br",

    # ─── Canais de Notícia ───
    "GLOBO NEWS": "São.Paulo/SP..GloboNews.br",
    "BAND NEWS": "São.Paulo/SP..Band.News.br",
    "CNN BRASIL": "São.Paulo/SP..CNN.Brasil.br",
    "CNN INTERNATIONAL": "São.Paulo/SP..CNN.International.br",
    "BBC WORLD NEWS": "São.Paulo/SP..BBC.World.News.br",
    "BLOOMBERG": "São.Paulo/SP..Bloomberg.TV.br",
    "JOVEM PAN NEWS": "Jovem.Pan.News.br",
    "FRANCE 24": "FRANCE.24.HD.br",

    # ─── HBO / MAX ───
    "HBO": "HBO.br",
    "HBO 2": "HBO.2.br",
    "HBO FAMILY": "HBO.Family.br",
    "HBO SIGNATURE": "HBO.Signature.br",
    "HBO XTREME": "HBO.Xtreme.br",
    "HBO MUNDI": "HBO.MUNDI.br",
    "HBO POP": "HBO.Pop.br",
    "HBO PLUS": "HBO.Plus.br",

    # ─── Telecine ───
    "TELECINE PREMIUM": "Telecine.Premium.br",
    "TELECINE ACTION": "Telecine.Action.br",
    "TELECINE TOUCH": "Telecine.Touch.br",
    "TELECINE PIPOCA": "Telecine.Pipoca.br",
    "TELECINE CULT": "Telecine.Cult.br",
    "TELECINE FUN": "Telecine.Fun.br",

    # ─── TNT / Space / Warner ───
    "TNT": "TNT.br",
    "TNT SERIES": "TNT.Séries.br",
    "TNT NOVELAS": "TNT.Novelas.br",
    "SPACE": "SPACE.br",
    "WARNER CHANNEL": "Warner.Channel.br",

    # ─── Sony / AXN / Studio Universal ───
    "SONY": "Sony.br",
    "AXN": "AXN.br",
    "STUDIO UNIVERSAL": "Studio.Universal.br",
    "UNIVERSAL TV": "Universal.TV.br",

    # ─── Outros Filmes e Séries ───
    "MEGAPIX": "Megapix.br",
    "TCM": "TCM.br",
    "AMC": "AMC.br",
    "CINEMAX": "Cinemax.br",
    "A&E": "A&E.br",
    "LIFETIME": "Lifetime.br",
    "SYFY": "Syfy.br",
    "FX": "FX.br",
    "STAR CHANNEL": "Star.Channel.br",
    "PARAMOUNT": "Paramount.Network.br",
    "COMEDY CENTRAL": "Comedy.Central.br",
    "SONY MOVIES": "Sony.Movies.Brazil.br",

    # ─── ESPN / SporTV ───
    "ESPN": "ESPN.br",
    "ESPN 2": "ESPN.2.br",
    "ESPN 3": "ESPN 3.br",
    "ESPN 4": "ESPN 4.br",
    "ESPN 5": "ESPN.5.br",
    "ESPN 6": "ESPN.6.br",
    "SPORTV": "SporTV.br",
    "SPORTV 2": "SporTV.2.br",
    "SPORTV 3": "SporTV.3.br",
    "BAND SPORTS": "Band.Sports.br",
    "COMBATE": "Combate.br",
    "PREMIERE": "Premiere.br",
    "PREMIERE 2": "Premiere.2.br",
    "PREMIERE 3": "Premiere.3.br",
    "PREMIERE 4": "Premiere.4.br",
    "PREMIERE 5": "Premiere.5.br",
    "PREMIERE 6": "Premiere.6.br",
    "PREMIERE 7": "Premiere.7.br",
    "PREMIERE CLUBES": "Premiere.Clubes.br",
    "CONMEBOL TV": "CONMEBOL.TV.4.HD.br",

    # ─── Discovery / Documentários ───
    "DISCOVERY CHANNEL": "Discovery.Channel.br",
    "DISCOVERY HOME": "Discovery.Home.&.Health.br",
    "DISCOVERY HOME AND HEALTH": "Discovery.Home.&.Health.br",
    "DISCOVERY H&H": "Discovery.Home.&.Health.br",
    "DISCOVERY SCIENCE": "Discovery.Science.br",
    "DISCOVERY THEATER": "Discovery.Theater.br",
    "DISCOVERY TURBO": "Discovery.Turbo.br",
    "DISCOVERY WORLD": "Discovery.World.br",
    "ANIMAL PLANET": "Animal.Planet.br",
    "HISTORY": "History.Channel.br",
    "HISTORY 2": "History.2.br",
    "HGTV": "HGTV.br",
    "TLC": "TLC.br",
    "ID": "ID.br",
    "CURTA": "Curta!.br",

    # ─── Infantil ───
    "CARTOON NETWORK": "Cartoon.Network.br",
    "NICKELODEON": "Nickelodeon.br",
    "NICK JR": "Nick.Jr..br",
    "DISCOVERY KIDS": "Discovery.Kids.br",
    "GLOOB": "Gloob.br",
    "GLOOBINHO": "Gloobinho.br",
    "CARTOONITO": "cartoonito.br",
    "TV RA TIM BUM": "TV.Rá.Tim.Bum.br",
    "BABY TV": "Baby.Tv.br",
    "ZOOMOO": "ZooMoo.br",
    "DISNEY CHANNEL": "Disney.Channel.br",

    # ─── Variedades / Entretenimento ───
    "MULTISHOW": "Multishow.br",
    "GNT": "GNT.br",
    "VIVA": "Viva.br",
    "MTV": "MTV.br",
    "BIS": "BIS.br",
    "OFF": "Off.br",
    "E!": "E!..br",
    "CANAL BRASIL": "Canal.Brasil.br",
    "ARTE 1": "Arte.1.br",
    "FILM&ARTS": "Film.&.Arts.br",
    "EUROCHANNEL": "Eurochannel.br",
    "PRIME BOX BRAZIL": "Prime.Box.Brazil.br",
    "MUSIC BOX BRAZIL": "Music.Box.Brazil.br",
    "TRAVEL BOX BRAZIL": "Travel.Box.Brasil.br",
    "FOOD NETWORK": "Food.Network.br",
    "FISH TV": "FISH.TV.br",
    "FASHION TV": "Fashion.TV.br",

    # ─── Adultos ───
    "SEXY HOT": "Sexy.Hot.br",
    "SEXTREME": "Sextreme.br",
    "VENUS": "Venus.br",
    "PLAYBOY": "Playboy.br",

    # ─── Outros ───
    "WOOHOO": "Woohoo.br",
    "DOG TV": "DogTV.br",
    "NHK WORLD": "NHK.World.Premium.br",
    "RAI INTERNATIONAL": "RAI.International.br",
    "TV5 MONDE": "TV5.Monde.br",
    "SIC INTERNATIONAL": "SIC.International.br",
    "DW": "DW-TV.br",
    "CGTN": "CGTN.br",
}


def strip_accents(text):
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize(text):
    """Normalize a string for comparison: lowercase, no accents, collapse whitespace."""
    return re.sub(r"\s+", " ", strip_accents(text.lower())).strip()


def extract_channel_core(name):
    """
    Extract the "core" channel name from a LiveWatch channel entry.
    Strips quality suffixes (HD, FHD, SD, 4K, UHD, H265, HEVC),
    location info patterns, and dedup suffixes like [2], [3].
    """
    core = name
    # Remove leading country/language tags like [US], [BR], [PT], [EN], [DUAL AUDIO]
    core = re.sub(r"^\s*\[[^\]]*\]\s*", "", core)
    # Remove trailing bracketed suffixes: [2], [3], [4K], [HD], etc.
    core = re.sub(r"\s*\[[^\]]*\]\s*$", "", core)
    # Remove quality/resolution suffixes (standalone words)
    core = re.sub(
        r"\b(FHD|HD|SD|4K|UHD|H265|HEVC|H\.265|FHD\s*H265)\b",
        "",
        core,
        flags=re.IGNORECASE,
    )
    # Remove trailing resolution marker like ², ³
    core = re.sub(r"[²³]+$", "", core)
    # Remove empty brackets/parentheses left after stripping
    core = re.sub(r"\[\s*\]", "", core)
    core = re.sub(r"\(\s*\)", "", core)
    # Collapse whitespace
    core = re.sub(r"\s+", " ", core).strip()
    return core


def extract_epg_core(epg_id):
    """
    Extract the core channel name from an EPG channel ID.
    EPG IDs look like: 'São.Paulo/SP..Globo.br' or 'ESPN.br' or 'CNN.us'
    Returns the core part: 'Globo' or 'ESPN' or 'CNN'
    """
    # Remove country suffix (e.g., .br, .us, .uk, .pt, etc.)
    epg_id = re.sub(r"\.[a-z]{2,3}$", "", epg_id)
    # Split by '..' to separate location from channel name
    if ".." in epg_id:
        core = epg_id.rsplit("..", 1)[-1]
    else:
        core = epg_id
    # Decode HTML entities (&amp; -> &)
    core = core.replace("&amp;", "&")
    # Replace dots with spaces
    core = core.replace(".", " ")
    # Remove superscript numbers and other artifacts
    core = re.sub(r"[²³¹⁴⁵⁶⁷⁸⁹⁰]+", "", core)
    # Remove parenthetical suffixes like (espelho)
    core = re.sub(r"\([^)]*\)", "", core)
    # Collapse whitespace
    core = re.sub(r"\s+", " ", core).strip()
    return core


def build_epg_index(epg_ids):
    """
    Build a lookup index from EPG IDs.
    Returns dict: {normalized_core_name: best_epg_id}
    The "best" EPG ID is the shortest one (preferring generic over location-specific).
    """
    index = {}
    for epg_id in epg_ids:
        core = normalize(extract_epg_core(epg_id))
        if not core:
            continue
        if core not in index or len(epg_id) < len(index[core]):
            index[core] = epg_id
    return index


def fetch_epg_ids(sources=None):
    """
    Fetch EPG channel IDs from epgshare01.online.
    Tries the lightweight .txt files first (which list only channel IDs),
    falling back to parsing the full .xml.gz files.

    Args:
        sources: List of full URLs to EPG .xml.gz files.
                 If None, uses default BR sources.
    """
    if sources is None:
        sources = EPG_SOURCES_DEFAULT

    all_ids = []
    for url in sources:
        try:
            # Try .txt file first (much smaller, contains only channel IDs)
            txt_url = url.replace(".xml.gz", ".txt")
            print(f"[EPG] Baixando IDs: {txt_url.rsplit('/', 1)[-1]}")
            resp = requests.get(txt_url, timeout=30)
            resp.raise_for_status()

            lines = resp.text.strip().splitlines()
            ids_from_txt = 0
            for line in lines:
                line = line.strip()
                # Skip header lines (timestamps, comments)
                if line.startswith("--") or line.startswith("#") or len(line) < 3:
                    continue
                if line.startswith("20") and len(line) < 20:
                    continue  # skip date stamps
                all_ids.append(line)
                ids_from_txt += 1

            if ids_from_txt > 0:
                print(f"[EPG]   {ids_from_txt} IDs encontrados (via .txt)")
                continue

            # Fallback to parsing .xml.gz
            print(f"[EPG]   .txt vazio, baixando .xml.gz: {url.rsplit('/', 1)[-1]}")
            resp = requests.get(url, timeout=120)
            resp.raise_for_status()

            buf = BytesIO(resp.content)
            with gzip.GzipFile(fileobj=buf) as f:
                xml_content = f.read()

            root = ET.fromstring(xml_content)
            channels = root.findall("channel")
            for ch in channels:
                ch_id = ch.get("id")
                if ch_id:
                    all_ids.append(ch_id)
            print(f"[EPG]   {len(channels)} canais encontrados (via XML)")

        except Exception as e:
            print(f"[EPG]   ERRO ao baixar/parsear {url}: {e}")

    # Deduplicate preserving order
    seen = set()
    unique_ids = []
    for eid in all_ids:
        if eid not in seen:
            seen.add(eid)
            unique_ids.append(eid)
    return unique_ids


def get_epg_sources_for_countries(country_codes):
    """
    Convert a list of country codes into full EPG URLs from ALL sources.
    Returns (epgshare_urls, globetv_urls, extra_urls) tuple.
    """
    epgshare_urls = []
    globetv_urls = []
    extra_urls = []

    for cc in country_codes:
        if cc in EPG_COUNTRY_SOURCES:
            for fname in EPG_COUNTRY_SOURCES[cc]:
                epgshare_urls.append(f"{EPG_BASE}/{fname}")
        if cc in GLOBETV_COUNTRY_SOURCES:
            for fpath in GLOBETV_COUNTRY_SOURCES[cc]:
                globetv_urls.append(f"{GLOBETV_BASE}/{fpath}")
        if cc in EXTRA_EPG_URLS:
            extra_urls.extend(EXTRA_EPG_URLS[cc])

    if not epgshare_urls and not globetv_urls:
        epgshare_urls = EPG_SOURCES_DEFAULT

    return epgshare_urls, globetv_urls, extra_urls


def fetch_epg_ids_from_globetv(urls):
    """Fetch EPG channel IDs from globetvapp/epg .xml.gz files."""
    all_ids = []
    for url in urls:
        try:
            print(f"[EPG] Baixando globetv EPG: {url.rsplit('/', 1)[-1]}")
            resp = requests.get(url, timeout=120)
            resp.raise_for_status()

            buf = BytesIO(resp.content)
            with gzip.GzipFile(fileobj=buf) as f:
                xml_content = f.read()

            root = ET.fromstring(xml_content)
            channels = root.findall("channel")
            for ch in channels:
                ch_id = ch.get("id")
                if ch_id:
                    all_ids.append(ch_id)
            print(f"[EPG]   {len(channels)} canais encontrados")
        except Exception as e:
            print(f"[EPG]   ERRO ao baixar/parsear {url}: {e}")

    return all_ids


def build_channel_mapper(epg_ids=None, sources=None, globetv_sources=None):
    """
    Build a channel mapper that translates LiveWatch channel names into EPG tvg-id values.

    Args:
        epg_ids: Pre-fetched list of EPG channel IDs. Takes precedence over sources.
        sources: List of epgshare01 EPG source URLs.
        globetv_sources: List of globetvapp/epg source URLs.

    Returns a function: mapper(channel_name) -> tvg_id or None
    """
    if epg_ids is None:
        epg_ids = fetch_epg_ids(sources)
        # Also fetch from globetvapp for additional coverage
        if globetv_sources:
            globetv_ids = fetch_epg_ids_from_globetv(globetv_sources)
            # Add globetv IDs at the end (epgshare IDs take priority)
            seen = set(epg_ids)
            for gid in globetv_ids:
                if gid not in seen:
                    seen.add(gid)
                    epg_ids.append(gid)
            print(f"[EPG] Total IDs (epgshare + globetv): {len(epg_ids)}")

    # Build EPG index from downloaded IDs
    epg_index = build_epg_index(epg_ids)

    # Build normalized manual map and pre-tokenize keys
    manual_index = {}
    manual_tokens = {}  # {key: set_of_words}
    for livewatch_core, epg_id in MANUAL_TVG_MAP.items():
        key = normalize(livewatch_core)
        manual_index[key] = epg_id
        manual_tokens[key] = set(key.split())

    # Pre-tokenize EPG index keys
    epg_tokens = {k: set(k.split()) for k in epg_index}

    def tokenize(text):
        return set(text.split())

    def word_boundary_match(query_words, target_words, target_ordered=None):
        """
        Check if query words match target words with strict rules.
        Prevents false positives like 'LIGA DA JUSTICA' matching 'TV JUSTICA'.
        """
        # Common stop words that shouldn't trigger matches
        stopwords = {"the", "and", "of", "in", "on", "at", "to", "for", "is", "it",
                     "de", "da", "do", "das", "dos", "e", "em", "no", "na", "a", "o"}
        query_words = {w for w in query_words if len(w) >= 3 and w not in stopwords}
        target_words = {w for w in target_words if len(w) >= 3 and w not in stopwords}
        if not query_words:
            return False
        matching = query_words & target_words
        if len(matching) == 0:
            return False
        if len(matching) >= 2:
            return True
        if target_ordered and len(target_ordered) > 0:
            target_ordered = [w for w in target_ordered if len(w) >= 3 and w not in stopwords]
            matched_word = list(matching)[0]
            for idx, w in enumerate(target_ordered):
                if w == matched_word:
                    if idx <= 1:
                        return True
                    break
        return False

    def mapper(channel_name):
        core_raw = extract_channel_core(channel_name)
        core = normalize(core_raw)
        core_words = tokenize(core)
        core_words_ordered = [w for w in core.split() if len(w) >= 3]

        # 1. Exact match in manual map
        if core in manual_index:
            return manual_index[core]

        # 2. Word-boundary match in manual map
        for manual_core, epg_id in manual_index.items():
            if word_boundary_match(manual_tokens[manual_core], core_words, core_words_ordered):
                return epg_id

        # 3. Exact match in downloaded EPG index
        if core in epg_index:
            return epg_index[core]

        # 4. Strip region codes (PR, RS, SC, SP, etc.) and try again
        core_no_region = re.sub(
            r"\b(PR|RS|SC|SP|RJ|MG|BA|PE|CE|DF|GO|MT|MS|PA|AM|MA|PI|RN|PB|AL|SE|ES|RO|RR|AP|AC|TO)\b",
            "",
            core,
            flags=re.IGNORECASE,
        )
        core_no_region = re.sub(r"\s+", " ", core_no_region).strip()
        if core_no_region and core_no_region != core:
            if core_no_region in manual_index:
                return manual_index[core_no_region]
            if core_no_region in epg_index:
                return epg_index[core_no_region]
            # Also try word-boundary with region-stripped core
            core_no_region_words = tokenize(core_no_region)
            core_no_region_ordered = [w for w in core_no_region.split() if len(w) >= 3]
            for manual_core, epg_id in manual_index.items():
                if word_boundary_match(manual_tokens[manual_core], core_no_region_words, core_no_region_ordered):
                    return epg_id

        # 5. Word-boundary match against EPG index
        for epg_core, epg_id in epg_index.items():
            if word_boundary_match(epg_tokens[epg_core], core_words, core_words_ordered):
                return epg_id

        return None

    return mapper


def enrich_entries(entries, epg_ids=None, tvg_url=None):
    """
    Enrich M3U entries with tvg-id attribute.

    Args:
        entries: List of (group_title, name, url) tuples
        epg_ids: Optional pre-fetched list of EPG IDs
        tvg_url: Optional x-tvg-url for the #EXTM3U header

    Returns:
        (header_extras, enriched_entries) where:
        - header_extras is a dict of extra #EXTM3U attributes (e.g., {'x-tvg-url': '...'})
        - enriched_entries is a list of (group_title, name, url, tvg_id_or_none) tuples
    """
    mapper = build_channel_mapper(epg_ids)
    header = {}
    if tvg_url:
        header["x-tvg-url"] = tvg_url

    enriched = []
    matched = 0
    total = 0
    for group_title, name, url in entries:
        tvg_id = mapper(name)
        enriched.append((group_title, name, url, tvg_id))
        total += 1
        if tvg_id:
            matched += 1

    print(f"[EPG] Mapeamento EPG: {matched}/{total} canais com tvg-id ({matched * 100 // max(total, 1)}%)")
    return header, enriched


# ── CLI entry point for testing ───────────────────────────────────────────
if __name__ == "__main__":
    print("[EPG] Testando modulo EPG...")
    epg_ids = fetch_epg_ids()
    print(f"[EPG] Total EPG IDs (BR): {len(epg_ids)}")

    mapper = build_channel_mapper(epg_ids)

    test_channels = [
        "GLOBO PR RPC CURITIBA FHD",
        "SBT PR MARINGÁ HD",
        "RECORD PR FHD",
        "BAND PR FHD",
        "HBO HD",
        "HBO 2 HD",
        "TELECINE PREMIUM HD",
        "ESPN HD",
        "ESPN 2 HD",
        "SPORTV HD",
        "SPORTV 2 HD",
        "DISCOVERY CHANNEL HD",
        "DISCOVERY HOME AND HEALTH HD",
        "ANIMAL PLANET HD",
        "HISTORY HD",
        "CARTOON NETWORK HD",
        "NICKELODEON HD",
        "TNT HD",
        "TNT SERIES HD",
        "SPACE HD",
        "SONY HD",
        "AXN HD",
        "WARNER CHANNEL HD",
        "STUDIO UNIVERSAL HD",
        "MEGAPIX HD",
        "COMBATE HD",
        "GLOBO NEWS HD",
        "BAND NEWS HD",
        "CNN BRASIL HD",
        "MULTISHOW HD",
        "GNT HD",
        "VIVA HD",
        "CINEMAX HD",
        "AMC HD",
        "A&E HD",
        "TCM HD",
        "CULTURA HD",
        "FUTURA HD",
        "GAZETA HD",
        "REDE VIDA HD",
        "TV BRASIL HD",
        "CANAL BRASIL HD",
        "BAND SPORTS HD",
        "PREMIERE 2 HD",
        "PREMIERE CLUBES HD",
        "HGTV HD",
        "TLC HD",
        "ID HD",
        "MTV HD",
        "GLOOB HD",
        "DISCOVERY KIDS HD",
        "NICK JR HD",
        "COMEDY CENTRAL HD",
        "BIS HD",
        "CURTA HD",
        "ARTE 1 HD",
        "FOOD NETWORK HD",
        "REDE BRASIL HD",
        "RECORD NEWS HD",
        "CNN INTERNATIONAL HD",
        "BBC WORLD NEWS HD",
        "CANAL DO BOI HD",
        "CANAL RURAL HD",
        "TERRA VIVA HD",
        "STAR CHANNEL HD",
        "SYFY HD",
        "FX HD",
        "PARAMOUNT HD",
        "LIFETIME HD",
        "WOOHOO HD",
        "TV CAMARA HD",
        "TV SENADO HD",
        "TV ESCOLA HD",
        "TV RÁ TIM BUM HD",
        "BABY TV HD",
        "ZOOMOO HD",
        "FISH TV HD",
        "PRIME BOX BRAZIL HD",
        "MUSIC BOX BRAZIL HD",
        "EUROCHANNEL HD",
        "FILM&ARTS HD",
        "LIFETIME HD",
    ]

    for ch in test_channels:
        tvg_id = mapper(ch)
        status = "OK" if tvg_id else "FALHOU"
        print(f"  [{status}] {ch:45s} -> {tvg_id or '---'}")
