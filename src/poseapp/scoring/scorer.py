# src/poseapp/scoring/scorer.py
import numpy as np  # numerical operations

def score_band(measured: float, target: float):
    if measured is None or not np.isfinite(measured):  # invalid value → fail
        return 0.0, "Red"  # zero score
    d = abs(float(measured) - float(target))  # deviation from target
    if d <= 5:  return 1.0, "Green"  # within 5° = perfect
    if d <= 10: return 0.5, "Amber"  # within 10° = moderate
    return 0.0, "Red"  # else poor

def form_stability(angle_series):
    if not angle_series or len(angle_series) < 5:  # need enough samples
        return 0.0
    arr = np.array([a for a in angle_series if a is not None and np.isfinite(a)], dtype=float)  # filter valid angles
    if arr.size < 5:  # still too few values
        return 0.0
    k = max(1, int(0.2 * arr.size))  # take top 20% of values
    top = np.sort(arr)[-k:]  # extract that subset
    std_top = float(np.std(top))  # standard deviation of top angles
    return float(np.clip(1.0 - (std_top / 15.0), 0.0, 1.0))  # map std → stability score [0..1]

def symmetry_index(L, R):
    if L is None or R is None or (L + R) == 0:  # invalid limbs data
        return 0.0
    return 100.0 * abs(L - R) / (0.5 * (L + R) + 1e-6)  # % asymmetry (smaller is better)

def final_score(rep_scores, form_stab, si):
    mean_rep = float(np.mean(rep_scores)) if rep_scores else 0.0  # average of rep scores
    score = 0.7 * mean_rep + 0.3 * float(form_stab)  # weighted blend
    if si > 15.0:  # large asymmetry penalty
        score *= 0.9
    return round(100.0 * score, 1)  # return final score (0–100)
