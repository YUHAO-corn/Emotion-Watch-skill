#!/usr/bin/env python3
"""
Emotion Watch — Silent stress monitor with live visualization.
Uses MediaPipe FaceLandmarker (tasks API) with blendshapes, 100% local.
"""

import cv2
import mediapipe as mp
import numpy as np
import time
import json
import os
import random
from collections import deque
from mediapipe.tasks.python import vision, BaseOptions
from mediapipe import Image, ImageFormat

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(SCRIPT_DIR, "face_landmarker_v2_with_blendshapes.task")

STRESS_THRESHOLD = 60
COOLDOWN_SECONDS = 120
CONSECUTIVE_REQUIRED = 3
CAPTURE_INTERVAL = 2
WINDOW_NAME = "Emotion Watch"
PANEL_W = 360
CAM_W = 480
CAM_H = 480
TOTAL_W = CAM_W + PANEL_W

MESSAGES = {
    "brow_furrow": "Your forehead's been working hard. Try releasing your jaw and letting your shoulders drop.",
    "expression_freeze": "You've gone really still — that can be a sign of overload. Step away for just 2 minutes.",
    "lip_press": "There's some tension around your mouth. Three slow breaths — in through nose, out through mouth.",
    "eye_squint": "Your eyes look strained. Look at something 20 feet away for 20 seconds.",
}
HIGH_STRESS_MSG = "Hey — your face is showing something your mind might not have caught yet. Take a real break."
DEFAULT_POOL = [
    "Quick check-in: grab some water and look away from the screen.",
    "Your body's picking up stress before you are. Stand up and stretch.",
    "Take a breath. Look at something far away for one minute.",
    "Small pause — how are you actually doing right now?",
    "You've been locked in for a while. Five minutes away will pay back double.",
]

BLENDSHAPE_MAP = {}


def find_builtin_camera():
    """Try camera indices 0-4, prefer the one that isn't the iPhone Continuity Camera."""
    for idx in range(5):
        cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None and frame.shape[0] > 0:
                h, w = frame.shape[:2]
                print(f"Camera {idx}: {w}x{h} — OK")
                cap.release()
                return idx
            cap.release()
    return 0


def build_blendshape_map(blendshapes):
    global BLENDSHAPE_MAP
    if not BLENDSHAPE_MAP:
        for i, bs in enumerate(blendshapes):
            BLENDSHAPE_MAP[bs.category_name] = i


def get_bs(blendshapes, name):
    idx = BLENDSHAPE_MAP.get(name)
    if idx is not None and idx < len(blendshapes):
        return blendshapes[idx].score
    return 0.0


def compute_stress(blendshapes):
    build_blendshape_map(blendshapes)

    brow_down_l = get_bs(blendshapes, "browDownLeft")
    brow_down_r = get_bs(blendshapes, "browDownRight")
    mouth_press_l = get_bs(blendshapes, "mouthPressLeft")
    mouth_press_r = get_bs(blendshapes, "mouthPressRight")
    eye_squint_l = get_bs(blendshapes, "eyeSquintLeft")
    eye_squint_r = get_bs(blendshapes, "eyeSquintRight")
    jaw_open = get_bs(blendshapes, "jawOpen")

    brow_furrow = min(1.0, (brow_down_l + brow_down_r) / 2.0 * 2.5)
    lip_press = min(1.0, (mouth_press_l + mouth_press_r) / 2.0 * 2.5)
    eye_squint = min(1.0, (eye_squint_l + eye_squint_r) / 2.0 * 2.5)
    jaw_clench = max(0, 1.0 - jaw_open * 5) if jaw_open < 0.1 else 0.0
    expression_freeze = min(1.0, lip_press * 0.3 + brow_furrow * 0.3 + (1.0 - eye_squint) * 0.1 + jaw_clench * 0.3)

    stress_score = int(100 * (0.50 * brow_furrow + 0.20 * lip_press + 0.10 * eye_squint + 0.20 * expression_freeze))
    stress_score = min(100, max(0, stress_score))

    signals = {
        "brow_furrow": round(brow_furrow, 2),
        "lip_press": round(lip_press, 2),
        "eye_squint": round(eye_squint, 2),
        "expression_freeze": round(expression_freeze, 2),
    }
    dominant = max(signals, key=signals.get)
    if signals[dominant] < 0.3:
        dominant = "none"

    return stress_score, signals, dominant


def select_message(stress_score, dominant):
    if stress_score >= 80:
        return HIGH_STRESS_MSG
    if dominant in MESSAGES:
        return MESSAGES[dominant]
    return random.choice(DEFAULT_POOL)


