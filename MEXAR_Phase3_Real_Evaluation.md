# MEXAR Phase 3 — Running the Real Evaluation to Generate Paper Numbers

**Purpose of this document:** hand this to an AI coding agent (Antigravity or similar) working directly in the `Mexar` repository (`github.com/devrajsinh2012/Mexar`). This is Phase 3 only: turning Phase 1's fixed architecture and Phase 2's real ~500-doc corpus into actual, reproducible numbers for Tables I-V and Figures 2-4. Assumes Phase 1 and Phase 2 are both done.

**Presentation date:** July 30-31, 2026. Target for this phase: days 12-16 (about 5 days). This is the densest phase, budget real time for it.

---

## 3.0 Read this first: a finding that changes the scope of this phase

Before writing any new evaluation code, understand what already exists in `backend/evaluation/` and what it actually measures, because it's not what the paper's Table I needs.

`backend/evaluation/baseline_runner.py` calls `engine.reason_crag_baseline()` and `engine.reason_raptor_baseline()`. Both route into `_run_baseline()` in `reasoning_engine.py`, whose own docstrings say "simulating CRAG flow" and "Simulates recursive summarization trees." What actually happens: the **same MEXAR hybrid retrieval** runs, and only the system prompt text changes ("You are a Corrective-RAG system..." vs "You are a RAPTOR baseline model..."). This is not a real CRAG implementation (no retrieval evaluator, no web-search fallback, no knowledge refinement) and not a real RAPTOR implementation (no hierarchical clustering, no recursive summarization tree built at index time). It's the same retrieval with a relabeled prompt.

More importantly: **Table I in the paper compares Naive RAG, BM25 Only, LangChain, Self-RAG, and MEXAR.** None of those four baseline systems exist anywhere in the codebase. `reason_crag_baseline` and `reason_raptor_baseline` aren't even the right systems, CRAG and RAPTOR are discussed in the paper's Related Work prose, not in Table I.

This phase has to build the four real Table I baselines from close to scratch. That's most of the work below. Don't try to reuse the CRAG/RAPTOR baseline functions for Table I, they measure the wrong thing.

---

## 3.1 Add per-stage latency instrumentation

**Why:** Table V reports millisecond-precision latency per pipeline stage (guardrail, embedding, retrieval, generation, verification). Right now those numbers have no instrumentation behind them anywhere in the code. This needs to be real before it can be reported.

**Modify `reasoning_engine.py`, `reason()` method:** wrap each stage with timing and return the breakdown in the response payload.

```python
import time

def reason(self, agent_name: str, query: str, **kwargs) -> Dict[str, Any]:
    timings = {}
    t0 = time.perf_counter()

    # Stage 1: Domain guardrail
    t_stage = time.perf_counter()
    in_domain, guardrail_score = self._check_guardrail(query, domain_signature, prompt_analysis)
    timings["domain_guardrail_ms"] = round((time.perf_counter() - t_stage) * 1000, 1)

    if not in_domain:
        timings["total_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        return self._out_of_scope_response(query, guardrail_score, timings)

    # Stage 2: Query embedding
    t_stage = time.perf_counter()
    query_embedding = list(self.embedding_model.embed([query]))[0]
    timings["query_embedding_ms"] = round((time.perf_counter() - t_stage) * 1000, 1)

    # Stage 3: Hybrid retrieval
    t_stage = time.perf_counter()
    search_results = self.searcher.search(query, agent["id"], top_k=20)
    timings["hybrid_retrieval_ms"] = round((time.perf_counter() - t_stage) * 1000, 1)

    # ... reranking, generation, verification stages follow the same pattern ...

    t_stage = time.perf_counter()
    answer = self._generate_answer(query, context, sys_prompt)
    timings["llm_generation_ms"] = round((time.perf_counter() - t_stage) * 1000, 1)

    t_stage = time.perf_counter()
    faithfulness_result = self.deberta_nli_scorer.score(answer, [c.content for c in top_chunks])
    timings["faithfulness_verification_ms"] = round((time.perf_counter() - t_stage) * 1000, 1)

    timings["total_ms"] = round((time.perf_counter() - t0) * 1000, 1)

    return {
        "answer": answer,
        # ... existing fields ...
        "timings": timings,
    }
```

