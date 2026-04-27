# Emotion Watch

> macOS · local MediaPipe · OpenClaw skill · also works with other CLI agents

Emotion Watch is a small local monitor for people who do not reliably notice stress building in their own body.

It opens a webcam dashboard, reads facial tension with MediaPipe blendshapes, and writes an alert file when the stress score stays high for a few readings. OpenClaw, Claude Code, or any other CLI agent can pick up that file and remind the user to take a break.

The idea is simple: a job coach can sometimes see overload before the person feels it. Emotion Watch tries to keep that early-warning loop around when the coach is not there.

## demo

Video and screenshots are not uploaded yet.

The current build has a live dashboard:

- webcam preview on the left
- background pixelated for privacy, with only the face area visible
- stress score and signal bars on the right
- current alert message, streak count, and cooldown status

## why this exists

For some people with alexithymia, "I am getting overwhelmed" is not an obvious internal signal. The first signs may be physical: a locked jaw, tight brows, pressed lips, eye strain, or a face that suddenly goes very still.

A job coach can notice those signs and say something small before the situation gets worse. Not a lecture. More like: stand up, drink water, breathe, step away for two minutes.

That is the behavior this project is trying to copy.

## how it works

```text
python3 scripts/emotion_watch.py
    ↓
OpenCV reads the webcam
    ↓
MediaPipe FaceLandmarker extracts 52 blendshapes
    ↓
Emotion Watch calculates stress from four local signals
    ↓
If stress stays high for 3 readings, it writes /tmp/oc_emotion_alert.json
    ↓
OpenClaw or another CLI agent reads the message and nudges the user
```

The monitor samples every 2 seconds. It needs 3 high readings in a row before it triggers, so a single bad frame does not immediately cause an alert. After an alert, it waits 120 seconds before sending another one.

## local stress signals

No cloud vision model is used. The stress score comes from MediaPipe face blendshapes on the local machine.

| Signal | What it looks for | Weight |
|---|---|---:|
| brow furrow | brow down / inner brow tension | 35% |
| lip press | pressed mouth, stretched mouth, jaw tension | 25% |
| eye squint | narrowed eyes and nearby tension | 20% |
| expression freeze | jaw held shut plus overall tension lock | 20% |

There is also a floor rule. If one signal is very high, the final score should show that instead of burying it in the average.

## agent integration

Emotion Watch is packaged as an OpenClaw skill, but the handoff is just a JSON file in `/tmp`. That makes it easy to use with other CLI agents too.

Known use cases:

- OpenClaw launches the monitor and watches for alerts
- Claude Code watches `/tmp/oc_emotion_alert.json` during a long work session
- a shell script or cron job relays the alert somewhere else

Example alert:

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

The agent should read the `message`, say it naturally, and then remove the file so it does not repeat the same alert.

```bash
rm -f /tmp/oc_emotion_alert.json
```

## alert style

The messages avoid abstract emotion labels when possible. "You seem anxious" is not always useful to someone who cannot identify anxiety from the inside.

The app uses body language and concrete actions instead:

| Dominant signal | Message |
|---|---|
| brow furrow | "Hey, things feeling a bit heavy right now? Take a slow breath — drop your shoulders, unclench your jaw. You've got this." |
| expression freeze | "You've been deep in it for a while. That kind of focus is great, but your brain needs air too. Two minutes away — seriously, it helps." |
| lip press | "Pause for a sec. Breathe in slowly through your nose... and out. Do that three times. You'll feel the difference." |
| eye squint | "Your eyes have been working overtime. Pick something far away and just... look at it for 20 seconds. No screen, no task. Just rest." |
| very high stress | "Hey — I think you need a real break right now. Not a quick stretch, a proper one. Step away for 5 minutes. You'll come back clearer, I promise." |

## privacy

The webcam makes this sensitive, so the current build keeps the image path short.

- analysis runs locally with MediaPipe
- no cloud vision API
- no screenshots saved to disk
- frames are processed in memory
- the dashboard pixelates the background and reveals only the face area
- the only persistent output is the alert JSON, with score, signal values, timestamp, and message
- press `q` or close the window to stop

## requirements

- macOS
- built-in webcam or USB camera
- Python 3
- `mediapipe`
- `opencv-python`

Install dependencies:

```bash
pip3 install mediapipe opencv-python
```

The MediaPipe task model is included at:

```text
scripts/face_landmarker_v2_with_blendshapes.task
```

## run it

```bash
python3 scripts/emotion_watch.py
```

A dashboard window opens. Press `q` or close it to stop.

## OpenClaw usage

Install this repository as an OpenClaw skill, then have OpenClaw launch the monitor:

```bash
python3 {baseDir}/scripts/emotion_watch.py &
```

Have the agent check for alerts every 30 to 60 seconds:

```bash
cat /tmp/oc_emotion_alert.json 2>/dev/null
```

If an alert exists, relay the `message` field and delete the file.

## project structure

```text
emotion-watch-skill/
├── SKILL.md
├── DESIGN.md
├── _meta.json
├── scripts/
│   ├── emotion_watch.py
│   ├── capture.sh
│   └── face_landmarker_v2_with_blendshapes.task
├── LICENSE
└── README.md
```

## license

MIT
