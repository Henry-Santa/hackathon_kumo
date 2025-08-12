from __future__ import annotations

import httpx
from urllib.parse import unquote, quote
from typing import List, Dict


WIKIDATA_SPARQL = """
SELECT ?item ?itemLabel ?unitid ?image ?website WHERE {
  ?item wdt:P1771 ?unitid.
  ?item wdt:P18 ?image.
  OPTIONAL { ?item wdt:P856 ?website }
  OPTIONAL { ?item wdt:P17 ?country }
  VALUES ?country { wd:Q30 }  # United States
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT 20000
"""


async def fetch_wikidata_images() -> List[Dict]:
    # Query Wikidata SPARQL endpoint
    url = "https://query.wikidata.org/sparql"
    headers = {"accept": "application/sparql-results+json"}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(url, params={"query": WIKIDATA_SPARQL}, headers=headers)
        r.raise_for_status()
        data = r.json()
    rows: List[Dict] = []
    for b in data.get("results", {}).get("bindings", []):
        unitid = b.get("unitid", {}).get("value")
        image = b.get("image", {}).get("value")  # Commons filename URL form
        website = b.get("website", {}).get("value") if b.get("website") else None
        item = b.get("item", {}).get("value")
        label = b.get("itemLabel", {}).get("value")
        if not unitid or not image:
            continue
        # Heuristic filter to avoid logos/seals
        bad_tokens = ["logo", "seal", "crest", "map", "icon"]
        lower = image.lower()
        if any(tok in lower for tok in bad_tokens):
            continue
        rows.append(
            {
                "unitid": int(unitid),
                "image": image,
                "label": label,
                "website": website,
                "item": item,
            }
        )
    return rows


def commons_file_url(filename_or_url: str, width: int = 1024) -> str:
    # If we got a full Commons file URL, return a thumbnail URL via Special:FilePath
    # Accepts either "https://commons.wikimedia.org/wiki/Special:FilePath/FILENAME" or "FILENAME"
    if filename_or_url.startswith("http"):
        name = filename_or_url.split("/")[-1]
    else:
        name = filename_or_url
    # Use Special:FilePath which redirects to an actual file URL; width param via thumb API alternative
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{name}?width={width}"


async def fetch_images_for_unitid(unitid: int, max_rows: int = 10) -> List[Dict]:
    # Fetch all P18 images for a specific IPEDS UnitID
    unitid_str = str(unitid)
    query = f"""
    SELECT ?item ?itemLabel ?unitid ?image ?website WHERE {{
      ?item wdt:P1771 "{unitid_str}".
      ?item wdt:P18 ?image.
      OPTIONAL {{ ?item wdt:P856 ?website }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT {max_rows}
    """
    url = "https://query.wikidata.org/sparql"
    headers = {"accept": "application/sparql-results+json"}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(url, params={"query": query}, headers=headers)
        r.raise_for_status()
        data = r.json()
    rows: List[Dict] = []
    for b in data.get("results", {}).get("bindings", []):
        image = b.get("image", {}).get("value")
        website = b.get("website", {}).get("value") if b.get("website") else None
        item = b.get("item", {}).get("value")
        label = b.get("itemLabel", {}).get("value")
        if not image:
            continue
        lower = image.lower()
        bad_tokens = ["logo", "seal", "crest", "map", "icon"]
        if any(tok in lower for tok in bad_tokens):
            continue
        rows.append(
            {
                "unitid": int(unitid),
                "image": image,
                "label": label,
                "website": website,
                "item": item,
            }
        )
    return rows


async def fetch_top_images_for_unitid(unitid: int, limit: int = 5) -> List[Dict]:
    """Fetch up to `limit` prioritized image URLs for a specific IPEDS UnitID.
    Uses P18 on the university, P18 on parts (P361), and files depicting the university (P180),
    scoring by campus-like keywords. Returns fully fetchable Wikimedia URLs.
    """
    unitid_str = str(unitid)
    sparql = f"""
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX schema: <http://schema.org/>

SELECT DISTINCT ?imageUrl ?source ?sourceLabel ?matchText WHERE {{
  ?uni wdt:P1771 "{unitid_str}".

  {{
    ?uni wdt:P18 ?img.
    BIND(REPLACE(STR(?img), "^.*File:", "") AS ?fname)
    BIND(IRI(CONCAT("https://commons.wikimedia.org/wiki/Special:FilePath/", ENCODE_FOR_URI(?fname))) AS ?imageUrl)
    BIND(?uni AS ?source)
  }}
  UNION
  {{
    ?part wdt:P361 ?uni.
    ?part wdt:P18 ?img2.
    BIND(REPLACE(STR(?img2), "^.*File:", "") AS ?fname)
    BIND(IRI(CONCAT("https://commons.wikimedia.org/wiki/Special:FilePath/", ENCODE_FOR_URI(?fname))) AS ?imageUrl)
    BIND(?part AS ?source)
  }}
  UNION
  {{
    ?file wdt:P180 ?uni.
    ?file schema:contentUrl ?imageUrl.
    BIND(STR(?file) AS ?fname)
    BIND(?file AS ?source)
  }}

  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
  BIND(COALESCE(LCASE(STR(?sourceLabel)), LCASE(STR(?fname)), "") AS ?matchText)
  BIND(IF(REGEX(?matchText, "harvard|campus|yard|quad|cambridge|memorial|commencement", "i"), 1, 0) AS ?isCampus)
}}
ORDER BY DESC(?isCampus)
LIMIT {max(1, int(limit))}
"""
    url = "https://query.wikidata.org/sparql"
    headers = {"accept": "application/sparql-results+json"}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(url, params={"query": sparql}, headers=headers)
        r.raise_for_status()
        data = r.json()
    out: List[Dict] = []
    for b in data.get("results", {}).get("bindings", []):
        raw_url = b.get("imageUrl", {}).get("value")
        src_label = b.get("sourceLabel", {}).get("value") if b.get("sourceLabel") else None
        match_text = b.get("matchText", {}).get("value") if b.get("matchText") else None
        if not raw_url:
            continue
        image_url = normalize_commons_image_url(raw_url)
        out.append({
            "unitid": unitid,
            "image_url": image_url,
            "source_label": src_label,
            "match_text": match_text,
        })
    return out


def normalize_commons_image_url(url_or_filename: str, width: int = 1024) -> str:
    """Normalize various Wikimedia/Wikidata image URL forms to a clean Special:FilePath URL.

    Handles cases where the URL itself is already a Special:FilePath link and has a
    percent-encoded nested Special:FilePath/HTTP URL. Also accepts plain filenames.
    """
    if not url_or_filename:
        return url_or_filename

    # If it's already a plain filename (no scheme), convert directly
    if not url_or_filename.startswith("http"):
        return commons_file_url(url_or_filename, width=width)

    lower = url_or_filename.lower()
    marker = "/special:filepath/"
    if marker in lower:
        # Extract the tail after Special:FilePath/
        idx = lower.rfind(marker)
        tail = url_or_filename[idx + len(marker):]
        tail_dec = unquote(tail)
        # If tail decodes to an http URL, strip to last path segment (the filename)
        if tail_dec.startswith("http://") or tail_dec.startswith("https://"):
            filename = tail_dec.split("/")[-1]
            return commons_file_url(filename, width=width)
        # Otherwise assume it's a filename (possibly with spaces), re-encode safely
        return f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(tail_dec)}?width={width}"

    # If it's a direct upload URL (upload.wikimedia.org/.../filename), keep as is
    return url_or_filename

