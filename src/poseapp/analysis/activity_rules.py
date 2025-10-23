# src/poseapp/analysis/activity_rules.py
import os  # filesystem utilities for path checks
import json  # (not used directly below, but kept if templates contain JSON we may inspect)
from dataclasses import dataclass  # for lightweight result containers
from typing import Dict, List, Tuple, Optional  # type hints

import numpy as np  # numeric helpers for simple stats

# Import scoring helpers from your scorer module
from ..scoring.scorer import score_band  # maps measured vs target angle to (score, band)

# ---------------------------------------------------------------------
# Utility: first existing path (project assets, then /mnt/data fallback)
# ---------------------------------------------------------------------
def _first_existing_path(*cands: str) -> Optional[str]:
    for p in cands:  # iterate through candidate paths in priority order
        if p and os.path.isfile(p):  # return the first that actually exists
            return p
    return None  # none found

# ---------------------------------------------------------------------
# Template registry: JSON/CSV paths per activity
# (assets/templates preferred; falls back to /mnt/data uploaded files)
# ---------------------------------------------------------------------
TEMPLATE_RULES: Dict[str, Dict[str, str]] = {
    "squat": {  # configuration/metadata for the squat activity
        "json": _first_existing_path(
            "assets/templates/squat_rule.json",  # primary location inside the repo
            "/mnt/data/squat_rule.json",         # fallback uploaded location
        ),
        "csv": _first_existing_path(
            "assets/templates/squat_rule.csv",
            "/mnt/data/squat_rule.csv",
        ),
        "overlay": _first_existing_path(  # optional reference overlay media
            "assets/templates/squat_overlay.mp4",
            "/mnt/data/squat_overlay.mp4",
        ),
        "primary_joints": ["knee_L_flex", "knee_R_flex", "hip_L_flex", "hip_R_flex", "ankle_L_pf", "ankle_R_pf"],  # joints we track
        "score_joint": "knee_ANY_flex",  # scalar used to count reps (ANY → avg/side)
        "targets": {  # target peak angles per joint
            "knee_L_flex": 100.0, "knee_R_flex": 100.0,
            "hip_L_flex": 60.0, "hip_R_flex": 60.0,
            "ankle_L_pf": 20.0, "ankle_R_pf": 20.0
        },
        "reps": 5,  # default target repetitions per set
        "phase_key": "phase",  # name of normalized phase vector in template JSON
    },
    "arm_abduction": {  # abduction of shoulders
        "json": _first_existing_path(
            "assets/templates/arm_abduction.json",
            "/mnt/data/arm_abduction.json",
        ),
        "csv": _first_existing_path(
            "assets/templates/arm_abduction.csv",
            "/mnt/data/arm_abduction.csv",
        ),
        "overlay": _first_existing_path(
            "assets/templates/arm_abduction_overlay.mp4",
            "/mnt/data/arm_abduction_overlay.mp4",
        ),
        "primary_joints": ["shoulder_L_abd", "shoulder_R_abd"],  # both arms
        "score_joint": "shoulder_ANY_abd",  # scalar used to count the cycle
        "targets": {"shoulder_L_abd": 175.0, "shoulder_R_abd": 175.0},  # near full abduction
        "reps": 5,
        "phase_key": "phase",
    },
    "forward_flexion": {  # one-sided shoulder flexion + supportive hip flexion
        "json": _first_existing_path(
            "assets/templates/forward_flexion.json",
            "/mnt/data/forward_flexion.json",
        ),
        "csv": _first_existing_path(
            "assets/templates/forward_flexion.csv",
            "/mnt/data/forward_flexion.csv",
        ),
        "overlay": _first_existing_path(
            "assets/templates/forward_flexion_overlay.mp4",
            "/mnt/data/forward_flexion_overlay.mp4",
        ),
        # visible-side only (ANY → we’ll lock to L or R once)
        "primary_joints": ["shoulder_ANY_flex", "hip_ANY_flex"],  # ANY means auto-lock later
        "score_joint": "shoulder_ANY_flex",  # main scalar for reps
        "targets": {"shoulder_L_flex": 90.0, "shoulder_R_flex": 90.0, "hip_L_flex": 30.0, "hip_R_flex": 30.0},  # per-side goals
        "reps": 5,
        "phase_key": "phase",
    },
    "calf_raise": {  # plantarflexion focus
        "json": _first_existing_path(
            "assets/templates/calf_raise.json",
            "/mnt/data/calf_raise.json",
        ),
        "csv": _first_existing_path(
            "assets/templates/calf_raise.csv",
            "/mnt/data/calf_raise.csv",
        ),
        "overlay": _first_existing_path(
            "assets/templates/calf_raise_overlay.mp4",
            "/mnt/data/calf_raise_overlay.mp4",
        ),
        "primary_joints": ["ankle_L_pf", "ankle_R_pf"],  # both ankles supported
        "score_joint": "ankle_ANY_pf",  # scalar may be ANY (visible side)
        "targets": {"ankle_L_pf": 25.0, "ankle_R_pf": 25.0},  # reasonable rise
        "reps": 10,
        "phase_key": "phase",
    },
    "jumping_jack": {  # compound arms + legs abduction rhythm
        "json": _first_existing_path(
            "assets/templates/jumping_jack.json",
            "/mnt/data/jumping_jack.json",
        ),
        "csv": _first_existing_path(
            "assets/templates/jumping_jack.csv",
            "/mnt/data/jumping_jack.csv",
        ),
        "overlay": _first_existing_path(
            "assets/templates/jumping_jack_overlay.mp4",
            "/mnt/data/jumping_jack_overlay.mp4",
        ),
        "primary_joints": ["shoulder_L_abd", "shoulder_R_abd", "hip_L_abd", "hip_R_abd"],  # arms + legs
        "score_joint": "shoulder_ANY_abd",  # cycle driven by arms
        "targets": {  # target abduction amounts
            "shoulder_L_abd": 175.0, "shoulder_R_abd": 175.0,
            "hip_L_abd": 30.0, "hip_R_abd": 30.0
        },
        "reps": 10,
        "phase_key": "phase",
    },
}

