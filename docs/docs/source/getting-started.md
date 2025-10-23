📘 PoseApp — Getting Started

PoseApp is a modular PySide6-based desktop tool for real-time human pose tracking, angle measurement, and guided activity scoring.
It is organized under a clean src/poseapp structure to separate logic layers (UI, metrics, analysis, I/O, etc.) for scalability and maintainability.

🧩 1. Project Structure
src/
└─ poseapp/
   ├─ ui/                    # PySide6 GUI panels, dialogs, and overlays
   │  ├─ main_window.py      # Main application orchestrator
   │  ├─ dialogs.py
   │  ├─ overlays.py
   │  ├─ guided_helpers.py
   │  └─ session_summary.py
   │
   ├─ metrics/               # Computation and analytical utilities
   │  ├─ angles_util.py      # Angle normalization and mapping
   │  └─ side_helpers.py     # Side detection + guided rep flow logic
   │
   ├─ analysis/              # Signal and rep cycle analysis logic
   │  ├─ rep_detector.py
   │  ├─ guide_match.py
   │  └─ activity_rules.py
   │
   ├─ activities/            # Definitions of activity templates and metadata
   │  └─ activity_defs.py
   │
   ├─ geometry/              # Pose geometry and keypoint utilities
   │  └─ angles.py
   │
   ├─ scoring/               # Form, stability, and symmetry scoring modules
   │  └─ scorer.py
   │
   ├─ gait/                  # Movement pattern and gait tracking utilities
   │  └─ metrics.py
   │
   ├─ io/                    # Logging, exporting, and session data handling
   │  └─ session_logger.py
   │
   ├─ utils/                 # Resource access, camera scanning, and constants
   │  ├─ resources.py
   │  └─ camera_scan.py
   │
   └─ camera/                # Camera capture, threading, and video worker
      └─ video_worker.py

⚙️ 2. Installation
a. Clone the repository
git clone 
cd PoseApp

b. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# or
.venv\Scripts\activate           # Windows

c. Install dependencies
pip install -r requirements.txt

🪄 3. Running the App

To launch the GUI from the root project directory:

python -m src.poseapp.ui.main_window


If you want to run the simplified CLI fallback:

python -m src.poseapp.main --cli