# 🧍‍♂️ PoseApp — Real-Time Human Pose & Angle Tracking

**PoseApp** is a cross-platform application for real-time human pose estimation, visualization, and movement analytics.  
It captures live camera input, draws the detected skeleton, computes joint angles, and visualizes live angle plots dynamically on the UI.

---

## 🧠 Overview

PoseApp provides an intuitive interface for biomechanical motion analysis.  
It can be used in fitness tracking, physiotherapy, sports analytics, and robotics applications where visualizing body joint angles and real-time tracking are important.

The system is built using:
- **PySide6 (Qt GUI Framework)** — for the interactive desktop interface  
- **TensorFlow Lite / MoveNet** — for fast, accurate pose detection  
- **Matplotlib** — for live plotting of joint angles  
- **OpenCV** — for frame capture and overlay rendering  

---

## ✨ Key Features

- 🎥 **Live Camera Feed**
  - Capture frames in real time using OpenCV
  - Visualize body keypoints as a skeleton overlay

- 📏 **Dynamic Angle Calculation**
  - Computes flexion/extension and abduction/adduction angles
  - Includes major joints: shoulders, elbows, hips, knees, and ankles

- 📊 **Live Angle Plot Panel**
  - Real-time rolling plots (10s window)
  - Auto-updates only for angles visible on screen
  - Continuous motion tracking

- ⚙️ **Cross-Platform**
  - Works on Windows, Ubuntu, and Fedora
  - Packaged via **PyInstaller** and **AppImage**

- 📘 **Integrated Documentation**
  - Built with **Sphinx**
  - Accessible via “Help → Documentation” in the menu

---

## 🧩 Project Structure

```
PoseApp/
├── app/
│   └── main.py                     # Entry launcher
├── src/
│   └── poseapp/
│       ├── ui/
│       │   ├── main_window.py      # Main GUI logic
│       │   ├── right_panel.py      # Live angle plots
│       │   ├── guided_panel.py     # Guided exercise (optional)
│       │   ├── session_summary.py  # Summary dialog
│       │   └── resources/          # Icons and UI assets
│       ├── geometry/
│       │   └── angles.py           # Angle calculations
│       ├── gait/
│       │   └── metrics.py          # Gait analysis utilities
│       ├── activities/
│       │   └── activity_defs.py    # Defined angle groups
│       ├── scoring/
│       │   └── scorer.py           # Angle-based scoring
│       ├── analysis/
│       │   ├── rep_detector.py     # Repetition cycle detector
│       │   └── guide_match.py      # Guide matching logic
│       ├── config.py               # Paths, constants, backend settings
│       └── __init__.py
│
├── packaging/
│   └── linux/
│       └── build_appimage.sh       # Script to build AppImage
│
├── docs/
│   ├── source/                     # Sphinx doc sources (.rst)
│   └── site/html/index.html        # Built documentation
│
├── dist/                           # Generated AppImage / binaries
├── build/                          # PyInstaller build folder
├── README.md                       # This file
├── requirements.txt
└── LICENSE
```

---

## 🖥️ Installation (Development Mode)

### 1️⃣ Clone the repository
```bash
git clone https://github.com/<your-username>/PoseApp.git
cd PoseApp
```

### 2️⃣ Create virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate   # Linux/macOS
# OR
.venv\Scripts\activate      # Windows
```

### 3️⃣ Install dependencies
```bash
pip install -r requirements.txt
```

### 4️⃣ Run the app
```bash
python -m app.main
```

---

## 🧰 Dependencies

| Library | Purpose |
|----------|----------|
| PySide6 | UI / Qt framework |
| OpenCV | Camera and frame capture |
| TensorFlow / tf-lite | Pose detection |
| NumPy | Math operations |
| Matplotlib | Live angle plotting |
| PyInstaller | Packaging executable |
| Sphinx | Documentation builder |

---

## 🧱 Building the AppImage (Linux)

### 1️⃣ Ensure dependencies
```bash
sudo apt update
sudo apt install -y python3-pip patchelf fuse file curl git
pip install pyinstaller
```

### 2️⃣ Run the build script
```bash
chmod +x packaging/linux/build_appimage.sh
bash packaging/linux/build_appimage.sh
```

This creates:
```
dist/PoseApp-x86_64.AppImage
```

### 3️⃣ Make executable
```bash
chmod +x dist/PoseApp-x86_64.AppImage
./dist/PoseApp-x86_64.AppImage
```

---

## 🧪 Building Windows Executable

On Windows PowerShell:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed app/main.py --name "PoseApp"
```

Output will appear in:
```
dist/PoseApp.exe
```

---

## 📚 Documentation

PoseApp uses **Sphinx** for API and developer documentation.

### Build docs manually:
```bash
cd docs
make html
```

### Access inside app:
> `Help → Open Documentation` → loads  
> `docs/site/html/index.html`

---

## 🧪 Developer Notes

- **Angle Calculation Logic:** implemented in `geometry/angles.py`
- **Detected Keypoints:** MoveNet returns 17 landmarks per frame
- **Angle Overlay Control:** shown dynamically based on keypoints detected
- **Live Angles Panel:** only plots angles currently visible on the frame

---

## 🧾 License

This project is licensed under the [MIT License](LICENSE).

---

## 🤝 Acknowledgements

- [TensorFlow MoveNet](https://www.tensorflow.org/hub/tutorials/movenet) for pose estimation
- [PySide6](https://doc.qt.io/qtforpython/) for GUI
- [AppImage](https://appimage.org/) for packaging

---

## 🚀 Roadmap

- [ ] Add activity recognition (squats, jumps, yoga)
- [ ] Add CSV export for angle data
- [ ] Integrate AI-based rep counting
- [ ] Multi-person tracking
- [ ] GPU-accelerated inference

---

## 💡 Example Use Cases

- Fitness tracking and workout feedback  
- Physiotherapy movement monitoring  
- Sports motion analysis  
- Robotics and kinematics studies  
- Research in human pose estimation

---

### 👨‍💻 Author
**A Mohammed Musharaff**  
📧 musharaffamohammed@gmail.com

