# 🏗️ PoseApp — System Architecture

This document describes the **software architecture**, **data flow**, and **module interactions** of the PoseApp system.  
PoseApp is a modular, cross-platform desktop application for **real-time human pose estimation**, **joint-angle computation**, and **dynamic motion visualization**.

---

## 🧩 1. System Overview

PoseApp performs the following tasks:
1. Captures frames from a live camera or video stream.  
2. Detects 17 keypoints of the human body using **MoveNet (TensorFlow Lite)**.  
3. Computes joint angles for major body parts (shoulders, elbows, hips, knees, ankles).  
4. Displays stick skeleton overlays and angle labels on the live feed.  
5. Plots live time-series graphs of angles on the **Right Panel**.  
6. Allows session-based tracking, guided exercise monitoring, and report generation.

---

## 🧱 2. High-Level Architecture

```
+------------------------------------------------------+
|                      PoseApp GUI                     |
|------------------------------------------------------|
|                 PySide6 Frontend Layer               |
|------------------------------------------------------|
|      Main Window       |       Right Panel           |
| (Frame + Overlay)      | (Angle Time-Series Plot)    |
+------------------------------------------------------+
|                 Business Logic Layer                 |
|------------------------------------------------------|
| Angle Engine | Pose Detection | Activity Logic | Gait |
+------------------------------------------------------+
|               Core AI Inference Layer                |
|------------------------------------------------------|
| TensorFlow Lite MoveNet Model | OpenCV Frame Capture |
+------------------------------------------------------+
|             System Runtime / Packaging Layer         |
|------------------------------------------------------|
| PyInstaller (Windows) | AppImage (Linux) | Qt Event  |
+------------------------------------------------------+
```

---

## 🧠 3. Layered Breakdown

### 🔹 A. **UI Layer (Frontend — PySide6)**
Located under:  
`src/poseapp/ui/`

#### Modules:
- **main_window.py** — Central window managing camera feed, overlay drawing, and integration with backend modules.
- **right_panel.py** — Displays live angle plots using Matplotlib embedded in QtCanvas.
- **session_summary.py** — End-of-session analytics (min/max angles, activity stats).
- **guided_panel.py** — Guided exercise interface comparing user motion against reference.

#### Responsibilities:
- Manage layout and signals/slots.
- Synchronize user interactions with data updates.
- Display both raw camera feed and computed results.

---

### 🔹 B. **Processing Layer (Core Application Logic)**
Located under:  
`src/poseapp/geometry/`, `src/poseapp/analysis/`, `src/poseapp/activities/`

#### 1️⃣ Pose Detection
- Uses **TensorFlow Lite MoveNet Thunder/Lightning** models.
- Extracts 17 body landmarks `(x, y, confidence)`.
- Maintains real-time inference speed (~30 FPS on CPU).

#### 2️⃣ Angle Engine (`geometry/angles.py`)
- Computes angles from keypoints using vector trigonometry.  
  Formula:
  ```
  θ = arccos( (AB · BC) / (|AB| * |BC|) )
  ```
- Defines functional joints: elbow_L_flex, knee_R_flex, etc.
- Filters invalid or missing keypoints.

#### 3️⃣ Analysis Modules
- **rep_detector.py** → Detects repetition cycles.
- **guide_match.py** → Compares movements with templates.
- **scorer.py** → Calculates stability and performance.
- **metrics.py** → Computes gait statistics.

#### 4️⃣ Activity Definition (`activities/activity_defs.py`)
- Stores metadata about activity types and monitored angles.

---

### 🔹 C. **Data Layer (Runtime Buffers & Plotting)**
- Uses Python `deque` for rolling 10-second data windows.
- Each angle key maintains `(timestamp, value)` pairs.
- Pruned dynamically for memory efficiency.

---

## 🔄 4. Data Flow Pipeline

```
+------------------+      +--------------------+      +------------------+      +--------------------+
|  Camera Capture  | ---> |  Pose Detection    | ---> |  Angle Computing  | ---> |  UI Rendering +    |
| (OpenCV frames)  |      | (MoveNet TFLite)   |      | (geometry/angles) |      |  Live Angle Plot   |
+------------------+      +--------------------+      +------------------+      +--------------------+
```

