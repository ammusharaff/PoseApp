# app/main.py
import os, sys, traceback
print("[Launcher] start", flush=True)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(APP_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
for p in (SRC_DIR, PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

print("[Launcher] importing PySide6", flush=True)
from PySide6 import QtWidgets

def fatal(msg: str):
    print(msg, file=sys.stderr, flush=True)
    try:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
        QtWidgets.QMessageBox.critical(None, "PoseApp – Startup Error", msg)
    except Exception:
        pass
    sys.exit(1)

print("[Launcher] importing MainWindow", flush=True)
try:
    from poseapp.ui.main_window import MainWindow
except Exception:
    fatal("Failed to import MainWindow:\n\n" + traceback.format_exc())

print("[Launcher] creating QApplication", flush=True)
app = QtWidgets.QApplication(sys.argv)

print("[Launcher] creating MainWindow", flush=True)
try:
    w = MainWindow()
except Exception:
    fatal("Exception inside MainWindow.__init__:\n\n" + traceback.format_exc())

app.main_window_ref = w  # keep strong ref
print("[Launcher] showing MainWindow", flush=True)
w.show()
print("[Launcher] entering event loop", flush=True)
rc = app.exec()
print("[Launcher] event loop exited rc=", rc, flush=True)
sys.exit(rc)
