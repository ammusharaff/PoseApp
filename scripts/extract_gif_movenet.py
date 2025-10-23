# scripts/extract_gif_movenet.py
import argparse
import json
import os
import sys
import math
import time
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict

import numpy as np
from PIL import Image, ImageSequence

try:
    import tflite_runtime.interpreter as tflite  # preferred
    _TFLITE_BACKEND = "tflite_runtime"
except Exception:
    try:
        import tensorflow as tf
        tflite = tf.lite
        _TFLITE_BACKEND = "tensorflow.lite"
    except Exception:
        print("ERROR: Neither 'tflite_runtime' nor 'tensorflow' is available.", file=sys.stderr)
        sys.exit(1)

try:
    import cv2
except Exception:
    cv2 = None

KEYPOINT_NAMES = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle"
]

@dataclass
class MoveNetSpec:
    name: str
    input_size: int  # 192 lightning, 256 thunder

def guess_movenet_spec(model_path: str) -> MoveNetSpec:
    low = model_path.lower()
    if "thunder" in low:
        return MoveNetSpec("MoveNet Thunder", 256)
    return MoveNetSpec("MoveNet Lightning", 192)

class MoveNetTFLite:
    def __init__(self, model_path: str):
        self.spec = guess_movenet_spec(model_path)
        self.interp = tflite.Interpreter(model_path="G:/AI_Decoded/Zeuron_Pose_Estimation/Try_3/PoseApp/models/movenet_singlepose_thunder.tflite")
        self.interp.allocate_tensors()
        self.in_details = self.interp.get_input_details()
        self.out_details = self.interp.get_output_details()
        self.in_idx = self.in_details[0]['index']
        self.out_idx = self.out_details[0]['index']

        # dtype & quantization info
        self.in_dtype = self.in_details[0]['dtype']              # np.uint8 / np.int8 / np.float32
        self.in_q = self.in_details[0].get('quantization', None) # (scale, zero_point) or (0.0, 0)
        # Some TF builds use 'quantization_parameters'
        if (not self.in_q or self.in_q == (0.0, 0)) and 'quantization_parameters' in self.in_details[0]:
            qp = self.in_details[0]['quantization_parameters']
            scale = float(qp['scales'][0]) if len(qp.get('scales', [])) else 0.0
            zp = int(qp['zero_points'][0]) if len(qp.get('zero_points', [])) else 0
            self.in_q = (scale, zp)

    def _preprocess(self, img_rgb: np.ndarray) -> np.ndarray:
        """Resize to input and quantize/normalize according to input dtype."""
        inp = Image.fromarray(img_rgb).resize(
            (self.spec.input_size, self.spec.input_size), Image.BILINEAR
        )
        arr = np.asarray(inp)

        if self.in_dtype == np.float32:
            arr = arr.astype(np.float32) / 255.0                       # [0..1]
        elif self.in_dtype == np.uint8:
            # typical uint8 quantization expects [0..255] with zero_point=0 or 128
            arr = arr.astype(np.uint8)
            # If a non-zero zero_point/scale is provided, map float->quant if needed.
            # For most uint8 models MoveNet takes raw 0..255 so this is sufficient.
        elif self.in_dtype == np.int8:
            # map [0..255] -> float32 [0..1] -> quant
            scale, zp = self.in_q if self.in_q else (1/255.0, 0)
            arr_f = (arr.astype(np.float32) / 255.0)                   # [0..1]
            arr_q = np.round(arr_f / (scale if scale != 0 else 1.0) + zp).astype(np.int8)
            arr = np.clip(arr_q, -128, 127)
        else:
            raise ValueError(f"Unsupported input dtype: {self.in_dtype}")

        # NHWC
        return arr[np.newaxis, ...]

    def infer(self, img_rgb: np.ndarray) -> List[Dict[str, float]]:
        inp = self._preprocess(img_rgb)
        self.interp.set_tensor(self.in_idx, inp)
        self.interp.invoke()
        out = self.interp.get_tensor(self.out_idx)

        # MoveNet outputs are usually float32 [1,1,17,3] (y, x, score)
        # but some converters use [1,17,3]. Handle both.
        kps = None
        if out.ndim == 4 and out.shape[0] == 1:
            kps = out[0, 0, :, :]
        elif out.ndim == 3 and out.shape[0] == 1:
            kps = out[0, :, :]
        else:
            raise ValueError(f"Unexpected output shape: {out.shape}")

        result = []
        for i, (yy, xx, sc) in enumerate(kps):
            result.append({
                "name": KEYPOINT_NAMES[i],
                "x": float(xx),
                "y": float(yy),
                "conf": float(sc),
            })
        return result

def load_gif_frames(path: str) -> Tuple[List[np.ndarray], List[float]]:
    img = Image.open(path)
    frames, durations = [], []
    default_ms = 100.0
    for frame in ImageSequence.Iterator(img):
        frames.append(np.array(frame.convert("RGB")))
        dur = frame.info.get("duration", default_ms)
        if dur is None or dur <= 0:
            dur = default_ms
        durations.append(float(dur))
    return frames, durations

def compute_timestamps(durations_ms: List[float]) -> Tuple[List[float], float]:
    t, acc = [], 0.0
    for d in durations_ms:
        t.append(acc / 1000.0)
        acc += d
    total_s = acc / 1000.0 if acc > 0 else 1e-6
    fps = (len(durations_ms) / total_s) if total_s > 0 else 0.0
    return t, fps

