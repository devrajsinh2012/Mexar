# MEXAR Phase 1 — Architecture Fixes to Match the Paper

**Purpose of this document:** hand this to an AI coding agent (Antigravity or similar) working directly in the `Mexar` repository (`github.com/devrajsinh2012/Mexar`). This is Phase 1 only: it closes the gap between what the paper *"Hybrid Retrieval and Claim Verification: An Empirical Study of Constrained RAG for High-Stakes Professional Domains"* claims about the system's architecture, and what the code currently does. No dataset work in this document, that's Phase 2, handled separately.

**Presentation date:** July 30-31, 2026. Target for this phase: 3 days.

**Ground rule for the agent:** every change below must keep the app deployable on the current stack (FastAPI backend on Hugging Face Spaces, Supabase Postgres + pgvector, React frontend on Vercel). Don't introduce services that need infra Dev doesn't already have.

---

## 1.0 Preconditions

- Add to `backend/requirements.txt`:
  ```
  scikit-learn>=1.4.0
  spacy>=3.7.0
  ```
- After install, download the small English model: `python -m spacy download en_core_web_sm`. Add this as a step in `Dockerfile` so it survives Hugging Face Spaces rebuilds.
- Verify the pgvector extension version on the Supabase project supports HNSW (needs pgvector >= 0.5.0). Run `SELECT extversion FROM pg_extension WHERE extname = 'vector';`. If below 0.5.0, run `ALTER EXTENSION vector UPDATE;` before touching the index migration in 1.2.

---

## 1.1 Domain Guardrail: replace the heuristic with real TF-IDF + NER + Jaccard

**Why:** Paper Section III-A defines the guardrail as TF-IDF term weighting (Eq. 1), NER-extracted domain entities, and Jaccard similarity between query and signature (Eq. 2). The current `_check_guardrail()` in `backend/modules/reasoning_engine.py` is a hand-tuned fuzzy-string-match heuristic with arbitrary bonus weights and no TF-IDF or NER anywhere. This needs to become the real thing.

**New file: `backend/utils/domain_signature.py`**

```python
"""
MEXAR - Domain Signature Construction
Implements Section III-A: TF-IDF lexical signature + NER entity signature.
"""
from typing import List, Dict, Set, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
import spacy
import logging

logger = logging.getLogger(__name__)
_nlp = None

def get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp

# Entity labels relevant to professional domains (medical/legal/financial)
RELEVANT_ENTITY_LABELS = {"ORG", "LAW", "PRODUCT", "GPE", "PERSON", "NORP", "EVENT", "FAC"}

def build_tfidf_signature(documents: List[str], top_n: int = 100, tau_tf: float = 0.0) -> List[Tuple[str, float]]:
    """
    Eq. 1: w(t, D) = tf(t, D) * log(|D| / |{d in D : t in d}|)
    Returns top_n (term, weight) pairs above tau_tf, sorted descending by weight.
    """
    if not documents or len(documents) < 2:
        # TF-IDF needs a corpus of multiple "documents" to compute IDF meaningfully.
        # If compiling from a single uploaded file, split it into paragraph-level
        # pseudo-documents so IDF is not degenerate.
        documents = _split_into_pseudo_documents(documents[0]) if documents else []

    vectorizer = TfidfVectorizer(
        max_features=2000,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1,
    )
    matrix = vectorizer.fit_transform(documents)
    scores = matrix.sum(axis=0).A1
    terms = vectorizer.get_feature_names_out()
    pairs = [(t, float(s)) for t, s in zip(terms, scores) if s > tau_tf]
    pairs.sort(key=lambda x: x[1], reverse=True)
    return pairs[:top_n]

def _split_into_pseudo_documents(text: str, chunk_size: int = 500) -> List[str]:
    words = text.split()
    return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)] or [text]

def extract_ner_entities(documents: List[str], tau_ent: int = 2, max_docs_to_scan: int = 200) -> List[str]:
    """
    Extracts named entities appearing in at least tau_ent documents.
    Capped at max_docs_to_scan for latency (spaCy is not free at compile time).
    """
    nlp = get_nlp()
    doc_freq: Dict[str, int] = {}
    for doc_text in documents[:max_docs_to_scan]:
        seen_in_this_doc: Set[str] = set()
        for ent in nlp(doc_text[:5000]).ents:  # cap per-doc length for speed
            if ent.label_ in RELEVANT_ENTITY_LABELS:
                key = ent.text.lower().strip()
                if key and key not in seen_in_this_doc:
                    seen_in_this_doc.add(key)
        for key in seen_in_this_doc:
            doc_freq[key] = doc_freq.get(key, 0) + 1
    return [k for k, v in doc_freq.items() if v >= tau_ent]

def build_domain_signature(
    documents: List[str],
    tau_tf: float = 0.0,
    tau_ent: int = 2,
    top_n_lexical: int = 100,
) -> Dict[str, List]:
    """Returns Sigma = Sigma_lex ∪ Sigma_ent as described in Section III-A, kept separate for inspection."""
    lexical_pairs = build_tfidf_signature(documents, top_n=top_n_lexical, tau_tf=tau_tf)
    lexical_terms = [t for t, _ in lexical_pairs]
    entities = extract_ner_entities(documents, tau_ent=tau_ent)
    return {
        "lexical": lexical_terms,
        "lexical_weights": {t: w for t, w in lexical_pairs},
        "entities": entities,
        "combined": sorted(set(lexical_terms) | set(e for e in entities)),
    }
```

