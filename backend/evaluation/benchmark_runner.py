"""
Runs evaluation on public benchmarks like MedQA, LegalBench.
"""
import sys
import os
import json
import argparse
from datetime import datetime
from typing import Any, Dict, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.reasoning_engine import create_reasoning_engine
from evaluation.metrics import MetricsRunner


def _extract_query(item: Dict[str, Any]) -> Optional[str]:
    query = item.get("question") or item.get("query")
    if not isinstance(query, str):
        return None
    query = query.strip()
    return query if query else None


def _summarize_scores(scores: List[float]) -> Optional[float]:
    if not scores:
        return None
    return round(sum(scores) / len(scores), 4)


def run_benchmark(
    dataset_path: str,
    agent_name: str,
    max_samples: Optional[int] = None,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    engine = create_reasoning_engine()
    metrics = MetricsRunner()

    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Benchmark dataset must be a JSON array of records")

    items = data if not max_samples else data[:max_samples]

    records: List[Dict[str, Any]] = []
    faithfulness_scores: List[float] = []
    succeeded = 0
    failed = 0
    skipped = 0

    for idx, item in enumerate(items, start=1):
        query = _extract_query(item)
        if not query:
            skipped += 1
            continue

        print(f"\n[{idx}/{len(items)}] Query: {query}")
        row: Dict[str, Any] = {
            "index": idx,
            "query": query,
        }

        try:
            result = engine.reason(agent_name, query)
            faithfulness = metrics.extract_faithfulness(result)
            confidence = metrics.extract_confidence(result)
            answer = result.get("answer", "")

            if isinstance(answer, str) and len(answer) > 120:
                answer_preview = f"{answer[:120]}..."
            else:
                answer_preview = answer

            row.update({
                "status": "ok",
                "in_domain": result.get("in_domain"),
                "confidence": confidence,
                "faithfulness": faithfulness,
                "answer_preview": answer_preview,
            })
            records.append(row)

            if faithfulness is not None:
                faithfulness_scores.append(faithfulness)
            succeeded += 1

            print(f"Answer: {answer_preview}")
            if faithfulness is None:
                print("Faithfulness: N/A")
            else:
                print(f"Faithfulness: {faithfulness:.3f}")
        except Exception as e:
            row.update({
                "status": "error",
                "error": str(e),
            })
            records.append(row)
            failed += 1
            print(f"Failed to process query: {e}")

    summary: Dict[str, Any] = {
        "dataset_path": dataset_path,
        "agent_name": agent_name,
        "total_rows": len(data),
        "attempted_rows": len(items),
        "succeeded": succeeded,
        "failed": failed,
        "skipped": skipped,
        "avg_faithfulness": _summarize_scores(faithfulness_scores),
        "generated_at_utc": datetime.utcnow().isoformat() + "Z",
    }

    print("\n--- Benchmark Summary ---")
    print(f"Attempted: {summary['attempted_rows']}")
    print(f"Succeeded: {summary['succeeded']}")
    print(f"Failed: {summary['failed']}")
    print(f"Skipped: {summary['skipped']}")
    print(f"Avg faithfulness: {summary['avg_faithfulness']}")

    if output_path:
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        payload = {
            "summary": summary,
            "results": records,
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"Saved report to: {output_path}")

    return {
        "summary": summary,
        "results": records,
    }


def _default_dataset_path() -> str:
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "test_data",
        "medqa_sample.json",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run benchmark dataset evaluation")
    parser.add_argument("--dataset-path", default=_default_dataset_path(), help="Path to benchmark JSON file")
    parser.add_argument("--agent-name", default="medical_agent", help="Compiled agent name")
    parser.add_argument(
        "--max-samples",
        type=int,
        default=0,
        help="Limit to first N records (0 means all)",
    )
    parser.add_argument("--output", default="", help="Optional output path for JSON report")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    max_samples = args.max_samples if args.max_samples > 0 else None
    output_path = args.output if args.output else None
    run_benchmark(args.dataset_path, args.agent_name, max_samples=max_samples, output_path=output_path)