# ---------------------------------------------------------------------
# Dataclass returned by assessors
# ---------------------------------------------------------------------
@dataclass
class RepAssessment:
    counted: bool  # whether the repetition passes thresholds to be counted
    bands: Dict[str, Tuple[float, str]]  # per-joint band scores: (numeric, "Green/Amber/Red")
    message: str  # short feedback message for the user

# ---------------------------------------------------------------------
# Helpers for windows / geometry (snapshots use normalized coords)
# ---------------------------------------------------------------------
def _peak_in_window(series: List[Tuple[float, float]], t0: float, t1: float) -> float:
    if not series:  # empty input
        return float("nan")
    vals = [v for (t, v) in series if t0 <= t <= t1]  # keep samples within rep time window
    return float(np.nanmax(vals)) if vals else float("nan")  # max value over the window

def _min_in_window(series: List[Tuple[float, float]], t0: float, t1: float) -> float:
    if not series:  # empty input
        return float("nan")
    vals = [v for (t, v) in series if t0 <= t <= t1]  # keep samples within window
    return float(np.nanmin(vals)) if vals else float("nan")  # min value over the window

def _distance(p1, p2) -> Optional[float]:
    if not p1 or not p2:  # missing points
        return None
    return float(np.hypot(p1["x"] - p2["x"], p1["y"] - p2["y"]))  # Euclidean distance

def _hip_width(snapshot: Dict[str, Dict[str, float]]) -> Optional[float]:
    L = snapshot.get("left_hip"); R = snapshot.get("right_hip")  # hip keypoints
    if not (L and R):
        return None
    return float(np.hypot(L["x"] - R["x"], L["y"] - R["y"]))  # pixel-distance between hips (normalized space)

