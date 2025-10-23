# 🧾 PoseApp — Compliance & Licensing Documentation

This document provides details on **open‑source compliance**, **ethical AI usage**, and **data privacy practices** followed in the PoseApp project.

---

## ⚖️ 1. Purpose of this Document

The purpose of this document is to ensure that PoseApp adheres to:
- Open‑source software licensing obligations.
- Data protection and ethical AI practices.
- Secure software engineering and distribution requirements.

---

## 📜 2. Licensing Summary

| Component | License | Source / Link | Usage |
|------------|----------|---------------|--------|
| **PySide6** (Qt for Python) | LGPL‑3.0 | https://doc.qt.io/qtforpython/ | UI and windowing framework |
| **OpenCV** | Apache‑2.0 | https://opencv.org/ | Real‑time image processing and rendering |
| **TensorFlow Lite (MoveNet)** | Apache‑2.0 | https://www.tensorflow.org/lite | Pose estimation inference |
| **Matplotlib** | PSF | https://matplotlib.org/ | Real‑time plotting and visualization |
| **NumPy** | BSD‑3‑Clause | https://numpy.org/ | Vector and matrix computations |
| **PyInstaller** | GPL‑2.0 | https://pyinstaller.org/ | Packaging and executable creation |
| **Sphinx** | BSD‑2‑Clause | https://www.sphinx-doc.org/ | Documentation generation |

➡️  All third‑party dependencies are open‑source and compatible for both **academic** and **commercial** redistribution provided license texts are included in binary distributions (e.g., AppImage or EXE).

---

## 🧠 3. Model Compliance (AI Components)

| Model | Source | License | Usage | Notes |
|--------|---------|----------|--------|-------|
| MoveNet Thunder & Lightning | TensorFlow Hub | Apache‑2.0 | Keypoint detection (17‑point) | CPU‑optimized via TFLite |
| Custom Angle Engine | In‑house (AI Decoded) | Proprietary | Angle & motion analysis | No external dependencies |

**Ethical usage rules:**
- Only stores transient frame data in memory (no saving to disk).
- No biometric or facial recognition performed.
- All inference runs locally on user’s device.

---

## 🔐 4. Data Privacy & Security Policy

PoseApp does **not** transmit, store, or share any user data externally.

| Category | Data Type | Stored? | Description |
|-----------|------------|----------|--------------|
| Video Frames | Raw RGB frames | ❌ No | Processed in RAM only |
| Pose Keypoints | Numeric vectors | ❌ No | Discarded after computation |
| Session Angles | Derived metrics | ⚪ Temporarily | Optional runtime buffer only |
| User Metadata | Name, camera ID | ❌ No | Not collected or persisted |

> ✅ **GDPR‑friendly:** PoseApp does not collect or process personally identifiable information (PII).  
> ✅ **Offline Processing:** All AI inference happens on‑device, with no cloud dependency.

---

## 🧩 5. Software Build & Distribution Compliance

### 5.1 Build Environments
- **Windows:** PyInstaller executable (`PoseApp.exe`)
- **Linux:** AppImage (`PoseApp-x86_64.AppImage`)
- **macOS:** PyInstaller bundle (`.app`)

All builds embed necessary **open‑source license texts** under `/licenses/` within the final package.

### 5.2 AppImage Notes
AppImages must include a copy of the LGPL‑3 license when shipping Qt‑based binaries (PySide6).  
Compliance is achieved by:
- Including `license/` directory in `AppDir/usr/share/licenses/`
- Dynamically linking to Qt libraries

---

## 🧰 6. Security Best Practices

| Area | Implementation | Notes |
|-------|----------------|-------|
| Dependencies | Pinned via `requirements.txt` | Avoids supply chain drift |
| Packaging | PyInstaller + SHA‑256 checksum | Verifies binary integrity |
| Runtime | Safe exception handling | Prevents camera / IO crashes |
| Logging | Local only (debug level) | No telemetry exported |
| Docs | Offline HTML (Sphinx) | No analytics or tracking |

---

## 🧮 7. Model Ethics Checklist

| Guideline | Compliance |
|------------|-------------|
| No facial or personal ID detection | ✅ |
| No cloud‑based inference | ✅ |
| Works entirely offline | ✅ |
| Transparent explainability (angles visible to user) | ✅ |
| No dataset scraping or private data use | ✅ |
| Supports research & rehabilitation use‑cases only | ✅ |

---

## 🧱 8. Documentation & Reproducibility

All source code and documentation are open and reproducible.

| Artifact | Location | Description |
|-----------|-----------|-------------|
| `/docs/site/html/` | Built with Sphinx | HTML technical docs |
| `/packaging/linux/` | Build scripts | PyInstaller & AppImage setup |
| `/src/poseapp/` | Core modules | Source and algorithm implementation |

---

## 🧩 9. Legal Notices

1. Redistribution of PoseApp binaries must retain author credits and license files.  
2. All embedded third‑party software remains the property of their respective owners.  
3. Commercial redistribution must comply with LGPL‑3 (for PySide6) and Apache‑2.0 (for TensorFlow / OpenCV).  
4. End users must accept the included EULA for commercial versions.

---

## 🧾 10. Version Compliance Table

| Component | Version | Verified License |
|------------|----------|------------------|
| Python | 3.10+ | PSF |
| PySide6 | 6.7.x | LGPL‑3 |
| OpenCV | 4.9.x | Apache‑2 |
| TensorFlow Lite | 2.15+ | Apache‑2 |
| PyInstaller | 6.16+ | GPL‑2 |
| Matplotlib | 3.8+ | PSF |

All versions verified using:
```bash
pip-licenses --from=mixed --with-urls --with-license-file
```

---

## 👨‍💻 Author & Maintainer

**A Mohammed Musharaff**  
📧 musharaffamohammed@gmail.com

---

© 2025 PoseApp — All rights reserved under dual license:  
- **Open‑Source (Research/Academic Use)** under MIT License  
- **Commercial Use** requires explicit permission from the author.
