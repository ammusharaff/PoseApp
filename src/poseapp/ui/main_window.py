# src/poseapp/ui/main_window.py
import os, json, time, math, platform, sys, numpy as np, cv2, webbrowser  # stdlib + numpy + OpenCV + web for docs
from typing import Dict, Any, Optional, List, Tuple  # type hints for clarity
from collections import deque  # efficient FIFO used for time-series buffers
from PySide6 import QtCore, QtGui, QtWidgets  # Qt UI framework (signals, widgets, etc.)
from PySide6.QtCore import QUrl  # URL class for opening local docs
from PySide6.QtGui import QAction  # toolbar actions

# Pull global configuration values / constants and BackendChoice dataclass
from ..config import (
    WINDOW_TITLE, FRAME_SIZE, CAM_INDEX, KP_CONF_THRESH,
    MOVENET_LIGHTNING_PATH, MOVENET_THUNDER_PATH,
    BACKEND_MOVENET, BACKEND_MEDIAPIPE, BackendChoice, THUNDER_MIN_FPS
)
# Pose geometry helpers: convert keypoints list to dict, get XY coords
from ..geometry.angles import to_kpmap, _get_xy
# Gait tracker to compute cadence/step metrics across frames
from ..gait.metrics import GaitTracker
# Activity definitions (labels, target joints/angles, reps, etc.)
from ..activities.activity_defs import ACTIVITY_LIBRARY
# Rep cycle detector (state machine) and its sensitivity parameters
from ..analysis.rep_detector import RepCycleDetector, CycleParams
# Template matching helpers for guided-mode comparisons
from ..analysis.guide_match import extract_scalar_window, guide_match_activity_window
# Scoring utilities: bands, form stability, symmetry, final score
from ..scoring.scorer import score_band, form_stability, symmetry_index, final_score
# Left dock panel for guided UI
from .mode_guided_panel import GuidedPanel
# Rule-based per-rep assessment (validity/bands/messages)
from ..analysis.activity_rules import assess_activity_rep
# Small mixin to show GIF previews in guided panel
from .guided_helpers import GifPreviewMixin


# new modular imports
from ..utils.resources import resource_path  # robust resource path helper (PyInstaller-safe)
from ..utils.camera_scan import enumerate_cameras  # enumerate working camera indices
from ..metrics.angles_util import cvimg_to_qt, resolve_angle, compute_angle_from_kps  # misc angle & image helpers
from ..io.session_logger import SessionLogger, SAVE_ROOT_TEMP, SAVE_ROOT_FINAL  # session IO/logging
from ..camera.video_worker import VideoWorker  # threaded video + backend inference
from .dialogs import SettingsDialog, ExportDialog  # settings and export dialogs
from .overlays import (
    draw_skeleton, overlay_angles, overlay_gait, overlay_guided,
    draw_mp_hands, draw_mp_holistic_extras
)  # drawing overlays on the frame
from ..metrics.side_helpers import overlay_guided_flow  # guided mode flow extracted to helper


now_mono = time.monotonic  # monotonic clock for stable timing (not affected by system clock)

