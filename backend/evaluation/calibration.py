"""
MEXAR - Expected Calibration Error (ECE) & Reliability Diagram Data (Figure 4).
Computes calibration metrics across confidence bins.
"""
import math
from typing import List, Tuple, Dict, Any
import numpy as np


def expected_calibration_error(confidences: List[float], correctness: List[bool], n_bins: int = 10) -> float:
    """
    Calculate Expected Calibration Error (ECE).
    confidences: predicted confidence per query (0.0 to 1.0)
    correctness: true correctness label per query (True / False)
    """
    if not confidences or len(confidences) != len(correctness):
        return 0.0

    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(confidences)

    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        in_bin = [
            (c, corr) for c, corr in zip(confidences, correctness)
            if (lo <= c < hi) or (i == n_bins - 1 and c == hi)
        ]
        if not in_bin:
            continue
        bin_conf = float(np.mean([c for c, _ in in_bin]))
        bin_acc = float(np.mean([1.0 if corr else 0.0 for _, corr in in_bin]))
        bin_weight = len(in_bin) / n
        ece += bin_weight * abs(bin_conf - bin_acc)

    return round(float(ece), 4)


def reliability_diagram_data(confidences: List[float], correctness: List[bool], n_bins: int = 10) -> List[Dict[str, float]]:
    """
    Generate Reliability Diagram coordinates (mean predicted confidence vs observed accuracy) per bin.
    """
    if not confidences or len(confidences) != len(correctness):
        return []

    bins = np.linspace(0.0, 1.0, n_bins + 1)
    points = []

    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        in_bin = [
            (c, corr) for c, corr in zip(confidences, correctness)
            if (lo <= c < hi) or (i == n_bins - 1 and c == hi)
        ]
        if not in_bin:
            continue
        bin_conf = float(np.mean([c for c, _ in in_bin]))
        bin_acc = float(np.mean([1.0 if corr else 0.0 for _, corr in in_bin]))
        points.append({
            "bin_range": f"{lo:.1f}-{hi:.1f}",
            "mean_confidence": round(bin_conf, 4),
            "observed_accuracy": round(bin_acc, 4),
            "count": len(in_bin)
        })

    return points
