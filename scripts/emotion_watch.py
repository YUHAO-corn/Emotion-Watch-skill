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


def draw_dashboard(frame, stress_score, signals, dominant, message, has_face, consecutive, cooldown_remaining):
    h, w = frame.shape[:2]
    overlay = frame.copy()

    panel_w = 320
    cv2.rectangle(overlay, (w - panel_w, 0), (w, h), (30, 30, 30), -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

    x0 = w - panel_w + 15
    y = 35

    cv2.putText(frame, "EMOTION WATCH", (x0, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 220, 255), 2)
    y += 15

    y += 30
    status_color = (0, 255, 0) if has_face else (0, 0, 255)
    status_text = "Face Detected" if has_face else "No Face"
    cv2.circle(frame, (x0 + 5, y - 5), 6, status_color, -1)
    cv2.putText(frame, status_text, (x0 + 20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, status_color, 1)

    if not has_face:
        return frame

    y += 40
    cv2.putText(frame, f"Stress Score: {stress_score}", (x0, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    y += 15
    bar_w = panel_w - 40
    bar_h = 20
    cv2.rectangle(frame, (x0, y), (x0 + bar_w, y + bar_h), (60, 60, 60), -1)
    fill_w = int(bar_w * stress_score / 100)
    if stress_score >= 80:
        bar_color = (0, 0, 255)
    elif stress_score >= 60:
        bar_color = (0, 165, 255)
    elif stress_score >= 40:
        bar_color = (0, 255, 255)
    else:
        bar_color = (0, 255, 0)
    cv2.rectangle(frame, (x0, y), (x0 + fill_w, y + bar_h), bar_color, -1)

    y += 45
    for name, val in signals.items():
        label = name.replace("_", " ").title()
        is_dominant = (name == dominant)
        color = (100, 220, 255) if is_dominant else (180, 180, 180)
        cv2.putText(frame, f"{label}: {val:.2f}", (x0, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
        y += 18
        sw = int((panel_w - 40) * val)
        cv2.rectangle(frame, (x0, y), (x0 + sw, y + 8), color, -1)
        y += 20

    y += 15
    cv2.putText(frame, f"Consecutive: {consecutive}/{CONSECUTIVE_REQUIRED}", (x0, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

    y += 25
    if cooldown_remaining > 0:
        cv2.putText(frame, f"Cooldown: {cooldown_remaining}s", (x0, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 165, 255), 1)

    if message:
        y += 35
        cv2.putText(frame, "ALERT:", (x0, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        y += 22
        words = message.split()
        line = ""
        for word in words:
            test = line + " " + word if line else word
            if len(test) > 35:
                cv2.putText(frame, line, (x0, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 255), 1)
                y += 18
                line = word
            else:
                line = test
        if line:
            cv2.putText(frame, line, (x0, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 255), 1)

    return frame


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

    cap = cv2.VideoCapture(0)
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

    print("Emotion Watch started. Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        now = time.time()

        if now - last_analysis_time >= CAPTURE_INTERVAL:
            last_analysis_time = now
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = Image(image_format=ImageFormat.SRGB, data=rgb)
            result = landmarker.detect(mp_image)

            if result.face_blendshapes and len(result.face_blendshapes) > 0:
                last_has_face = True
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

        frame = draw_dashboard(frame, avg_stress, last_signals, last_dominant, current_message, last_has_face, consecutive, cooldown_remaining)

        cv2.imshow(WINDOW_NAME, frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()
    print("Emotion Watch stopped.")


if __name__ == "__main__":
    main()
