"""
Calculates McNemar's test for significance between two models,
using the stated binarization threshold.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.reasoning_engine import ReasoningEngine

THRESHOLD = ReasoningEngine.MCNEMAR_BINARIZATION_THRESHOLD

def mcnemars_test(scores_model_A: list, scores_model_B: list):
    """
    Computes McNemar's test p-value for paired nominal data.
    scores are lists of float faithfulness scores.
    """
    if len(scores_model_A) != len(scores_model_B):
        raise ValueError("Must have same number of scores")
        
    # Binarize
    bin_A = [1 if s >= THRESHOLD else 0 for s in scores_model_A]
    bin_B = [1 if s >= THRESHOLD else 0 for s in scores_model_B]
    
    # Contingency table
    #              B correct | B wrong
    # A correct |     a      |    b
    # A wrong   |     c      |    d
    
    a, b, c, d = 0, 0, 0, 0
    for a_val, b_val in zip(bin_A, bin_B):
        if a_val == 1 and b_val == 1: a += 1
        elif a_val == 1 and b_val == 0: b += 1
        elif a_val == 0 and b_val == 1: c += 1
        else: d += 1
        
    # Chi-square statistic: (b - c)^2 / (b + c)
    if b + c == 0:
        print("Models are identical given the threshold.")
        return 1.0 # No difference
        
    chi_square = ((abs(b - c) - 1)**2) / (b + c)  # with continuity correction
    
    print(f"McNemar's Test Results:")
    print(f"Binarization Threshold: {THRESHOLD}")
    print(f"Contingency Table: a={a}, b={b}, c={c}, d={d}")
    print(f"Chi-square: {chi_square:.3f}")
    
    try:
        from scipy.stats import chi2
        p_value = 1 - chi2.cdf(chi_square, 1)
        print(f"p-value: {p_value:.4f}")
        return p_value
    except ImportError:
        print("Note: Install scipy ('pip install scipy') to automatically calculate the p-value.")
        return chi_square

def cohens_d(scores_a: list, scores_b: list) -> float:
    """
    Computes Cohen's d effect size between two paired/unpaired score distributions.
    Used for forest plots in Figure 3.
    """
    if not scores_a or not scores_b:
        return 0.0
    import numpy as np
    mean_diff = float(np.mean(scores_a) - np.mean(scores_b))
    std_a = np.std(scores_a, ddof=1) if len(scores_a) > 1 else 0.0
    std_b = np.std(scores_b, ddof=1) if len(scores_b) > 1 else 0.0
    pooled_std = np.sqrt((std_a**2 + std_b**2) / 2.0)
    return round(float(mean_diff / pooled_std), 3) if pooled_std > 0 else 0.0


if __name__ == "__main__":

    # Mock data
    scores_mexar = [0.8, 0.9, 0.4, 0.7, 0.65, 0.8]
    scores_baseline = [0.5, 0.7, 0.6, 0.4, 0.55, 0.8]
    mcnemars_test(scores_mexar, scores_baseline)
