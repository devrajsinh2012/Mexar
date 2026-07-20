"""
MEXAR - Domain Signature Construction
Implements Section III-A: TF-IDF lexical signature + NER entity signature.

build_domain_signature() produces Sigma = Sigma_lex ∪ Sigma_ent, kept separate
for inspection. The 'combined' list is stored in the domain_signature JSONB column
on agents; 'lexical_weights' is stored in domain_signature_weights for optional
weighted Jaccard use later.
"""
from typing import List, Dict, Set, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
import spacy
import logging

logger = logging.getLogger(__name__)

# Lazy-loaded spaCy model (avoid paying load cost at import time)
_nlp = None

# Entity labels relevant to professional domains (medical / legal / financial)
RELEVANT_ENTITY_LABELS = {"ORG", "LAW", "PRODUCT", "GPE", "PERSON", "NORP", "EVENT", "FAC"}


def get_nlp():
    """Lazy-load and cache the spaCy en_core_web_sm model."""
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy en_core_web_sm loaded for domain guardrail NER.")
        except OSError:
            logger.error(
                "spaCy model 'en_core_web_sm' not found. "
                "Run: python -m spacy download en_core_web_sm"
            )
            raise
    return _nlp


def build_tfidf_signature(
    documents: List[str],
    top_n: int = 100,
    tau_tf: float = 0.0,
) -> List[Tuple[str, float]]:
    """
    Eq. 1: w(t, D) = tf(t, D) * log(|D| / |{d in D : t in d}|)

    Returns top_n (term, weight) pairs above tau_tf, sorted descending by weight.

    Args:
        documents: List of per-source document texts.
        top_n: Maximum number of terms to return.
        tau_tf: Minimum TF-IDF weight threshold.

    Returns:
        List of (term, weight) tuples sorted by weight descending.
    """
    if not documents:
        return []

    # TF-IDF requires a corpus of multiple documents so IDF is non-degenerate.
    # If only a single document is provided (e.g. one uploaded file), split it
    # into paragraph-level pseudo-documents.
    if len(documents) < 2:
        documents = _split_into_pseudo_documents(documents[0]) if documents[0] else []
        if not documents:
            return []

    vectorizer = TfidfVectorizer(
        max_features=2000,
        stop_words="english",
        ngram_range=(1, 2),  # unigrams + bigrams for better domain specificity
        min_df=1,
    )
    try:
        matrix = vectorizer.fit_transform(documents)
    except ValueError as e:
        logger.warning(f"TF-IDF vectorizer failed: {e}")
        return []

    # Sum TF-IDF weights across all documents for each term
    scores = matrix.sum(axis=0).A1
    terms = vectorizer.get_feature_names_out()

    pairs = [(t, float(s)) for t, s in zip(terms, scores) if s > tau_tf]
    pairs.sort(key=lambda x: x[1], reverse=True)
    return pairs[:top_n]


def _split_into_pseudo_documents(text: str, chunk_size: int = 500) -> List[str]:
    """Split a single long text into word-chunk pseudo-documents for TF-IDF."""
    words = text.split()
    chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
    return chunks or [text]


def extract_ner_entities(
    documents: List[str],
    tau_ent: int = 2,
    max_docs_to_scan: int = 200,
) -> List[str]:
    """
    Extracts named entities (Sigma_ent) appearing in at least tau_ent documents.

    Capped at max_docs_to_scan for latency (spaCy NER is not free at compile time).
    Per-document de-duplication avoids inflating doc-frequency for repeated mentions.

    Args:
        documents: List of per-source document texts.
        tau_ent: Minimum document frequency for an entity to be included.
        max_docs_to_scan: Cap on number of documents processed (speed/latency trade-off).

    Returns:
        List of entity strings appearing in >= tau_ent documents.
    """
    if not documents:
        return []

    nlp = get_nlp()
    doc_freq: Dict[str, int] = {}

    for doc_text in documents[:max_docs_to_scan]:
        seen_in_this_doc: Set[str] = set()
        try:
            for ent in nlp(doc_text[:5000]).ents:  # cap per-doc chars for speed
                if ent.label_ in RELEVANT_ENTITY_LABELS:
                    key = ent.text.lower().strip()
                    if key and len(key) > 2 and key not in seen_in_this_doc:
                        seen_in_this_doc.add(key)
        except Exception as e:
            logger.warning(f"NER pass failed for a document: {e}")
            continue

        for key in seen_in_this_doc:
            doc_freq[key] = doc_freq.get(key, 0) + 1

    return [k for k, v in doc_freq.items() if v >= tau_ent]


def build_domain_signature(
    documents: List[str],
    tau_tf: float = 0.0,
    tau_ent: int = 2,
    top_n_lexical: int = 100,
) -> Dict[str, object]:
    """
    Returns Sigma = Sigma_lex ∪ Sigma_ent (Section III-A).

    The two components are kept separate for inspection and future weighted Jaccard use.

    Args:
        documents: List of per-source document texts (NOT a single concatenated string).
        tau_tf: TF-IDF weight threshold for lexical terms.
        tau_ent: Minimum doc-frequency for NER entities.
        top_n_lexical: Number of top TF-IDF terms to retain.

    Returns:
        Dict with keys:
            - 'lexical': list of top TF-IDF terms
            - 'lexical_weights': dict of {term: weight}
            - 'entities': list of NER entities meeting tau_ent threshold
            - 'combined': sorted list of all unique terms (lexical ∪ entities)
    """
    logger.info(
        f"Building domain signature from {len(documents)} documents "
        f"(tau_tf={tau_tf}, tau_ent={tau_ent}, top_n={top_n_lexical})"
    )

    lexical_pairs = build_tfidf_signature(documents, top_n=top_n_lexical, tau_tf=tau_tf)
    lexical_terms = [t for t, _ in lexical_pairs]
    lexical_weights = {t: w for t, w in lexical_pairs}

    entities = extract_ner_entities(documents, tau_ent=tau_ent)

    combined = sorted(set(lexical_terms) | set(entities))

    logger.info(
        f"Domain signature built: {len(lexical_terms)} lexical terms, "
        f"{len(entities)} NER entities, {len(combined)} combined."
    )

    return {
        "lexical": lexical_terms,
        "lexical_weights": lexical_weights,
        "entities": entities,
        "combined": combined,
    }
