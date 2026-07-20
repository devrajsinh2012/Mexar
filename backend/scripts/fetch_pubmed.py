"""
MEXAR - PubMed Central OA fetcher for the medical corpus.

Pulls ~220 documents from PubMed Central Open Access across three medical
subdomains (cardiology, oncology, internal medicine), parses the full-text XML
into plain text, and writes one .txt file per document into
test_data/medical_real/, along with a manifest.json for auditing.

Usage:
    python backend/scripts/fetch_pubmed.py

Requirements:
    pip install requests lxml

Environment:
    NCBI_EMAIL  — your email address (required by NCBI usage policy)
    NCBI_API_KEY — optional; raises rate limit from 3 req/sec to 10 req/sec

Run this locally (not in a network-restricted sandbox).
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

try:
    from lxml import etree
except ImportError:
    sys.exit(
        "lxml is required — run: pip install lxml"
    )

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# NCBI email is mandatory per NCBI E-utilities usage policy.
# Override with the NCBI_EMAIL environment variable or the --email CLI flag.
DEFAULT_NCBI_EMAIL: str = os.getenv("NCBI_EMAIL", "your_email@example.com")
NCBI_API_KEY: Optional[str] = os.getenv("NCBI_API_KEY")  # optional; raises rate cap to 10/s

# One .txt per doc, one manifest.json — relative to repo root.
OUTPUT_DIR = Path("test_data/medical_real")

# Three subdomains × 75 docs ≈ 220 total (some may fail or be empty).
SEARCH_TERMS: Dict[str, str] = {
    "cardiology": (
        '"cardiology treatment guideline"[Title/Abstract] AND "open access"[filter]'
    ),
    "oncology": (
        '"oncology treatment protocol"[Title/Abstract] AND "open access"[filter]'
    ),
    "internal_medicine": (
        '"internal medicine diagnostic criteria"[Title/Abstract] AND "open access"[filter]'
    ),
}
DOCS_PER_SUBDOMAIN: int = 75

# NCBI rate limits: 3 req/sec without key, 10/sec with key.
REQUEST_DELAY_NO_KEY: float = 0.35   # ≈ 2.9 req/sec — safe without key
REQUEST_DELAY_WITH_KEY: float = 0.12  # ≈ 8.3 req/sec — safe with key

NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# ---------------------------------------------------------------------------
# NCBI E-utilities helpers
# ---------------------------------------------------------------------------


def _ncbi_params(extra: dict, email: str) -> dict:
    """Return base params dict merged with extra, including optional API key."""
    params = {"email": email, **extra}
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    return params


def esearch(term: str, retmax: int, email: str) -> List[str]:
    """
    Run an E-search against the PMC database and return a list of PMC IDs.

    Args:
        term:   NCBI search query string.
        retmax: Maximum number of IDs to retrieve.
        email:  Requester email (required by NCBI).

    Returns:
        List of PMC ID strings (numeric, without the 'PMC' prefix).
    """
    url = f"{NCBI_BASE}/esearch.fcgi"
    params = _ncbi_params(
        {"db": "pmc", "term": term, "retmax": retmax, "retmode": "json"},
        email,
    )
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()["esearchresult"]["idlist"]


def efetch_xml(pmc_id: str, email: str) -> bytes:
    """
    Fetch the full-text XML for a single PMC article.

    Args:
        pmc_id: Numeric PMC ID string (without the 'PMC' prefix).
        email:  Requester email.

    Returns:
        Raw XML bytes from the PMC OA full-text endpoint.
    """
    url = f"{NCBI_BASE}/efetch.fcgi"
    params = _ncbi_params(
        {"db": "pmc", "id": pmc_id, "rettype": "full", "retmode": "xml"},
        email,
    )
    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    return resp.content


# ---------------------------------------------------------------------------
# XML → plain-text extraction
# ---------------------------------------------------------------------------

# Tags in the JATS PMC XML that contain useful body text.
_BODY_TAGS = {"abstract", "body", "sec", "p", "title"}


def _iter_text(element) -> str:
    """
    Recursively collect all text inside an lxml element, with
    paragraph-level whitespace to keep the output readable.
    """
    parts = []
    if element.text:
        parts.append(element.text.strip())
    for child in element:
        child_text = _iter_text(child)
        if child_text:
            # Add a blank line between sections/paragraphs.
            sep = "\n\n" if child.tag in {"sec", "p", "title", "abstract"} else " "
            parts.append(sep + child_text)
        if child.tail:
            parts.append(child.tail.strip())
    return " ".join(p for p in parts if p)


def xml_to_plain_text(xml_bytes: bytes) -> str:
    """
    Parse PMC full-text XML and extract human-readable plain text.

    Pulls text from <abstract>, <body>, and nested <sec>/<p> elements,
    strips all XML markup, and returns a clean, whitespace-normalised string.

    Args:
        xml_bytes: Raw XML bytes as returned by efetch.

    Returns:
        Plain-text string.  Empty string if parsing fails.
    """
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as exc:
        logger.warning("XML parse error: %s", exc)
        return ""

    sections: List[str] = []
    # Pull <article-title>, <abstract>, and <body> in document order.
    for tag in ("article-title", "abstract", "body"):
        for element in root.iter(tag):
            text = _iter_text(element).strip()
            if text:
                sections.append(text)

    plain = "\n\n".join(sections)
    # Collapse excessive whitespace.
    import re
    plain = re.sub(r" {2,}", " ", plain)
    plain = re.sub(r"\n{3,}", "\n\n", plain)
    return plain.strip()


def _get_article_meta(xml_bytes: bytes) -> Dict[str, str]:
    """Extract title and journal name from parsed PMC XML for the manifest."""
    meta: Dict[str, str] = {"title": "", "journal": ""}
    try:
        root = etree.fromstring(xml_bytes)
        title_el = root.find(".//article-title")
        if title_el is not None:
            meta["title"] = (_iter_text(title_el) or "").strip()
        journal_el = root.find(".//journal-title")
        if journal_el is not None:
            meta["journal"] = (journal_el.text or "").strip()
    except Exception:
        pass
    return meta


# ---------------------------------------------------------------------------
# Main fetch loop
# ---------------------------------------------------------------------------


def fetch_subdomain(
    subdomain: str,
    term: str,
    n: int,
    output_dir: Path,
    email: str,
    delay: float,
) -> List[Dict]:
    """
    Search for and download up to `n` PMC articles matching `term`.

    Args:
        subdomain:  Label string used in the manifest.
        term:       NCBI search query.
        n:          Target number of documents.
        output_dir: Directory to write .txt files into.
        email:      NCBI requester email.
        delay:      Seconds to sleep between requests.

    Returns:
        List of manifest entry dicts for successfully fetched documents.
    """
    logger.info("Subdomain '%s': searching for %d docs …", subdomain, n)
    try:
        ids = esearch(term, n, email)
    except Exception as exc:
        logger.error("esearch failed for '%s': %s", subdomain, exc)
        return []

    logger.info("  Found %d IDs; fetching full text …", len(ids))
    entries: List[Dict] = []

    for pmc_id in ids:
        time.sleep(delay)
        try:
            xml_bytes = efetch_xml(pmc_id, email)
            plain = xml_to_plain_text(xml_bytes)
        except requests.HTTPError as exc:
            logger.warning("HTTP error for PMC%s: %s", pmc_id, exc)
            continue
        except Exception as exc:
            logger.warning("Failed PMC%s: %s", pmc_id, exc)
            continue

        if len(plain) < 200:
            logger.debug("PMC%s: text too short (%d chars), skipping.", pmc_id, len(plain))
            continue

        out_path = output_dir / f"PMC{pmc_id}.txt"
        out_path.write_text(plain, encoding="utf-8")

        meta = _get_article_meta(xml_bytes)
        entries.append(
            {
                "pmc_id": pmc_id,
                "subdomain": subdomain,
                "title": meta["title"],
                "journal": meta["journal"],
                "source_url": f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/",
                "path": str(out_path),
                "char_count": len(plain),
            }
        )
        logger.info("  Saved PMC%s (%d chars)", pmc_id, len(plain))

    logger.info("  Subdomain '%s': %d documents saved.", subdomain, len(entries))
    return entries


def main(email: str = DEFAULT_NCBI_EMAIL, docs_per_subdomain: int = DOCS_PER_SUBDOMAIN) -> None:
    """
    Entry point.  Iterates over all three medical subdomains and writes results.
    """
    if email == "your_email@example.com":
        logger.warning(
            "Using placeholder email — set the NCBI_EMAIL env var or pass --email. "
            "NCBI may throttle requests without a valid email."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    delay = REQUEST_DELAY_WITH_KEY if NCBI_API_KEY else REQUEST_DELAY_NO_KEY
    manifest: List[Dict] = []

    for subdomain, term in SEARCH_TERMS.items():
        entries = fetch_subdomain(subdomain, term, docs_per_subdomain, OUTPUT_DIR, email, delay)
        manifest.extend(entries)

    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info(
        "Done.  %d medical documents fetched.  Manifest → %s",
        len(manifest),
        manifest_path,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch PubMed Central OA articles for the MEXAR medical corpus."
    )
    parser.add_argument(
        "--email",
        default=DEFAULT_NCBI_EMAIL,
        help="Your email address (required by NCBI usage policy).",
    )
    parser.add_argument(
        "--docs-per-subdomain",
        type=int,
        default=DOCS_PER_SUBDOMAIN,
        help="Number of documents to fetch per subdomain (default: %(default)s).",
    )
    args = parser.parse_args()
    main(email=args.email, docs_per_subdomain=args.docs_per_subdomain)
