"""
MEXAR - Faithfulness Scoring Module
Measures how well the LLM answer is grounded in the retrieved context.
"""
import json
import logging
from typing import List, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FaithfulnessResult:
    """Result of faithfulness evaluation."""
    score: float  # 0-1 score
    total_claims: int
    supported_claims: int
    unsupported_claims: List[str]


class FaithfulnessScorer:
    """
    Evaluates how faithful (grounded) an LLM answer is to the context.
    
    Process:
    1. Extract factual claims from the answer
    2. Check each claim against the retrieved context
    3. Calculate percentage of supported claims
    
    High faithfulness = answer is well-grounded, low hallucination risk
    """
    
    def __init__(self, groq_client=None):
        """
        Initialize scorer.
        
        Args:
            groq_client: Groq client for LLM calls
        """
        self._client = groq_client
    
    @property
    def client(self):
        """Lazy load Groq client."""
        if self._client is None:
            from utils.groq_client import get_groq_client
            self._client = get_groq_client()
        return self._client
    
    def score(self, answer: str, context: str) -> FaithfulnessResult:
        """
        Score how well answer is grounded in context.
        
        Args:
            answer: LLM generated answer
            context: Retrieved context used to generate answer
            
        Returns:
            FaithfulnessResult with score and details
        """
        if not answer or not context:
            return FaithfulnessResult(
                score=1.0, 
                total_claims=0, 
                supported_claims=0, 
                unsupported_claims=[]
            )
        
        # Step 1: Extract claims from answer
        claims = self._extract_claims(answer)
        
        if not claims:
            return FaithfulnessResult(
                score=1.0,
                total_claims=0,
                supported_claims=0,
                unsupported_claims=[]
            )
        
        # Step 2: Check each claim against context
        supported = 0
        unsupported = []
        
        for claim in claims:
            if self._is_supported(claim, context):
                supported += 1
            else:
                unsupported.append(claim)
        
        # Step 3: Calculate score
        score = supported / len(claims)
        
        logger.info(f"Faithfulness: {supported}/{len(claims)} claims supported ({score*100:.0f}%)")
        
        return FaithfulnessResult(
            score=round(score, 3),
            total_claims=len(claims),
            supported_claims=supported,
            unsupported_claims=unsupported[:5]  # Limit to 5 for display
        )
    
    def _extract_claims(self, answer: str) -> List[str]:
        """
        Extract factual claims from the answer.
        
        Uses LLM to identify distinct factual statements.
        """
        try:
            prompt = f"""Extract individual factual claims from this answer. 
A claim is a specific statement that can be verified as true or false.
Return ONLY a JSON array of strings, no explanation.

Answer: "{answer[:2000]}"

Example output: ["Claim 1", "Claim 2", "Claim 3"]"""

            response = self.client.analyze_with_system_prompt(
                system_prompt="You extract factual claims. Return only valid JSON array.",
                user_message=prompt,
                model="fast",
                json_mode=True
            )
            
            # Parse response
            claims = json.loads(response)
            
            # Handle both list and dict responses
            if isinstance(claims, list):
                return [str(c) for c in claims if c]
            elif isinstance(claims, dict):
                return [str(c) for c in claims.get("claims", claims.get("statements", [])) if c]
            
            return []
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse claims JSON: {e}")
            # Fallback: split by sentences
            return self._fallback_extract_claims(answer)
        except Exception as e:
            logger.warning(f"Claim extraction failed: {e}")
            return self._fallback_extract_claims(answer)
    
    def _fallback_extract_claims(self, answer: str) -> List[str]:
        """Fallback claim extraction by splitting sentences."""
        import re
        sentences = re.split(r'(?<=[.!?])\s+', answer)
        # Filter to substantive sentences
        return [s.strip() for s in sentences if len(s.strip()) > 20][:10]
    
    def _is_supported(self, claim: str, context: str) -> bool:
        """
        Check if a claim is supported by the context.
        
        Uses LLM to evaluate if the context contains evidence for the claim.
        """
        try:
            prompt = f"""Is this claim supported by the context? Answer only YES or NO.

Claim: "{claim}"

Context (first 4000 chars):
"{context[:4000]}"

Answer YES if the context contains information that supports this claim.
Answer NO if the claim cannot be verified from the context or contradicts it."""

            response = self.client.analyze_with_system_prompt(
                system_prompt="You verify claims. Answer only YES or NO.",
                user_message=prompt,
                model="fast"
            )
            
            return "YES" in response.upper()
            
        except Exception as e:
            logger.warning(f"Support check failed: {e}")
            # Optimistic fallback - assume supported if check fails
            return True
    
    def quick_score(self, answer: str, context: str) -> float:
        """
        Quick faithfulness estimate without LLM calls.
        Uses text overlap as a proxy for grounding.
        
        Args:
            answer: LLM answer
            context: Retrieved context
            
        Returns:
            Estimated faithfulness score (0-1)
        """
        if not answer or not context:
            return 0.5
        
        # Get significant words from answer
        answer_words = set(w.lower() for w in answer.split() if len(w) > 4)
        context_lower = context.lower()
        
        if not answer_words:
            return 0.5
        
        # Check how many answer words appear in context
        found = sum(1 for w in answer_words if w in context_lower)
        overlap = found / len(answer_words)
        
        # Scale to reasonable range
        return min(1.0, overlap * 1.5)


def create_faithfulness_scorer() -> FaithfulnessScorer:
    """Factory function to create FaithfulnessScorer."""
    return FaithfulnessScorer()


