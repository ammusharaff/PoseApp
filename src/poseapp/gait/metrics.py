# src/poseapp/gait/metrics.py
from typing import Dict, Any, Optional  # type hints
import collections  # for bounded history (deque)
import numpy as np  # numerical ops and NaN handling

class GaitTracker:
    """
    Lightweight gait feature extractor for Mode A:
    - Cadence via local minima in ankle Y.
    - Step time from successive minima.
    - Symmetry index from left vs right step time.

    Inputs:
      update(t, ankleL_y, ankleR_y, hip_width_px=None)
    """
    def __init__(self, max_hist=300, min_event_separation_s: float = 0.25):
        # Maintain rolling history of time and keypoints (ankle positions, etc.)
        self.hist = {
            "t": collections.deque(maxlen=max_hist),
            "ankleL_y": collections.deque(maxlen=max_hist),
            "ankleR_y": collections.deque(maxlen=max_hist),
            "hip_width_px": collections.deque(maxlen=max_hist),
        }
        self.events_L = []  # detected left-side step events as (timestamp, y)
        self.events_R = []  # detected right-side step events
        self.cadence_spm = 0.0  # steps per minute
        self.step_time_L: Optional[float] = None  # last detected left step duration
        self.step_time_R: Optional[float] = None  # last detected right step duration
        self.si: Optional[float] = None  # symmetry index (balance metric)
        self.min_event_separation_s = float(min_event_separation_s)  # event refractory window

    def update(self, t: float, ankleL_y: Optional[float], ankleR_y: Optional[float], hip_width_px: Optional[float]=None):
        # Add latest readings to deque history
        self.hist["t"].append(t)
        self.hist["ankleL_y"].append(ankleL_y if ankleL_y is not None else np.nan)
        self.hist["ankleR_y"].append(ankleR_y if ankleR_y is not None else np.nan)
        self.hist["hip_width_px"].append(hip_width_px if hip_width_px is not None else np.nan)
        self._detect_events()  # detect step events (local minima)
        self._recompute_metrics()  # recompute gait features

    def _detect_events(self):
        # Detect local minima based on last 3 samples for each side
        for side in ("L", "R"):
            y_deque = self.hist["ankleL_y"] if side == "L" else self.hist["ankleR_y"]
            if len(y_deque) >= 3:
                a = y_deque[-3]
                b = y_deque[-2]
                c = y_deque[-1]
                y3 = np.array([a, b, c], dtype=float)
                # Check if b is local minimum (b < a and b < c)
                if np.isfinite(y3).all() and (b < a) and (b < c):
                    t_mid = self.hist["t"][-2]
                    # Refractory check: ignore events that occur too soon after previous
                    ev = self.events_L if side == "L" else self.events_R
                    if not ev or (t_mid - ev[-1][0]) >= self.min_event_separation_s:
                        ev.append((t_mid, float(b)))  # store event

    def _recompute_metrics(self):
        # Helper: compute time between last two events
        def step_time(ev):
            if len(ev) >= 2:
                return ev[-1][0] - ev[-2][0]
            return None

        stL = step_time(self.events_L)
        stR = step_time(self.events_R)
        self.step_time_L = stL
        self.step_time_R = stR

        # Compute cadence (steps per minute)
        sts = [s for s in (stL, stR) if s is not None and s > 0]
        if sts:
            avg = float(np.mean(sts))
            self.cadence_spm = 60.0 / avg
        else:
            self.cadence_spm = 0.0

        # Compute symmetry index (SI) between left and right steps
        if stL and stR and stL > 0 and stR > 0:
            self.si = 100.0 * abs(stL - stR) / (0.5 * (stL + stR) + 1e-6)
        else:
            self.si = None

    def metrics(self) -> Dict[str, Any]:
        # Return the computed gait metrics as a dict
        return {
            "cadence_spm": float(self.cadence_spm),
            "step_time_L": None if self.step_time_L is None else float(self.step_time_L),
            "step_time_R": None if self.step_time_R is None else float(self.step_time_R),
            "symmetry_index": None if self.si is None else float(self.si),
        }
