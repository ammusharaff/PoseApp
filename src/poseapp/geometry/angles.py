# src/poseapp/geometry/angles.py
from typing import Dict, Any, List, Tuple, Optional  # type hints for structured data
import math  # math operations for trigonometry
import numpy as np  # numerical computations

# Type aliases for clarity
Point = Tuple[float, float]  # (x, y)
KeypointMap = Dict[str, Dict[str, float]]  # mapping of keypoint name → {x, y, conf}

def _get_xy(kpmap: KeypointMap, name: str) -> Optional[Point]:
    # Return (x, y) if keypoint exists and confidence ≥ 0.3
    if name in kpmap and kpmap[name].get("conf", 0) >= 0.3:
        return (kpmap[name]["x"], kpmap[name]["y"])
    return None  # fallback when missing or low confidence

def midpoint(a: Point, b: Point) -> Point:
    # Compute midpoint between two 2D points
    return ((a[0]+b[0])/2.0, (a[1]+b[1])/2.0)

def vec(a: Point, b: Point) -> np.ndarray:
    # Return 2D vector from b → a
    return np.array([a[0]-b[0], a[1]-b[1]], dtype=np.float32)

def angle_deg(a: Point, j: Point, b: Point, eps: float=1e-6) -> Optional[float]:
    # Compute angle (in degrees) at joint j formed by points a-j-b
    v1 = vec(a, j)
    v2 = vec(b, j)
    n1 = np.linalg.norm(v1); n2 = np.linalg.norm(v2)
    if n1 < eps or n2 < eps:  # avoid division by zero
        return None
    cosv = float(np.clip(np.dot(v1, v2)/(n1*n2), -1.0, 1.0))  # cosine law
    return float(math.degrees(math.acos(cosv)))  # convert to degrees

def compute_derived(kpmap: KeypointMap) -> Dict[str, Point]:
    # Derive higher-level body points such as shoulder_center, hip_center, neck, torso_axis
    out: Dict[str, Point] = {}
    ls = _get_xy(kpmap, "left_shoulder")
    rs = _get_xy(kpmap, "right_shoulder")
    lh = _get_xy(kpmap, "left_hip")
    rh = _get_xy(kpmap, "right_hip")
    nose = _get_xy(kpmap, "nose")

    if ls and rs:
        shoulder_center = midpoint(ls, rs); out["shoulder_center"] = shoulder_center
    if lh and rh:
        hip_center = midpoint(lh, rh); out["hip_center"] = hip_center
    if ls and rs and nose:
        # Approximate neck as midpoint between shoulders projected toward nose
        sc = midpoint(ls, rs)
        neck = midpoint(sc, nose)
        out["neck"] = neck
    if "shoulder_center" in out and "hip_center" in out:
        # Torso axis vector (shoulders to hips)
        out["torso_axis"] = (out["shoulder_center"][0]-out["hip_center"][0],
                             out["shoulder_center"][1]-out["hip_center"][1])
    return out

def angles_of_interest(kpmap: KeypointMap) -> Dict[str, float]:
    """Return a small set of key angles for Mode A overlay."""
    drv = compute_derived(kpmap)
    ang: Dict[str, float] = {}

    # Elbow flexion angles
    for side in ("left","right"):
        wrist = _get_xy(kpmap, f"{side}_wrist")
        elbow = _get_xy(kpmap, f"{side}_elbow")
        shoulder = _get_xy(kpmap, f"{side}_shoulder")
        if wrist and elbow and shoulder:
            a = angle_deg(wrist, elbow, shoulder)
            if a is not None: ang[f"elbow_{side}"] = a

    # Knee flexion angles
    for side in ("left","right"):
        ankle = _get_xy(kpmap, f"{side}_ankle")
        knee = _get_xy(kpmap, f"{side}_knee")
        hip = _get_xy(kpmap, f"{side}_hip")
        if ankle and knee and hip:
            a = angle_deg(ankle, knee, hip)
            if a is not None: ang[f"knee_{side}"] = a

    # Hip flexion angles relative to shoulder center
    if "shoulder_center" in drv:
        sc = drv["shoulder_center"]
        for side in ("left","right"):
            knee = _get_xy(kpmap, f"{side}_knee")
            hip = _get_xy(kpmap, f"{side}_hip")
            if knee and hip:
                a = angle_deg(knee, hip, sc)
                if a is not None: ang[f"hip_{side}"] = a

    # Neck flexion/extension (approx): angle between torso axis and neck→nose vector
    if "torso_axis" in drv and "neck" in drv and "nose" in kpmap:
        neck = drv["neck"]; nose = _get_xy(kpmap, "nose")
        if neck and nose:
            ta = np.array(drv["torso_axis"], dtype=np.float32)
            nh = vec(nose, neck)
            n1, n2 = np.linalg.norm(ta), np.linalg.norm(nh)
            if n1 >= 1e-6 and n2 >= 1e-6:
                cosv = float(np.clip(np.dot(ta, nh)/(n1*n2), -1, 1))
                ang["neck_flex"] = float(math.degrees(math.acos(cosv)))
    return ang  # dictionary of all computed angles

def to_kpmap(kps: List[Dict[str, Any]]) -> KeypointMap:
    # Convert list of keypoints to dict keyed by name
    return {k["name"]: k for k in kps}
