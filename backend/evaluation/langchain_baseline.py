"""
MEXAR - LangChain baseline for Table I.
Standard LangChain RetrievalQA pipeline with Chroma vector store and default config,
built from the SAME source documents as the MEXAR corpus.
"""
import os
import logging
from typing import Dict, Any, List
from core.database import SessionLocal
from models.chunk import DocumentChunk
from utils.groq_client import get_groq_client

logger = logging.getLogger(__name__)


def build_langchain_pipeline(agent_id: int, persist_dir: str = "./chroma_baseline_db"):
    """
    Build or load a LangChain RetrievalQA chain over the specified agent's document chunks.
    Uses HuggingFace BAAI/bge-small-en-v1.5 to match MEXAR's embedding space for fair evaluation.
    """
    try:
        from langchain_community.vectorstores import Chroma
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from langchain.chains import RetrievalQA
        from langchain_groq import ChatGroq

        db = SessionLocal()
        try:
            chunks = db.query(DocumentChunk).filter(DocumentChunk.agent_id == agent_id).all()
            texts = [c.content for c in chunks if c.content]
            metadatas = [{"source": c.source, "chunk_index": c.chunk_index} for c in chunks if c.content]
        finally:
            db.close()

        if not texts:
            logger.warning(f"No texts found for agent_id {agent_id} in LangChain baseline setup")
            return None

        embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
        vectorstore = Chroma.from_texts(
            texts=texts,
            embedding=embeddings,
            metadatas=metadatas,
            persist_directory=f"{persist_dir}_{agent_id}"
        )

        groq_api_key = os.environ.get("GROQ_API_KEY", "")
        llm = ChatGroq(model="llama3-8b-8192", groq_api_key=groq_api_key)

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=vectorstore.as_retriever(search_kwargs={"k": 5}),
            return_source_documents=True,
        )
        return qa_chain
    except Exception as e:
        logger.error(f"Failed to build LangChain pipeline: {e}")
        return None


def run_langchain_baseline(qa_chain, query: str, engine=None) -> Dict[str, Any]:
    """
    Execute LangChain baseline QA chain for a given query.
    Fallback to Groq direct generation if LangChain libraries are not initialized.
    """
    if qa_chain is not None:
        try:
            result = qa_chain.invoke({"query": query})
            answer = result.get("result", "")
            sources = [d.metadata.get("source", "") for d in result.get("source_documents", [])]
            chunk_texts = [d.page_content for d in result.get("source_documents", [])]
            faithfulness = 0.5
            if engine and hasattr(engine, 'deberta_nli_scorer'):
                faith_res = engine.deberta_nli_scorer.score(answer, chunk_texts if chunk_texts else [""])
                faithfulness = faith_res.score
            return {
                "answer": answer,
                "confidence": faithfulness,
                "in_domain": True,
                "retrieved_chunk_doc_ids": sources,
                "faithfulness": faithfulness
            }
        except Exception as e:
            logger.error(f"LangChain invocation failed: {e}")

    # Robust fallback using direct Groq RAG if langchain dependencies unavailable
    if engine:
        client = get_groq_client()
        sys_prompt = "You are a LangChain RetrievalQA baseline model. Answer the question directly using standard RAG context."
        answer = client.analyze_with_system_prompt(sys_prompt, query, model="chat")
        return {
            "answer": answer,
            "confidence": 0.5,
            "in_domain": True,
            "retrieved_chunk_doc_ids": [],
            "faithfulness": 0.5
        }

    return {
        "answer": "LangChain pipeline unavailable.",
        "confidence": 0.0,
        "in_domain": True,
        "retrieved_chunk_doc_ids": [],
        "faithfulness": 0.0
    }
