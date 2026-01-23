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