class MainWindow(QtWidgets.QMainWindow):  # main application window (central controller/orchestrator)
    angles_updated = QtCore.Signal(dict)  # signal: emit current angles dict to right-panel plot

    def __init__(self):
        super().__init__()  # init base QMainWindow
        self._t0_mono = None  # session start timestamp (monotonic)
        self._t_prev_mono = None  # previous frame time for FPS
        self.setWindowTitle(WINDOW_TITLE)  # set window title from config
        self.resize(1120, 740)  # initial window size
        self.video_label = QtWidgets.QLabel("Starting…\n Click on Start to begin. or press 'S' to start.")  # placeholder text
        self.video_label.setAlignment(QtCore.Qt.AlignCenter)  # center text / later used to show frames
        self.setCentralWidget(self.video_label)  # main central area is the video label
        self._gif_helper = GifPreviewMixin()  # helper to manage guided preview GIF
        self._autoswitch_cooldown_until = 0.0


        self.worker = None  # VideoWorker instance (created when starting)
        self.worker_thread = None  # QThread that hosts the worker
        self._current_cam_index = CAM_INDEX  # default camera index from config
        QtCore.QTimer.singleShot(0, self.build_ui)  # defer building UI to allow full init

    # ---------------- UI & toolbar ----------------
    def build_ui(self):
        self.status = self.statusBar()  # system status bar at bottom
        self.model_indicator = QtWidgets.QLabel("Active: —")  # shows active backend label
        self.status.addPermanentWidget(self.model_indicator)  # stick it on the right side of the status bar

        self.tb = self.addToolBar("Controls")  # top toolbar
        self.btn_start = QAction("Start", self)  # action to start the pipeline
        self.btn_stop  = QAction("Stop", self); self.btn_stop.setEnabled(False)  # stop action (disabled until started)
        self._is_mediapipe = False  # flag to draw MediaPipe extras only when using that backend

        self.cmb_backend = QtWidgets.QComboBox()  # backend selector (hidden by default)
        self.cmb_backend.addItems([f"{BACKEND_MOVENET} (auto)", BACKEND_MEDIAPIPE])  # options: movenet auto, mediapipe
        self.cmb_backend.setCurrentIndex(0)  # default to MoveNet auto
        self.cmb_backend.currentIndexChanged.connect(self.on_backend_change)  # react to change
        self.cmb_backend.setVisible(False)  # hide unless you want to expose manual control

        self.cmb_mode = QtWidgets.QComboBox(); self.cmb_mode.addItems(["Freestyle", "Guided"])  # app modes
        self.cmb_mode.currentIndexChanged.connect(self.on_mode_change)  # update UI/logic on mode switch

        self.cmb_camera = QtWidgets.QComboBox()  # camera device selector
        self._cams = enumerate_cameras(10)  # probe camera indices [0..10]
        self.cmb_camera.clear()  # clear in case of rebuild
        for idx, label in self._cams: self.cmb_camera.addItem(label, idx)  # add each working camera
        if self._cams:
            default_row = next((r for r,(i,_) in enumerate(self._cams) if i==0), 0)  # prefer index 0 if present
            self.cmb_camera.setCurrentIndex(default_row)  # select default camera row
            self._current_cam_index = int(self.cmb_camera.currentData())  # store chosen index
        else:
            self._current_cam_index = 0  # fallback to 0 even if not working
            self.btn_start.setEnabled(False)  # disable start if no camera
            QtWidgets.QMessageBox.warning(self, "Camera", "No usable camera found. Plug in a webcam and click Start again.")  # user hint
        self.cmb_camera.currentIndexChanged.connect(self.on_camera_change)  # restart pipeline on camera change

        # toolbar order (add widgets/actions in a neat sequence)
        self.tb.addWidget(QtWidgets.QLabel("Camera: ")); self.tb.addWidget(self.cmb_camera); self.tb.addSeparator()
        self.tb.addAction(self.btn_start); self.tb.addAction(self.btn_stop); self.tb.addSeparator()
        self.tb.addWidget(QtWidgets.QLabel("  Mode: ")); self.tb.addWidget(self.cmb_mode); self.tb.addSeparator()
        self.act_settings = QAction("Settings", self); self.act_export = QAction("Export", self)  # extra actions
        self.tb.addAction(self.act_settings); self.tb.addAction(self.act_export)
        # session actions (for logging/session lifecycle)
        self.tb.addSeparator()
        self.btn_session_start = QAction("Start Session", self)  # begin logging to temp folder
        self.btn_session_stop  = QAction("Stop Session", self); self.btn_session_stop.setEnabled(False)  # end logging
        self.tb.addAction(self.btn_session_start); self.tb.addAction(self.btn_session_stop)
        # docs entry point (opens local built docs in system browser)
        self.act_docs = QAction("Help Docs", self); self.tb.addAction(self.act_docs); self.act_docs.triggered.connect(self.on_open_docs)

        # connect toolbar actions to handlers
        self.btn_start.triggered.connect(self.on_start); self.btn_stop.triggered.connect(self.on_stop)
        self.btn_session_start.triggered.connect(self.on_session_start)
        self.btn_session_stop.triggered.connect(self.on_session_stop)
        self.act_settings.triggered.connect(self.on_open_settings)
        self.act_export.triggered.connect(self.on_open_export)

        # guided dock (left side)
        self.guided_dock = QtWidgets.QDockWidget("Guided Task Panel", self)  # container dock
        self.guided_panel = GuidedPanel(self)  # custom widget with activity selector + counters
        self.guided_dock.setWidget(self.guided_panel)  # place panel into dock
        self.guided_dock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea)  # only left area allowed
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.guided_dock)  # attach dock to main window
        self.guided_dock.hide()  # start hidden (mode defaults to freestyle)
        self.guided_dock.visibilityChanged.connect(self._on_guided_dock_visibility)  # keep mode/dock state in sync
        self.guided_panel.installEventFilter(self)  # intercept resize events to scale GIF preview

        # right dock (angles) — real-time plotting of angles
        from .right_panel import RightPanel  # local import to avoid circular deps at module import time
        self.right_dock = QtWidgets.QDockWidget("Live Angles (10 s)", self)  # container for plot
        self.right_panel = RightPanel()  # plotting widget with Matplotlib
        self.right_dock.setWidget(self.right_panel)  # embed
        self.right_dock.setAllowedAreas(QtCore.Qt.RightDockWidgetArea)  # right side only
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.right_dock)  # attach
        self.angles_updated.connect(self.right_panel.update_angles)  # push angle dict updates every frame

        self.act_live_angles = QAction("Live Angles", self); self.act_live_angles.setCheckable(True); self.act_live_angles.setChecked(True)  # toggle action
        self.act_live_angles.toggled.connect(self.right_dock.setVisible)  # show/hide plot dock
        self.right_dock.visibilityChanged.connect(self.act_live_angles.setChecked)  # keep state synced
        self.tb.addAction(self.act_live_angles)  # put it on the toolbar

        # keyboard shortcuts to drive main actions quickly
        QtGui.QShortcut(QtGui.QKeySequence("S"), self, activated=self._shortcut_start_stop)  # S = start/stop
        QtGui.QShortcut(QtGui.QKeySequence("G"), self, activated=self._shortcut_toggle_mode)  # G = guided/freestyle
        QtGui.QShortcut(QtGui.QKeySequence("M"), self, activated=self._shortcut_toggle_model)  # M = backend toggle
        QtGui.QShortcut(QtGui.QKeySequence("E"), self, activated=self._shortcut_export)  # E = export dialog
        for key, idx in [("1",0),("2",1),("3",2),("4",3),("5",4)]:  # numeric keys pick guided activity index
            QtGui.QShortcut(QtGui.QKeySequence(key), self, activated=lambda i=idx: self._shortcut_pick_activity(i))

        # state initialization
        self.choice = BackendChoice()  # backend config (auto/variant/hands)
        self.gait = GaitTracker()  # cadence/step tracker
        self._last_auto_variant = "lightning"  # track last auto-selected MoveNet variant
        self._fps_meas = 0.0  # smoothed FPS
        self._mode = "freestyle"  # current mode
        self._active_model_label = "—"  # UI label for model
        self._guided: Optional[Dict[str, Any]] = None  # guided mode state/config
        self.session_active = False  # are we logging?
        self.logger: Optional[SessionLogger] = None  # session logger handle
        self._set_idx = 1  # current set counter
        self._target_reps = 5  # default rep target
        self._session_payloads: List[Dict[str, Any]] = []  # accumulate guided set payloads

        self.status.showMessage("Ready. Press Start.")  # status hint
        QtCore.QTimer.singleShot(300, self._prompt_export_if_pending)  # prompt user about unexported sessions (if any)
        self._ensure_guided_panel_hooks()  # populate guided panel (activities, preview, signals)

    # ---------- docs ----------
    def _find_docs_index(self) -> Optional[str]:
        here = os.path.abspath(os.path.dirname(__file__))
        proj_root = os.path.abspath(os.path.join(here, "..", "..", ".."))
        meipass = getattr(sys, "_MEIPASS", "")
        for p in (
            os.path.abspath(os.path.join(os.getcwd(), "docs", "site", "html", "index.html")),
            os.path.join(proj_root, "docs", "site", "html", "index.html"),
            os.path.join(meipass, "docs", "site", "html", "index.html"),  # <-- frozen bundle
            os.path.join(os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else "", "docs", "site", "html", "index.html"),
        ):
            if p and os.path.isfile(p):
                return p
        return None


    def on_open_docs(self):
        path = self._find_docs_index()  # locate docs index.html
        if not path:
            QtWidgets.QMessageBox.information(self, "Help Docs", "Documentation not found at 'docs/site/html/index.html'.")  # friendly hint
            return
        url = QUrl.fromLocalFile(path)  # make a file:// URL
        if not QtGui.QDesktopServices.openUrl(url):  # try via Qt
            webbrowser.open_new_tab(path)  # fallback to system webbrowser

    # ---------- session ----------
    def on_session_start(self):
        if self.session_active:
            self.status.showMessage("Session already running"); return  # avoid duplicate starts
        self.logger = SessionLogger(mode=self._mode)  # create new temporary session folder & open files
        self._session_payloads.clear()  # clear prior guided set rollups
        self.session_active = True  # mark active
        self.btn_session_start.setEnabled(False); self.btn_session_stop.setEnabled(True)  # toggle buttons
        self.status.showMessage(f"Session started in {self._mode} mode (temporary until export).")  # feedback

    def on_session_stop(self):
        if not self.session_active:
            self.status.showMessage("No active session"); return  # nothing to stop
        try:
            final = {}  # session-wide summary payload
            if self._session_payloads:  # aggregate guided sets if present
                total_sets = len(self._session_payloads)  # number of sets
                by_activity = {}  # group sets by activity key
                for p in self._session_payloads:
                    a = p.get("activity", "unknown"); by_activity.setdefault(a, []).append(p)
                overall_mean_final = np.nanmean([p.get("final_percent", float("nan")) for p in self._session_payloads]) \
                                     if self._session_payloads else float("nan")  # mean of final scores
                final = {  # structured session summary
                    "total_sets": total_sets,
                    "overall_mean_final_percent": float(overall_mean_final) if np.isfinite(overall_mean_final) else None,
                    "activities": {
                        a: {
                            "sets": len(lst),
                            "mean_final_percent": float(np.nanmean([pp.get("final_percent", float("nan")) for pp in lst])) if lst else None
                        } for a, lst in by_activity.items()
                    }
                }
            if self.logger:
                self.logger.close(final_scores=final); self.logger = None  # write summary.json and close files
        finally:
            self.session_active = False  # toggle state
            self.btn_session_start.setEnabled(True); self.btn_session_stop.setEnabled(False)  # buttons back
            self.status.showMessage("Session stopped (files saved to temporary folder)")  # feedback

    # ---------- mode/dock ----------
    def _on_guided_dock_visibility(self, visible: bool):
        if not visible and self._mode == "guided":
            self._mode = "freestyle"; self.cmb_mode.setCurrentIndex(0)  # sync UI to freestyle if dock gets closed
            self.status.showMessage("Mode switched to Freestyle (Guided panel closed)")
        elif visible and self._mode == "freestyle":
            self.guided_dock.hide()  # if visible but mode is freestyle, hide it (safety)

    def on_mode_change(self, idx: int):
        self._mode = "guided" if idx == 1 else "freestyle"  # map combobox index → mode string
        if self._mode == "guided":
            self.guided_dock.show(); self.status.showMessage("Mode B – Guided Task"); self._ensure_guided_panel_hooks()  # reveal left dock
        else:
            self.guided_dock.hide(); self.status.showMessage("Mode A – Freestyle")  # hide left dock

    # ---------- controls ----------
    def on_backend_change(self, _idx: int):
        if not self.worker: return  # ignore if pipeline not started
        if self.cmb_backend.currentIndex() == 1:
            self.worker.set_backend(BackendChoice(name=BACKEND_MEDIAPIPE, hands_required=True))  # switch to MediaPipe
        else:
            self.worker.set_backend(BackendChoice(name=BACKEND_MOVENET, variant=self._last_auto_variant))  # MoveNet (auto-variant)

    @QtCore.Slot(str)
    def on_backend_changed(self, label: str):
        self.model_indicator.setText(f"Active: {label}")  # update status bar label
        self._active_model_label = label  # cache active model label (also logged)
        self._is_mediapipe = ("MediaPipe" in label)  # if mediapipe, enable drawing hands/extras

    def on_open_settings(self):
        dlg = SettingsDialog(self, current_backend_idx=self.cmb_backend.currentIndex())  # open settings modal
        if dlg.exec() == QtWidgets.QDialog.Accepted:  # user pressed OK
            new_idx = dlg.selected_backend_index()  # retrieve selected backend
            if new_idx != self.cmb_backend.currentIndex():  # only update if changed
                self.cmb_backend.setCurrentIndex(new_idx); self.on_backend_change(new_idx)  # apply selection

    # ---------- export ----------
    def _list_temp_sessions(self) -> List[str]:
        base = SAVE_ROOT_TEMP  # temp sessions root
        if not os.path.isdir(base): return []  # nothing to list
        items = []  # collect valid sessions
        for d in sorted(os.listdir(base)):  # iterate by timestamp folder
            full = os.path.join(base, d)
            if os.path.isdir(full):
                if any(os.path.isfile(os.path.join(full, name)) for name in ("raw_keypoints.json","angles.csv","gait.csv")):
                    items.append(full)  # consider it a valid session
        return items

    def _export_session_dir(self, tmp_dir: str) -> Optional[str]:
        try:
            os.makedirs(SAVE_ROOT_FINAL, exist_ok=True)  # ensure final sessions folder exists
            basename = os.path.basename(tmp_dir.rstrip("/\\"))  # strip trailing slashes and get folder name
            dest = os.path.join(SAVE_ROOT_FINAL, basename); base_try = dest; i = 2  # destination path
            while os.path.exists(dest): dest = f"{base_try}_{i}"; i += 1  # avoid collisions by suffixing _2, _3, ...
            os.replace(tmp_dir, dest); return dest  # move directory atomically
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Export error", str(e)); return None  # show error and propagate None

    def on_open_export(self):
        if self.session_active:
            QtWidgets.QMessageBox.information(self,"Export","Stop the current session before exporting."); return  # safety: avoid moving live files
        sessions = self._list_temp_sessions()  # enumerate temp sessions
        if not sessions:
            QtWidgets.QMessageBox.information(self,"Export","No temporary sessions to export."); return  # nothing to export
        dlg = ExportDialog(self, sessions)  # let user pick sessions
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            moved = []  # track moved session names
            for tmp in dlg.exported:
                newp = self._export_session_dir(tmp)  # move to final folder
                if newp: moved.append(os.path.basename(newp))
            if moved:
                QtWidgets.QMessageBox.information(self, "Export", "Exported:\n- " + "\n- ".join(moved))  # confirmation message

    def _prompt_export_if_pending(self):
        sessions = self._list_temp_sessions()  # auto-detect unexported sessions
        if not sessions: return  # no prompt if none
        ret = QtWidgets.QMessageBox.question(
            self, "Export sessions",
            f"{len(sessions)} un-exported session(s) found. Export now?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if ret == QtWidgets.QMessageBox.Yes: self.on_open_export()  # open export dialog if user agrees

    # ---------- lifecycle ----------
    def on_start(self):
        try:
            if self.worker_thread and self.worker_thread.isRunning(): return  # already running
            self.worker_thread = QtCore.QThread(self)  # create thread container
            if self.cmb_backend.currentIndex() == 1:
                self.choice = BackendChoice(name=BACKEND_MEDIAPIPE, hands_required=True)
            else:
                self.choice = BackendChoice(name=BACKEND_MOVENET, variant=self._last_auto_variant)
            #self.choice = BackendChoice()  # init backend choice (default/auto)
            self.worker = VideoWorker(self.choice, cam_index=self._current_cam_index)  # worker manages camera + model
            self.worker.backend_changed.connect(self.on_backend_changed)  # update label when backend auto-switches
            self.worker.moveToThread(self.worker_thread)  # move worker to thread context
            self.worker.frame_ready.connect(self.on_frame)  # receive processed frame callbacks
            self.worker.error.connect(self.on_error)  # show errors
            self.worker_thread.started.connect(self.worker.start)  # start worker when thread starts
            self.worker_thread.start()  # start the thread
            self.btn_stop.setEnabled(True)  # enable stop button
            self.status.showMessage(f"Running… Mode {self._mode.title()}")  # UI update
            self._t0_mono = now_mono(); self._t_prev_mono = self._t0_mono  # reset timing for FPS/relative logging
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Start error", str(e)); raise  # report and re-raise

    def on_stop(self):
        try:
            if self.worker: self.worker.stop()  # stop backend + camera
            if self.worker_thread:
                self.worker_thread.quit(); self.worker_thread.wait()  # cleanly stop thread
        finally:
            self.btn_start.setEnabled(True); self.btn_stop.setEnabled(False)  # reset controls
            if self.logger: self.logger.close(); self.logger = None  # close session if left open
            self._guided = None; self.status.showMessage("Stopped")  # clear guided state and notify

    def on_camera_change(self, _i: int):
        data = self.cmb_camera.currentData()  # new camera index from combo
        self._current_cam_index = int(data) if data is not None else 0  # update internal index
        if self.worker_thread and self.worker_thread.isRunning():
            self.on_stop(); self.on_start()  # restart pipeline to apply camera change
    
    def eventFilter(self, obj, event):
        try:
            if (obj is self.guided_panel
                and self._gif_helper._preview_gif_label is not None
                and event.type() == QtCore.QEvent.Resize):
                lbl = self._gif_helper._preview_gif_label  # the label showing GIF
                if self._gif_helper._gif_movie and lbl.width() > 0 and lbl.height() > 0:
                    self._gif_helper._gif_movie.setScaledSize(lbl.size())  # rescale GIF to fit panel on resize
        except Exception:
            pass  # never crash due to preview errors
        return super().eventFilter(obj, event)  # default processing
    
    def closeEvent(self, ev: QtGui.QCloseEvent) -> None:
        try:
            self.on_stop()  # stop camera/threads on close
            if self.session_active:  # if user is closing mid-session, close gracefully with a final summary
                final = {}
                if self._session_payloads:
                    total_sets = len(self._session_payloads)
                    by_activity = {}
                    for p in self._session_payloads:
                        a = p.get("activity","unknown"); by_activity.setdefault(a, []).append(p)
                    overall_mean_final = np.nanmean([p.get("final_percent", float("nan")) for p in self._session_payloads]) \
                                         if self._session_payloads else float("nan")
                    final = {
                        "total_sets": total_sets,
                        "overall_mean_final_percent": float(overall_mean_final) if np.isfinite(overall_mean_final) else None,
                        "activities": {
                            a: {
                                "sets": len(lst),
                                "mean_final_percent": float(np.nanmean([pp.get("final_percent", float("nan")) for pp in lst])) if lst else None
                            } for a, lst in by_activity.items()
                        }
                    }
                if self.logger: self.logger.close(final_scores=final); self.logger = None  # write final summary and close files
                self.session_active = False  # clear flag
            self._prompt_export_if_pending()  # remind about exporting any pending sessions
        finally:
            super().closeEvent(ev)  # call base close

    # ---------- guided panel plumbing ----------
    def _ensure_guided_panel_hooks(self):
        items = [(k, v.get("label", k)) for k, v in ACTIVITY_LIBRARY.items()]  # build (key,label) list from activity defs
        
        if self.guided_panel.layout() is None:
            self.guided_panel.setLayout(QtWidgets.QVBoxLayout())  # ensure there is a layout
        combos = self.guided_panel.findChildren(QtWidgets.QComboBox)  # try to find an existing combo
        if combos: activity_combo = combos[0]  # reuse existing if present
        else:
            activity_combo = QtWidgets.QComboBox(self.guided_panel)  # create a basic combo if GuidedPanel didn’t
            for _, label in items: activity_combo.addItem(label)  # add labels as fallback items
            self.guided_panel.layout().addWidget(QtWidgets.QLabel("Select activity:", self.guided_panel))  # add caption
            self.guided_panel.layout().addWidget(activity_combo)  # insert combo
        
        if hasattr(self.guided_panel, "populate"):
            try: self.guided_panel.populate(items)  # proper population with (key,label) and userData
            except Exception: pass
        try: self.guided_panel.start_trial.connect(self.on_start_trial)  # connect “Start Guided Trial” button
        except Exception: pass

        # preview text (below the combo) shows description/targets
        labels = [w for w in self.guided_panel.findChildren(QtWidgets.QLabel)]
        preview_text = labels[0] if labels else QtWidgets.QLabel("Select an activity to see details.", self.guided_panel)  # make one if missing
        preview_text.setWordWrap(True); preview_text.setMinimumHeight(60)  # readable block
        if not labels: self.guided_panel.layout().addWidget(preview_text)  # add only when we created it
        self._activity_combo = activity_combo  # keep a ref for later
        self._preview_text = preview_text
        activity_combo.currentIndexChanged.connect(self._on_activity_changed, QtCore.Qt.ConnectionType.UniqueConnection)  # update preview on change
        self._on_activity_changed(activity_combo.currentIndex())  # initialize preview

    # ---------- errors ----------
    def on_error(self, msg: str):
        QtWidgets.QMessageBox.critical(self, "Error", f"{msg}\n\nTip: Use the 'Camera' dropdown to pick another index.")  # show error dialog
        self.on_stop()  # stop pipeline on error (safe state)

    # ---------- frame loop ----------
    def on_frame(self, frame_bgr, info):
        tnow = info.get("t_mono") or info.get("meta", {}).get("t_mono") or now_mono()  # monotonic timestamp from backend or local
        if self._t_prev_mono is None: self._t_prev_mono = tnow  # initialize previous time for FPS
        dt = tnow - self._t_prev_mono; self._t_prev_mono = tnow  # frame duration delta
        if dt > 0: self._fps_meas = 0.2 * (1.0 / dt) + 0.8 * getattr(self, "_fps_meas", 0.0)  # EMA smoothing of FPS

        if self.cmb_backend.currentIndex() == 0:  # Auto MoveNet mode only
            fps_hint = (info.get("meta") or {}).get("fps_hint")
            if isinstance(fps_hint, (int, float)):
                now_t = now_mono()
                if now_t >= getattr(self, "_autoswitch_cooldown_until", 0.0):
                    want = "thunder" if fps_hint >= (THUNDER_MIN_FPS + 2.0) else "lightning"  # hysteresis
                    if want != self._last_auto_variant:
                        self._last_auto_variant = want
                        if self.worker:
                            self.worker.set_backend(BackendChoice(name=BACKEND_MOVENET, variant=want))
                        self.status.showMessage(f"Auto-selected MoveNet: {want} (FPS~{fps_hint:.1f})")
                        self._autoswitch_cooldown_until = now_t + 2.0  # 2s cooldown

        kps = info["kps"]  # raw keypoints from backend
        kpmap = to_kpmap(kps)  # map name → {x,y,conf}
        from ..geometry.angles import angles_of_interest  # local import avoids import cycles at module load
        ang = angles_of_interest(kpmap)  # compute angles we care about from kpmap

        if not ang:
            # compute a few staples for plotting as fallback so UI isn’t empty
            for key in ("knee_L_flex","knee_R_flex","hip_L_flex","hip_R_flex","shoulder_L_abd","shoulder_R_abd","ankle_L_pf","ankle_R_pf"):
                v = compute_angle_from_kps(key, kpmap)
                if v is not None and np.isfinite(v): ang[key] = float(v)

        # send to right panel (plotter)
        self.angles_updated.emit(ang)

        # logging (if a session is active)
        if self.session_active and self.logger:
            trel = (tnow - self._t0_mono) if self._t0_mono is not None else 0.0  # relative time from session start
            self.logger.log_keypoints(trel, getattr(self, "_active_model_label","—"), kps)  # append keypoints row
            self.logger.log_angles(trel, ang)  # append angles row

        # gait (compute cadence/steps using ankle verticals and hip width for scale)
        h, w = frame_bgr.shape[:2]  # frame dimensions
        ankleL = _get_xy(kpmap, "left_ankle"); ankleR = _get_xy(kpmap, "right_ankle")  # ankle points if visible
        hip_w = None  # optional scale
        if "left_hip" in kpmap and "right_hip" in kpmap:
            lhp = (kpmap["left_hip"]["x"]*w, kpmap["left_hip"]["y"]*h)
            rhp = (kpmap["right_hip"]["x"]*w, kpmap["right_hip"]["y"]*h)
            hip_w = float(np.hypot(lhp[0]-rhp[0], lhp[1]-rhp[1]))  # pixel distance between hips as rough scale
        self.gait.update(info.get("t", tnow), ankleL[1] if ankleL else None, ankleR[1] if ankleR else None, hip_w)  # push sample
        gait = self.gait.metrics()  # read derived metrics
        if self.session_active and self.logger:
            self.logger.log_gait((tnow - self._t0_mono) if self._t0_mono else 0.0, gait)  # append gait row

        # overlays: model label at bottom-left
        active = getattr(self, "_active_model_label", "—")
        cv2.putText(frame_bgr, f"Model: {active}", (10, h-70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,220,180), 2, cv2.LINE_AA)

        if self._mode == "freestyle":  # Mode A: show generic overlays
            draw_skeleton(frame_bgr, kpmap)  # draw lines/joints
            if self._is_mediapipe:
                try:
                    meta = info.get("meta", {}) or {}  # metadata may include hands/face/extras
                    draw_mp_hands(frame_bgr, meta) # draw if available
                    draw_mp_holistic_extras(frame_bgr, meta) # draw if available
                except Exception: # catch all exceptions
                    pass # never crash due to drawing errors
            shown = overlay_angles(frame_bgr, ang)  # text list of angles (and capture which keys were shown)
            overlay_gait(frame_bgr, gait)  # cadence/step stats at bottom
            try: self.right_panel.set_detected_from_main(shown)  # inform plotter which keys are currently visible on overlay
            except Exception: pass
        else:  # Mode B: Guided — show skeleton + guided overlays (and optional MediaPipe extras)
            draw_skeleton(frame_bgr, kpmap)
            if self._is_mediapipe:
                try:
                    meta = info.get("meta", {}) or {}  # metadata may include hands/face/extras
                    draw_mp_hands(frame_bgr, meta); draw_mp_holistic_extras(frame_bgr, meta)  # draw if available
                except Exception: pass
            self._overlay_guided_flow(frame_bgr, ang, kpmap)  # delegate to helper that handles rep detection + overlays

        # fps + blit to Qt label
        cv2.putText(frame_bgr, f"FPS ~{self._fps_meas:.1f}", (10, h-50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,255,200), 2, cv2.LINE_AA)  # live FPS
        qimg = cvimg_to_qt(QtGui, cv2, frame_bgr)  # convert cv2 BGR ndarray → QImage
        self.video_label.setPixmap(QtGui.QPixmap.fromImage(qimg))  # display frame in central widget

    # ---- guided orchestration (unchanged logic, just compartmentalized) ----
    def on_start_trial(self, key: str):
        act = ACTIVITY_LIBRARY[key]  # fetch activity metadata by key
        getattr(self.guided_panel, 'run_countdown_blocking', lambda *_: None)(5)  # blocking inline countdown (5s)
        now = time.time()  # wall-clock used for flow stages
        wait_until = now + 2.0; ready_until = wait_until + 2.0  # WAIT → READY durations
        cp = CycleParams(baseline_band=8, up_thresh=30, down_thresh=12, min_duration=0.80, max_duration=6.0, peak_hold=0.10) if key=="squat" else CycleParams()  # tuned params for squat, default otherwise
        self._gif_helper.set_activity_preview(self.guided_panel, key)  # show exercise GIF
        template = self._load_template_rule(key) if key=="squat" else None  # optional template for squat
        self._set_idx = 1; self._target_reps = act["reps"]  # reset set/reps counters
        self._guided = {  # runtime state for guided flow
            "key": key, "label": act["label"], "primary": act["primary_joints"],
            "score_joint": act.get("score_joint", act["primary_joints"][0]),
            "targets": act["targets"].copy(), "repdet": RepCycleDetector(params=cp),
            "series_by_joint": {j: [] for j in act["primary_joints"]},
            "angles_series": [], "reps_done": 0, "rep_scores": [],
            "set_idx": self._set_idx, "reps_target": self._target_reps,
            "start_time": now, "phase": "WAIT", "wait_until": wait_until, "ready_until": ready_until,
            "overlay_msg": "wait", "template": template, "kp_snaps": deque(maxlen=400)
        }
        # show counters in the dock UI
        if hasattr(self.guided_panel, "set_counters"):
            self.guided_panel.set_counters(0, self._guided["reps_target"], self._guided["set_idx"])
        self.status.showMessage(f"Guided: {act['label']} – countdown, then wait/ready/start for {self._guided['reps_target']} reps.")  # feedback

    def _overlay_guided_flow(self, frame_bgr, ang, kpmap):
        overlay_guided_flow(self, frame_bgr, ang, kpmap)  # call helper module that handles side locking, bands, rep counting, UI, logging
        
    # ---- templates ----
    def _template_path_json(self, key: str) -> str: return os.path.join("assets","templates",f"{key}_rule.json")  # path to template json
    def _load_template_rule(self, key: str) -> Optional[Dict[str, Any]]:
        p = self._template_path_json(key)  # compute path
        if not os.path.exists(p): return None  # absent → no template
        with open(p,"r",encoding="utf-8") as f: return json.load(f)  # load JSON into dict

    # ---- activity select ----
    def _on_activity_changed(self, idx: int):
        keys = list(ACTIVITY_LIBRARY.keys())  # ordered list of keys
        if not keys:
            if hasattr(self, "_preview_text") and self._preview_text:
                self._preview_text.setText("No activities found in ACTIVITY_LIBRARY."); return  # inform if library empty
        if idx < 0 or idx >= len(keys): idx = 0  # clamp index
        key = keys[idx]; meta = ACTIVITY_LIBRARY.get(key, {})  # get metadata for selected activity
        label = meta.get("label", key); primary = meta.get("primary_joints", meta.get("primary", []))  # title + target joints
        targets = meta.get("targets", {})  # goal angles
        bullets = []
        if primary: bullets.append(f"Primary joints: {', '.join(primary)}")  # summary lines
        if targets: bullets.append("Targets: " + ", ".join([f"{k}→{v}°" for k,v in targets.items()]))
        desc = meta.get("desc") or meta.get("description") or ""  # friendly description
        txt = f"<b>{label}</b><br>{desc}<br>" + "<br>".join(bullets)  # rich text
        if hasattr(self, "_preview_text") and self._preview_text: self._preview_text.setText(txt)  # update dock text
        # (optional) you can plug GIF preview mixin here if you want
        self._gif_helper.set_activity_preview(self.guided_panel, key)  # show the matching exercise GIF
    
    # ---------- shortcuts ----------
    def _shortcut_start_stop(self): self.on_stop() if self.btn_stop.isEnabled() else self.on_start()  # S key → toggle start/stop
    def _shortcut_toggle_mode(self): self.cmb_mode.setCurrentIndex(1 - self.cmb_mode.currentIndex())  # G key → toggle mode
    def _shortcut_toggle_model(self): self.cmb_backend.setCurrentIndex(1 - self.cmb_backend.currentIndex())  # M key → toggle backend index
    def _shortcut_export(self): self.on_open_export()  # E key → export dialog
    def _shortcut_pick_activity(self, idx: int):
        try:
            if self._mode == "guided":
                combos = self.guided_panel.findChildren(QtWidgets.QComboBox)  # find the combo within the dock
                if combos and 0 <= idx < combos[0].count(): combos[0].setCurrentIndex(idx)  # switch to requested activity index
        except Exception: pass  # ignore if not available
