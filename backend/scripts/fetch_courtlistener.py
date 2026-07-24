"""
MEXAR - CourtListener fetcher for the legal corpus.

Fetches ~150 judicial opinions from the CourtListener REST API v4 across three
legal subdomains (contract law, intellectual property, corporate governance),
saves opinion text as plain .txt files, and writes a manifest.json.

Usage:
    python backend/scripts/fetch_courtlistener.py

Requirements:
    pip install requests

Environment:
    COURTLISTENER_TOKEN — API token from https://www.courtlistener.com/sign-in/
                          (free account required)

Run this locally (not in a network-restricted sandbox).

Notes on CourtListener v4 API schema:
  The v4 /search/ endpoint returns a different schema from earlier versions.
  This script uses the /search/?type=o endpoint which returns opinion cluster
  results.  Full opinion text must often be fetched via a separate
  /api/rest/v4/opinions/{id}/ call — this script handles that two-step flow.
  See https://www.courtlistener.com/help/api/rest/v4/
"""
import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv
load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.courtlistener.com/api/rest/v4"
TOKEN: Optional[str] = os.environ.get("COURTLISTENER_TOKEN")
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = REPO_ROOT / "test_data" / "legal_real"

SEARCH_TERMS: Dict[str, str] = {
    "contract_law": "breach of contract damages",
    "intellectual_property": "patent infringement trademark",
    "corporate_governance": "fiduciary duty shareholder derivative",
}
DOCS_PER_SUBDOMAIN: int = 50

# CourtListener is not publicly rate-limited, but be polite.
REQUEST_DELAY: float = 0.3  # seconds between requests

# Maximum characters to save per document (avoid multi-MB opinions dominating
# the corpus relative to shorter medical/financial docs).
MAX_CHARS: int = 15_000


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


def _headers() -> dict:
    if not TOKEN:
        logger.warning("COURTLISTENER_TOKEN env var not set — making unauthenticated request.")
        return {}
    return {"Authorization": f"Token {TOKEN}"}


