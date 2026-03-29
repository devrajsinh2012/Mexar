"""
Runs CRAG and RAPTOR baselines against a set of test queries.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.reasoning_engine import create_reasoning_engine
from evaluation.metrics import MetricsRunner

def run_baselines(agent_name: str, queries: list):
    engine = create_reasoning_engine()
    metrics = MetricsRunner()
    
    results = {"CRAG": [], "RAPTOR": [], "MEXAR": []}
    
    for q in queries:
        print(f"\nProcessing query: {q}")
        
        try:
            # Original MEXAR
            res_mexar = engine.reason(agent_name, q)
            results["MEXAR"].append(float(res_mexar["explainability"]["faithfulness"].strip('%'))/100)
            
            # CRAG
            res_crag = engine.reason_crag_baseline(agent_name, q)
            results["CRAG"].append(res_crag["confidence"]) # The raw score
            
            # RAPTOR
            res_raptor = engine.reason_raptor_baseline(agent_name, q)
            results["RAPTOR"].append(res_raptor["confidence"])
        except Exception as e:
            print(f"Error evaluating query '{q}': {e}")
        
    print("\n--- Baseline Comparison (Faithfulness) ---")
    for b_name in results:
        if results[b_name]:
            avg = sum(results[b_name]) / len(results[b_name])
            print(f"{b_name}: {avg:.4f}")
        else:
            print(f"{b_name}: No results")

if __name__ == "__main__":
    # Example usage
    test_queries = [
        "What are the symptoms of a common cold?",
        "How do I bake a chocolate cake?"
    ]
    # Replace 'medical_agent' with an actual compiled agent name in DB
    run_baselines("medical_agent", test_queries)