def _min_wrist_to_foot_norm(snaps: List[Tuple[float, Dict[str, Dict[str, float]]]], side: str) -> Optional[float]:
    """Min wrist→(ankle/toe/heel) distance normalized by hip width, across rep window."""
    wrist = "left_wrist" if side == "L" else "right_wrist"  # pick side-specific wrist
    ankle = "left_ankle" if side == "L" else "right_ankle"  # preferred foot anchor
    toe   = "left_toe"   if side == "L" else "right_toe"    # fallback toe if present
    heel  = "left_heel"  if side == "L" else "right_heel"   # fallback heel if present
    best = None  # track minimum normalized distance
    for _, s in snaps:  # iterate over snapshots inside the rep
        W = s.get(wrist); F = s.get(toe) or s.get(ankle) or s.get(heel)  # pick available foot landmark
        hw = _hip_width(s)  # normalization scale
        if not (W and F and hw and hw > 1e-6):  # guard against missing/degenerate geometry
            continue
        d = _distance(W, F) / hw  # normalize distance by hip width
        best = d if best is None else min(best, d)  # keep minimum reach distance
    return best  # None if nothing valid

def _ankle_vertical_rise_norm(snaps: List[Tuple[float, Dict[str, Dict[str, float]]]], side: str) -> Optional[float]:
    """(y_max - y_min)/hip_width for ankle y across window (y↓ is down; rise→y decreases)."""
    name = "left_ankle" if side == "L" else "right_ankle"  # choose ankle
    ys, hws = [], []  # collect y and hip-width per snapshot
    for _, s in snaps:
        A = s.get(name)
        hw = _hip_width(s)
        if A and hw and hw > 1e-6:
            ys.append(float(A["y"]))  # store vertical position
            hws.append(hw)            # store normalization scale
    if len(ys) < 2 or not hws:  # need at least two samples
        return None
    # Use median hip width for normalization (robust to jitter)
    hw_med = float(np.median(hws))
    return (max(ys) - min(ys)) / hw_med  # positive if there is upward excursion

def _dominant_side_from_series(keys: List[str], fallback: str = "L") -> str:
    """Infer locked side (L/R) from the presence of *_L_* or *_R_* keys in the series dict."""
    hasL = any(("_L_" in k) or k.endswith("_L") for k in keys)  # detect left series
    hasR = any(("_R_" in k) or k.endswith("_R") for k in keys)  # detect right series
    if hasL and not hasR:
        return "L"  # only left present
    if hasR and not hasL:
        return "R"  # only right present
    return fallback  # if both present/ambiguous, use fallback

# ---------------------------------------------------------------------
# Squat assessor
# ---------------------------------------------------------------------
def _squat_constraints(
    t0: float,
    t1: float,
    series_by_joint: Dict[str, List[Tuple[float, float]]],
    snapshots: List[Tuple[float, Dict[str, Dict[str, float]]]],
    targets: Dict[str, float],
) -> Tuple[bool, str, Dict[str, Tuple[float, str]]]:

    bands: Dict[str, Tuple[float, str]] = {}  # per-joint band results

    for jkey in ("knee_L_flex", "knee_R_flex", "hip_L_flex", "hip_R_flex", "ankle_L_pf", "ankle_R_pf"):
        tgt = float(targets.get(jkey, 90.0))  # default target if missing
        vmax = _peak_in_window(series_by_joint.get(jkey, []), t0, t1)  # peak angle in window
        s, band = score_band(vmax, tgt)  # compare to target
        bands[jkey] = (s, band)  # store score and band

    # hip/lower COM drop cue: mid-hip y increases (image y increases downward)
    dropped = False  # whether hips have descended visibly
    if snapshots:
        ys = []  # collect mid-hip vertical positions during the rep
        for _, kp in snapshots:
            yL = kp.get("left_hip", {}).get("y", None)
            yR = kp.get("right_hip", {}).get("y", None)
            if yL is not None and yR is not None:
                ys.append(0.5 * (float(yL) + float(yR)))  # average L/R hips
        if len(ys) >= 3:
            dropped = (max(ys) - min(ys)) >= 0.03  # threshold for visible drop

    best_knee = max(bands["knee_L_flex"][0], bands["knee_R_flex"][0])  # take better knee
    counted = (best_knee >= 0.5) and dropped  # require Amber+ knee + hip drop

    msg = []  # feedback
    if best_knee < 0.5: msg.append("bend knees deeper")  # encourage more knee flexion
    if not dropped: msg.append("lower hips more")  # encourage deeper squat
    if not msg: msg = ["ok"]  # success message
    return counted, "; ".join(msg), bands  # result for squat

