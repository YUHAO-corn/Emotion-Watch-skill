---
name: emotion-watch
description: Silent background stress monitor with live dashboard. Uses MediaPipe FaceMesh blendshapes to detect facial tension (brow furrow, lip press, eye squint, expression freeze) locally — no images leave your machine. Shows a real-time visualization window and sends caring nudges when sustained stress is detected.
homepage: https://github.com/godcorn/emotion-watch
metadata: {"openclaw": {"emoji": "🫂", "requires": {"pip": ["mediapipe", "opencv-python"], "bin": ["python3"]}, "primaryEnv": ""}}
---

# Emotion Watch

A silent stress guardian that monitors your face locally and nudges you before you hit a breaking point. Built for people with alexithymia — watches your face so you don't have to.

## Quick Start

```bash
python3 ~/.openclaw/workspace/skills/emotion-watch/scripts/emotion_watch.py
```

Press `q` to quit.

## What It Does

- Opens webcam with a live dashboard overlay
- Runs MediaPipe FaceMesh blendshapes every 2 seconds (100% local, no network)
- Computes stress score from 4 signals: brow furrow, lip press, eye squint, expression freeze
- When stress stays above threshold for ~6 seconds, sends a caring nudge
- Writes alert JSON to `/tmp/oc_emotion_alert.json` for OpenClaw to pick up

## Dashboard Shows

- Live camera feed with face mesh
- Stress score bar (green → yellow → orange → red)
- Individual signal bars (brow, lip, eye, freeze)
- Consecutive high-reading counter
- Cooldown timer after an alert
- Alert message when triggered

## Stress Formula

```
stress = 100 × (50% brow_furrow + 20% lip_press + 10% eye_squint + 20% expression_freeze)
```

Trigger: score >= 60 sustained for 3 consecutive readings (~6 seconds), then 120s cooldown.

## Privacy

- All analysis runs locally via MediaPipe — zero network calls
- No frames saved to disk
- No images sent anywhere
- Camera feed only exists in memory while the window is open

## Integration with OpenClaw

When stress is detected, the script writes `/tmp/oc_emotion_alert.json`:

```json
{
  "timestamp": "2026-04-27 14:30:00",
  "stress_score": 72,
  "signals": {"brow_furrow": 0.8, "lip_press": 0.3, "eye_squint": 0.2, "expression_freeze": 0.5},
  "message": "Your forehead's been working hard. Try releasing your jaw."
}
```

OpenClaw can watch this file and relay the message to the user through any channel.

## One-Shot Check

If the user asks "how am I doing?" or "check my stress" — run the script, read the latest `/tmp/oc_emotion_alert.json`, and share the result conversationally.
