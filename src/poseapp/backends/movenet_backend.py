# src/poseapp/backends/movenet_backend.py
import time
from typing import Dict, Any, List, Tuple
import numpy as np
import cv2
import os
from ..utils.resources import resource_path

try:
    # Prefer lightweight TFLite runtime if available
    from tflite_runtime.interpreter import Interpreter
except Exception:
    # Fallback to TensorFlow's full interpreter if not
    from tensorflow.lite.python.interpreter import Interpreter

from .base import PoseBackend, Keypoint

# MoveNet COCO keypoint ordering (17 landmarks)
COCO_KEYPOINTS = [
    "nose","left_eye","right_eye","left_ear","right_ear",
    "left_shoulder","right_shoulder","left_elbow","right_elbow",
    "left_wrist","right_wrist","left_hip","right_hip",
    "left_knee","right_knee","left_ankle","right_ankle"
]

class MoveNetBackend(PoseBackend):
    def __init__(self, model_path: str, variant: str = "lightning"):
        # Load the TensorFlow Lite MoveNet model
        self.model_path = model_path
        self.variant = variant

         # Resolve whether running from source or PyInstaller (_MEIPASS)
        resolved_model = resource_path(model_path)
        if not os.path.exists(resolved_model):
            # helpful error to see the *resolved* path
            raise FileNotFoundError(f"MoveNet model not found: {resolved_model}")

        self.interpreter = Interpreter(model_path=resolved_model, num_threads=4)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        
       
        
        # Extract input tensor details
        in0 = self.input_details[0]
        self.in_h = int(in0["shape"][1])  # model input height
        self.in_w = int(in0["shape"][2])  # model input width
        self.input_dtype = in0["dtype"]   # could be uint8, int8, or float32
        self.input_quant = in0.get("quantization", (0.0, 0))  # (scale, zero_point)
        self._smoothed_fps = None  # track smoothed FPS estimate

        # Output tensor index (MoveNet: [1,1,17,3])
        self.out_idx = self.output_details[0]["index"]

    def name(self) -> str:
        # Return backend label (e.g., MoveNet-lightning)
        return f"MoveNet-{self.variant}"

    def _preprocess(self, frame_bgr) -> np.ndarray:
        # Convert input image to RGB and resize for model
        img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (self.in_w, self.in_h), interpolation=cv2.INTER_LINEAR)

        # Match model input type
        if self.input_dtype == np.uint8:
            # Quantized uint8 → direct use (0–255)
            img = img.astype(np.uint8)
        elif self.input_dtype == np.int8:
            # For symmetric quantization models
            scale, zero_point = self.input_quant if self.input_quant else (1.0, 0)
            u8 = img.astype(np.uint8)
            q = np.round(u8.astype(np.float32) / max(scale, 1e-9) + float(zero_point))
            q = np.clip(q, -128, 127).astype(np.int8)
            img = q
        else:
            # Default: float32 input (MoveNet accepts [0..255] range)
            img = img.astype(np.float32)

        return np.expand_dims(img, axis=0)  # shape → [1,H,W,3]

    def infer(self, frame_bgr) -> Tuple[List[Keypoint], Dict[str, Any]]:
        # Run inference and return keypoints + metadata
        t0 = time.time()
        inp = self._preprocess(frame_bgr)
        self.interpreter.set_tensor(self.input_details[0]["index"], inp)
        self.interpreter.invoke()
        out = self.interpreter.get_tensor(self.out_idx)  # [1,1,17,3]
        out = out[0, 0]  # reshape to [17,3] (y, x, conf)

        kps: List[Keypoint] = []
        for i, (y, x, c) in enumerate(out):
            # Convert each keypoint to dictionary format
            kps.append({
                "name": COCO_KEYPOINTS[i],
                "x": float(np.clip(x, 0, 1)),  # normalized coords
                "y": float(np.clip(y, 0, 1)),
                "z": None,
                "conf": float(np.clip(c, 0, 1)),  # confidence score
            })

        # Compute instantaneous and smoothed FPS
        dt = time.time() - t0
        inst_fps = 1.0 / max(dt, 1e-6)
        self._smoothed_fps = inst_fps if self._smoothed_fps is None else 0.2 * inst_fps + 0.8 * self._smoothed_fps
        return kps, {"fps_hint": float(self._smoothed_fps or inst_fps)}

    def close(self) -> None:
        # Placeholder for backend cleanup
        pass
