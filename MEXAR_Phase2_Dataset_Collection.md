# MEXAR Phase 2 — Real Datasets at Reduced, Disclosed Scale

**Purpose of this document:** hand this to an AI coding agent (Antigravity or similar) working directly in the `Mexar` repository (`github.com/devrajsinh2012/Mexar`). This is Phase 2 only: it brings in real documents and real queries so the numbers in the paper are reproducible. Assumes Phase 1 (architecture fixes: TF-IDF/NER guardrail, HNSW index, DeBERTa faithfulness scorer) is already done and verified.

**Presentation date:** July 30-31, 2026. Target for this phase: days 4-11 (about a week).

---

## 2.0 Scope decision (already agreed with Dev)

Target **500-600 total documents** across the three domains for the presentation, not the 5,226 stated in the current paper draft. This is a resource-constrained pilot, and the paper's dataset section (IV-A) gets rewritten to say so honestly. Query sets are also reduced and single-annotator (Dev/Om/Jay), not the 900+600 two-expert-annotated set currently described. This is a normal, defensible thing to disclose in a paper, and far safer than presenting numbers nobody can reproduce live.

**Target split:**

| Domain | Target docs | Source |
|---|---|---|
| Medical | ~220 | PubMed Central OA subset |
| Legal | ~150 | CourtListener (Free Law Project) |
| Financial | ~130 | SEC EDGAR full-text search |
| **Total** | **~500** | |

**Important for the agent:** these fetch scripts hit external APIs (PubMed E-utilities, CourtListener, SEC EDGAR) that are outside a typical restricted sandbox's allowed network domains. Run these scripts in Dev's own local dev environment or a CI runner with normal internet access, not inside a network-restricted container.

---

## 2.1 Medical corpus — PubMed Central OA

**New script:** `backend/scripts/fetch_pubmed.py`

- Use the NCBI E-utilities API (`esearch` + `efetch`), no key required for low-volume use, but request one from NCBI if fetching more than 3 requests/sec.
- Query terms per subdomain, run three separate searches and cap results:
  - `"cardiology treatment guideline"[Title/Abstract] AND "open access"[filter]`
  - `"oncology treatment protocol"[Title/Abstract] AND "open access"[filter]`
  - `"internal medicine diagnostic criteria"[Title/Abstract] AND "open access"[filter]`
- Pull ~75 docs per subdomain (≈220 total).
- Save each as plain text (abstract + body if available via the OA subset bulk XML) into `test_data/medical_real/`, one file per document, named by PMCID, e.g. `PMC1234567.txt`.
- Respect NCBI's rate limits (3 req/sec without an API key, 10/sec with one) and identify yourself via the `email` parameter on every request, per NCBI's usage policy.
- Log a manifest file `test_data/medical_real/manifest.json` mapping PMCID → title → subdomain → source URL, this becomes supporting material for the paper's dataset section and makes the corpus auditable.

**Skeleton:**
```python
"""
MEXAR - PubMed Central OA fetcher for the medical corpus.
Run this locally (not in a network-restricted sandbox).
"""
import requests
import time
import json
import os

NCBI_EMAIL = "your_email@example.com"  # required by NCBI usage policy
OUTPUT_DIR = "test_data/medical_real"
SEARCH_TERMS = {
    "cardiology": '"cardiology treatment guideline"[Title/Abstract] AND "open access"[filter]',
    "oncology": '"oncology treatment protocol"[Title/Abstract] AND "open access"[filter]',
    "internal_medicine": '"internal medicine diagnostic criteria"[Title/Abstract] AND "open access"[filter]',
}
DOCS_PER_SUBDOMAIN = 75

def esearch(term, retmax):
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {"db": "pmc", "term": term, "retmax": retmax, "retmode": "json", "email": NCBI_EMAIL}
    r = requests.get(url, params=params)
    r.raise_for_status()
    return r.json()["esearchresult"]["idlist"]

def efetch_fulltext(pmc_id):
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {"db": "pmc", "id": pmc_id, "rettype": "full", "retmode": "xml", "email": NCBI_EMAIL}
    r = requests.get(url, params=params)
    r.raise_for_status()
    return r.text  # parse out body text with an XML parser before saving as plain text

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    manifest = []
    for subdomain, term in SEARCH_TERMS.items():
        ids = esearch(term, DOCS_PER_SUBDOMAIN)
        for pmc_id in ids:
            time.sleep(0.34)  # stay under 3 req/sec
            try:
                xml_text = efetch_fulltext(pmc_id)
                # TODO: parse XML body text out with e.g. lxml, strip tags, save plain text
                plain_text = xml_text  # placeholder, replace with real extraction
                out_path = os.path.join(OUTPUT_DIR, f"PMC{pmc_id}.txt")
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(plain_text)
                manifest.append({"pmc_id": pmc_id, "subdomain": subdomain, "path": out_path})
            except Exception as e:
                print(f"Failed to fetch PMC{pmc_id}: {e}")
    with open(os.path.join(OUTPUT_DIR, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Fetched {len(manifest)} medical documents.")

if __name__ == "__main__":
    main()
```
The agent should replace the placeholder XML-to-text extraction with a real parser (e.g. `lxml` or `BeautifulSoup`) that pulls the `<body>` text out of the PMC XML format and strips markup, don't save raw XML as the "plain text" corpus.

