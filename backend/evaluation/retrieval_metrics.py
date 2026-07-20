"""
MEXAR - Retrieval Quality Metrics Module
Provides Precision@k, Recall@k, Mean Reciprocal Rank (MRR), and nDCG@k algorithms.
Evaluates retrieved document chunk sources against expected ground-truth document IDs.
"""
import math
from typing import List, Any


def precision_at_k(retrieved_doc_ids: List[str], relevant_doc_ids: List[str], k: int = 5) -> float:
    """Calculate Precision at position K."""
    top_k = retrieved_doc_ids[:k]
    if not top_k:
        return 0.0
    relevant_set = set(relevant_doc_ids or [])
    if not relevant_set:
        return 0.0
    hits = sum(1 for d in top_k if any(rel in str(d) or str(d) in rel for rel in relevant_set))
    return round(hits / len(top_k), 4)


def recall_at_k(retrieved_doc_ids: List[str], relevant_doc_ids: List[str], k: int = 10) -> float:
    """Calculate Recall at position K."""
    relevant_set = set(relevant_doc_ids or [])
    if not relevant_set:
        return 0.0
    top_k = retrieved_doc_ids[:k]
    hits = sum(1 for rel in relevant_set if any(rel in str(d) or str(d) in rel for d in top_k))
    return round(hits / len(relevant_set), 4)


def mrr(retrieved_doc_ids: List[str], relevant_doc_ids: List[str]) -> float:
    """Calculate Mean Reciprocal Rank (MRR)."""
    relevant_set = set(relevant_doc_ids or [])
    if not relevant_set:
        return 0.0
    for i, d in enumerate(retrieved_doc_ids, start=1):
        if any(rel in str(d) or str(d) in rel for rel in relevant_set):
            return round(1.0 / i, 4)
    return 0.0


def ndcg_at_k(retrieved_doc_ids: List[str], relevant_doc_ids: List[str], k: int = 10) -> float:
    """Calculate Normalized Discounted Cumulative Gain at position K (nDCG@k)."""
    relevant_set = set(relevant_doc_ids or [])
    if not relevant_set:
        return 0.0

    def dcg(doc_ids: List[str]) -> float:
        score = 0.0
        for i, d in enumerate(doc_ids[:k], start=1):
            is_rel = 1.0 if any(rel in str(d) or str(d) in rel for rel in relevant_set) else 0.0
            score += is_rel / math.log2(i + 1)
        return score

    actual_dcg = dcg(retrieved_doc_ids)
    ideal_docs = list(relevant_set)[:k]
    ideal_dcg = dcg(ideal_docs)

    if ideal_dcg <= 0.0:
        return 0.0
    return round(actual_dcg / ideal_dcg, 4)
