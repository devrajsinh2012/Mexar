"""
MEXAR - Table I Systems Comparison Baseline Runner.
Runs Naive RAG, BM25 Only, LangChain, Self-RAG, and MEXAR across evaluation query sets.
"""
import sys
import os
import logging
from typing import Dict, List, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.reasoning_engine import create_reasoning_engine
from evaluation.langchain_baseline import build_langchain_pipeline, run_langchain_baseline
from evaluation.self_rag_baseline import run_self_rag_baseline

logger = logging.getLogger(__name__)


def run_table_1_comparison(agent_name: str, queries: List[Dict[str, Any]], domain: str) -> Dict[str, Any]:
    """
    Run 5-way baseline evaluation on Table I for a single domain query set.
    """
    engine = create_reasoning_engine()
    agent = engine._load_agent(agent_name)
    langchain_chain = build_langchain_pipeline(agent["id"]) if agent else None

    results = {
        "Naive RAG": [],
        "BM25 Only": [],
        "LangChain": [],
        "Self-RAG": [],
        "MEXAR": []
    }

    for item in queries:
        q = item["query"] if isinstance(item, dict) else item
        expected_docs = item.get("expected_source_docs", []) if isinstance(item, dict) else []

        try:
            # 1. Naive RAG
            naive_res = engine.reason_naive_rag_baseline(agent_name, q)
            naive_res["query"] = q
            naive_res["expected_source_docs"] = expected_docs
            results["Naive RAG"].append(naive_res)

            # 2. BM25 Only
            bm25_res = engine.reason_bm25_baseline(agent_name, q)
            bm25_res["query"] = q
            bm25_res["expected_source_docs"] = expected_docs
            results["BM25 Only"].append(bm25_res)

            # 3. LangChain
            lc_res = run_langchain_baseline(langchain_chain, q, engine=engine)
            lc_res["query"] = q
            lc_res["expected_source_docs"] = expected_docs
            results["LangChain"].append(lc_res)

            # 4. Self-RAG
            self_res = run_self_rag_baseline(engine, agent_name, q)
            self_res["query"] = q
            self_res["expected_source_docs"] = expected_docs
            results["Self-RAG"].append(self_res)

            # 5. MEXAR (Full Pipeline)
            mexar_res = engine.reason(agent_name, q)
            mexar_res["query"] = q
            mexar_res["expected_source_docs"] = expected_docs
            results["MEXAR"].append(mexar_res)

        except Exception as e:
            logger.error(f"Error running Table I baselines for query '{q}': {e}")

    # Summarize mean faithfulness / confidence per system
    summary = {}
    for sys_name, res_list in results.items():
        if res_list:
            faith_scores = [r.get("faithfulness", r.get("confidence", 0.0)) for r in res_list]
            avg_faith = sum(faith_scores) / len(faith_scores)
            summary[sys_name] = {
                "mean_faithfulness": round(avg_faith, 4),
                "sample_size": len(res_list),
                "raw_results": res_list
            }

    return summary
