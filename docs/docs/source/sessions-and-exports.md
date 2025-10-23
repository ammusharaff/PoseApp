📁 PoseApp — Sessions and Exports

PoseApp automatically saves every Guided or Freestyle activity into structured session folders that can be reviewed, exported, or analyzed later.
This ensures traceable progress tracking, post-analysis, and easy reporting for users, trainers, and developers.

🧩 1. Overview

Each session captures:

Metadata — user, activity, model, and timestamp

Repetition scores (Guided Mode)

Angle timelines (Freestyle Mode)

Symmetry and stability metrics

Snapshot frames for visual inspection

Sessions are managed by the module:

src/poseapp/io/session_logger.py


and exported through:

src/poseapp/ui/session_summary.py

🧱 2. Directory Structure

When a session starts, PoseApp creates a timestamped folder inside sessions/ or a configured export directory:

sessions/
└─ session_2025-10-23_01-10-58/
   ├─ guided_summary.json
   ├─ rep_scores.csv
   ├─ freestyle_angles.csv
   ├─ keypoints_snapshot.json
   ├─ summary_popup.png
   └─ screenshots/

🧠 3. Session Management Logic
Stage	Module	Description
Start Session	ui/main_window.py	Initializes a session and logger instance.
Data Logging	io/session_logger.py	Stores angles, keypoints, rep events, and metrics.
Session Update	metrics/side_helpers.py	Appends rep summaries during guided flow.
Summary Display	ui/session_summary.py	Shows a popup summary with scoring and export options.
File Export	session_logger.py	Saves JSON + CSV reports for analytics.
🧾 4. Export Formats
🟢 Guided Mode Exports

File: guided_summary.json

{
  "activity": "squat",
  "label": "Squat",
  "set_idx": 1,
  "reps_counted": 10,
  "rep_scores": [0.95, 0.92, 0.90, 0.94, 0.93, 0.89, 0.97, 0.91, 0.92, 0.95],
  "form_stability": 0.92,
  "symmetry_index": 4.8,
  "final_percent": 93.6,
  "scoring_rules": {
    "bands": {"Green": "≤5°", "Amber": "≤10°", "Red": ">10°"},
    "rep_score": "mean of joint band scores",
    "final": "0.7 * rep_mean + 0.3 * stability"
  }
}


File: rep_scores.csv

Rep	Score	Band	Symmetry	Comment
1	0.95	Green	5.0	Excellent form
2	0.92	Green	4.8	Good depth
…	…	…	…	…
🔵 Freestyle Mode Exports

File: freestyle_angles.csv

Timestamp	Shoulder_L	Shoulder_R	Hip_L	Hip_R	Confidence
1698318121.45	88.4	90.3	176.2	177.1	0.92
1698318121.48	87.6	89.9	175.8	176.8	0.91

File: pose_keypoints.json

{
  "frame_id": 102,
  "timestamp": 1698318121.48,
  "keypoints": {
    "left_shoulder": {"x": 242, "y": 198, "conf": 0.98},
    "right_shoulder": {"x": 392, "y": 192, "conf": 0.97}
  }
}

🧮 5. Data Fields
Field	Type	Description
activity	string	Name of the guided exercise
set_idx	int	Current set number
reps_counted	int	Number of repetitions detected
rep_scores	list[float]	Individual repetition quality scores
form_stability	float	Temporal consistency of motion
symmetry_index	float	Difference between left/right joints
final_percent	float	Weighted overall performance
timestamp	float	Session time marker (Unix)
📤 6. Exporting a Session

After a guided set completes, a popup automatically appears (SessionSummaryDialog).

Options available:

Export CSV — writes detailed rep-by-rep results.

Export JSON — saves full metadata and metrics.

Export Screenshots — saves annotated images of key rep frames.

All export logic is managed by:

src/poseapp/ui/session_summary.py

🧠 7. Advanced Developer Exports

Developers can export programmatically using SessionLogger:

from src.poseapp.io.session_logger import SessionLogger

logger = SessionLogger(mode="guided")
payload = {
    "activity": "forward_flexion",
    "final_percent": 94.8,
    "form_stability": 0.91
}
logger.add_guided_scorecard(payload)
logger.add_scorecard_row(payload)
logger.save()


The logger automatically handles directory creation and file rotation per session.

🧩 8. Integration with Guided Flow

overlay_guided_flow() from metrics/side_helpers.py
calls the SessionLogger APIs whenever:

A repetition is completed

A set summary is computed

This ensures that each activity session automatically produces:

Incremental CSV entries

Final summary JSON report

Live export-ready data

📈 9. Post-Session Analysis

All exported sessions can be reviewed later using:

The Sessions tab (UI-level reloader).

External analysis tools (e.g., pandas, Power BI).

Example:

import pandas as pd

df = pd.read_csv("sessions/session_2025-10-23_01-10-58/rep_scores.csv")
print(df.describe())

🧰 10. Best Practices
Tip	Benefit
Use consistent folder naming	Easier session management
Enable logging for both modes	Cross-compare guided vs freestyle
Store videos externally	Reduce log size and improve FPS
Periodically archive sessions	Prevent excessive disk usage

🎯 11. Summary
Feature	      Guided Mode	Freestyle Mode
Rep Logging	      ✅	          ❌
Angle Timeline	  ✅	          ✅
Form Scores	      ✅	          ❌
Stability Metric	✅	          ✅
Export CSV/JSON	  ✅	          ✅
Screenshots	      ✅	          ✅