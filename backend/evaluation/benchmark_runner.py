"""
Runs evaluation on public benchmarks like MedQA, LegalBench.
"""
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.reasoning_engine import create_reasoning_engine

def run_benchmark(dataset_path: str, agent_name: str):
    engine = create_reasoning_engine()
    
    if not os.path.exists(dataset_path):
        print(f"Dataset not found: {dataset_path}")
        return
        
    with open(dataset_path, "r") as f:
        data = json.load(f)
        
    for item in data[:10]: # Run first 10 for demo
        query = item.get("question") or item.get("query")
        if not query:
            continue
            
        print(f"\nQuery: {query}")
        try:
            result = engine.reason(agent_name, query)
            print(f"Answer: {result['answer'][:100]}...")
            print(f"Faithfulness: {result['explainability']['faithfulness']}")
        except Exception as e:
            print(f"Failed to process query: {e}")

if __name__ == "__main__":
    run_benchmark(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "test_data", "medqa_sample.json"), "medical_agent")
