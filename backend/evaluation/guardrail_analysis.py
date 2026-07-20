"""
MEXAR - Domain Guardrail Analysis for Table IV.
Evaluates out-of-domain query boundary rejection precision, recall, and F1 across all cross-domain pairs.
"""
import sys
import os
import json
import logging
from typing import Dict, List, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.reasoning_engine import create_reasoning_engine

logger = logging.getLogger(__name__)


def load_query_set(query_sets_dir: str, domain: str) -> List[Dict[str, Any]]:
    """Load query set JSON for a given domain."""
    filepath = os.path.join(query_sets_dir, f"{domain}_queries.json")
    if not os.path.exists(filepath):
        logger.warning(f"Query set file not found: {filepath}")
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def run_table_4_analysis(query_sets_dir: str = "test_data/query_sets") -> Dict[str, Any]:
    """
    Run domain guardrail boundary evaluation for Table IV.
    Evaluates cross-domain queries against target domain agents.
    """
    engine = create_reasoning_engine()
    domain_pairs = [
        ("medical", "legal"),
        ("medical", "financial"),
        ("legal", "medical"),
        ("legal", "financial"),
        ("financial", "medical"),
        ("financial", "legal"),
    ]

    results = {}

    for source_domain, target_domain in domain_pairs:
        target_agent_name = f"{target_domain}_agent"
        source_queries = load_query_set(query_sets_dir, source_domain)

        # Filter out-of-domain queries or queries targeted at another domain
        ood_queries = [
            q for q in source_queries
            if not q.get("is_in_domain", True) or q.get("domain") == source_domain
        ]

        tp = fp = fn = tn = 0

        for item in ood_queries:
            query_text = item["query"]
            truly_out_of_scope = not item.get("is_in_domain", True) or (source_domain != target_domain)

            res = engine.reason(target_agent_name, query_text)
            rejected = not res.get("in_domain", True)

            if rejected and truly_out_of_scope:
                tp += 1
            elif rejected and not truly_out_of_scope:
                fp += 1
            elif not rejected and truly_out_of_scope:
                fn += 1
            else:
                tn += 1

        total = len(ood_queries)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        pair_key = f"{source_domain}_to_{target_domain}"
        results[pair_key] = {
            "source_domain": source_domain,
            "target_domain": target_domain,
            "total_evaluated": total,
            "rejected_count": tp + fp,
            "true_positives_rejected": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "true_negatives": tn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4)
        }

    return results


if __name__ == "__main__":
    t4 = run_table_4_analysis()
    print(json.dumps(t4, indent=2))