# ---------------------------------------------------------------------
# Arm abduction assessor
# ---------------------------------------------------------------------
def _arm_abduction_constraints(
    t0: float,
    t1: float,
    series_by_joint: Dict[str, List[Tuple[float, float]]],
    snapshots: List[Tuple[float, Dict[str, Dict[str, float]]]],
    targets: Dict[str, float],
) -> Tuple[bool, str, Dict[str, Tuple[float, str]]]:
    bands: Dict[str, Tuple[float, str]] = {}  # per-joint band results
    for jkey in ("shoulder_L_abd", "shoulder_R_abd"):  # evaluate both shoulders
        tgt = float(targets.get(jkey, 175.0))  # near full abduction
        vmax = _peak_in_window(series_by_joint.get(jkey, []), t0, t1)  # peak in window
        s, band = score_band(vmax, tgt)  # convert to (score, band)
        bands[jkey] = (s, band)

    best = max(bands["shoulder_L_abd"][0], bands["shoulder_R_abd"][0])  # stronger arm result

    # optional crossing cue
    wrx = []  # left-right wrist x difference series to detect crossing midline
    for (t, kp) in snapshots:
        if not (t0 <= t <= t1):
            continue
        lw, rw = kp.get("left_wrist", None), kp.get("right_wrist", None)
        if lw and rw and lw.get("conf", 0.4) >= 0.4 and rw.get("conf", 0.4) >= 0.4:
            wrx.append(float(lw["x"] - rw["x"]))  # sign change implies crossing

    crossed = False  # whether wrists crossed midline at least once
    if len(wrx) >= 3:
        for a, b in zip(wrx[:-1], wrx[1:]):  # scan consecutive differences
            if np.sign(a) == 0 or np.sign(b) == 0 or np.sign(a) != np.sign(b):
                crossed = True
                break

    counted = (best >= 0.5) and (crossed or len(wrx) < 3)  # Amber+ ; if we can’t judge crossing, don’t block
    msg = []  # feedback
    if best < 0.5: msg.append("raise arms wider")  # encourage more range
    if len(wrx) >= 3 and not crossed: msg.append("wrists didn’t cross midline")  # rhythm/form cue
    if not msg: msg = ["ok"]  # success
    return counted, "; ".join(msg), bands  # result for arm abduction

# ---------------------------------------------------------------------
# Forward flexion assessor (single side, wrist→foot reach)
# ---------------------------------------------------------------------
def _forward_flexion_constraints(
    t0: float,
    t1: float,
    series_by_joint: Dict[str, List[Tuple[float, float]]],
    snapshots: List[Tuple[float, Dict[str, Dict[str, float]]]],
    targets: Dict[str, float],
) -> Tuple[bool, str, Dict[str, Tuple[float, str]]]:

    # Determine dominant/locked side from series keys (your main_window locks side beforehand)
    side = _dominant_side_from_series(list(series_by_joint.keys()), fallback="L")  # pick L/R
    sj = f"shoulder_{side}_flex"  # shoulder flexion joint name
    hj = f"hip_{side}_flex"       # supportive hip flexion joint name

    bands: Dict[str, Tuple[float, str]] = {}  # band results

    # Shoulder flex band
    tgt_sh = float(targets.get(sj, 90.0))  # default target shoulder flex
    vmax_sh = _peak_in_window(series_by_joint.get(sj, []), t0, t1)  # peak shoulder flex in window
    s_sh, b_sh = score_band(vmax_sh, tgt_sh)  # band for shoulder
    bands[sj] = (s_sh, b_sh)

    # Optional hip band (supportive, not required)
    tgt_hip = float(targets.get(hj, 30.0))  # hip support target
    vmax_hip = _peak_in_window(series_by_joint.get(hj, []), t0, t1)  # peak hip flex
    s_hip, b_hip = score_band(vmax_hip, tgt_hip)  # band for hip
    bands[hj] = (s_hip, b_hip)

    # Geometric cue: wrist should approach foot on the SAME side
    dmin = _min_wrist_to_foot_norm(snapshots, side)  # normalized by hip width
    prox_ok = (dmin is not None) and (dmin <= 0.60)   # threshold for proximity to foot

    # Count if shoulder >= Amber and proximity ok
    counted = (s_sh >= 0.5) and prox_ok  # primary rule

    msg = []  # feedback
    if s_sh < 0.5:
        msg.append("flex shoulder more")  # insufficient shoulder range
    if not prox_ok:
        msg.append("reach closer to feet")  # insufficient reach
    if not msg:
        msg = ["ok"]  # success

    # If proximity is weak, nudge band to Amber/Red (still counted per your spec if s_sh>=Amber)
    if dmin is None:
        bands[sj] = (s_sh, "Red")  # cannot judge proximity → pessimistic band
    elif not prox_ok and b_sh == "Green":
        bands[sj] = (0.5, "Amber")  # downgrade to Amber if range is good but reach is weak

    return counted, "; ".join(msg), bands  # result for forward flexion

