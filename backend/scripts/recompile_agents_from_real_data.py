"""
MEXAR - Bulk Recompile Domain Agents from Real Data.
Reads real text documents from test_data/medical_real/, test_data/legal_real/, and test_data/financial_real/
and compiles knowledge into SQLite database and FastEmbed vector store for medical_agent, legal_agent, and financial_agent.
"""
import os
import sys
import glob
import logging
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.knowledge_compiler import create_knowledge_compiler
from modules.prompt_analyzer import create_prompt_analyzer
from core.database import Base, engine as db_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def recompile_domain_agent(domain_key: str, agent_name: str, system_prompt: str):
    data_dir = REPO_ROOT / "test_data" / f"{domain_key}_real"
    txt_files = list(data_dir.glob("*.txt"))

    if not txt_files:
        logger.warning(f"No .txt files found in {data_dir} for domain '{domain_key}'")
        return

    logger.info(f"Recompiling '{agent_name}' from {len(txt_files)} documents in {data_dir}...")

    parsed_data = []
    for fpath in sorted(txt_files):
        try:
            content = fpath.read_text(encoding="utf-8")
            parsed_data.append({
                "file_name": fpath.name,
                "source": fpath.name,
                "text": content,
                "content": content,
                "format": "txt"
            })
        except Exception as e:
            logger.error(f"Error reading {fpath}: {e}")

    analyzer = create_prompt_analyzer()
    prompt_analysis = analyzer.analyze_prompt(system_prompt)
    prompt_analysis["domain"] = domain_key

    compiler = create_knowledge_compiler()
    res = compiler.compile(
        agent_name=agent_name,
        parsed_data=parsed_data,
        system_prompt=system_prompt,
        prompt_analysis=prompt_analysis
    )

    logger.info(
        f"Recompiled '{agent_name}': signature terms={len(res.get('domain_signature', []))}, "
        f"processed {len(parsed_data)} files successfully."
    )


def main():
    Base.metadata.create_all(bind=db_engine)

    agents_config = [
        (
            "medical",
            "medical_agent",
            "You are an expert medical AI assistant specialized in cardiology, oncology, and internal medicine."
        ),
        (
            "legal",
            "legal_agent",
            "You are an expert legal AI assistant specialized in contract law, intellectual property, and corporate governance."
        ),
        (
            "financial",
            "financial_agent",
            "You are an expert financial AI assistant specialized in SEC EDGAR 10-K filings, MD&A, and risk factor analysis."
        )
    ]

    for domain_key, agent_name, system_prompt in agents_config:
        recompile_domain_agent(domain_key, agent_name, system_prompt)


if __name__ == "__main__":
    main()