1. **Frame Acquisition** → OpenCV captures frames.  
2. **Pose Estimation** → MoveNet model predicts keypoints.  
3. **Angle Calculation** → Angles computed using geometry vectors.  
4. **Overlay Rendering** → Draws skeleton and angle values.  
5. **Signal Emission** → Angle dict emitted to RightPanel.  
6. **Dynamic Plotting** → Matplotlib updates plots in real time.

---

## ⚙️ 5. Inter-Module Communication

| Source | Signal | Target | Purpose |
|---------|--------|---------|----------|
| `MainWindow` | `new_angles_ready(dict)` | `RightPanel.update_angles()` | Update live plots |
| `MainWindow` | `set_detected_from_main(list)` | `RightPanel.set_detected_from_main()` | Sync visible angles |
| `PoseEngine` | internal callback | `MainWindow.on_frame()` | Update every frame |
| `MainWindow` | UI buttons | `Qt signals` | Start/stop camera, show docs |

---

## 🧮 6. Mathematical Engine (Angle Computation)

```
Angle(A, B, C) = arccos( (AB · CB) / (|AB| * |CB|) )
```
Where:
- `A`, `B`, `C` are joint coordinates.  
- Results converted to degrees.  
- Invalid or missing keypoints ignored.

**Implementation:** `src/poseapp/geometry/angles.py`

---

## 💡 7. GUI Rendering and Synchronization

| Component | Library | Role |
|------------|----------|------|
| OpenCV | Capture & overlay drawing |
| PySide6 | UI event handling |
| Matplotlib | Embedded live plots |
| NumPy | Math operations |
| TensorFlow Lite | Pose inference |

---

## 📊 8. Live Angles Visualization

- `RightPanel` receives angle data each frame.  
- Only **visible angles** plotted.  
- `deque(maxlen=2000)` keeps rolling 10s window.  
- Graph scrolls continuously with new data.

---

## 🧱 9. Deployment Architecture

### 🪟 Windows
- Built via **PyInstaller**
- Output: `PoseApp.exe`

### 🐧 Linux
- Built via **AppImage**
- Script: `packaging/linux/build_appimage.sh`
- Output: `PoseApp-x86_64.AppImage`

### 🍎 macOS
- Build using PyInstaller command with `--windowed` flag.

---

## 🌐 10. Documentation System

| Component | Tool | Output |
|------------|------|--------|
| Sphinx | Converts `.rst` → HTML | `/docs/site/html/` |
| ReadTheDocs theme | Modern docs style | index.html |
| Integrated link | "Help → Documentation" | Opens local docs |

---

## ⚙️ 11. Error Handling & Logging

| Source | Logged Warnings |
|---------|----------------|
| OpenCV | Camera unavailable |
| TensorFlow | Delegate fallback |
| Pose Engine | Missing keypoints |
| UI | Safe error suppression |

---

## 🧩 12. Extensibility

- Replace MoveNet with YOLO-Pose or MediaPipe.  
- Add multi-person tracking.  
- Connect to cloud inference API.  
- Export CSV/PDF session reports.  
- Integrate rep counting models.

---

## 📁 13. Key Directories

| Directory | Purpose |
|------------|----------|
| `/src/poseapp/ui` | GUI components |
| `/src/poseapp/geometry` | Angle computations |
| `/src/poseapp/gait` | Motion metrics |
| `/src/poseapp/analysis` | Pattern analysis |
| `/packaging/linux` | AppImage scripts |
| `/docs/` | Sphinx documentation |
| `/dist/` | Built binaries |

---

## 🧾 14. Summary

| Layer | Description |
|--------|--------------|
| **Frontend** | User interface and visualization |
| **Logic** | Pose processing, angle computation |
| **Backend** | TensorFlow inference engine |
| **Data Layer** | Real-time rolling buffers |
| **Deployment** | PyInstaller & AppImage executables |

---

### 👨‍💻 Author
**A Mohammed Musharaff**  
📧 musharaffamohammed@gmail.com