**Acceptance test:** run 10 in-domain queries and confirm `timings` is present and non-zero on every stage in every response. Table V's mean/std values in the paper should come from aggregating this field across the full query set in Phase 3.5's orchestrator, not from typing in numbers by hand.

---

## 3.2 Add component toggle flags for ablation

**Why:** Table III (component ablation) needs six configurations: Naive RAG baseline, +Guardrail, +Hybrid Retrieval, +Faithfulness Verification, Hybrid-without-verification, Verification-without-hybrid. There's currently no way to turn individual components on/off in `reason()`, everything is hardwired on.

**Modify `reasoning_engine.py`:** add a config dataclass and thread it through `reason()`.

```python
from dataclasses import dataclass

@dataclass
class PipelineConfig:
    guardrail_enabled: bool = True
    retrieval_mode: str = "hybrid"  # "semantic", "lexical", or "hybrid"
    verification_enabled: bool = True

def reason(self, agent_name: str, query: str, config: PipelineConfig = None, **kwargs) -> Dict[str, Any]:
    config = config or PipelineConfig()

    if config.guardrail_enabled:
        in_domain, guardrail_score = self._check_guardrail(query, domain_signature, prompt_analysis)
        if not in_domain:
            return self._out_of_scope_response(query, guardrail_score, {})
    else:
        in_domain, guardrail_score = True, 1.0

    if config.retrieval_mode == "semantic":
        search_results = self.searcher._semantic_only_search(db, query_embedding, agent["id"], top_k=20)
    elif config.retrieval_mode == "lexical":
        search_results = self.searcher.lexical_only_search(query, agent["id"], top_k=20)  # see 3.5.2, needs to be added
    else:
        search_results = self.searcher.search(query, agent["id"], top_k=20)

    # ... generation happens the same way regardless of config ...

    if config.verification_enabled:
        faithfulness_result = self.deberta_nli_scorer.score(answer, [c.content for c in top_chunks])
    else:
        faithfulness_result = None  # confidence falls back to retrieval/rerank signal only

    # ...
```

**Table III configuration mapping for the agent to use later in 3.8:**

| Configuration | guardrail_enabled | retrieval_mode | verification_enabled |
|---|---|---|---|
| Naive RAG (Baseline) | False | semantic | False |
| + Domain Guardrail | True | semantic | False |
| + Hybrid Retrieval | True | hybrid | False |
| + Faithfulness Verification (full MEXAR) | True | hybrid | True |
| Hybrid without verification | True | hybrid | False |
| Verification without hybrid | True | semantic | True |

Note rows 3 and 5 are the same configuration, that's expected, the paper's ablation table reuses that row.

---

## 3.3 Build the retrieval quality metrics module

**Why:** Table II (P@5, R@10, MRR, nDCG) needs real relevance judgments. Phase 2's query sets include `expected_source_docs` per query, that's the ground truth to score against.

**New file: `backend/evaluation/retrieval_metrics.py`**

```python
"""
MEXAR - Retrieval quality metrics: Precision@k, Recall@k, MRR, nDCG.
Scores retrieved chunk source-document IDs against a query's expected_source_docs.
"""
import math
from typing import List

def precision_at_k(retrieved_doc_ids: List[str], relevant_doc_ids: List[str], k: int) -> float:
    top_k = retrieved_doc_ids[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for d in top_k if d in relevant_doc_ids)
    return hits / len(top_k)

def recall_at_k(retrieved_doc_ids: List[str], relevant_doc_ids: List[str], k: int) -> float:
    if not relevant_doc_ids:
        return 0.0
    top_k = retrieved_doc_ids[:k]
    hits = sum(1 for d in top_k if d in relevant_doc_ids)
    return hits / len(relevant_doc_ids)

def mrr(retrieved_doc_ids: List[str], relevant_doc_ids: List[str]) -> float:
    for i, d in enumerate(retrieved_doc_ids, start=1):
        if d in relevant_doc_ids:
            return 1.0 / i
    return 0.0

def ndcg_at_k(retrieved_doc_ids: List[str], relevant_doc_ids: List[str], k: int) -> float:
    def dcg(doc_ids):
        return sum(
            (1.0 if d in relevant_doc_ids else 0.0) / math.log2(i + 1)
            for i, d in enumerate(doc_ids[:k], start=1)
        )
    ideal = dcg(relevant_doc_ids[:k] + [None] * max(0, k - len(relevant_doc_ids)))
    actual = dcg(retrieved_doc_ids)
    return actual / ideal if ideal > 0 else 0.0
```

