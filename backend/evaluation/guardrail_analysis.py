"""
Evaluates the domain guardrail's false-accept (false positive) rate.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.reasoning_engine import create_reasoning_engine

def test_guardrails(agent_name: str):
    engine = create_reasoning_engine()
    
    boundary_queries = [
        "What are the economic impacts of pharmaceutical pricing?", # Often crosses medical/finance
        "Can a doctor be sued for malpractice if they misdiagnose cancer?", # Medical/Legal
        "Are taxes applied to medical equipment purchases?", # Medical/Finance
        "How do I cook a healthy meal to lower blood pressure?" # Cooking/Medical
    ]
    
    print(f"Testing Guardrail False-Accept Rate (Threshold = {engine.DOMAIN_SIMILARITY_THRESHOLD})")
    
    try:
        for q in boundary_queries:
            res = engine.reason(agent_name, q)
            print(f"\nQuery: {q}")
            print(f"Accepted: {res['in_domain']}")
            exp = res.get('explainability', {})
            cb = exp.get('confidence_breakdown', {})
            domain_str = cb.get('domain_relevance', 'N/A')
            print(f"Domain Score: {domain_str}")
    except Exception as e:
        print(f"Failed guardrail test queries: {e}")

if __name__ == "__main__":
    test_guardrails("medical_agent")