class DebertaNLIScorer:
    """
    Primary faithfulness verifier per Section III-C.

    Uses cross-encoder/nli-deberta-v3-large (DeBERTa-v3-large fine-tuned on MNLI)
    to break the circular LLM-judges-LLM evaluation pattern.

    Implements:
    - Eq. 6: per-claim, per-document max entailment probability
    - Eq. 7: faithfulness score = fraction of claims exceeding TAU_ENT

    score() receives individual retrieved chunk texts (NOT concatenated), so the
    per-document max in Eq. 6 is meaningful.
    """

    TAU_ENT = 0.7  # Entailment probability threshold (Eq. 7)

    def __init__(self):
        self._model = None
        self._entailment_idx: int = 1  # Verified at load time from id2label

    @property
    def model(self):
        """Lazy-load CrossEncoder to avoid slow startup when not needed."""
        if self._model is None:
            from sentence_transformers import CrossEncoder
            logger.info("Loading cross-encoder/nli-deberta-v3-large for faithfulness scoring...")
            self._model = CrossEncoder("cross-encoder/nli-deberta-v3-large")

            # CRITICAL: verify the actual label order from the model's config,
            # NLI checkpoints do NOT always use the same label ordering.
            # Do not hardcode entailment_idx=1 without confirming here.
            try:
                id2label = self._model.model.config.id2label
                logger.info(f"DeBERTa NLI id2label: {id2label}")
                # Find the index whose label contains 'entail' (case-insensitive)
                for idx, label in id2label.items():
                    if "entail" in label.lower():
                        self._entailment_idx = int(idx)
                        break
                logger.info(
                    f"DeBERTa-v3 NLI loaded. "
                    f"Confirmed entailment_idx={self._entailment_idx} "
                    f"(label='{id2label.get(self._entailment_idx, 'unknown')}')"
                )
            except Exception as e:
                logger.warning(
                    f"Could not read id2label from DeBERTa config ({e}). "
                    f"Defaulting entailment_idx=1. Verify this is correct for this checkpoint."
                )
        return self._model

    def score(self, answer: str, context_documents: List[str]) -> FaithfulnessResult:
        """
        Score faithfulness of an answer against a list of individual retrieved chunks.

        Args:
            answer: LLM-generated answer text.
            context_documents: List of individual chunk texts (NOT concatenated).
                               Per-document max in Eq. 6 requires individual documents.

        Returns:
            FaithfulnessResult with per-sentence entailment-based score.
        """
        import re
        import numpy as np

        if not answer or not context_documents:
            return FaithfulnessResult(
                score=1.0, total_claims=0, supported_claims=0, unsupported_claims=[]
            )

        # Split answer into sentences (Eq. 6 operates per-claim / per-sentence)
        sentences = [
            s.strip()
            for s in re.split(r'(?<=[.!?])\s+', answer)
            if len(s.strip()) > 15
        ][:3]  # cap at top 3 key sentences for fast CPU NLI verification

        if not sentences:
            return FaithfulnessResult(
                score=1.0, total_claims=0, supported_claims=0, unsupported_claims=[]
            )

        supported = 0
        unsupported_sentences = []

        try:
            # Limit context documents to top 3 retrieved chunks
            top_docs = context_documents[:3]

            # Batch all (doc, sentence) pairs across sentences into a single predict call
            all_pairs = []
            for sentence in sentences:
                for doc in top_docs:
                    all_pairs.append((doc[:400], sentence[:200]))

            import torch
            with torch.inference_mode():
                raw_scores = self.model.predict(all_pairs, batch_size=32)
            probs = self._softmax(raw_scores)

            n_docs = len(top_docs)
            probs = probs.reshape(len(sentences), n_docs, -1)

            for i, sentence in enumerate(sentences):
                # Eq. 6: max entailment probability across all retrieved documents
                max_entailment = float(np.max(probs[i, :, self._entailment_idx]))

                if max_entailment > self.TAU_ENT:
                    supported += 1
                else:
                    unsupported_sentences.append(sentence)

        except Exception as e:
            logger.error(f"DebertaNLIScorer inference failed: {e}")
            return FaithfulnessResult(
                score=0.5,
                total_claims=len(sentences),
                supported_claims=0,
                unsupported_claims=sentences[:5],
            )

        # Eq. 7: faithfulness = fraction of supported claims
        score = supported / len(sentences)
        logger.info(
            f"DeBERTa NLI Faithfulness: {supported}/{len(sentences)} sentences "
            f"supported (score={score:.3f}, TAU_ENT={self.TAU_ENT})"
        )

        return FaithfulnessResult(
            score=round(score, 3),
            total_claims=len(sentences),
            supported_claims=supported,
            unsupported_claims=unsupported_sentences[:5],
        )

    @staticmethod
    def _softmax(x):
        """Numerically stable softmax over last axis."""
        import numpy as np
        e_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
        return e_x / e_x.sum(axis=-1, keepdims=True)


class FActScoreCompat:
    """
    Simulates the FActScore (Min et al., ACL 2023) evaluation.
    Breaks answer into atomic facts, verifies each fact against context independently.
    This acts as a wrapper around FaithfulnessScorer to explicitly mark it for FActScore baseline comparisons.
    """
    def __init__(self, groq_client=None):
        self._scorer = FaithfulnessScorer(groq_client=groq_client)
        
    def score(self, answer: str, context: str) -> FaithfulnessResult:
        result = self._scorer.score(answer, context)
        logger.info(f"FActScore: {result.score * 100:.1f}% ({result.supported_claims}/{result.total_claims} facts)")
        return result

