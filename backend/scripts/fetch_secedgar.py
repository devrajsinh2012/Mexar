"""
MEXAR - SEC EDGAR fetcher for the financial corpus.

Fetches ~130 10-K filing sections (MD&A, Risk Factors) from SEC EDGAR using
the full-text search API, follows through to the actual EDGAR filing documents,
extracts the relevant section text, and saves one .txt file per document plus
a manifest.json.

Usage:
    python backend/scripts/fetch_secedgar.py

Requirements:
    pip install requests beautifulsoup4 lxml

SEC Fair Access Policy:
    Every request MUST include a descriptive User-Agent header in the format:
    "FirstName LastName email@example.com"
    without this, SEC will block your IP.

    Override with the SEC_USER_AGENT environment variable.

Run this locally (not in a network-restricted sandbox).
"""
import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests
from dotenv import load_dotenv
load_dotenv()

try:
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("beautifulsoup4 is required — run: pip install beautifulsoup4 lxml")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# SEC requires a descriptive User-Agent on every request.
# Format: "Name Email" — use yours or set SEC_USER_AGENT env var.
_DEFAULT_USER_AGENT = "Devrajsinh Gohil djgohil2012@gmail.com"
USER_AGENT: str = os.getenv("SEC_USER_AGENT", _DEFAULT_USER_AGENT)

HEADERS: Dict[str, str] = {
    "User-Agent": USER_AGENT,
    "Accept-Encoding": "gzip, deflate",
    "Host": "efts.sec.gov",
}
EDGAR_HEADERS: Dict[str, str] = {
    "User-Agent": USER_AGENT,
    "Accept-Encoding": "gzip, deflate",
}

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = REPO_ROOT / "test_data" / "financial_real"

# Search terms and per-term document targets (~130 total).
SEARCH_CONFIG: List[Tuple[str, str, int]] = [
    ("risk_factors",              "risk factors",                     45),
    ("management_discussion",     "management discussion and analysis", 45),
    ("accounting_standards",      "GAAP IFRS accounting standards",   40),
]

# Maximum characters per saved document — keep consistent with medical/legal sizes.
MAX_CHARS: int = 15_000

# Be polite to SEC servers.
REQUEST_DELAY: float = 0.25  # seconds

# EDGAR full-text search endpoint.
EFTS_URL = "https://efts.sec.gov/LATEST/search-index"
EDGAR_ARCHIVES = "https://www.sec.gov/Archives/edgar/data"

# ---------------------------------------------------------------------------
# SEC EDGAR API helpers
# ---------------------------------------------------------------------------


def _get(url: str, params: dict = None, extra_headers: dict = None) -> requests.Response:
    """GET with SEC-compliant headers and error handling."""
    h = {**EDGAR_HEADERS}
    if extra_headers:
        h.update(extra_headers)
    resp = requests.get(url, headers=h, params=params or {}, timeout=30)
    resp.raise_for_status()
    return resp


def full_text_search(query: str, count: int) -> List[dict]:
    """
    Query the SEC EDGAR full-text search API for 10-K filings.

    The EFTS search endpoint returns hit metadata only — not the filing body.
    Each hit contains the accession number and CIK needed to locate the filing
    document in EDGAR archives.

    Args:
        query: Search phrase (e.g. "risk factors").
        count: Maximum number of hits to return.

    Returns:
        List of _source dicts from the EFTS hits array.
    """
    # EFTS search uses query-string encoding.
    params = {
        "q": f'"{query}"',
        "forms": "10-K",
        "dateRange": "custom",
        "startdt": "2020-01-01",
        "enddt": "2024-12-31",
    }
    try:
        resp = _get(
            EFTS_URL,
            params=params,
            extra_headers={"Host": "efts.sec.gov"},
        )
    except Exception as exc:
        logger.error("EFTS search failed for '%s': %s", query, exc)
        return []

    data = resp.json()
    hits = data.get("hits", {}).get("hits", [])
    logger.info("  EFTS returned %d hits for '%s'", len(hits), query)
    return [h.get("_source", {}) for h in hits[:count]]


# ---------------------------------------------------------------------------
# Filing document text extraction
# ---------------------------------------------------------------------------

def _accession_to_path(accession: str) -> str:
    """Convert '0001234567-23-012345' → '000123456723012345'."""
    return accession.replace("-", "")


