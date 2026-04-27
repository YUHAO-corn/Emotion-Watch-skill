# Emotion Watch design notes

Emotion Watch is a local facial stress monitor that can be driven by OpenClaw or another CLI agent.

The monitor itself is a Python script. It opens a webcam dashboard, runs MediaPipe FaceLandmarker locally, calculates a stress score from face blendshapes, and writes an alert file when stress stays high. The agent side is deliberately boring: read a JSON file, say the message, delete the file.

## runtime shape

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
      OpenClaw / Claude Code / CLI agent
```

There is no MiniMax call in the current build. No cloud vision call. No image upload.

## dashboard

The dashboard has a camera area and a signal panel.

The camera area is intentionally privacy-heavy: the background is pixelated and the face area is shown through a soft ellipse. This also makes for a clearer demo, because viewers can see that the app cares about the face signal, not the room.

The panel shows:

- stress score
- brow, lip, eye, and freeze signals
- current streak
- cooldown status
- active alert message

## stress formula

Every 2 seconds, the monitor runs FaceLandmarker and reads the face blendshapes.

| Signal | Inputs | Weight |
|---|---|---:|
| brow_furrow | `browDownLeft`, `browDownRight`, `browInnerUp` | 35% |
| lip_press | `mouthPressLeft`, `mouthPressRight`, `mouthStretchLeft`, `mouthStretchRight`, `jawForward` | 25% |
| eye_squint | `eyeSquintLeft`, `eyeSquintRight`, `noseSneerLeft`, `noseSneerRight` | 20% |
| expression_freeze | jaw held shut plus average tension | 20% |

Score:

```text
stress = 100 * max(weighted_average, max_signal * 0.65)
```

The second term is a floor. If one signal spikes hard, the score should not look harmless just because the other signals are quiet.

## trigger rules

- threshold: `stress_score >= 60`
- required streak: 3 readings
- sample interval: 2 seconds
- approximate trigger delay: 6 seconds
- cooldown: 120 seconds

No face means no alert. The streak resets.

## alert file

Path:

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

The agent should relay `message`, not the raw JSON. After that, remove the file.

## message selection

If `stress_score >= 80`, use the high-stress message.

Otherwise, pick the message from the dominant signal:

- `brow_furrow`
- `expression_freeze`
- `lip_press`
- `eye_squint`

If no signal dominates, pick from the default pool of short body-based actions: water, stretch, walk, breathe, look away from the screen.

## privacy model

- frames are analyzed in memory
- no screenshots are written to disk
- no cloud API is called
- background is pixelated in the dashboard
- only the alert JSON persists, and it has no image data

## platform

The current build targets macOS. MacBooks have a built-in camera and predictable OpenCV access. USB cameras should work, but the hackathon version was tested for Mac first.

## files

```text
SKILL.md                                      OpenClaw skill instructions
DESIGN.md                                     design notes
_meta.json                                    OpenClaw metadata
scripts/emotion_watch.py                      local monitor
scripts/face_landmarker_v2_with_blendshapes.task  MediaPipe model
scripts/capture.sh                            simple capture helper, kept for experiments
```
