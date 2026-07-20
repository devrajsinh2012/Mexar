"""
MEXAR - Self-RAG Baseline for Table I.
Implements Self-RAG reflection-token aware baseline logic.
Uses prompted proxy on Llama 3 8B emitting critique tokens ([Retrieval], [IsREL], [IsSUP])
to simulate reflection-based RAG decoding.
"""
import logging
from typing import Dict, Any
from utils.groq_client import get_groq_client

logger = logging.getLogger(__name__)


def run_self_rag_baseline(engine, agent_name: str, query: str) -> Dict[str, Any]:
    """
    Execute Self-RAG baseline with self-reflection / critique token decoding.
    """
    agent = engine._load_agent(agent_name)
    
    # 1. Retrieval decision: check if retrieval is needed
    search_results = engine.searcher.search(query, agent["id"], top_k=5) if engine.searcher else []
    chunks = [r[0] for r in search_results]
    context = "\n---\n".join([c.content for c in chunks])
    
    sys_prompt = f"""You are a Self-RAG baseline system trained to generate explicit self-reflection and critique tokens.
When answering the query:
1. Output [Retrieval] if retrieval is necessary.
2. Evaluate each context chunk and output [IsREL: Relevant] or [IsREL: Irrelevant].
3. Generate the answer incorporating [IsSUP: Supported] or [IsSUP: Partially Supported] reflection tags before key statements.

RETRIEVED CONTEXT:
{context[:8000]}
"""
    
    client = get_groq_client()
    answer = client.analyze_with_system_prompt(
        system_prompt=sys_prompt,
        user_message=query,
        model="chat"
    )
    
    faithfulness_res = engine.deberta_nli_scorer.score(answer, [c.content for c in chunks]) if chunks else engine.deberta_nli_scorer.score(answer, ["Context empty"])
    
    return {
        "answer": answer,
        "confidence": faithfulness_res.score,
        "in_domain": True,
        "top_chunks": chunks,
        "retrieved_chunk_doc_ids": [c.source for c in chunks if hasattr(c, 'source')],
        "faithfulness": faithfulness_res.score
    }
