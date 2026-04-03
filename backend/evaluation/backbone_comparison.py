"""
Compares different LLM backbones (Llama 3, Mixtral, Gemma).
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from modules.reasoning_engine import create_reasoning_engine
from evaluation.metrics import MetricsRunner

def run_comparison(agent_name: str, queries: list):
    backbones = ["llama3", "mixtral", "gemma"]
    metrics = MetricsRunner()
    original_backbone = getattr(settings, "LLM_BACKBONE", None)

    try:
        for bb in backbones:
            settings.LLM_BACKBONE = bb
            print(f"\n--- Testing Backbone: {bb} ---")
            try:
                # Must recreate engine so GroqClient picks up config
                engine = create_reasoning_engine()

                for q in queries:
                    res = engine.reason(agent_name, q)
                    faithfulness = metrics.extract_faithfulness(res)
                    print(f"Q: {q}")
                    print(f"A ({bb}): {res['answer'][:100]}...")
                    if faithfulness is None:
                        print("Faithfulness: N/A")
                    else:
                        print(f"Faithfulness: {faithfulness:.3f}")
            except Exception as e:
                print(f"Failed to run with backbone {bb}: {e}")
    finally:
        settings.LLM_BACKBONE = original_backbone
        print(f"\nRestored LLM_BACKBONE to: {original_backbone}")

if __name__ == "__main__":
    test_queries = ["What are the symptoms of a common cold?"]
    # Replace 'medical_agent' with an actual compiled agent name
    run_comparison("medical_agent", test_queries)
