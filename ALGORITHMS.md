# ⚙️ PoseApp — Algorithmic Workflow

This document outlines the **algorithms, data transformations, and computational logic** used by **PoseApp** — a cross-platform real-time human pose estimation and angle visualization system.

---

## 🧠 1. Overview

The PoseApp algorithm processes each video frame in a **continuous loop** to:
1. Capture frames from the webcam.
2. Detect human body keypoints using the **MoveNet model (TensorFlow Lite)**.
3. Calculate joint angles from detected keypoints.
4. Overlay skeletons and angles on the video feed.
5. Send computed values to the **Right Panel** for live angle plotting.

This pipeline runs in real-time (~30 FPS) and adapts dynamically to visibility of body parts.

---

## 🔄 2. Core Processing Pipeline

```
┌─────────────────────┐
│  Camera Capture     │ ← OpenCV
└────────┬────────────┘
         │ (frame)
         ▼
┌─────────────────────┐
│  Pose Detection     │ ← MoveNet (TF-Lite)
│  17 keypoints       │
└────────┬────────────┘
         │ (x, y, conf)
         ▼
┌─────────────────────┐
│  Angle Computation  │ ← geometry/angles.py
│  (Vector Math)      │
└────────┬────────────┘
         │ (angles dict)
         ▼
┌─────────────────────┐
│  Overlay Rendering  │ ← OpenCV drawing
│  + Live Plot Update │ ← Matplotlib
└─────────────────────┘
```

---

## 🧮 3. Key Algorithmic Steps

### Step 1: Frame Acquisition
**File:** `main_window.py`

```python
ret, frame = self.cap.read()
if not ret:
    return  # skip frame if no capture
```

- Frames are captured using `cv2.VideoCapture(0)`.
- Resized and normalized before feeding into the model.
- Optional FPS throttling to maintain real-time response.

---

### Step 2: Pose Detection — MoveNet Inference
**File:** `poseapp/models/movenet.py`

Algorithm:
1. Resize image to `192×192` or `256×256`.
2. Normalize pixel values to `[0, 1]`.
3. Run inference on TFLite interpreter.
4. Extract `17 keypoints` with confidence scores.

Keypoints represent:
```
[0] Nose        [1] Left Eye      [2] Right Eye
[3] Left Ear    [4] Right Ear     [5] Left Shoulder
[6] Right Shoulder [7] Left Elbow [8] Right Elbow
[9] Left Wrist  [10] Right Wrist  [11] Left Hip
[12] Right Hip  [13] Left Knee    [14] Right Knee
[15] Left Ankle [16] Right Ankle
```

Each output is `(x, y, confidence)` in normalized image coordinates.

---

### Step 3: Keypoint Post-Processing

**Algorithm:**
```python
for i, (x, y, c) in enumerate(keypoints):
    if c < 0.3:
        keypoints[i] = None  # filter unreliable points
```

- Low-confidence points are discarded.
- The remaining valid keypoints are scaled back to image size.

---

### Step 4: Angle Computation (Geometric Model)
**File:** `geometry/angles.py`

For each joint angle `(A-B-C)`:
- Compute vectors:
  ```
  AB = A - B
  CB = C - B
  ```
- Apply cosine law:
  ```
  θ = arccos( (AB · CB) / (|AB| × |CB|) )
  ```
- Convert radians to degrees:
  ```
  angle_deg = np.degrees(θ)
  ```
- Handle invalid or missing keypoints gracefully.

Example:
```python
def compute_angle(A, B, C):
    AB = A - B
    CB = C - B
    cosine_angle = np.dot(AB, CB) / (np.linalg.norm(AB) * np.linalg.norm(CB))
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
    return np.degrees(angle)
```

Output Dictionary (Example):
```json
{
  "elbow_L_flex": 145.6,
  "elbow_R_flex": 152.8,
  "knee_L_flex": 163.2,
  "shoulder_L_abd": 42.7
}
```

---

### Step 5: Overlay Drawing
**File:** `main_window.py`

Each frame is annotated using OpenCV:

```python
cv2.line(frame, A, B, color, thickness)
cv2.putText(frame, f"{angle:.1f}°", pos, font, size, color, thickness)
```

- Angles are rendered near their joints.
- The skeleton connects standard MoveNet keypoint pairs.
- Only visible and finite angles are displayed.

