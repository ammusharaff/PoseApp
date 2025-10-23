🎥 PoseApp — Freestyle Mode

Freestyle Mode allows users to analyze movement in an open, unstructured format — without activity templates or repetition targets.
It is designed for real-time biomechanical feedback, posture tracking, and movement analytics using PoseApp’s live camera pipeline.

🧩 1. Overview

Unlike Guided Mode, Freestyle Mode doesn’t rely on pre-defined joint targets or repetition cycles.
It continuously tracks angles, pose stability, and motion flow while displaying overlays in real-time.

This mode is ideal for:

Open-ended movement analysis

Yoga and flexibility tracking

Dance or sports motion capture

Posture correction monitoring

⚙️ 2. Module Responsibilities
Component	File	Description
Main Orchestrator	ui/main_window.py	Initializes Freestyle Mode panel, manages camera feed, UI rendering, and data flow.
Angle Computation	metrics/angles_util.py	Converts keypoints to biomechanical angles.
Camera Worker	camera/video_worker.py	Captures frames asynchronously from webcam or video input.
Pose Geometry Utils	geometry/angles.py	Provides keypoint mapping and trigonometric angle computation.
Session Logger	io/session_logger.py	Optionally records continuous freestyle data for later review.
🧠 3. How It Works

The app starts capturing frames via video_worker.py.

Pose detection runs per frame (MoveNet, MediaPipe, or custom model).

Detected keypoints are passed to:

metrics/angles_util.py → for computing angles of interest.

ui/overlays.py → for drawing skeletons and annotated joints.

Each frame’s result is rendered on the main camera canvas.

Optionally, results (angles, timestamps) are logged into a session file.

🔍 4. Real-Time Feedback

During freestyle tracking, PoseApp displays:

Overlay Element	Description
Joint Angles	Numeric angle values over major joints (shoulder, elbow, hip, knee).
Skeleton Lines	Real-time visual overlay using OpenCV and PySide6.
Confidence Heatmap	(Optional) Color-coded joint confidence visualization.
Status Bar Updates	Display current frame rate, detected pose model, and visibility score.

These elements are drawn in the rendering loop handled by ui/overlays.py.

🧾 5. Data Logging

When enabled, Freestyle Mode writes continuous pose data to session files managed by io/session_logger.py.

Each freestyle session includes:

session_<timestamp>/
├─ freestyle_angles.csv
├─ pose_keypoints.json
└─ screenshots/


Data columns:

Column	Description
timestamp	Unix time (seconds)
angle_shoulder_L	Left shoulder angle
angle_elbow_L	Left elbow angle
angle_hip_R	Right hip angle
confidence_avg	Mean keypoint confidence
🧮 6. Extending Freestyle Analytics

You can add custom real-time analysis in the metrics/ or analysis/ modules.
For example:

Example: Add a Stability Tracker

Create a new file:

src/poseapp/metrics/stability_tracker.py

import numpy as np

class StabilityTracker:
    def __init__(self):
        self.history = []

    def update(self, kpmap):
        confs = [v.get("conf", 0.0) for v in kpmap.values()]
        mean_conf = np.mean(confs)
        self.history.append(mean_conf)
        return mean_conf


Then integrate it into the main_window.py render loop to visualize real-time stability changes.

🧰 7. Developer Hooks

Freestyle mode exposes simple entry points for developers:

Hook	Description
on_frame_processed(frame, kpmap, angles)	Called for each processed frame; can be extended to record or stream data.
on_pose_detected(kpmap)	Triggered when valid keypoints are detected.
on_export_freestyle()	Invoked when the user exports freestyle results.

Add these in ui/main_window.py or extend via inheritance.

🧑‍💻 8. Example Customization

Add a motion trendline widget:

# ui/widgets/trend_widget.py
from PySide6 import QtWidgets, QtCharts

class TrendWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.chart = QtCharts.QChartView()
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.chart)


Then register it inside main_window.py to visualize live data trends such as angle fluctuations.

🧩 9. Integration with Guided Components

Even though freestyle mode runs independently, it shares core components with guided mode:

metrics/angles_util.py — for angle computation

geometry/angles.py — for 2D keypoint geometry

camera/video_worker.py — for continuous frame acquisition

This ensures consistent coordinate normalization and processing across both modes.

🎯 10. Summary
Feature	            Guided Mode	Freestyle Mode
Repetition Counting	    ✅	       ❌
Form Scoring	        ✅	       ❌
Real-Time Feedback	    ✅	       ✅
Data Logging	        ✅	       ✅
Open-Ended Tracking	    ❌	       ✅