# ---------------------------------------------------------------------
# Calf raise assessor (single side, heel rise)
# ---------------------------------------------------------------------
def _calf_raise_constraints(
    t0: float,
    t1: float,
    series_by_joint: Dict[str, List[Tuple[float, float]]],
    snapshots: List[Tuple[float, Dict[str, Dict[str, float]]]],
    targets: Dict[str, float],
) -> Tuple[bool, str, Dict[str, Tuple[float, str]]]:

    # Determine dominant/locked side (main_window locks the side; we respect that)
    side = _dominant_side_from_series(list(series_by_joint.keys()), fallback="L")  # choose L/R
    aj = f"ankle_{side}_pf"  # plantarflexion joint key

    bands: Dict[str, Tuple[float, str]] = {}  # per-joint band

    tgt = float(targets.get(aj, 25.0))  # required plantarflexion angle
    vmax = _peak_in_window(series_by_joint.get(aj, []), t0, t1)  # peak angle in window
    s, band = score_band(vmax, tgt)  # (score, band) for ankle
    bands[aj] = (s, band)

    # Geometric cue: visible heel/ankle should RISE (ankle y decreases) — normalize by hip width
    rise_norm = _ankle_vertical_rise_norm(snapshots, side)  # (y_max - y_min)/hip_width
    # thresholds tuned for normalized geometry (0.05 ~ small but visible rise)
    if rise_norm is None:
        rise_ok = False  # cannot verify rise
    else:
        rise_ok = rise_norm >= 0.05  # minimal visible rise

    counted = (s >= 0.5) and rise_ok  # Amber+ and visible rise

    msg = []  # feedback
    if s < 0.5:
        msg.append("plantarflex more")  # need more ankle PF
    if not rise_ok:
        msg.append("rise onto toes more")  # need more vertical excursion
    if not msg:
        msg = ["ok"]  # success

    # If rise is weak, nudge band down but still count per your rule if Amber achieved
    if rise_norm is None:
        bands[aj] = (s, "Red")  # cannot verify → pessimistic
    elif (not rise_ok) and band == "Green":
        bands[aj] = (0.5, "Amber")  # downgrade quality

    return counted, "; ".join(msg), bands  # result for calf raise

