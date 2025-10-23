# guide_match.py
from __future__ import annotations
import os
import json
import csv
from typing import Dict, List, Tuple, Optional

import numpy as np

from .activity_rules import TEMPLATE_RULES  # activity templates metadata

# -----------------------------------------------------------------------------
# Load template JSON/CSV exported by extract_gif_movenet.py
# Each template stores reference joint-angle curves for a specific activity.
# -----------------------------------------------------------------------------
def load_template_for_activity(key: str) -> Dict[str, object]:
    # Fetch metadata paths for the given activity (json + csv)
    meta = TEMPLATE_RULES.get(key, {})
    js_path = meta.get("json", None)
    csv_path = meta.get("csv", None)

    phase = np.array([], dtype=np.float32)  # normalized time/phase array
    series: Dict[str, np.ndarray] = {}      # joint name -> angle array

    # Load phase vector from JSON file if available
    if js_path and os.path.isfile(js_path):
        with open(js_path, "r", encoding="utf-8") as f:
            js = json.load(f)
        if "phase" in js:
            phase = np.asarray(js["phase"], dtype=np.float32)

    # Load per-joint angle series from CSV file
    if csv_path and os.path.isfile(csv_path):
        buckets: Dict[str, List[float]] = {}
        with open(csv_path, "r", encoding="utf-8", newline="") as cf:
            rdr = csv.DictReader(cf)
            # Expected columns: frame, phase, joint, value
            for row in rdr:
                jn = row.get("joint")
                val = row.get("value")
                if jn is None or val is None:
                    continue
                try:
                    buckets.setdefault(jn, []).append(float(val))
                except Exception:
                    continue
        # Convert lists to numpy arrays
        series = {k: np.asarray(v, dtype=np.float32) for k, v in buckets.items()}

    # Return both phase and series data
    return {"phase": phase, "series": series, "fps": 0.0}

# -----------------------------------------------------------------------------
# Extracts the portion of (t, value) pairs that lie between t0 and t1
# Used for comparing user motion to a segment of the reference.
# -----------------------------------------------------------------------------
def extract_scalar_window(series: List[Tuple[float, float]], t0: float, t1: float) -> List[Tuple[float, float]]:
    return [(t, v) for (t, v) in series if t0 <= t <= t1]

# -----------------------------------------------------------------------------
# Selects the relevant scalar (angle) series from the template based on activity type
# -----------------------------------------------------------------------------
def _template_scalar_for(key: str, tpl_series: Dict[str, np.ndarray]) -> Optional[np.ndarray]:
    # Mapping of activity types to their representative joint angles
    order = {
        "squat": ["knee_ANY_flex", "knee_L_flex", "knee_R_flex"],
        "arm_abduction": ["shoulder_ANY_abd", "shoulder_L_abd", "shoulder_R_abd"],
        "forward_flexion": ["shoulder_ANY_flex", "shoulder_L_flex", "shoulder_R_flex"],
        "calf_raise": ["ankle_ANY_pf", "ankle_L_pf", "ankle_R_pf"],
        "jumping_jack": ["shoulder_ANY_abd", "shoulder_L_abd", "shoulder_R_abd"],
    }
    cands = order.get(key, [])
    # Return first available matching joint angle
    for c in cands:
        if c in tpl_series:
            return tpl_series[c]
    # Fallback: use the average of all angle series if no match found
    if tpl_series:
        allv = np.stack([v for v in tpl_series.values()], axis=0)
        return np.nanmean(allv, axis=0)
    return None

# -----------------------------------------------------------------------------
# Compare a user's motion (time-windowed scalar) with the stored template.
# Produces MAE (mean absolute error), phase correlation, and color-coded band.
# -----------------------------------------------------------------------------
def guide_match_activity_window(
    key: str,
    user_series: List[Tuple[float, float]],  # [(timestamp, angle_in_deg), ...]
    t0: float,
    t1: float,
) -> Dict[str, float | str]:
    # Load template data and pick the relevant scalar
    tpl = load_template_for_activity(key)
    tpl_scalar = _template_scalar_for(key, tpl["series"])

    # Early return if data is insufficient
    if tpl_scalar is None or len(user_series) < 4:
        return {"mean_abs_err": float("nan"), "phase_corr": 0.0, "band": "Red"}

    # Separate timestamps and angle values
    ut, uv = zip(*user_series)
    ut = np.asarray(ut, dtype=np.float32)
    uv = np.asarray(uv, dtype=np.float32)

    # Normalize user’s time axis to [0, 1] range for phase alignment
    ph_user = (ut - t0) / max(1e-6, (t1 - t0))
    ph_tpl = np.linspace(0.0, 1.0, num=len(tpl_scalar), dtype=np.float32)

    # Interpolate user’s angles to match template phase grid
    uv_on_tpl = np.interp(ph_tpl, ph_user, uv)

    # Compute Mean Absolute Error (MAE) between template and user
    mae = float(np.nanmean(np.abs(uv_on_tpl - tpl_scalar)))

    # Compute phase correlation using normalized z-scores
    def _z(a):
        m, s = np.nanmean(a), np.nanstd(a) + 1e-6
        return (a - m) / s
    pcorr = float(1.0 - np.nanmean(np.abs(_z(uv_on_tpl) - _z(tpl_scalar))))
    pcorr = max(0.0, min(1.0, pcorr))  # clamp between [0,1]

    # Assign qualitative color band based on error
    if mae <= 5.0:
        band = "Green"   # excellent match
    elif mae <= 10.0:
        band = "Amber"   # moderate deviation
    else:
        band = "Red"     # poor match

    # Return comparison metrics
    return {"mean_abs_err": mae, "phase_corr": pcorr, "band": band}