---

## 2.2 Legal corpus — CourtListener

**New script:** `backend/scripts/fetch_courtlistener.py`

- Use the CourtListener REST API (`https://www.courtlistener.com/api/rest/v4/`), requires a free account and API token (set as `COURTLISTENER_TOKEN` env var).
- Pull opinions/case summaries across contract law, IP, and corporate governance search terms, plus a handful of statutory/regulatory text pages if accessible via their `opinions` and `search` endpoints.
- Target ~50 docs per subdomain (≈150 total).
- Save the opinion text (or summary if full text is very long, truncate to a reasonable chunking size, e.g. first 3000 words) into `test_data/legal_real/`, one file per case, named by CourtListener opinion ID.
- Same manifest pattern as 2.1: `test_data/legal_real/manifest.json` with case name, subdomain, court, date, source URL.

**Skeleton:**
```python
"""
MEXAR - CourtListener fetcher for the legal corpus.
Requires COURTLISTENER_TOKEN env var. Run locally.
"""
import requests
import os
import json

TOKEN = os.environ["COURTLISTENER_TOKEN"]
HEADERS = {"Authorization": f"Token {TOKEN}"}
BASE_URL = "https://www.courtlistener.com/api/rest/v4"
OUTPUT_DIR = "test_data/legal_real"
SEARCH_TERMS = {
    "contract_law": "breach of contract damages",
    "intellectual_property": "patent infringement trademark",
    "corporate_governance": "fiduciary duty shareholder derivative",
}
DOCS_PER_SUBDOMAIN = 50

def search_opinions(query, count):
    url = f"{BASE_URL}/search/"
    params = {"q": query, "type": "o", "order_by": "score desc"}
    results = []
    while len(results) < count:
        r = requests.get(url, headers=HEADERS, params=params)
        r.raise_for_status()
        data = r.json()
        results.extend(data["results"])
        if not data.get("next"):
            break
        url = data["next"]
        params = {}
    return results[:count]

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    manifest = []
    for subdomain, term in SEARCH_TERMS.items():
        opinions = search_opinions(term, DOCS_PER_SUBDOMAIN)
        for op in opinions:
            text = op.get("plain_text") or op.get("snippet", "")
            if not text:
                continue
            op_id = op.get("id") or op.get("cluster_id")
            out_path = os.path.join(OUTPUT_DIR, f"case_{op_id}.txt")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text[:15000])  # cap length
            manifest.append({
                "id": op_id, "subdomain": subdomain,
                "case_name": op.get("caseName", ""), "path": out_path,
            })
    with open(os.path.join(OUTPUT_DIR, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Fetched {len(manifest)} legal documents.")

if __name__ == "__main__":
    main()
```
The agent should verify the actual current CourtListener v4 search response schema (field names like `plain_text` vs `snippet` vs a separate opinion-text endpoint may have changed) before trusting this skeleton verbatim, API responses drift over time.

---

## 2.3 Financial corpus — SEC EDGAR

**New script:** `backend/scripts/fetch_secedgar.py`

- Use SEC EDGAR's full-text search API (`https://efts.sec.gov/LATEST/search-index`) and the regular filing index to pull excerpts from 10-K filings and select analyst/accounting-standard documents.
- **Mandatory:** SEC requires a descriptive `User-Agent` header identifying the requester (name + email) on every request, or you get blocked. Format: `"YourName YourEmail@example.com"`.
- Target ~130 docs, mixing filing sections (MD&A, risk factors) rather than entire 10-Ks, which are too long and would dominate the corpus disproportionately relative to medical/legal document sizes.
- Save into `test_data/financial_real/`, named by CIK + accession number.
- Same manifest pattern.

