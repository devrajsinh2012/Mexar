"""
MEXAR - Evaluation Metrics Helper
Calculates common metrics across different baselines and experiments.
"""
import sys
import os
from typing import Any, Dict, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.faithfulness import FaithfulnessScorer, BartNLIScorer, FActScoreCompat


class MetricsRunner:
    def __init__(self):
        self.faith_scorer = FaithfulnessScorer()
        self.bart_nli = BartNLIScorer()
        self.factscore = FActScoreCompat()

    def evaluate_all(self, answer: str, context: str) -> Dict[str, float]:
        faith_res = self.faith_scorer.score(answer, context)
        bart_res = self.bart_nli.score(answer, context)
        fact_res = self.factscore.score(answer, context)
        return {
            "faithfulness": faith_res.score,
            "bart_nli": bart_res.score,
            "factscore": fact_res.score,
        }

    def extract_faithfulness(self, response: Dict[str, Any]) -> Optional[float]:
        """Extract faithfulness score from response payloads across formats."""
        if not isinstance(response, dict):
            return None

        explainability = response.get("explainability") or {}
        confidence_breakdown = explainability.get("confidence_breakdown") or {}

        for candidate in (
            confidence_breakdown.get("faithfulness"),
            explainability.get("faithfulness"),
        ):
            parsed = self._parse_numeric(candidate)
            if parsed is not None:
                return self._clamp(parsed)

        return None

    def extract_confidence(self, response: Dict[str, Any]) -> Optional[float]:
        """Extract numeric confidence score if available."""
        if not isinstance(response, dict):
            return None

        parsed = self._parse_numeric(response.get("confidence"))
        if parsed is None:
            return None
        return self._clamp(parsed)

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    @staticmethod
    def _parse_numeric(value: Any) -> Optional[float]:
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return None

            if cleaned.endswith("%"):
                cleaned = cleaned[:-1].strip()
                try:
                    return float(cleaned) / 100.0
                except ValueError:
                    return None

            try:
                return float(cleaned)
            except ValueError:
                return None

        return None
