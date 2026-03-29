"""
MEXAR - Evaluation Metrics Helper
Calculates common metrics across different baselines and experiments.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.faithfulness import FaithfulnessScorer, BartNLIScorer, FActScoreCompat

class MetricsRunner:
    def __init__(self):
        self.faith_scorer = FaithfulnessScorer()
        self.bart_nli = BartNLIScorer()
        self.factscore = FActScoreCompat()

    def evaluate_all(self, answer: str, context: str):
        faith_res = self.faith_scorer.score(answer, context)
        bart_res = self.bart_nli.score(answer, context)
        fact_res = self.factscore.score(answer, context)
        return {
            "faithfulness": faith_res.score,
            "bart_nli": bart_res.score,
            "factscore": fact_res.score
        }