**Skeleton:**
```python
"""
MEXAR - SEC EDGAR fetcher for the financial corpus.
Run locally. Requires a descriptive User-Agent per SEC's fair access policy.
"""
import requests
import os
import json
import time

USER_AGENT = "Devrajsinh Gohil djgohil2012@gmail.com"  # SEC requires this format
HEADERS = {"User-Agent": USER_AGENT}
OUTPUT_DIR = "test_data/financial_real"
SEARCH_TERMS = ["risk factors", "management discussion analysis", "GAAP IFRS accounting standards"]
DOCS_PER_TERM = 45  # ~130 total across 3 terms

def full_text_search(query, count):
    url = "https://efts.sec.gov/LATEST/search-index?q=%22{}%22&forms=10-K".format(query.replace(" ", "+"))
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    hits = r.json().get("hits", {}).get("hits", [])
    return hits[:count]

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    manifest = []
    for term in SEARCH_TERMS:
        hits = full_text_search(term, DOCS_PER_TERM)
        for hit in hits:
            time.sleep(0.2)  # be polite to SEC's rate limits
            source = hit.get("_source", {})
            cik = source.get("ciks", ["unknown"])[0]
            accession = source.get("adsh", "unknown")
            # TODO: fetch actual filing document text via the filing index URL,
            # this skeleton only captures search-hit metadata, not full text.
            excerpt = source.get("display_names", [""])[0]
            out_path = os.path.join(OUTPUT_DIR, f"{cik}_{accession}.txt")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(excerpt)
            manifest.append({"cik": cik, "accession": accession, "term": term, "path": out_path})
    with open(os.path.join(OUTPUT_DIR, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Fetched {len(manifest)} financial documents.")

if __name__ == "__main__":
    main()
```
This one needs the most work from the agent: the full-text search endpoint returns hit metadata, not the actual filing body text. The agent needs to follow through to the actual filing document (via the CIK/accession-number-derived URL under `https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/`) and extract the relevant section text (MD&A, risk factors) from the filing HTML, rather than saving just the search snippet.

---

## 2.4 Ingestion format

Each fetch script should output files in whatever format `backend/modules/data_validator.py`'s parsers already expect, check the `.txt`/`.json` handling there first, don't invent a new schema. Simplest path: one `.txt` file per document, plain text body, filename as a stable ID, so the existing agent-compilation flow (`KnowledgeCompiler.compile()`) can ingest them exactly like a user-uploaded file batch, no special-casing needed in the app itself.

---

## 2.5 Query set authoring

Create `test_data/query_sets/{medical,legal,financial}_queries.json` with this schema:
```json
[
  {
    "query": "What is the first-line treatment for stage 2 hypertension?",
    "domain": "medical",
    "is_in_domain": true,
    "expected_source_docs": ["PMC1234567"],
    "annotator": "devrajsinh"
  }
]
```
- ~40-50 in-domain queries per domain (authored by whoever on the team is most comfortable with that domain, split the load across Dev/Om/Jay).
- ~25-35 out-of-domain queries per domain-pair (medical→legal, legal→financial, etc.) for guardrail testing, reusing the structure already implied by Table IV in the paper, just at a smaller count.
- Single annotator per query is fine at this scale, note this explicitly as a limitation instead of claiming inter-annotator agreement you didn't actually measure.

---

## 2.6 Suggested paper text for Section IV-A

Drafted now so it's ready when the paper gets updated in Phase 4:

> *"Due to resource constraints, this study evaluates on a reduced corpus of approximately 500 documents (220 medical, 150 legal, 130 financial) sourced from PubMed Central Open Access, CourtListener, and SEC EDGAR respectively, with 120-150 in-domain queries and approximately 90 out-of-domain queries authored by the paper's co-authors. We report this as a pilot-scale evaluation and note that a larger, multi-annotator study is needed to confirm these findings generalize at production scale."*

Adjust the exact counts once the fetch scripts finish and real numbers are known.

---

## Summary of new files in Phase 2

| File | Purpose |
|---|---|
| `backend/scripts/fetch_pubmed.py` | pulls ~220 medical docs |
| `backend/scripts/fetch_courtlistener.py` | pulls ~150 legal docs |
| `backend/scripts/fetch_secedgar.py` | pulls ~130 financial docs |
| `test_data/medical_real/`, `test_data/legal_real/`, `test_data/financial_real/` | fetched corpora + manifests |
| `test_data/query_sets/*.json` | authored query sets with domain/expected-source labels |

---

## What Phase 2 does NOT cover (handled later)

- Running `baseline_runner.py`, `benchmark_runner.py`, `guardrail_analysis.py`, `statistical_tests.py` against this real data to produce actual paper numbers, that's Phase 3.
- Rewriting Tables I-V and Figures 2-4 in the paper, and rehearsing the live demo, that's Phase 4.

Once Phase 1 (architecture) and Phase 2 (data) are both done, the evaluation scripts already in `backend/evaluation/` should be able to run against real inputs with minimal further changes, since Phase 1 kept their function signatures stable.