def _get_filing_index(cik: str, accession: str) -> Optional[dict]:
    """
    Fetch the filing index JSON from EDGAR to find the primary document URL.

    Returns the parsed index data dict, or None on failure.
    """
    cik_int = str(int(cik)) if cik.isdigit() else cik
    acc_path = _accession_to_path(accession)
    url = (
        f"https://data.sec.gov/submissions/CIK{cik_int.zfill(10)}.json"
    )
    # Use the filing index endpoint instead.
    index_url = (
        f"https://www.sec.gov/cgi-bin/browse-edgar"
        f"?action=getcompany&CIK={cik_int}&type=10-K&dateb=&owner=include&count=1&search_text="
    )
    # Directly hit the accession-number based index.
    direct_url = (
        f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_path}/{accession}-index.json"
    )
    try:
        resp = _get(direct_url)
        return resp.json()
    except Exception:
        pass
    # Fallback: try the .htm index.
    try:
        htm_url = (
            f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_path}/{accession}-index.htm"
        )
        resp = _get(htm_url)
        # Parse the index page for the primary document link.
        soup = BeautifulSoup(resp.text, "lxml")
        return {"_html": resp.text, "_base": f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_path}/"}
    except Exception as exc:
        logger.debug("Filing index fetch failed for %s/%s: %s", cik, accession, exc)
        return None


def _find_primary_document_url(cik: str, accession: str, index_data: dict) -> Optional[str]:
    """
    Given filing index data, return the URL of the primary 10-K HTML document.
    """
    acc_path = _accession_to_path(accession)
    base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_path}/"

    # JSON index format (modern filings).
    if "documents" in index_data:
        for doc in index_data.get("documents", []):
            doc_type = doc.get("type", "").upper()
            if doc_type in ("10-K", "10-K/A"):
                filename = doc.get("filename") or doc.get("documentName", "")
                if filename:
                    return base + filename

    # HTML index fallback.
    if "_html" in index_data:
        soup = BeautifulSoup(index_data["_html"], "lxml")
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 3:
                doc_type = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                if "10-K" in doc_type:
                    link = cells[2].find("a")
                    if link and link.get("href"):
                        href = link["href"]
                        if href.startswith("/"):
                            return "https://www.sec.gov" + href
                        return href
        # If no 10-K row found, grab any .htm link from the table.
        for link in soup.select("table a[href]"):
            href = link["href"]
            if href.endswith(".htm") or href.endswith(".html"):
                if href.startswith("/"):
                    return "https://www.sec.gov" + href
                return href

    return None


