"""
Ablation study on chunk size effect on faithfulness and retrieval quality.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.knowledge_compiler import create_knowledge_compiler
from modules.reasoning_engine import create_reasoning_engine

def run_chunk_ablation(agent_name: str, parsed_data: list, system_prompt: str, prompt_analysis: dict, test_queries: list):
    sizes = [64, 128, 256, 512, 1024]
    
    for size in sizes:
        print(f"\n=====================")
        print(f"Testing Chunk Size: {size}")
        print(f"=====================")
        
        compiler = create_knowledge_compiler()
        original_chunk_text = compiler._chunk_text
        compiler._chunk_text = lambda text, chunk_size=size, overlap=size//10: original_chunk_text(text, chunk_size, overlap)
        
        # Recompile
        try:
            compiler.compile(agent_name, parsed_data, system_prompt, prompt_analysis)
            
            # Test
            engine = create_reasoning_engine()
            for q in test_queries:
                res = engine.reason(agent_name, q)
                print(f"Q: {q}")
                print(f"Faithfulness: {res['explainability']['faithfulness']}")
        except Exception as e:
            print(f"Failed ablation step for size {size}: {e}")

if __name__ == "__main__":
    print("Chunk size ablation script ready. Needs actual parsed data to recompile.")
