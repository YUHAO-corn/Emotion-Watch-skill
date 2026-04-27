---
name: emotion-watch
description: Silent background stress monitor. Launches a local webcam dashboard that analyzes facial tension via MediaPipe blendshapes — 100% offline, no images leave the machine. When sustained stress is detected, writes an alert to /tmp/oc_emotion_alert.json. Any agent (OpenClaw, Claude Code, CLI agents) can watch this file and relay caring nudges to the user.
homepage: https://github.com/godcorn/emotion-watch
metadata: {"openclaw": {"emoji": "🫂", "requires": {"pip": ["mediapipe", "opencv-python"], "bin": ["python3"]}, "primaryEnv": ""}}
---

# Emotion Watch

A silent stress guardian. It watches your face so you don't have to.

Built for people with alexithymia (difficulty perceiving their own emotional state) — the same group that job coaches support in the workplace. When the coach isn't there, this skill fills the gap.

## How It Works

A Python script runs in the background with a live dashboard window:

- **Left side**: webcam feed with mosaic privacy (background pixelated, only face revealed via elliptical mask)
- **Right side**: real-time stress analysis panel (score, signal bars, alerts)

Every 2 seconds, MediaPipe FaceLandmarker extracts 52 blendshapes from the face and computes a stress score from 4 signals:

| Signal | What it measures | Weight |
|---|---|---|
| Brow Furrow | browDown + browInnerUp | 35% |
| Lip Press | mouthPress + mouthStretch + jawForward | 25% |
| Eye Squint | eyeSquint + noseSneer | 20% |
| Expression Freeze | jaw clenched + average tension lock | 20% |

A floor rule ensures that if any single signal is very high, the total score reflects it (at least 65% of the max signal).

**Trigger**: stress_score >= 60 for 3 consecutive readings (~6 seconds), then 120s cooldown before next alert.

## For Agents: How to Use This Skill

### Step 1: Launch the Monitor

```bash
python3 {baseDir}/scripts/emotion_watch.py &
```

This opens a dashboard window and starts monitoring. It runs until the user presses `q` or closes the window.

### Step 2: Watch for Alerts

Poll `/tmp/oc_emotion_alert.json` periodically (every 30-60 seconds):

```bash
cat /tmp/oc_emotion_alert.json 2>/dev/null
```

When the file exists and has been recently updated, it contains:

```json
{
  "timestamp": "2026-04-27 14:30:00",
  "stress_score": 72,
  "signals": {"brow_furrow": 0.8, "lip_press": 0.3, "eye_squint": 0.2, "expression_freeze": 0.5},
  "message": "Your forehead's been working hard. Try releasing your jaw and letting your shoulders drop."
}
```

### Step 3: Relay the Message

When you detect a new alert (check timestamp), relay the `message` field to the user in a warm, caring tone. Don't dump the JSON — speak like a friend:

> "Hey — I noticed your stress monitor picked up some tension. Your forehead's been working hard. Maybe try releasing your jaw and letting your shoulders drop."

After relaying, you can delete the file to avoid re-sending:

```bash
rm -f /tmp/oc_emotion_alert.json
```

### One-Shot Check

If the user asks "how am I doing?" or "check my stress":

1. If the monitor is already running, read `/tmp/oc_emotion_alert.json`
2. If not running, launch it: `python3 {baseDir}/scripts/emotion_watch.py &`
3. Share the result conversationally

## Privacy

- **100% local** — MediaPipe runs on-device, zero network calls
- **No images saved** — frames exist only in memory during analysis
- **Mosaic privacy** — dashboard pixelates everything except the face, making privacy protection visually obvious
- **No cloud APIs** — unlike vision API approaches, nothing leaves the machine

## Requirements

- macOS with built-in webcam (or any USB camera)
- Python 3 with `mediapipe` and `opencv-python`
- Install: `pip3 install mediapipe opencv-python`

## Alert Messages

Messages are selected based on the dominant stress signal:

| Dominant Signal | Message |
|---|---|
| brow_furrow | "Feels like things have been a bit intense lately. Try taking a slow breath and letting your shoulders drop." |
| expression_freeze | "You've been really focused for a while — that kind of deep lock-in can sneak up on you. Step away for just 2 minutes." |
| lip_press | "Might be a good moment to pause. Three slow breaths — in through your nose, out through your mouth." |
| eye_squint | "You've been staring at the screen for a while. Look at something far away for 20 seconds — your eyes will thank you." |
| score >= 80 | "Hey — it might be time for a real break. Walk away from the screen for 5 minutes. You'll come back sharper." |

When no single signal dominates, a random gentle nudge is picked from a pool of 5 messages — all concrete physical actions (drink water, stretch, walk, breathe), never abstract advice.
