# Emotion Watch

> macOS · 100% local · MediaPipe blendshapes · Works with OpenClaw, Claude Code, and other CLI agents

Emotion Watch is a local stress-signal monitor for people with alexithymia: people who may not notice their own stress building until it is too late.

It opens a small webcam dashboard, reads facial tension through MediaPipe blendshapes, and writes a gentle alert to `/tmp/oc_emotion_alert.json` when sustained stress is detected. Any agent or CLI can watch that file and relay the message back to the user.

It does not "surveil" you. It quietly observes the signals you may not be able to feel yourself.

> Your face is always talking. You just can't hear it.
> Emotion Watch listens for you.

## demo

Video and screenshots are coming soon.

<!-- TODO: add demo video/GIF/screenshots -->

The current app already includes a live visual dashboard:

- left: webcam preview with mosaic privacy; the background is pixelated and only the face area is revealed
- right: real-time stress score, signal bars, streak counter, cooldown, and active alert message

## who this is for

Some people with alexithymia do not get the internal signal that says "I need a break." Their face may show the signs first: brow tension, lip pressing, eye strain, a frozen expression. A human job coach can notice those signs and gently intervene before a workplace meltdown.

But job coaches are not always present. Emotion Watch is a lightweight electronic job coach that keeps the early warning loop running when the person is working independently.

## how it works

```text
Python monitor starts
    ↓
OpenCV reads webcam frames
    ↓
MediaPipe FaceLandmarker extracts 52 face blendshapes
    ↓
Emotion Watch computes a stress score from four signals
    ↓
If stress ≥ 60 for 3 consecutive readings, write an alert JSON
    ↓
OpenClaw / Claude Code / any CLI agent reads the alert and reminds the user
```

The monitor samples every 2 seconds. It triggers only after 3 consecutive high readings, roughly 6 seconds, then enters a 120-second cooldown.

## local stress signals

Emotion Watch does not use a cloud vision model. It uses MediaPipe face blendshapes locally.

| Signal | What it looks for | Weight |
|---|---|---:|
| brow furrow | brow down / inner brow tension | 35% |
| lip press | pressed mouth, stretched mouth, jaw tension | 25% |
| eye squint | narrowed eyes and nearby tension | 20% |
| expression freeze | jaw held shut plus overall tension lock | 20% |

There is also a floor rule: if one signal is very high, the final stress score is not allowed to hide it inside the weighted average.

## agent integration

Emotion Watch is built as an OpenClaw skill, but the runtime boundary is intentionally simple: alerts are plain JSON files in `/tmp`.

That means it can work with:

- OpenClaw
- Claude Code
- other local CLI agents
- shell scripts or cron jobs
- any process that can read `/tmp/oc_emotion_alert.json`

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

The agent should not dump the JSON. It should relay the `message` warmly, then delete the alert file so the same message is not repeated.

## alert style

The messages avoid abstract emotion labels where possible. "You seem anxious" is not very useful to someone who cannot identify anxiety from the inside.

Emotion Watch uses body-based language and concrete actions:

| Dominant signal | Message |
|---|---|
| brow furrow | "Hey, things feeling a bit heavy right now? Take a slow breath — drop your shoulders, unclench your jaw. You've got this." |
| expression freeze | "You've been deep in it for a while. That kind of focus is great, but your brain needs air too. Two minutes away — seriously, it helps." |
| lip press | "Pause for a sec. Breathe in slowly through your nose... and out. Do that three times. You'll feel the difference." |
| eye squint | "Your eyes have been working overtime. Pick something far away and just... look at it for 20 seconds. No screen, no task. Just rest." |
| very high stress | "Hey — I think you need a real break right now. Not a quick stretch, a proper one. Step away for 5 minutes. You'll come back clearer, I promise." |

## privacy

Privacy is the point of the implementation.

- 100% local inference. MediaPipe runs on the machine.
- No cloud vision API. No image upload.
- No images saved. Frames are processed in memory.
- Mosaic privacy in the dashboard: the background is pixelated, face area only is revealed.
- The only persistent output is `/tmp/oc_emotion_alert.json`, which contains a timestamp, score, signal values, and a message.
- Close the dashboard window or press `q` to stop.

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

The MediaPipe task model is included in `scripts/face_landmarker_v2_with_blendshapes.task`.

## run it

Launch the local monitor:

```bash
python3 scripts/emotion_watch.py
```

The dashboard opens immediately. Press `q` or close the window to stop.

## OpenClaw usage

Install this repository as an OpenClaw skill, then ask OpenClaw to launch the monitor:

```bash
python3 {baseDir}/scripts/emotion_watch.py &
```

Then have OpenClaw poll the alert file every 30-60 seconds:

```bash
cat /tmp/oc_emotion_alert.json 2>/dev/null
```

When an alert appears, OpenClaw should relay the message and delete the file:

```bash
rm -f /tmp/oc_emotion_alert.json
```

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