**Wiring:** for each query in the Phase 2 query sets, run retrieval (using the `retrieval_mode` toggle from 3.2 to get semantic-only, lexical-only, and hybrid result sets separately), extract the source document ID for each returned chunk, and score against `expected_source_docs`. This is what produces the real Table II numbers, don't hand-write them.

---

## 3.4 Add a lexical-only search method

**Why:** needed for both the BM25 Only Table I baseline (3.5) and the "Lexical Only" row of Table II (3.3). No pure lexical-only Python method currently exists, only inside the fused SQL RPC.

**Modify `backend/utils/hybrid_search.py`:** add alongside `_semantic_only_search`:

```python
def lexical_only_search(
    self,
    query: str,
    agent_id: int,
    top_k: int = 20
) -> List[Tuple[DocumentChunk, float]]:
    """Pure lexical (ts_rank) search, no semantic component. Used for the BM25 Only baseline and Table II."""
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT id, ts_rank_cd(content_tsv, plainto_tsquery('english', :query_text)) AS score
            FROM document_chunks
            WHERE agent_id = :agent_id
              AND content_tsv @@ plainto_tsquery('english', :query_text)
            ORDER BY score DESC
            LIMIT :top_k
        """), {"query_text": query, "agent_id": agent_id, "top_k": top_k})
        rows = result.fetchall()
        if not rows:
            return []
        chunk_ids = [row.id for row in rows]
        chunks = db.query(DocumentChunk).filter(DocumentChunk.id.in_(chunk_ids)).all()
        chunk_map = {c.id: c for c in chunks}
        return [(chunk_map[row.id], row.score) for row in rows if row.id in chunk_map]
    finally:
        db.close()
```

Verify the actual tsvector column name against `backend/migrations/hybrid_search_function.sql`, the skeleton above assumes `content_tsv`, confirm before trusting it.

---

## 3.5 Build the four real Table I baselines

**Why:** these don't exist yet. Building them properly is most of this phase's effort.

### 3.5.1 Naive RAG

Semantic-only search (reuse `_semantic_only_search`), no guardrail, no verification, Llama 3 8B generation. This is just `PipelineConfig(guardrail_enabled=False, retrieval_mode="semantic", verification_enabled=False)` from 3.2, but generate the answer with a plain unconstrained system prompt (no citation instructions, no domain constraints) to match the paper's description of it as the true baseline. Add a `reason_naive_rag_baseline()` method to `reasoning_engine.py` that wraps this configuration.

### 3.5.2 BM25 Only

Same idea, `retrieval_mode="lexical"` using the new `lexical_only_search()` from 3.4, no guardrail, no verification. Add `reason_bm25_baseline()`.

### 3.5.3 LangChain

This one is genuinely separate infrastructure, not a config toggle. It needs its own small standalone pipeline, not routed through `ReasoningEngine` at all.

**New file: `backend/evaluation/langchain_baseline.py`**
```python
"""
MEXAR - LangChain baseline for Table I.
Standard LangChain RetrievalQA pipeline with Chroma vector store and default config,
built from the SAME source documents as the MEXAR corpus, kept separate from the
production Supabase-backed pipeline entirely.
"""
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
from langchain_groq import ChatGroq  # or whatever LLM wrapper matches the Groq backbone used elsewhere
import os

def build_langchain_pipeline(source_documents: list, persist_dir: str = "./chroma_baseline_db"):
    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")  # match MEXAR's embedding model for a fair comparison
    vectorstore = Chroma.from_texts(source_documents, embeddings, persist_directory=persist_dir)
    llm = ChatGroq(model="llama3-8b-8192", groq_api_key=os.environ["GROQ_API_KEY"])
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever(search_kwargs={"k": 5}),
        return_source_documents=True,
    )
    return qa_chain

def run_langchain_baseline(qa_chain, query: str) -> dict:
    result = qa_chain.invoke({"query": query})
    return {
        "answer": result["result"],
        "source_documents": [d.page_content for d in result.get("source_documents", [])],
    }
```
Add `langchain`, `langchain-community`, `langchain-groq` to `backend/requirements.txt`, scoped to the evaluation environment if it's kept separate from the production deploy (Hugging Face Spaces doesn't need these, only the evaluation run does).

