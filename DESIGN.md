# Emotion Watch — design doc

OpenClaw skill / local CLI-agent companion / hackathon build

## what it does

Emotion Watch is a local facial stress-signal monitor.

It runs a Python dashboard, reads webcam frames, extracts MediaPipe FaceLandmarker blendshapes, and computes a stress score from facial tension signals. When stress stays high for several readings, it writes a JSON alert to `/tmp/oc_emotion_alert.json`.

OpenClaw, Claude Code, or any other CLI agent can watch that file and turn the alert into a warm reminder in chat.

The target user is someone with alexithymia. They may not notice their own emotional load rising, but their face can show early physical signs. Emotion Watch acts like a lightweight electronic job coach.

## architecture

```text
scripts/emotion_watch.py
    │
    ├─ OpenCV camera capture
    ├─ MediaPipe FaceLandmarker task model
    ├─ 52 blendshapes
    ├─ local stress formula
    ├─ OpenCV dashboard
    └─ /tmp/oc_emotion_alert.json
             │
             ▼
      OpenClaw / CLI agent relays message
```

No MiniMax. No cloud vision. No image upload.

## dashboard

The dashboard has two parts:

- camera panel: mosaic background with an elliptical face reveal
- analysis panel: score, signal bars, streak, cooldown, and alert message

The mosaic is not just decoration. It makes the privacy model visible in the demo: the app needs the face, not the room.

## stress formula

Every 2 seconds, the monitor runs FaceLandmarker and reads blendshapes.

Signals:

| Signal | Blendshapes / calculation | Weight |
|---|---|---:|
| brow_furrow | `browDownLeft`, `browDownRight`, `browInnerUp` | 35% |
| lip_press | `mouthPressLeft`, `mouthPressRight`, `mouthStretchLeft`, `mouthStretchRight`, `jawForward` | 25% |
| eye_squint | `eyeSquintLeft`, `eyeSquintRight`, `noseSneerLeft`, `noseSneerRight` | 20% |
| expression_freeze | jaw held shut plus average tension | 20% |

Weighted score:

```text
stress = 100 * max(weighted_average, max_signal * 0.65)
```

The floor rule prevents one strong signal from disappearing inside the average.

## trigger rules

- threshold: `stress_score >= 60`
- required streak: 3 consecutive readings
- sample interval: 2 seconds
- trigger delay: about 6 seconds
- cooldown: 120 seconds

If no face is detected, the streak resets and no alert is written.

## alert output

Alert file path:

```text
/tmp/oc_emotion_alert.json
```

Example:

```json
{
  "timestamp": "2026-04-27 14:30:00",
  "stress_score": 72,
  "signals": {
    "brow_furrow": 0.8,
    "lip_press": 0.3,
    "eye_squint": 0.2,
    "expression_freeze": 0.5
  },
  "message": "Hey, things feeling a bit heavy right now? Take a slow breath — drop your shoulders, unclench your jaw. You've got this."
}
```

Agents should relay `message`, not the raw JSON, then remove the file.

## message selection

If `stress_score >= 80`, the high-stress message overrides everything.

Otherwise, the message is selected by dominant signal:

- brow_furrow
- expression_freeze
- lip_press
- eye_squint

If no signal dominates, the monitor picks from a default pool of body-based actions: water, stretch, walk, breathing, looking away from the screen.

## privacy model

- frames are analyzed in memory
- no screenshots are written to disk
- no cloud API is called
- background is pixelated in the dashboard
- only the JSON alert persists, and it contains no image data

## platform

Current build targets macOS because MacBooks have a predictable built-in webcam setup and OpenCV camera access is straightforward. USB cameras should work too.

## files

```text
SKILL.md                                      OpenClaw skill instructions
DESIGN.md                                     this document
_meta.json                                    OpenClaw metadata
scripts/emotion_watch.py                      main local monitor
scripts/face_landmarker_v2_with_blendshapes.task  MediaPipe model
scripts/capture.sh                            legacy/simple capture helper
```
