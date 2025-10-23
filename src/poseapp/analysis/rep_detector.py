# src/poseapp/analysis/rep_detector.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class CycleParams:
    # Defines configuration thresholds and timing for a repetition detection cycle.
    baseline_band: float = 6.0      # how close to baseline counts as "at baseline"
    up_thresh: float = 25.0         # angle difference above baseline needed to start a rep
    down_thresh: float = 12.0       # not directly used (legacy param; can be tuned)
    min_duration: float = 0.40      # minimum valid rep time (prevents bounce)
    max_duration: float = 6.00      # timeout for resetting rep detection
    peak_hold: float = 0.08         # how long angle must stay above up_thresh to confirm a rep peak

class RepCycleDetector:
    """
    Detects and counts a full repetition cycle from continuous joint angles.

    Logic sequence:
      BASELINE → GOING_UP → ABOVE_THRESH(held) → GOING_DOWN → BACK_TO_BASELINE → +1 rep

    Notes:
    - 'baseline' is initialized from early angles and then slowly adapts (EMA).
    - Works with joint angles like shoulder_abd, knee_flex, etc.
    """
    def __init__(self, params: CycleParams = CycleParams()) -> None:
        # Store parameter object and reset state machine
        self.p = params
        self.reset()

    def reset(self) -> None:
        # Initialize the detector’s state machine and internal variables
        self.state = "INIT"         # possible states: INIT, AT_BASELINE, GOING_UP, ABOVE, GOING_DOWN
        self.baseline: Optional[float] = None
        self._last_t: Optional[float] = None
        self._t_cycle_start: Optional[float] = None   # timestamp when a cycle starts
        self._t_above_start: Optional[float] = None   # timestamp when above threshold begins

    def _is_near_baseline(self, a: float) -> bool:
        # Checks if current angle is within the baseline band
        if self.baseline is None:
            return False
        return abs(a - self.baseline) <= self.p.baseline_band

    def _ensure_baseline(self, a: float) -> None:
        # Slowly update baseline (EMA) when near baseline values
        if self.baseline is None:
            self.baseline = a
        else:
            self.baseline = 0.98 * self.baseline + 0.02 * a  # slow drift correction

    def update(self, t: float, a: float) -> Optional[dict]:
        """
        Called for each frame with timestamp `t` and angle `a`.

        Returns:
            dict {'t0': start_time, 't1': end_time} once per completed rep,
            otherwise None if rep not yet completed.
        """
        if a is None or not (a == a):   # skip invalid / NaN inputs
            self._last_t = t
            return None

        # Initialize baseline on first frames
        if self.baseline is None:
            self.baseline = a

        # -------------------------
        # State machine transitions
        # -------------------------
        if self.state == "INIT":
            # Wait until the signal stabilizes near baseline
            if self._is_near_baseline(a):
                self._ensure_baseline(a)
                self.state = "AT_BASELINE"
            self._last_t = t
            return None

        if self.state == "AT_BASELINE":
            # At rest — monitor for start of motion upward
            self._ensure_baseline(a)
            if (a - self.baseline) >= self.p.up_thresh:
                self.state = "GOING_UP"
                self._t_cycle_start = t
                self._t_above_start = None

        elif self.state == "GOING_UP":
            # Check if angle has reached and held above threshold
            if (a - self.baseline) >= self.p.up_thresh:
                if self._t_above_start is None:
                    self._t_above_start = t
                elif (t - self._t_above_start) >= self.p.peak_hold:
                    self.state = "ABOVE"
            else:
                # Fell back prematurely — revert if still near baseline
                if self._is_near_baseline(a):
                    self.state = "AT_BASELINE"
                    self._t_cycle_start = None
                    self._t_above_start = None

        elif self.state == "ABOVE":
            # Now descending from the top toward baseline
            if (a - self.baseline) < self.p.up_thresh * 0.5:
                self.state = "GOING_DOWN"

        elif self.state == "GOING_DOWN":
            # Once near baseline again → count as a completed repetition
            if self._is_near_baseline(a):
                if self._t_cycle_start is not None:
                    dur = t - self._t_cycle_start
                    self.state = "AT_BASELINE"
                    self._t_above_start = None
                    self._t_cycle_start = None
                    if self.p.min_duration <= dur <= self.p.max_duration:
                        return {"t0": t - dur, "t1": t}  # one rep completed
                else:
                    # fallback: just reset baseline state
                    self.state = "AT_BASELINE"

        # Safety timeout: reset if cycle exceeds allowed duration
        if self._t_cycle_start is not None and (t - self._t_cycle_start) > self.p.max_duration:
            self.state = "AT_BASELINE"
            self._t_cycle_start = None
            self._t_above_start = None

        self._last_t = t
        return None  # no rep detected this frame