---

### Step 6: Live Angle Plot Update
**File:** `ui/right_panel.py`

The angle dictionary is sent from the main window to the live plot panel:

```python
self.right_panel.update_angles(angles)
```

Algorithm:
1. Receive dictionary `{angle_name: value}`.
2. Append each angle’s value to a rolling `deque(maxlen=2000)`.
3. Prune entries older than 10 seconds.
4. Update the corresponding Matplotlib `Line2D` object.

Plot Update Example:
```python
xs = [t - now for (t, _) in data]
ys = [v for (_, v) in data]
line.set_data(xs, ys)
```

---

## 🧩 4. Core Algorithm Summary

| Step | Process | Algorithm | Module |
|------|----------|------------|--------|
| 1 | Capture frame | OpenCV read & resize | `main_window.py` |
| 2 | Pose detection | MoveNet TFLite inference | `pose_engine.py` |
| 3 | Keypoint filtering | Confidence thresholding | `pose_engine.py` |
| 4 | Angle computation | Vector cosine law | `geometry/angles.py` |
| 5 | Overlay rendering | OpenCV draw lines/text | `main_window.py` |
| 6 | Live plot update | Matplotlib rolling series | `right_panel.py` |

---

## 🧠 5. Auxiliary Algorithms

### A. Repetition Detection (`rep_detector.py`)
Detects cycles of motion using angle peaks:
```python
if angle_prev < angle_curr and next_angle < angle_curr:
    reps += 1  # detected one full cycle
```

### B. Guide Matching (`guide_match.py`)
Compares current movement with a reference:
```python
corr = np.corrcoef(current_series, guide_series)[0, 1]
match_score = round(corr * 100, 2)
```

### C. Gait Tracking (`metrics.py`)
Calculates stride time and symmetry:
```python
symmetry = abs(left_stride - right_stride) / max(left_stride, right_stride)
```

---

## 🧾 6. Data Structures

| Type | Name | Description |
|------|------|--------------|
| `dict` | `angles` | Stores computed joint angles |
| `deque` | `_series[k]` | Rolling buffer of each angle |
| `list` | `keypoints` | 17 pose landmarks |
| `dict` | `metrics` | Per-session analysis data |

---

## 🔄 7. Real-Time Synchronization Logic

1. The camera loop runs in Qt’s event thread.
2. Every frame → `on_frame()` emits a signal.
3. Signal carries both the processed frame and angles dictionary.
4. UI updates occur asynchronously, preventing frame lag.

---

## 📊 8. Performance Optimizations

- Uses **TensorFlow Lite XNNPACK Delegate** for CPU acceleration.
- Skips processing when detection fails or frame is invalid.
- Uses **`deque`** instead of list for O(1) insert/remove.
- Real-time FPS maintained using:
  ```python
  time.sleep(max(0, 1/FPS - (end - start)))
  ```

---

## 📈 9. Example Runtime Flow

```
Frame N:
  → Detect Pose
  → Compute 12 valid angles
  → Overlay skeleton
  → Send {angles} to plot
  → Append values to deques
  → Update rolling chart window (10s)
```

Continuous frames form an **animated time-series of motion**.

---

## ⚙️ 10. Algorithmic Design Advantages

- **Resilient:** Skips noisy or missing keypoints.
- **Efficient:** Maintains constant-time updates.
- **Dynamic:** Plots only visible angles on screen.
- **Extensible:** Can integrate additional metrics like velocity or acceleration.

---

## 🧮 11. Computational Complexity

| Step | Operation | Complexity |
|------|------------|-------------|
| Pose detection | Model inference | O(1) per frame |
| Angle computation | Vector math | O(n) (n ≈ 12 joints) |
| Overlay rendering | Line + text draw | O(n) |
| Plot update | Deque append + redraw | O(n) |
| **Total** | **Real-time (linear per frame)** | ≈ O(17) |

---

## 🧾 12. Termination & Session Handling

When session stops:
1. Frame capture loop terminates.
2. Final angle data is frozen.
3. Session summary displayed with:
   - Average angle values  
   - Max/min per joint  
   - Total repetitions  
   - Time duration

---

## 👨‍💻 Author
**A Mohammed Musharaff**  
📧 musharaffamohammed@gmail.com
