"""
MEXAR - Annotate Expected Source Docs for Query Sets.
Populates expected_source_docs in medical_queries.json, legal_queries.json, and financial_queries.json
by matching in-domain queries against actual downloaded document manifests in test_data/*_real/.
"""
import os
import sys
import json
import logging
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def annotate_query_set(domain: str):
    manifest_path = REPO_ROOT / "test_data" / f"{domain}_real" / "manifest.json"
    queries_path = REPO_ROOT / "test_data" / "query_sets" / f"{domain}_queries.json"

    if not manifest_path.exists():
        logger.error(f"Manifest not found: {manifest_path}")
        return

    if not queries_path.exists():
        logger.error(f"Queries file not found: {queries_path}")
        return

    manifest = []
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            manifest = []

    domain_dir = REPO_ROOT / "test_data" / f"{domain}_real"
    if not manifest:
        logger.info(f"Manifest empty or missing for {domain}. Scanning .txt files in {domain_dir}...")
        for txt_file in domain_dir.glob("*.txt"):
            doc_id = txt_file.stem
            manifest.append({"id": doc_id, "path": str(txt_file)})

    # Also update and save manifest.json if it was empty
    if manifest and manifest_path.exists() and manifest_path.stat().st_size <= 2:
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    with open(queries_path, "r", encoding="utf-8") as f:
        queries = json.load(f)

    # Collect document texts and doc IDs
    doc_ids = []
    doc_texts = []

    for item in manifest:
        # Determine ID key
        doc_id = item.get("id") or item.get("pmc_id") or item.get("opinion_id") or item.get("doc_id") or item.get("file_name")
        if not doc_id and "path" in item:
            doc_id = os.path.basename(item["path"]).replace(".txt", "")

        raw_path = item.get("path", "")
        txt_file_path = Path(raw_path) if raw_path else None
        if txt_file_path and not txt_file_path.is_absolute():
            txt_file_path = REPO_ROOT / raw_path

        text_content = item.get("title", "") + " " + item.get("case_name", "") + " " + item.get("snippet", "") + " " + item.get("summary", "")

        if txt_file_path and txt_file_path.exists():
            try:
                text_content += " " + txt_file_path.read_text(encoding="utf-8")[:10000]
            except Exception:
                pass

        if doc_id:
            doc_ids.append(str(doc_id))
            doc_texts.append(text_content)

    if not doc_texts:
        logger.error(f"No document text found for domain '{domain}'")
        return

    vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
    doc_tfidf = vectorizer.fit_transform(doc_texts)

    annotated_count = 0
    for query_entry in queries:
        # Only annotate in-domain queries for this domain
        if query_entry.get("is_in_domain", True) and query_entry.get("domain", domain) == domain:
            query_str = query_entry["query"]
            q_vec = vectorizer.transform([query_str])
            sims = cosine_similarity(q_vec, doc_tfidf)[0]

            # Top 2 matching document IDs above similarity 0.05
            top_indices = sims.argsort()[::-1][:2]
            matched_docs = [doc_ids[idx] for idx in top_indices if sims[idx] > 0.01]

            if not matched_docs:
                matched_docs = [doc_ids[top_indices[0]]]

            query_entry["expected_source_docs"] = matched_docs
            annotated_count += 1
        else:
            query_entry["expected_source_docs"] = []

    with open(queries_path, "w", encoding="utf-8") as f:
        json.dump(queries, f, indent=2)

    logger.info(f"Annotated {annotated_count} in-domain queries in {queries_path.name}")


def main():
    for domain in ["medical", "legal", "financial"]:
        annotate_query_set(domain)


if __name__ == "__main__":
    main()
