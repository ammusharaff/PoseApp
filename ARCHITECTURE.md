# Architecture (Skeleton)

## Modules
- `poseapp.backends` – adapters for MediaPipe and MoveNet.
- `poseapp.geometry` – angle math and derived joints.
- `poseapp.filters` – EMA / 1‑Euro smoothing.
- `poseapp.gait` – cadence, step time, symmetry.
- `poseapp.mode` – Mode A (Freestyle), Mode B (Guided).
- `poseapp.io` – CSV/JSON writers.
- `poseapp.ui` – Qt/PySide6 GUI.

## Data Flow
Camera → Backend → Keypoints → Geometry/Filters → Gait/Scoring → UI Overlay → Writers.

## Error Handling
- Placeholder: exceptions & retries.

## Threading Model
- Placeholder: capture thread, inference thread, UI thread.
