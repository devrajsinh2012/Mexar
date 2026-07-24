"""
MEXAR - Domain Guardrail Threshold Sweep.
Sweeps candidate DOMAIN_SIMILARITY_THRESHOLD values over all domain query sets and agents
to compute out-of-scope rejection Precision, Recall, F1, and In-Domain False Rejection Rate.
Exports results to evaluation_outputs/guardrail_threshold_sweep.json.
"""
import os
import sys
import json
import logging
from typing import Dict, List, Any, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.reasoning_engine import create_reasoning_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUTPUT_DIR_BACKEND = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "evaluation_outputs"))
OUTPUT_DIR_ROOT = os.path.abspath(os.path.join(REPO_ROOT, "evaluation_outputs"))
QUERY_SETS_DIR = os.path.join(REPO_ROOT, "test_data", "query_sets")


def load_all_query_sets() -> Dict[str, List[Dict[str, Any]]]:
    """Load query set JSON files for medical, legal, and financial domains."""
    domains = ["medical", "legal", "financial"]
    query_sets = {}
    for domain in domains:
        filepath = os.path.join(QUERY_SETS_DIR, f"{domain}_queries.json")
        if not os.path.exists(filepath):
            logger.error(f"Query set file not found: {filepath}")
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            query_sets[domain] = json.load(f)
    return query_sets


def run_threshold_sweep() -> Dict[str, Any]:
    """
    Run threshold sweep over candidate threshold values [0.02, 0.05, 0.08, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40].
    Measures confusion matrix for out-of-scope rejection across all query x agent combinations.
    """
    engine = create_reasoning_engine()
    query_sets = load_all_query_sets()
    domains = ["medical", "legal", "financial"]

    # Pre-load agents
    agents = {}
    for d in domains:
        agent_name = f"{d}_agent"
        agents[d] = engine._load_agent(agent_name)

    candidate_thresholds = [0.02, 0.05, 0.08, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]

    sweep_results = []
    best_threshold = 0.05
    best_f1 = -1.0
    best_metrics = {}

    for thresh in candidate_thresholds:
        # Override instance threshold
        engine.DOMAIN_SIMILARITY_THRESHOLD = thresh

        tp = 0  # Truly out-of-scope, rejected
        fp = 0  # Truly in-scope, rejected (False Rejection)
        fn = 0  # Truly out-of-scope, accepted (Leak)
        tn = 0  # Truly in-scope, accepted

        for source_domain, queries in query_sets.items():
            for item in queries:
                query_text = item["query"]
                item_is_in_domain = item.get("is_in_domain", True)

                for target_domain in domains:
                    target_agent = agents[target_domain]
                    target_agent_name = f"{target_domain}_agent"

                    # Determine ground truth scope for target agent
                    truly_in_scope = (source_domain == target_domain) and item_is_in_domain
                    truly_out_of_scope = not truly_in_scope

                    # Check guardrail directly
                    in_domain_flag, score = engine._check_guardrail(
                        query_text,
                        target_agent["domain_signature"],
                        target_agent["prompt_analysis"]
                    )
                    rejected = not in_domain_flag

                    if rejected and truly_out_of_scope:
                        tp += 1
                    elif rejected and truly_in_scope:
                        fp += 1
                    elif not rejected and truly_out_of_scope:
                        fn += 1
                    else:
                        tn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        false_rejection_rate = fp / (fp + tn) if (fp + tn) > 0 else 0.0

        res_entry = {
            "threshold": thresh,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "false_rejection_rate": round(false_rejection_rate, 4)
        }
        sweep_results.append(res_entry)

        if f1 > best_f1:
            best_f1 = f1
            best_threshold = thresh
            best_metrics = res_entry

    # Format table for console output
    print("\n" + "=" * 70)
    print("GUARDRAIL THRESHOLD SWEEP RESULTS")
    print("=" * 70)
    print(f"{'Threshold':<10} | {'Precision':<10} | {'Recall':<10} | {'F1 Score':<10} | {'False Rejection Rate':<20}")
    print("-" * 70)
    for r in sweep_results:
        star = " *" if r["threshold"] == best_threshold else ""
        print(f"{r['threshold']:<10.2f} | {r['precision']:<10.4f} | {r['recall']:<10.4f} | {r['f1']:<10.4f} | {r['false_rejection_rate']:<20.4f}{star}")
    print("=" * 70)
    print(f"Optimal Threshold: {best_threshold} (F1 = {best_f1:.4f}, False Rejection Rate = {best_metrics.get('false_rejection_rate', 0.0):.4f})")
    print("=" * 70 + "\n")

    output_payload = {
        "sweep_results": sweep_results,
        "optimal_threshold": best_threshold,
        "optimal_f1": round(best_f1, 4),
        "optimal_false_rejection_rate": best_metrics.get("false_rejection_rate", 0.0),
        "best_metrics": best_metrics
    }

    for out_dir in [OUTPUT_DIR_BACKEND, OUTPUT_DIR_ROOT]:
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, "guardrail_threshold_sweep.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(output_payload, f, indent=2)
        logger.info(f"Sweep results written to {out_file}")

    return output_payload


if __name__ == "__main__":
    run_threshold_sweep()