# ---------------------------------------------------------------------
# Jumping jack assessor
# ---------------------------------------------------------------------
def _jumping_jack_constraints(
    t0: float,
    t1: float,
    series_by_joint: Dict[str, List[Tuple[float, float]]],
    snapshots: List[Tuple[float, Dict[str, Dict[str, float]]]],
    targets: Dict[str, float],
) -> Tuple[bool, str, Dict[str, Tuple[float, str]]]:

    bands: Dict[str, Tuple[float, str]] = {}  # store arm/leg bands
    # arms
    for jkey in ("shoulder_L_abd", "shoulder_R_abd"):  # evaluate both arms
        tgt = float(targets.get(jkey, 175.0))  # near full abduction
        vmax = _peak_in_window(series_by_joint.get(jkey, []), t0, t1)  # peak arm abduction
        s, band = score_band(vmax, tgt)  # map to band
        bands[jkey] = (s, band)
    # legs
    for jkey in ("hip_L_abd", "hip_R_abd"):  # evaluate both legs
        tgt = float(targets.get(jkey, 30.0))  # modest hip abduction
        vmax = _peak_in_window(series_by_joint.get(jkey, []), t0, t1)  # peak leg abduction
        s, band = score_band(vmax, tgt)  # map to band
        bands[jkey] = (s, band)

    best_arm = max(bands["shoulder_L_abd"][0], bands["shoulder_R_abd"][0])  # best arm
    best_leg = max(bands["hip_L_abd"][0], bands["hip_R_abd"][0])            # best leg

    # rhythm cue (arms up when legs wide): crude correlation between arm signal & leg signal
    def _avg_in_window(keys: List[str]) -> List[Tuple[float, float]]:
        buckets: Dict[float, List[float]] = {}  # aggregate values by timestamp
        for k in keys:
            for (t, v) in series_by_joint.get(k, []):
                if t0 <= t <= t1:  # within rep window
                    buckets.setdefault(t, []).append(float(v))  # collect per time
        pts = sorted((t, float(np.mean(vs))) for t, vs in buckets.items())  # mean across keys
        return pts

    arms = _avg_in_window(["shoulder_L_abd", "shoulder_R_abd"])  # arm trajectory
    legs = _avg_in_window(["hip_L_abd", "hip_R_abd"])            # leg trajectory

    rhythm_ok = True  # default to OK if insufficient data
    if len(arms) >= 4 and len(legs) >= 4:
        ta, va = zip(*arms)  # arms time/values
        tl, vl = zip(*legs)  # legs time/values
        ts = np.linspace(max(min(ta), min(tl)), min(max(ta), max(tl)), num=20, dtype=np.float32)  # common time grid
        va_i = np.interp(ts, ta, va)  # interpolate arms onto grid
        vl_i = np.interp(ts, tl, vl)  # interpolate legs onto grid
        da = np.diff(va_i)  # first derivative (motion trend)
        dl = np.diff(vl_i)
        corr = np.corrcoef(da, dl)[0, 1] if (np.std(da) > 1e-3 and np.std(dl) > 1e-3) else 0.0  # correlation of trends
        rhythm_ok = bool(corr >= 0.2)  # require weak positive correlation

    counted = (best_arm >= 0.5) and (best_leg >= 0.5) and rhythm_ok  # Amber+ both + rhythm
    msg = []  # feedback
    if best_arm < 0.5: msg.append("raise arms higher")  # arm range cue
    if best_leg < 0.5: msg.append("spread legs wider")  # leg range cue
    if not rhythm_ok: msg.append("sync arms/legs rhythm")  # coordination cue
    if not msg: msg = ["ok"]  # success
    return counted, "; ".join(msg), bands  # result for jumping jack

# ---------------------------------------------------------------------
# Public dispatcher
# ---------------------------------------------------------------------
def assess_activity_rep(
    key: str,  # activity key (e.g., "squat")
    series_by_joint: Dict[str, List[Tuple[float, float]]],  # per-joint time series (t, angle)
    t0: float,  # rep start time
    t1: float,  # rep end time
    snapshots: List[Tuple[float, Dict[str, Dict[str, float]]]],  # (t, kpmap snapshot) during rep
    targets: Dict[str, float],  # target angles per joint
) -> RepAssessment:
    if key == "squat":  # route to squat assessor
        counted, message, bands = _squat_constraints(t0, t1, series_by_joint, snapshots, targets)
        return RepAssessment(counted=counted, bands=bands, message=message)
    if key == "arm_abduction":  # route to arm abduction assessor
        counted, message, bands = _arm_abduction_constraints(t0, t1, series_by_joint, snapshots, targets)
        return RepAssessment(counted=counted, bands=bands, message=message)
    if key == "forward_flexion":  # route to forward flexion assessor
        counted, message, bands = _forward_flexion_constraints(t0, t1, series_by_joint, snapshots, targets)
        return RepAssessment(counted=counted, bands=bands, message=message)
    if key == "calf_raise":  # route to calf raise assessor
        counted, message, bands = _calf_raise_constraints(t0, t1, series_by_joint, snapshots, targets)
        return RepAssessment(counted=counted, bands=bands, message=message)
    if key == "jumping_jack":  # route to jumping jack assessor
        counted, message, bands = _jumping_jack_constraints(t0, t1, series_by_joint, snapshots, targets)
        return RepAssessment(counted=counted, bands=bands, message=message)

    # default: if unknown activity, consider rep counted with no band details
    return RepAssessment(counted=True, bands={}, message="ok")