**Modify `backend/modules/knowledge_compiler.py`:**
Replace `_extract_domain_signature()` so it calls `build_domain_signature()` from the new module, passing in the raw per-source-document text list (not the flattened `text_context` string, we need per-document granularity for TF-IDF's document-frequency term to mean anything). Store the result's `combined` list in the existing `domain_signature` JSONB column, and add the `lexical_weights` dict to a **new** JSONB column (see migration below) so the guardrail can compute a weighted Jaccard rather than a flat one if useful later.

**New migration** (Alembic or raw SQL depending on how `backend/migrations` is structured, check `backend/migrations/README.md` for the convention already in use):
```sql
ALTER TABLE agents ADD COLUMN IF NOT EXISTS domain_signature_weights JSONB;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS domain_entities JSONB;
```

**Rewrite `_check_guardrail()` in `backend/modules/reasoning_engine.py`:**
Delete the fuzzy-match/bonus-score implementation entirely. Replace with real Eq. 2:

```python
def _check_guardrail(self, query: str, domain_signature: List[str], prompt_analysis: Dict[str, Any]) -> Tuple[bool, float]:
    """Eq. 2: sim(q, Sigma) = |Phi(q) ∩ Sigma| / |Phi(q)|"""
    from utils.domain_signature import get_nlp
    nlp = get_nlp()
    query_doc = nlp(query.lower())
    # Phi(q): lemmatized content tokens, excluding stopwords/punctuation
    phi_q = {
        tok.lemma_ for tok in query_doc
        if not tok.is_stop and not tok.is_punct and len(tok.text) > 2
    }
    sigma = set(s.lower() for s in (domain_signature or []))

    if not phi_q:
        return False, 0.0

    intersection = phi_q & sigma
    score = len(intersection) / len(phi_q)

    is_in_domain = score >= self.DOMAIN_SIMILARITY_THRESHOLD
    logger.info(f"Guardrail: sim={score:.3f}, |Phi(q)|={len(phi_q)}, |intersection|={len(intersection)}, in_domain={is_in_domain}")
    return is_in_domain, score
```

**Tune `DOMAIN_SIMILARITY_THRESHOLD`:** the current 0.05 was calibrated against the *old* heuristic scorer, it will not transfer to real Jaccard similarity, which tends to produce lower absolute values on short queries. Don't guess this: after wiring the new guardrail, run `backend/evaluation/guardrail_analysis.py` against a small hand-labeled set of ~20 in-domain and ~20 out-of-domain queries per existing test_data domain, sweep the threshold from 0.05 to 0.4 in steps of 0.05, and pick the value that maximizes F1. Record that sweep, it becomes supporting evidence for Table IV in the paper instead of a guessed constant.

**Acceptance test:** for the medical test agent, a query like "what is the recommended treatment for stage 2 hypertension" should be accepted; a query like "how do I file a small claims lawsuit" should be rejected. Log both the old and new guardrail score during a transition period to sanity-check before removing the old code path.

---

## 1.2 Vector index: IVFFlat → HNSW

**Why:** Paper Section III-B explicitly claims HNSW indexing. The current migration (`backend/migrations/hybrid_search_function.sql`, lines ~98-101) creates an IVFFlat index instead.

**New migration file** `backend/migrations/switch_to_hnsw_index.sql`:
```sql
-- Drop the old IVFFlat index
DROP INDEX IF EXISTS idx_document_chunks_embedding;

-- Create HNSW index to match paper Section III-B
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw
ON document_chunks USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

COMMENT ON INDEX idx_document_chunks_embedding_hnsw IS
  'HNSW index for cosine similarity search, m=16, ef_construction=64 (Section III-B)';
```
Apply via `Supabase:apply_migration` (or however existing migrations are run, check for a runner script referenced in `backend/migrations/README.md`) rather than editing the old file, so history is preserved.

**Note for the agent:** HNSW build time scales worse than IVFFlat with corpus size, but at the 500-600 document / few-thousand-chunk scale planned for the presentation, this is a non-issue. No further tuning needed.

**Acceptance test:** `\d document_chunks` in psql (or `SELECT indexdef FROM pg_indexes WHERE tablename = 'document_chunks';`) should show the HNSW index, not IVFFlat. Re-run a handful of existing queries and confirm retrieval still returns coherent top-5 chunks (HNSW is approximate, results may reorder slightly versus IVFFlat, that's expected and fine).

---

## 1.3 RRF weighting: reconcile code and paper

**Why:** Paper Eq. 5 is unweighted RRF. `backend/migrations/hybrid_search_function.sql` applies a 0.6 semantic / 0.4 keyword weighting inside the SQL function.

**Decision for this project (recommended, don't re-litigate):** keep the 0.6/0.4 weighting in code, it's a reasonable and defensible design choice, and update the paper instead. This is less risky than ripping out a tuned weighting under time pressure. The agent does not need to touch `hybrid_search_function.sql` for this item, just flag it in a "paper edits needed" note for later.

If Dev instead decides to match the paper exactly, the one-line change is setting `semantic_weight := 0.5; keyword_weight := 0.5;` in that SQL function, but this is **not** the default action, don't do it unless explicitly told.

---

## 1.4 Faithfulness verification: make DeBERTa-v3 NLI the real, primary signal

**Why:** this is the most important fix. Paper Section III-C and the entire Related Work argument against LLM-judging-LLM circularity claim the production system verifies claims with "an NLI model (DeBERTa-v3-large fine-tuned on MNLI)" using per-document max entailment (Eq. 6). In the actual code:
- The primary confidence-driving call in `reasoning_engine.reason()` (Step 6) is `self.faithfulness_scorer.score(answer, context)`, which is `FaithfulnessScorer` in `backend/utils/faithfulness.py`, an LLM (Groq) extracting claims and then Groq again answering YES/NO. That's exactly the circularity the paper argues against.
- The actual NLI model in the repo, `BartNLIScorer`, uses `facebook/bart-large-mnli`, not DeBERTa-v3-large, and it's computed only as a side "reviewer feedback" score (`bart_nli_result` in `reason()`), it never feeds the confidence calculation.
- The NLI scorer concatenates all retrieved context into a single premise string, it does not implement the per-document max in Eq. 6.

**Model choice:** use `cross-encoder/nli-deberta-v3-large` from Hugging Face. This is a DeBERTa-v3-large architecture fine-tuned specifically for NLI (SNLI + MultiNLI), it is the standard, citable checkpoint people mean when they say "DeBERTa-v3-large fine-tuned on MNLI" in RAG faithfulness papers, and it loads cleanly through `sentence-transformers`'s `CrossEncoder` class, which is already a dependency.

**Modify `backend/utils/faithfulness.py`:** replace the `BartNLIScorer` class with:

```python
class DebertaNLIScorer:
    """
    Primary faithfulness verifier per Section III-C.
    Per-claim, per-document max entailment probability (Eq. 6),
    aggregated as the fraction of claims exceeding tau_ent (Eq. 7).
    """
    LABEL_MAP = {0: "contradiction", 1: "entailment", 2: "neutral"}  # verify against model card at load time
    TAU_ENT = 0.7

    def __init__(self):
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder
            logger.info("Loading cross-encoder/nli-deberta-v3-large...")
            self._model = CrossEncoder("cross-encoder/nli-deberta-v3-large")
            logger.info("DeBERTa-v3 NLI model loaded.")
        return self._model

    def score(self, answer: str, context_documents: List[str]) -> FaithfulnessResult:
        """
        context_documents: list of individual retrieved chunk texts (NOT concatenated),
        so per-document max in Eq. 6 is meaningful.
        """
        import re
        import numpy as np

        if not answer or not context_documents:
            return FaithfulnessResult(score=1.0, total_claims=0, supported_claims=0, unsupported_claims=[])

        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', answer) if len(s.strip()) > 15][:10]
        if not sentences:
            return FaithfulnessResult(score=1.0, total_claims=0, supported_claims=0, unsupported_claims=[])

        supported = 0
        unsupported = []

        for sentence in sentences:
            pairs = [(doc[:2000], sentence) for doc in context_documents]
            scores = self.model.predict(pairs)  # shape: (n_docs, 3) logits/probs per label
            probs = self._softmax(scores)
            entailment_idx = 1  # confirm this matches the model's actual label order at integration time
            max_entailment = float(np.max(probs[:, entailment_idx]))
            if max_entailment > self.TAU_ENT:
                supported += 1
            else:
                unsupported.append(sentence)

        score = supported / len(sentences)
        return FaithfulnessResult(
            score=round(score, 3),
            total_claims=len(sentences),
            supported_claims=supported,
            unsupported_claims=unsupported[:5],
        )

    @staticmethod
    def _softmax(x):
        import numpy as np
        e_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
        return e_x / e_x.sum(axis=-1, keepdims=True)
```

**Important integration detail for the agent:** verify `cross-encoder/nli-deberta-v3-large`'s actual `id2label` mapping from its `config.json` on first load and print it to logs, cross-encoder NLI checkpoints don't always use the same label order. Don't hardcode `entailment_idx = 1` blindly, confirm it, this is exactly the kind of silent bug that would quietly invalidate the reported faithfulness numbers.

**Modify `backend/modules/reasoning_engine.py`, `reason()` method:**
- Rename the old `FaithfulnessScorer` usage. Keep the class in the codebase (don't delete it), but relabel its role: it becomes the **"LLM-as-judge baseline"** used for baseline comparison tables (this is genuinely useful, RAGAS-style LLM self-eval is a legitimate baseline to compare against in Table I/III, just not the production signal).
- Swap Step 6 to call `self.deberta_nli_scorer.score(answer, [c.content for c in top_chunks])` (passing the list of individual chunks, not the concatenated `context` string) as the **primary** `faithfulness_result` used in `_calculate_confidence()` and in the returned `explainability` payload.
- Keep computing the old LLM-based score too, but store it under a clearly-labeled `"llm_judge_baseline_score"` key in `explainability.confidence_breakdown`, not as the headline faithfulness number.

**Acceptance test:** feed a known-hallucinated answer (write one manually, e.g. an answer that states a fabricated statistic not present in any retrieved chunk) through the pipeline and confirm the DeBERTa scorer flags it as unsupported. Feed a fully-grounded answer and confirm it scores above `TAU_ENT`. Compare against the LLM-judge baseline score on the same pair, they should usually agree, but if they diverge a lot on the same input, that's worth investigating before trusting either for the paper's numbers.

---

## 1.5 Wiring check

After 1.1-1.4 are done, re-run the existing `backend/evaluation/baseline_runner.py` and `backend/evaluation/benchmark_runner.py` against the current small `test_data/` samples (not for final numbers, just as a smoke test) and confirm nothing throws. Fix any interface mismatches from the `context: str` → `context_documents: List[str]` signature change in the faithfulness scorer, other call sites (`evaluation/metrics.py`, `_run_baseline()` in `reasoning_engine.py`) pass a concatenated string today and will need the same list-of-chunks treatment.

---

## Summary of files touched in Phase 1

| File | Change |
|---|---|
| `backend/requirements.txt` | add scikit-learn, spacy |
| `backend/Dockerfile` | add spacy model download step |
| `backend/utils/domain_signature.py` | **new** — TF-IDF + NER signature builder |
| `backend/modules/knowledge_compiler.py` | `_extract_domain_signature()` rewritten to use new module |
| `backend/modules/reasoning_engine.py` | `_check_guardrail()` rewritten to real Jaccard; Step 6 rewired to DeBERTa scorer |
| `backend/utils/faithfulness.py` | `BartNLIScorer` replaced with `DebertaNLIScorer` (per-doc max, Eq. 6/7) |
| `backend/migrations/switch_to_hnsw_index.sql` | **new** — HNSW index migration |
| `backend/migrations/*` (new file) | add `domain_signature_weights`, `domain_entities` columns |
| `backend/evaluation/*` | update call sites for the `context: str` → `context_documents: List[str]` signature change |

---

## What Phase 1 does NOT cover (handled in the separate Phase 2 document)

- Fetching real medical/legal/financial documents
- Building the query sets
- Running the actual evaluation to generate paper numbers
- Rewriting the paper's dataset section

Phase 1 is architecture only. Once this is done and verified against the small existing `test_data/` samples, move to the Phase 2 document to bring in real data at the ~500-600 document scale.
