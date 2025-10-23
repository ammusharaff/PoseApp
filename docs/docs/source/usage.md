⚙️ PoseApp — Usage Guide

PoseApp provides two primary modes of use:

Graphical Interface (GUI Mode) — for real-time guided or freestyle tracking.

Command-Line Interface (CLI Mode) — for testing, debugging, and scripting.

This guide explains both usage styles, their runtime behavior, and how to customize PoseApp for your workflow.

🖥️ 1. Running the GUI

From the root of your project:

python -m src.poseapp.ui.main_window


This launches the full PoseApp UI, built using PySide6, and initializes the default camera input pipeline.

✅ What happens on launch:

Loads model configurations from src/poseapp/config.py (if present).

Initializes the camera thread via camera/video_worker.py.

Loads activity definitions from activities/activity_defs.py.

Configures guided and freestyle panels dynamically.

Prepares logging paths in io/session_logger.py.

You’ll see the Main Window with:

Left panel → mode selection & session controls

Center view → live camera feed + overlays

Right panel → activity preview & statistics

⚡ 2. Running in CLI Mode

For systems without GUI dependencies, or for debugging:

python -m src.poseapp.main --cli


This runs PoseApp in headless mode, printing live angle and pose data to the console.

You can configure backend behavior using command-line options:

Flag	Description
--camera <index>	Select a different webcam (default: 0)
--model <name>	Choose backend model (e.g., movenet, mediapipe)
--no-angles	Disable real-time angle computation
--save <path>	Save frame-by-frame outputs for analysis
--fps <n>	Target capture framerate

Example:

python -m src.poseapp.main --cli --camera 1 --fps 30 --model movenet

🧩 3. Mode Overview
Mode	Module	Description
Guided Mode	metrics/side_helpers.py + ui/guided_helpers.py	Structured exercise sessions with rep detection and form scoring.
Freestyle Mode	ui/freestyle_panel.py (within main_window)	Open-ended tracking for live pose analysis and visual overlays.
Session Management	io/session_logger.py	Session start, export, and summary logs.
Analysis	analysis/rep_detector.py, analysis/guide_match.py	Detects repetition cycles and compares user movement with template data.
🧠 4. Developer Workflow

PoseApp is designed for modular extension.
Developers can add or modify modules without breaking the UI.

🏗️ Adding a new activity

Define your new activity in:

src/poseapp/activities/activity_defs.py


Example:

"shoulder_press": {
    "label": "Shoulder Press",
    "primary": ["shoulder_ANY_abd"],
    "score_joint": "shoulder_ANY_abd",
    "reps": 10,
    "targets": {"shoulder_ANY_abd": 90},
}


Add an optional GIF preview under:

assets/guides/shoulder_press.gif


PoseApp will automatically load and render the activity in Guided Mode.

🧩 5. Integrating a Custom Model

You can swap or extend the backend model from src/poseapp/config.py or within main_window.py.

Supported model backends:

Backend	Config Constant	Description
MoveNet (Lightning/Thunder)	BACKEND_MOVENET	Fast TensorFlow-based model.
MediaPipe Pose	BACKEND_MEDIAPIPE	Lightweight CPU-friendly model.
Custom / Torch Model	BACKEND_CUSTOM	Integrate your own trained model.

To add a new backend:

Place model inference logic in src/poseapp/models/.

Update config.py and import into main_window.py.

🧾 6. Logs and Exports

All runtime logs and session exports are handled by:

io/session_logger.py → manages JSON + CSV outputs

sessions-and-exports.md → explains export formats in detail

Each session folder contains:

session_<timestamp>/
├─ summary.json
├─ rep_scores.csv
└─ snapshots/

🧰 7. Troubleshooting
Issue	Likely Cause	Fix
No camera feed	Invalid camera index	Update CAM_INDEX in config or CLI flag.
GIF previews missing	Missing or misnamed files in assets/guides/	Ensure filenames match activity key.
Reps not counting	Guided loop not running	Verify _overlay_guided_flow() uses side_helpers.overlay_guided_flow.
UI not launching	PySide6 missing	Run pip install PySide6.
💡 8. Pro Tips

Adjust thresholds in analysis/rep_detector.py for different motion amplitudes.

Tune scoring rules in scoring/scorer.py for stricter or looser performance bands.

To debug guided flow, print a and rep variables in side_helpers.overlay_guided_flow().