def _extract_section(html: str, section: str) -> str:
    """
    Extract a named section (e.g. 'risk factors', 'management discussion')
    from a 10-K HTML document.

    Strategy:
    1. Parse with BeautifulSoup.
    2. Find the first heading element (<b>, <strong>, <h2>, <h3>, <p>) whose
       text closely matches the section name.
    3. Collect all subsequent paragraph text until the next major heading.

    Falls back to returning the first 15,000 chars of the full body text if
    no matching section heading is found.
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove script/style noise.
    for tag in soup(["script", "style", "meta", "link"]):
        tag.decompose()

    section_lower = section.lower()
    # Headings to search in.
    heading_candidates = soup.find_all(
        ["b", "strong", "h1", "h2", "h3", "h4", "p"],
    )

    section_start = None
    for el in heading_candidates:
        text = el.get_text(" ", strip=True).lower()
        if section_lower in text and len(text) < 200:
            section_start = el
            break

    if section_start is None:
        # No section heading found — return the full text (truncated).
        full_text = soup.get_text(" ", strip=True)
        return re.sub(r" {2,}", " ", full_text)

    # Collect text from siblings/following elements until next major heading.
    parts: List[str] = []
    total = 0
    for sibling in section_start.find_all_next():
        tag_name = sibling.name or ""
        text = sibling.get_text(" ", strip=True)
        if not text:
            continue

        # Stop at the next major heading that looks like a different section.
        if tag_name in ("h1", "h2", "h3"):
            break
        if tag_name in ("b", "strong", "p") and len(text) < 200:
            text_lower = text.lower()
            # Check for common 10-K section heading patterns.
            if re.match(r"(item\s+\d|part\s+[iv]+)", text_lower):
                break

        parts.append(text)
        total += len(text)
        if total >= MAX_CHARS:
            break

    extracted = " ".join(parts)
    extracted = re.sub(r" {2,}", " ", extracted)
    return extracted.strip()


def fetch_and_extract(source: dict, query_label: str) -> Tuple[str, str, int]:
    """
    Follow through from an EFTS hit's metadata to the actual filing text.

    Args:
        source:      _source dict from an EFTS hit.
        query_label: Human-readable label for the search term (used for
                     section extraction hints).

    Returns:
        (text, filing_url, char_count)  — text is empty string on failure.
    """
    cik_list = source.get("ciks", [])
    cik = str(cik_list[0]) if cik_list else source.get("cik", "")
    accession = source.get("adsh", "")

    if not cik or not accession:
        return "", "", 0

    acc_path = _accession_to_path(accession)
    filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_path}/"

    time.sleep(REQUEST_DELAY)

    # Step 1: Get filing index to find the primary document.
    index_data = _get_filing_index(cik, accession)
    if not index_data:
        logger.debug("No index for %s / %s", cik, accession)
        return "", filing_url, 0

    doc_url = _find_primary_document_url(cik, acc_path, index_data)
    if not doc_url:
        logger.debug("Could not locate primary doc for %s / %s", cik, accession)
        return "", filing_url, 0

    time.sleep(REQUEST_DELAY)

    # Step 2: Fetch the 10-K document.
    try:
        resp = _get(doc_url)
        html = resp.text
    except Exception as exc:
        logger.debug("Failed to fetch filing document %s: %s", doc_url, exc)
        return "", filing_url, 0

    # Step 3: Extract the relevant section.
    section_hint = query_label.replace("_", " ")
    text = _extract_section(html, section_hint)
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]

    return text, doc_url, len(text)


# ---------------------------------------------------------------------------
# Main fetch loop
# ---------------------------------------------------------------------------


def fetch_term(
    label: str,
    query: str,
    n: int,
    output_dir: Path,
) -> List[Dict]:
    """
    Search EDGAR for `n` filings matching `query`, extract section text, save.

    Args:
        label:      Short label for the search term (used in filename + manifest).
        query:      EDGAR full-text search phrase.
        n:          Target document count.
        output_dir: Directory to write .txt files into.

    Returns:
        List of manifest entry dicts.
    """
    logger.info("Term '%s': searching EDGAR for %d docs …", label, n)
    sources = full_text_search(query, n)

    entries: List[Dict] = []
    seen = set()

    for source in sources:
        cik_list = source.get("ciks", [])
        cik = str(cik_list[0]) if cik_list else source.get("cik", "")
        accession = source.get("adsh", "")

        if not cik or not accession:
            continue

        doc_key = f"{cik}_{accession}"
        if doc_key in seen:
            continue
        seen.add(doc_key)

        text, doc_url, char_count = fetch_and_extract(source, label)
        if char_count < 200:
            logger.debug("Skipping %s — insufficient text (%d chars).", doc_key, char_count)
            continue

        out_path = output_dir / f"{doc_key}.txt"
        out_path.write_text(text, encoding="utf-8")

        company_names = source.get("display_names", [])
        company = company_names[0] if company_names else source.get("entity_name", "")

        entries.append(
            {
                "cik": cik,
                "accession": accession,
                "company": company,
                "term": label,
                "filing_date": source.get("period_of_report", ""),
                "source_url": doc_url,
                "path": str(out_path),
                "char_count": char_count,
            }
        )
        logger.info("  Saved %s (%d chars)", doc_key, char_count)

    logger.info("  Term '%s': %d documents saved.", label, len(entries))
    return entries


def main() -> None:
    """Entry point."""
    if USER_AGENT == _DEFAULT_USER_AGENT:
        logger.warning(
            "Using default User-Agent '%s'. "
            "Set the SEC_USER_AGENT env var to 'YourName your@email.com' "
            "to comply with SEC fair access policy.",
            USER_AGENT,
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: List[Dict] = []

    for label, query, target_n in SEARCH_CONFIG:
        entries = fetch_term(label, query, target_n, OUTPUT_DIR)
        manifest.extend(entries)

    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info(
        "Done.  %d financial documents fetched.  Manifest → %s",
        len(manifest),
        manifest_path,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch SEC EDGAR 10-K sections for the MEXAR financial corpus."
    )
    parser.add_argument(
        "--user-agent",
        default=None,
        help=(
            "SEC-compliant User-Agent string ('FirstName LastName email@example.com'). "
            "Overrides the SEC_USER_AGENT environment variable."
        ),
    )
    args = parser.parse_args()
    if args.user_agent:
        USER_AGENT = args.user_agent
        HEADERS["User-Agent"] = USER_AGENT
        EDGAR_HEADERS["User-Agent"] = USER_AGENT
    main()