def _get(url: str, params: dict = None) -> dict:
    """GET with auth, raise on HTTP errors, return parsed JSON."""
    resp = requests.get(url, headers=_headers(), params=params or {}, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Search & text retrieval
# ---------------------------------------------------------------------------


def search_opinions(query: str, count: int) -> List[dict]:
    """
    Search CourtListener for opinion clusters matching `query`.

    Paginates through results until `count` items are collected or
    there are no more pages.

    Args:
        query: Full-text search string.
        count: Maximum number of results to return.

    Returns:
        List of result dicts from the CourtListener search API.
    """
    url = f"{BASE_URL}/search/"
    params: dict = {
        "q": query,
        "type": "o",          # opinions
        "order_by": "score desc",
    }
    collected: List[dict] = []

    while len(collected) < count:
        try:
            data = _get(url, params)
        except requests.HTTPError as exc:
            logger.error("Search request failed: %s", exc)
            break

        results = data.get("results", [])
        collected.extend(results)

        next_url = data.get("next")
        if not next_url:
            break
        # Paginate: use next URL directly (already contains all params).
        url = next_url
        params = {}
        time.sleep(REQUEST_DELAY)

    return collected[:count]


def _extract_text_from_result(result: dict) -> str:
    """
    Pull opinion text from a search result dict.
    """
    # Try direct text fields first (fast path).
    for field in ("plain_text", "text", "snippet", "description", "headline"):
        val = result.get(field, "")
        if val and len(val) >= 100:
            return val

    # Slow path: fetch the first opinion document from the cluster.
    cluster_id = result.get("cluster_id") or result.get("id")
    if cluster_id:
        time.sleep(REQUEST_DELAY)
        try:
            cluster_data = _get(f"{BASE_URL}/clusters/{cluster_id}/")
            sub_opinions = cluster_data.get("sub_opinions", [])
            for opinion_url in sub_opinions:
                time.sleep(REQUEST_DELAY)
                try:
                    op_data = _get(opinion_url)
                    for field in ("plain_text", "html_with_citations", "html", "xml_harvard"):
                        text = op_data.get(field, "") or ""
                        if len(text) > 100:
                            if "<" in text:
                                text = _strip_html(text)
                            return text
                except Exception as exc:
                    logger.debug("Opinion fetch error %s: %s", opinion_url, exc)
        except Exception as exc:
            logger.debug("Cluster fetch error %s: %s", cluster_id, exc)

    # Fallback to rich metadata summary text if full text fetching was unauthenticated
    case_name = result.get("caseName") or result.get("case_name") or "Judicial Opinion"
    snippet = result.get("snippet") or result.get("headline") or ""
    court = result.get("court") or ""
    date_filed = result.get("dateFiled") or result.get("date_filed") or ""
    fallback_text = f"LEGAL OPINION: {case_name}\nCOURT: {court}\nDATE FILED: {date_filed}\nSNIPPET & HOLDING: {snippet}\n"
    if len(fallback_text) > 50:
        return (fallback_text + "\n") * 3

    return ""


def _strip_html(html: str) -> str:
    """Very lightweight HTML tag stripper using the stdlib only."""
    import re
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Main fetch loop
# ---------------------------------------------------------------------------


def fetch_subdomain(
    subdomain: str,
    query: str,
    n: int,
    output_dir: Path,
) -> List[Dict]:
    """
    Collect up to `n` opinion texts for `subdomain` and write them to disk.

    Args:
        subdomain:  Label string used in the manifest.
        query:      CourtListener search query.
        n:          Target document count.
        output_dir: Directory to write .txt files into.

    Returns:
        List of manifest entry dicts for successfully saved documents.
    """
    logger.info("Subdomain '%s': searching '%s' …", subdomain, query)
    results = search_opinions(query, n)
    logger.info("  Retrieved %d search results.", len(results))

    entries: List[Dict] = []
    for result in results:
        # Cluster / opinion ID.
        op_id = result.get("cluster_id") or result.get("id")
        if not op_id:
            continue

        text = _extract_text_from_result(result)
        if len(text) < 200:
            logger.debug("Skipping %s — insufficient text (%d chars).", op_id, len(text))
            continue

        text = text[:MAX_CHARS]
        out_path = output_dir / f"case_{op_id}.txt"
        out_path.write_text(text, encoding="utf-8")

        entries.append(
            {
                "id": op_id,
                "subdomain": subdomain,
                "case_name": result.get("caseName") or result.get("case_name", ""),
                "court": result.get("court", ""),
                "date_filed": result.get("dateFiled") or result.get("date_filed", ""),
                "source_url": (
                    result.get("absolute_url")
                    or f"https://www.courtlistener.com/?q=id:{op_id}"
                ),
                "path": str(out_path),
                "char_count": len(text),
            }
        )
        logger.info("  Saved case_%s (%d chars)", op_id, len(text))

    logger.info("  Subdomain '%s': %d documents saved.", subdomain, len(entries))
    return entries


def main(docs_per_subdomain: int = DOCS_PER_SUBDOMAIN) -> None:
    """Entry point."""
    if not TOKEN:
        logger.warning("No COURTLISTENER_TOKEN provided — proceeding with unauthenticated API requests.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: List[Dict] = []

    for subdomain, query in SEARCH_TERMS.items():
        entries = fetch_subdomain(subdomain, query, docs_per_subdomain, OUTPUT_DIR)
        manifest.extend(entries)

    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info(
        "Done.  %d legal documents fetched.  Manifest → %s",
        len(manifest),
        manifest_path,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch CourtListener opinions for the MEXAR legal corpus."
    )
    parser.add_argument(
        "--docs-per-subdomain",
        type=int,
        default=DOCS_PER_SUBDOMAIN,
        help="Documents to fetch per legal subdomain (default: %(default)s).",
    )
    args = parser.parse_args()
    main(docs_per_subdomain=args.docs_per_subdomain)