def normalize_phase(timestamps: List[float]) -> List[float]:
    if not timestamps:
        return []
    t0 = timestamps[0]
    t1 = timestamps[-1] if len(timestamps) > 1 else t0 + 1.0
    dur = max(1e-9, t1 - t0)
    return [(ti - t0) / dur for ti in timestamps]

def write_json_rule(out_path: str, src_gif: str, model_label: str,
                    fps: float, timestamps: List[float],
                    kp_per_frame: List[List[Dict[str, float]]]) -> None:
    data = {
        "source_gif": src_gif,
        "model": model_label,
        "backend": _TFLITE_BACKEND,
        "frames": len(kp_per_frame),
        "fps": float(fps),
        "timestamps": [float(t) for t in timestamps],
        "phase": normalize_phase(timestamps),
        "keypoints": kp_per_frame,
        "keypoint_names": KEYPOINT_NAMES,
        "schema": {"keypoints": "list of length F; each frame is list[17] of {name,x,y,conf} with x,y normalized (0..1)"},
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def write_csv(csv_path: str, timestamps: List[float],
              kp_per_frame: List[List[Dict[str, float]]]) -> None:
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("t,idx,name,x,y,conf\n")
        for fi, (t, kps) in enumerate(zip(timestamps, kp_per_frame)):
            for idx, k in enumerate(kps):
                f.write(f"{t:.6f},{idx},{k['name']},{k['x']:.6f},{k['y']:.6f},{k['conf']:.6f}\n")

def save_overlay_video(vis_path: str,
                       frames_rgb: List[np.ndarray],
                       kp_per_frame: List[List[Dict[str, float]]],
                       fps: float) -> None:
    if cv2 is None:
        print("OpenCV not installed; skip --vis.", file=sys.stderr)
        return
    os.makedirs(os.path.dirname(vis_path), exist_ok=True)
    H, W = frames_rgb[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    vw = cv2.VideoWriter(vis_path, fourcc, max(1.0, fps), (W, H))
    pairs = [
        ("left_shoulder","right_shoulder"), ("left_hip","right_hip"),
        ("left_shoulder","left_elbow"), ("left_elbow","left_wrist"),
        ("right_shoulder","right_elbow"), ("right_elbow","right_wrist"),
        ("left_hip","left_knee"), ("left_knee","left_ankle"),
        ("right_hip","right_knee"), ("right_knee","right_ankle"),
        ("left_shoulder","left_hip"), ("right_shoulder","right_hip"),
    ]
    name2idx = {n:i for i,n in enumerate(KEYPOINT_NAMES)}
    for frame, kps in zip(frames_rgb, kp_per_frame):
        bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        for a,b in pairs:
            ia, ib = name2idx.get(a), name2idx.get(b)
            if ia is None or ib is None: continue
            ka, kb = kps[ia], kps[ib]
            if ka["conf"] > 0.3 and kb["conf"] > 0.3:
                ax, ay = int(ka["x"]*W), int(ka["y"]*H)
                bx, by = int(kb["x"]*W), int(kb["y"]*H)
                cv2.line(bgr, (ax,ay), (bx,by), (0,255,0), 2)
        for k in kps:
            if k["conf"] > 0.3:
                x, y = int(k["x"]*W), int(k["y"]*H)
                cv2.circle(bgr, (x,y), 3, (0,128,255), -1)
        vw.write(bgr)
    vw.release()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gif", required=True, help="Path to guide GIF")
    ap.add_argument("--model", required=True, help="Path to MoveNet .tflite (thunder or lightning)")
    ap.add_argument("--out", required=True, help="Output rule JSON path")
    ap.add_argument("--csv", default=None, help="Optional CSV path")
    ap.add_argument("--vis", default=None, help="Optional MP4 path to save skeleton overlay")
    ap.add_argument("--min_conf", type=float, default=0.1, help="Min conf (kept in file even if lower)")
    args = ap.parse_args()

    frames, durations = load_gif_frames(args.gif)
    if not frames:
        print("No frames in GIF.", file=sys.stderr)
        sys.exit(2)

    timestamps, fps = compute_timestamps(durations)
    print(f"[GIF] frames={len(frames)} fps≈{fps:.2f} backend={_TFLITE_BACKEND}")

    mv = MoveNetTFLite(args.model)
    print(f"[MoveNet] {mv.spec.name} input={mv.spec.input_size}x{mv.spec.input_size} dtype={mv.in_dtype} quant={mv.in_q}")

    kp_all: List[List[Dict[str,float]]] = []
    for i, rgb in enumerate(frames):
        kps = mv.infer(rgb)
        kp_all.append(kps)

    write_json_rule(args.out, args.gif, mv.spec.name, fps, timestamps, kp_all)
    print(f"[OUT] JSON rule -> {args.out}")

    if args.csv:
        write_csv(args.csv, timestamps, kp_all)
        print(f"[OUT] CSV -> {args.csv}")

    if args.vis:
        if cv2 is None:
            print("OpenCV not available; cannot save --vis.", file=sys.stderr)
        else:
            save_overlay_video(args.vis, frames, kp_all, fps)
            print(f"[OUT] Overlay video -> {args.vis}")

    print("[Done]")

if __name__ == "__main__":
    main()