def draw_signal_bar(panel, x, y, w, val, color):
    bar_h = 10
    cv2.rectangle(panel, (x, y), (x + w, y + bar_h), (60, 60, 60), -1)
    fill = int(w * min(1.0, val))
    if fill > 0:
        cv2.rectangle(panel, (x, y), (x + fill, y + bar_h), color, -1)
    return y + bar_h + 6


def stress_color(score):
    if score >= 80:
        return (70, 70, 255)
    elif score >= 60:
        return (60, 180, 255)
    elif score >= 40:
        return (60, 230, 230)
    return (80, 220, 120)


def wrap_text(text, max_chars=38):
    words = text.split()
    lines = []
    line = ""
    for word in words:
        test = line + " " + word if line else word
        if len(test) > max_chars:
            if line:
                lines.append(line)
            line = word
        else:
            line = test
    if line:
        lines.append(line)
    return lines


def build_panel(h, stress_score, signals, dominant, message, has_face, consecutive, cooldown_remaining, snapshot):
    panel = np.zeros((h, PANEL_W, 3), dtype=np.uint8)
    panel[:] = (25, 25, 30)

    x0 = 20
    y = 40

    # Title
    cv2.putText(panel, "EMOTION WATCH", (x0, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 220, 255), 2)
    y += 12

    # Divider
    y += 10
    cv2.line(panel, (x0, y), (PANEL_W - 20, y), (60, 60, 60), 1)
    y += 20

    # Status dot
    status_color = (80, 220, 120) if has_face else (70, 70, 255)
    status_text = "Face Detected" if has_face else "No Face Detected"
    cv2.circle(panel, (x0 + 6, y - 5), 7, status_color, -1)
    cv2.putText(panel, status_text, (x0 + 22, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, status_color, 1)
    y += 30

    # Snapshot thumbnail (last analyzed frame)
    if snapshot is not None:
        thumb_h = 120
        thumb_w = 160
        thumb = cv2.resize(snapshot, (thumb_w, thumb_h))
        ty = y
        tx = (PANEL_W - thumb_w) // 2
        # Border color based on stress
        border_color = stress_color(stress_score) if has_face else (60, 60, 60)
        cv2.rectangle(panel, (tx - 2, ty - 2), (tx + thumb_w + 2, ty + thumb_h + 2), border_color, 2)
        panel[ty:ty + thumb_h, tx:tx + thumb_w] = thumb
        cv2.putText(panel, "Last Analyzed Frame", (tx, ty + thumb_h + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (120, 120, 120), 1)
        y += thumb_h + 30

    if not has_face:
        cv2.putText(panel, "Waiting for face...", (x0, y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)
        return panel

    # Stress score
    cv2.putText(panel, "STRESS SCORE", (x0, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)
    y += 8

    # Big number
    sc = stress_color(stress_score)
    cv2.putText(panel, str(stress_score), (x0, y + 42), cv2.FONT_HERSHEY_SIMPLEX, 1.6, sc, 3)
    cv2.putText(panel, "/ 100", (x0 + 75, y + 42), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)
    y += 52

    # Stress bar
    bar_w = PANEL_W - 40
    bar_h = 14
    cv2.rectangle(panel, (x0, y), (x0 + bar_w, y + bar_h), (50, 50, 50), -1)
    fill_w = int(bar_w * stress_score / 100)
    if fill_w > 0:
        cv2.rectangle(panel, (x0, y), (x0 + fill_w, y + bar_h), sc, -1)
    y += bar_h + 20

    # Divider
    cv2.line(panel, (x0, y), (PANEL_W - 20, y), (60, 60, 60), 1)
    y += 15

    # Signal breakdown
    cv2.putText(panel, "SIGNAL BREAKDOWN", (x0, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
    y += 18

    signal_labels = {
        "brow_furrow": "Brow Furrow",
        "lip_press": "Lip Press",
        "eye_squint": "Eye Squint",
        "expression_freeze": "Expr. Freeze",
    }
    bar_w = PANEL_W - 130
    for key, label in signal_labels.items():
        val = signals.get(key, 0)
        is_dom = (key == dominant)
        color = (100, 220, 255) if is_dom else (140, 140, 140)
        marker = " *" if is_dom else ""
        cv2.putText(panel, f"{label}{marker}", (x0, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        cv2.putText(panel, f"{val:.2f}", (PANEL_W - 60, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        y += 5
        y = draw_signal_bar(panel, x0, y, bar_w, val, color)
        y += 4

    # Consecutive + cooldown
    y += 5
    cv2.line(panel, (x0, y), (PANEL_W - 20, y), (60, 60, 60), 1)
    y += 15
    cv2.putText(panel, f"Consecutive: {consecutive}/{CONSECUTIVE_REQUIRED}", (x0, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (140, 140, 140), 1)
    y += 22
    if cooldown_remaining > 0:
        cv2.putText(panel, f"Cooldown: {cooldown_remaining}s", (x0, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (60, 180, 255), 1)
        y += 22

    # Alert message
    if message:
        y += 5
        cv2.line(panel, (x0, y), (PANEL_W - 20, y), (70, 70, 255), 1)
        y += 18
        cv2.putText(panel, "ALERT", (x0, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (70, 70, 255), 2)
        y += 22
        for line in wrap_text(message):
            cv2.putText(panel, line, (x0, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 255), 1)
            y += 18

    return panel


def write_alert(message, stress_score, signals):
    alert = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "stress_score": stress_score,
        "signals": signals,
        "message": message,
    }
    with open("/tmp/oc_emotion_alert.json", "w") as f:
        json.dump(alert, f, indent=2)
    print(f"\n{'='*50}")
    print(f"STRESS ALERT (score: {stress_score})")
    print(f"Message: {message}")
    print(f"Signals: {json.dumps(signals)}")
    print(f"{'='*50}\n")


def main():
    print("Scanning cameras...")
    cam_idx = find_builtin_camera()
    print(f"Using camera index: {cam_idx}")

    options = vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        output_face_blendshapes=True,
        output_facial_transformation_matrixes=False,
        num_faces=1,
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        running_mode=vision.RunningMode.IMAGE,
    )
    landmarker = vision.FaceLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(cam_idx)
    if not cap.isOpened():
        print("ERROR: Cannot open camera")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    consecutive = 0
    last_alert_time = 0
    current_message = None
    message_display_until = 0
    stress_history = deque(maxlen=5)
    last_analysis_time = 0
    last_signals = {"brow_furrow": 0, "lip_press": 0, "eye_squint": 0, "expression_freeze": 0}
    last_dominant = "none"
    last_has_face = False
    last_stress = 0
    snapshot = None

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_AUTOSIZE)
    print("Emotion Watch started. Press 'q' or close window to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        now = time.time()

        # Resize camera feed to fixed size
        cam_frame = cv2.resize(frame, (CAM_W, CAM_H))

        if now - last_analysis_time >= CAPTURE_INTERVAL:
            last_analysis_time = now
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = Image(image_format=ImageFormat.SRGB, data=rgb)
            result = landmarker.detect(mp_image)

            if result.face_blendshapes and len(result.face_blendshapes) > 0:
                last_has_face = True
                snapshot = frame.copy()
                blendshapes = result.face_blendshapes[0]
                stress_score, signals, dominant = compute_stress(blendshapes)
                last_stress = stress_score
                last_signals = signals
                last_dominant = dominant
                stress_history.append(stress_score)

                avg_stress = int(sum(stress_history) / len(stress_history))
                cooldown_remaining = max(0, int(COOLDOWN_SECONDS - (now - last_alert_time)))

                if avg_stress >= STRESS_THRESHOLD and cooldown_remaining == 0:
                    consecutive += 1
                    if consecutive >= CONSECUTIVE_REQUIRED:
                        current_message = select_message(avg_stress, dominant)
                        message_display_until = now + 10
                        last_alert_time = now
                        consecutive = 0
                        write_alert(current_message, avg_stress, signals)
                else:
                    if avg_stress < STRESS_THRESHOLD:
                        consecutive = 0
            else:
                last_has_face = False
                stress_history.clear()
                consecutive = 0

        if now > message_display_until:
            current_message = None

        cooldown_remaining = max(0, int(COOLDOWN_SECONDS - (now - last_alert_time)))
        avg_stress = int(sum(stress_history) / len(stress_history)) if stress_history else 0

        # Build side panel
        panel = build_panel(
            CAM_H, avg_stress, last_signals, last_dominant,
            current_message, last_has_face, consecutive, cooldown_remaining, snapshot
        )

        # Combine: camera left, panel right
        combined = np.hstack([cam_frame, panel])

        cv2.imshow(WINDOW_NAME, combined)

        # Check for 'q' key or window close
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        try:
            if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                break
        except cv2.error:
            break

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()
    print("Emotion Watch stopped.")


if __name__ == "__main__":
    main()
