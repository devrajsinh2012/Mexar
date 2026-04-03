"""
Runs CRAG and RAPTOR baselines against a set of test queries.
"""
import sys
import os
from typing import Dict, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.reasoning_engine import create_reasoning_engine
from evaluation.metrics import MetricsRunner


def _append_score(results: Dict[str, List[float]], baseline: str, score: Optional[float]) -> None:
    if score is None:
        print(f"{baseline}: Faithfulness score unavailable for this query.")
        return
    results[baseline].append(score)


def run_baselines(agent_name: str, queries: List[str]):
    engine = create_reasoning_engine()
    metrics = MetricsRunner()

    results: Dict[str, List[float]] = {"CRAG": [], "RAPTOR": [], "MEXAR": []}

    for q in queries:
        print(f"\nProcessing query: {q}")

        try:
            # Original MEXAR
            res_mexar = engine.reason(agent_name, q)
            mexar_score = metrics.extract_faithfulness(res_mexar)
            _append_score(results, "MEXAR", mexar_score)

            # CRAG
            res_crag = engine.reason_crag_baseline(agent_name, q)
            crag_score = metrics.extract_faithfulness(res_crag)
            if crag_score is None:
                crag_score = metrics.extract_confidence(res_crag)
            _append_score(results, "CRAG", crag_score)

            # RAPTOR
            res_raptor = engine.reason_raptor_baseline(agent_name, q)
            raptor_score = metrics.extract_faithfulness(res_raptor)
            if raptor_score is None:
                raptor_score = metrics.extract_confidence(res_raptor)
            _append_score(results, "RAPTOR", raptor_score)

            print(
                "Scores -> "
                f"MEXAR: {mexar_score if mexar_score is not None else 'N/A'}, "
                f"CRAG: {crag_score if crag_score is not None else 'N/A'}, "
                f"RAPTOR: {raptor_score if raptor_score is not None else 'N/A'}"
            )
        except Exception as e:
            print(f"Error evaluating query '{q}': {e}")

    print("\n--- Baseline Comparison (Faithfulness) ---")
    for b_name, scores in results.items():
        if scores:
            avg = sum(scores) / len(scores)
            print(f"{b_name}: {avg:.4f} (n={len(scores)})")
        else:
            print(f"{b_name}: No results")

    return results


if __name__ == "__main__":
    # Example usage
    test_queries = [
        "What are the symptoms of a common cold?",
        "How do I bake a chocolate cake?"
    ]
    # Replace 'medical_agent' with an actual compiled agent name in DB
    run_baselines("medical_agent", test_queries)