**Fairness note for the agent:** embed the same corpus (Phase 2's ~500 docs) into this separate Chroma store so the comparison is apples-to-apples with MEXAR's Supabase-backed corpus, not a different or smaller dataset.

### 3.5.4 Self-RAG — decision point, don't skip this

The paper says "Public checkpoint implementing reflection tokens for retrieval critique." The real Self-RAG checkpoint is `selfrag/selfrag_llama2_7b`, a 7B-parameter model that needs to actually run inference with reflection-token-aware decoding, not just a differently-worded prompt on Llama 3 8B via Groq (that would repeat the exact CRAG/RAPTOR mistake flagged in 3.0).

Two honest paths, pick one explicitly, don't default silently:

- **Path A (real):** run the actual `selfrag/selfrag_llama2_7b` checkpoint via a Hugging Face Inference Endpoint or local GPU inference (needs roughly 16GB+ VRAM for reasonable speed, or a quantized version if hardware is constrained). This matches the paper's claim exactly and is the safer choice if a reviewer probes it.
- **Path B (disclosed proxy):** if GPU access isn't available in the timeline, build a prompted proxy (Llama 3 8B instructed to emit reflection-style self-critique tokens before answering) and **change the paper's baseline description** to say so explicitly, e.g. "a prompted approximation of Self-RAG's reflection mechanism, as the original 7B checkpoint was not feasible to deploy at evaluation scale." This is a legitimate disclosed limitation. What's not legitimate is calling it "Self-RAG" in Table I without the caveat.

Flag this decision to Dev before the agent proceeds, don't have the agent silently pick Path B and let it read as Path A in the paper.

### 3.5.5 Update `baseline_runner.py`

Rewrite it to run all five systems (Naive RAG, BM25 Only, LangChain, Self-RAG, MEXAR) per query and log faithfulness, confidence, and retrieval metrics for each, replacing the current CRAG/RAPTOR comparison entirely:

```python
def run_table_1_comparison(agent_name: str, queries: list, domain: str):
    engine = create_reasoning_engine()
    results = {"Naive RAG": [], "BM25 Only": [], "LangChain": [], "Self-RAG": [], "MEXAR": []}
    langchain_chain = build_langchain_pipeline(...)  # loaded once per domain

    for q in queries:
        results["Naive RAG"].append(engine.reason_naive_rag_baseline(agent_name, q))
        results["BM25 Only"].append(engine.reason_bm25_baseline(agent_name, q))
        results["LangChain"].append(run_langchain_baseline(langchain_chain, q))
        results["Self-RAG"].append(run_self_rag_baseline(q))  # per 3.5.4's chosen path
        results["MEXAR"].append(engine.reason(agent_name, q))

    return results
```
Save full raw output per query, not just averages, Phase 4 needs the per-query pairs for McNemar's test.

---

## 3.6 Expand guardrail analysis to real Table IV

**Why:** the current `guardrail_analysis.py` only prints results for 4 hardcoded queries. Table IV needs precision/recall/F1 per domain-pair (Medical→Legal, Medical→Financial, etc.) computed over the full out-of-domain query set from Phase 2.

**Rewrite `backend/evaluation/guardrail_analysis.py`:**
```python
def run_table_4_analysis(query_sets_dir: str = "test_data/query_sets"):
    engine = create_reasoning_engine()
    domain_pairs = [
        ("medical", "legal"), ("medical", "financial"),
        ("legal", "medical"), ("legal", "financial"),
        ("financial", "medical"), ("financial", "legal"),
    ]
    results = {}
    for source_domain, target_agent_domain in domain_pairs:
        queries = load_out_of_domain_queries(query_sets_dir, source_domain, target_agent_domain)
        tp = fp = fn = tn = 0
        for item in queries:
            res = engine.reason(f"{target_agent_domain}_agent", item["query"])
            rejected = not res["in_domain"]
            truly_out_of_scope = not item["is_in_domain"]
            if rejected and truly_out_of_scope: tp += 1
            elif rejected and not truly_out_of_scope: fp += 1
            elif not rejected and truly_out_of_scope: fn += 1
            else: tn += 1
        precision = tp / (tp + fp) if (tp + fp) else 0
        recall = tp / (tp + fn) if (tp + fn) else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0
        results[f"{source_domain}_to_{target_agent_domain}"] = {
            "rejected": tp, "total": len(queries), "precision": round(precision, 2),
            "recall": round(recall, 2), "f1": round(f1, 2),
        }
    return results
```
`load_out_of_domain_queries` needs to filter Phase 2's query set JSON by domain-pair, the agent should implement this against whatever schema Phase 2 actually produced.

---

## 3.7 Run the Table III ablation

Using the `PipelineConfig` toggles from 3.2 and the configuration mapping table in that section, run each of the six configurations against the full in-domain query set (all three domains combined, matching how the paper's Table III doesn't split by domain) and record faithfulness scores per configuration. Average per configuration, compute the delta vs. Naive RAG baseline, and check whether the superadditive pattern the paper claims (combined effect > sum of individual effects) actually holds on real data, don't assume it will, that's an empirical claim that needs to survive contact with real numbers.

---

## 3.8 Build the calibration (ECE) module

**Why:** Figure 4's reliability diagram and the ECE = 0.06 claim need a real calculator, none exists in the repo currently.

**New file: `backend/evaluation/calibration.py`**
```python
"""
MEXAR - Expected Calibration Error and reliability diagram data.
"""
from typing import List, Tuple
import numpy as np

def expected_calibration_error(confidences: List[float], correctness: List[bool], n_bins: int = 10) -> float:
    """
    confidences: predicted confidence per query (0-1)
    correctness: whether the answer was actually correct per query (from human/expert review)
    """
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    n = len(confidences)
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        in_bin = [(c, corr) for c, corr in zip(confidences, correctness) if lo <= c < hi or (i == n_bins - 1 and c == hi)]
        if not in_bin:
            continue
        bin_conf = np.mean([c for c, _ in in_bin])
        bin_acc = np.mean([1.0 if corr else 0.0 for _, corr in in_bin])
        ece += (len(in_bin) / n) * abs(bin_conf - bin_acc)
    return round(ece, 4)

def reliability_diagram_data(confidences: List[float], correctness: List[bool], n_bins: int = 10) -> List[Tuple[float, float]]:
    """Returns (mean_predicted_confidence, observed_accuracy) per bin, for plotting Figure 4."""
    bins = np.linspace(0, 1, n_bins + 1)
    points = []
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        in_bin = [(c, corr) for c, corr in zip(confidences, correctness) if lo <= c < hi or (i == n_bins - 1 and c == hi)]
        if not in_bin:
            continue
        bin_conf = float(np.mean([c for c, _ in in_bin]))
        bin_acc = float(np.mean([1.0 if corr else 0.0 for _, corr in in_bin]))
        points.append((bin_conf, bin_acc))
    return points
```

**Important:** `correctness` needs to come from actual human judgment of whether each answer was right, not from the faithfulness score itself, otherwise ECE would be measuring the faithfulness scorer's agreement with itself, which is circular in the same way the paper criticizes elsewhere. This means someone (Dev, Om, or Jay) needs to mark each query's MEXAR answer as correct/incorrect by hand, this is a real annotation task, budget time for it in this phase, it can't be automated away.

---

## 3.9 Effect size and significance summary

Reuse the existing `statistical_tests.py` McNemar implementation (it's legitimate, no changes needed there) but wrap it to also compute Cohen's d for the forest plot in Figure 3:

```python
def cohens_d(scores_a: list, scores_b: list) -> float:
    import numpy as np
    mean_diff = np.mean(scores_a) - np.mean(scores_b)
    pooled_std = np.sqrt((np.std(scores_a, ddof=1)**2 + np.std(scores_b, ddof=1)**2) / 2)
    return round(mean_diff / pooled_std, 3) if pooled_std > 0 else 0.0
```
Run this for every pairwise comparison Figure 3 shows (Hybrid vs Lexical Only, Hybrid vs Semantic Only, MEXAR vs Self-RAG, MEXAR vs LangChain, MEXAR vs BM25 Only, MEXAR vs Naive RAG), using the per-query score arrays saved in 3.5.5.

---

## 3.10 Orchestrator script

**New file: `backend/evaluation/run_all.py`**, ties everything above together and writes results to `evaluation_outputs/`:

```python
"""
MEXAR - Full evaluation orchestrator. Run this once Phase 1-2 and all of Phase 3's
components are in place. Produces every number Phase 4 needs to update the paper.
"""
import json
import os
from datetime import datetime

OUTPUT_DIR = "evaluation_outputs"

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    table1 = run_table_1_comparison_all_domains()       # 3.5
    table2 = run_retrieval_ablation_all_domains()        # 3.3 + 3.4
    table3 = run_table_3_ablation()                      # 3.7
    table4 = run_table_4_analysis()                      # 3.6
    table5 = aggregate_latency_stats()                   # 3.1
    calibration = run_calibration_analysis()             # 3.8
    significance = run_all_significance_tests(table1)    # 3.9

    payload = {
        "run_id": run_id,
        "table1_system_comparison": table1,
        "table2_retrieval_ablation": table2,
        "table3_component_ablation": table3,
        "table4_guardrail_boundary": table4,
        "table5_latency": table5,
        "calibration": calibration,
        "significance_tests": significance,
    }
    out_path = os.path.join(OUTPUT_DIR, f"full_evaluation_{run_id}.json")
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Full evaluation saved to {out_path}")

if __name__ == "__main__":
    main()
```

---

## 3.11 Sanity checklist before trusting any number

Before handing anything to Phase 4, check:

- [ ] Every table's numbers came from `evaluation_outputs/full_evaluation_*.json`, not typed in by hand.
- [ ] Self-RAG's scope (Path A or B from 3.5.4) is explicitly recorded, so Phase 4 knows how to describe it in the paper.
- [ ] The ECE calculation used real human-marked correctness labels, not the faithfulness score used as a stand-in for correctness.
- [ ] The superadditive claim in Table III (35% > 23% + 18%) is checked against the real numbers, if it doesn't hold, the paper's Section V-B prose needs to change too, not just the table.
- [ ] Latency numbers came from actual `timings` fields aggregated across a real run, not the current placeholder table.
- [ ] LangChain baseline used the same ~500-doc corpus as MEXAR, not a smaller or different sample.

---

## Summary of files touched/created in Phase 3

| File | Change |
|---|---|
| `backend/modules/reasoning_engine.py` | add timing instrumentation, `PipelineConfig`, `reason_naive_rag_baseline()`, `reason_bm25_baseline()` |
| `backend/utils/hybrid_search.py` | add `lexical_only_search()` |
| `backend/evaluation/retrieval_metrics.py` | **new** — P@k, R@k, MRR, nDCG |
| `backend/evaluation/langchain_baseline.py` | **new** — real LangChain/Chroma pipeline |
| `backend/evaluation/self_rag_baseline.py` | **new** — real or disclosed-proxy Self-RAG (per 3.5.4 decision) |
| `backend/evaluation/baseline_runner.py` | rewritten to run real Table I comparison |
| `backend/evaluation/guardrail_analysis.py` | rewritten to compute real Table IV over Phase 2's out-of-domain queries |
| `backend/evaluation/calibration.py` | **new** — ECE + reliability diagram data |
| `backend/evaluation/run_all.py` | **new** — orchestrator, single entry point for the full evaluation |
| `backend/requirements.txt` | add langchain, langchain-community, langchain-groq (evaluation-only if kept separate from prod) |

## What Phase 3 does NOT cover

- Editing the paper itself, that's Phase 4.
- Preparing or rehearsing the live demo, that's Phase 4.

Once `evaluation_outputs/full_evaluation_*.json` exists with real numbers, move to the Phase 4 document.
