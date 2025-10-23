🏋️ PoseApp — Guided Mode

Guided Mode is the structured workout experience of PoseApp — providing rep counting, form scoring, symmetry analysis, and set summaries for each guided activity.
It uses your camera input and compares detected motion patterns against predefined activity templates from activities/activity_defs.py.

🧩 1. Overview

In Guided Mode, users select an activity (e.g., squat, jumping jack, forward flexion), and PoseApp:

Displays a GIF preview for visual reference.

Tracks your joint angles using the camera feed.

Detects repetitions automatically.

Scores each rep for form, range, and stability.

Displays a detailed set summary on completion.

⚙️ 2. Core Modules
Component	File	Description
Activity Templates	activities/activity_defs.py	Defines metadata for all guided exercises.
Main Logic	metrics/side_helpers.py	Contains overlay_guided_flow() — the main guided mode engine.
Side Detection Helpers	metrics/side_helpers.py	Provides best_visible_side_for_arm() and best_visible_side_for_leg().
UI Layer	ui/main_window.py	Renders guided panel, calls overlay_guided_flow() each frame.
GIF Preview	ui/guided_helpers.py	Loads visual guide animations for each activity.
Rep Detection	analysis/rep_detector.py	Tracks movement cycles and identifies valid repetitions.
Guide Matching	analysis/guide_match.py	Compares your motion curve with the reference pattern.
Form Assessment	analysis/activity_rules.py	Evaluates per-joint motion compliance with activity goals.
Scoring Engine	scoring/scorer.py	Calculates final form stability, symmetry, and overall performance.
🧠 3. How It Works

When you start an activity:

The app creates a guided session dictionary (_guided) containing keys like key, primary, targets, repdet, etc.

The UI panel (guided_panel) updates and shows a GIF preview using guided_helpers.py.

For each camera frame:

Angles are computed (metrics/angles_util.py).

overlay_guided_flow() is called from side_helpers.py to:

Auto-detect the visible side (L/R).

Track angle changes over time.

Update RepCycleDetector.

Trigger rep completion events.

On each detected rep:

PoseApp computes:

Joint compliance bands (Green/Amber/Red) via scorer.score_band().

Guide match (MAE + phase correlation).

Form stability and symmetry index.

Results are displayed in the status bar and logged to the active session.

When a full set is completed:

A Session Summary Dialog appears (ui/session_summary.py),
showing average scores, form stability, and symmetry results.

🔍 4. Key Function: overlay_guided_flow()

Defined in src/poseapp/metrics/side_helpers.py,
this is the heart of the guided-mode pipeline.

🔧 Responsibilities:

Draw overlays (ui/overlays.py)

Detect visible sides (best_visible_side_for_arm / best_visible_side_for_leg)

Track angles and compute scalar motion variable a

Pass values into RepCycleDetector

Evaluate rep boundaries and band scores

Log session payloads into io/session_logger.py

Trigger SessionSummaryDialog on set completion

🧩 5. Activity Definition Example

Each guided activity is defined in activities/activity_defs.py as follows:

"forward_flexion": {
    "label": "Forward Flexion",
    "primary": ["shoulder_ANY_flex"],
    "score_joint": "shoulder_ANY_flex",
    "reps": 10,
    "targets": {"shoulder_ANY_flex": 90},
    "description": "Bend forward while keeping your back straight."
}


"primary": joints to monitor for rep motion

"score_joint": single joint used for primary angle tracking

"targets": desired angles for evaluation

"reps": target number of repetitions per set

🧮 6. Scoring Metrics
Metric	Module	Description
Angle Band Score	scoring/scorer.py → score_band()	Evaluates per-joint deviation from target (Green ≤5°, Amber ≤10°).
Form Stability	scoring/scorer.py → form_stability()	Measures consistency of motion across repetitions.
Symmetry Index	scoring/scorer.py → symmetry_index()	Compares left/right performance balance.
Final Score	scoring/scorer.py → final_score()	Weighted average combining rep performance and stability.

Each set’s overall score is displayed in the summary popup.

📊 7. Data Logging

All guided-mode data are stored via io/session_logger.py:

session_<timestamp>/
├─ guided_summary.json
├─ rep_scores.csv
└─ pose_snapshots/


Each entry includes:

activity, label, set_idx

rep_scores, form_stability, symmetry_index

final_percent, scoring_rules

These results can be reloaded in the “Sessions” tab for post-analysis.

🧩 8. Session Summary Popup

After completing all repetitions:

PoseApp computes mean and variance metrics for that activity.

The summary dialog (ui/session_summary.py) shows:

Average rep score

Form stability graph

Symmetry index

Option to Export CSV / JSON

⚙️ 9. Configuration Parameters

Adjust thresholds in:

src/poseapp/analysis/rep_detector.py

Parameter	Default	Description
min_peak_height	5.0	Minimum movement amplitude for valid rep.
min_peak_distance	0.5s	Minimum time between reps.
angle_smoothing	True	Applies moving-average filter for noisy input.

You can fine-tune these per-activity by editing CycleParams in on_start_trial() inside main_window.py.

🧰 10. Debugging Reps

If reps aren’t detected:

Confirm _overlay_guided_flow() is calling overlay_guided_flow(self, frame, ang, kpmap) from side_helpers.py.

Print out the scalar a in side_helpers.py to verify motion detection.

Check that your camera field of view shows full limb visibility.

Adjust CycleParams thresholds for amplitude or time spacing.

🎯 11. Summary
Feature	Description
Automatic Rep Counting	Tracks cycles based on joint angles.
Real-Time Scoring	Evaluates motion quality per repetition.
Symmetry Analysis	Detects side dominance or imbalance.
Set Summaries	Provides final performance evaluation.
GIF Previews	Visual exercise guide for each activity.