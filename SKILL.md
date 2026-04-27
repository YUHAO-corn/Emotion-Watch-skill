---
name: emotion-watch
description: Silent background stress monitor. Captures webcam frames via cron, analyzes facial tension with MiniMax vision, and sends caring nudges when stress is detected. Built for alexithymia — watches your face so you don't have to.
homepage: https://github.com/godcorn/emotion-watch
metadata: {"openclaw": {"emoji": "🫂", "requires": {"env": ["OPENCLAW_MINIMAX_API_KEY"], "bin": ["imagesnap"]}, "primaryEnv": "OPENCLAW_MINIMAX_API_KEY"}}
---

# Emotion Watch

A silent guardian that monitors your facial stress signals in the background and sends gentle nudges before you hit a breaking point.

## How It Works

This skill is designed to run on a **cron schedule (every 30 seconds)**. Each tick:

1. Capture a webcam frame
2. Analyze it for stress signals via MiniMax vision
3. Apply rule engine (thresholds + cooldown)
4. Send a caring message if stress is detected
5. Clean up — frame is deleted immediately

**The user does nothing.** This skill runs silently. Like a job coach sitting beside you, watching for the signs you can't see yourself.

## Step 1: Capture Webcam Frame

```bash
imagesnap -q -w 1 /tmp/oc_emotion_frame.jpg
```

If the command fails, stop — camera may be unavailable. Reply `HEARTBEAT_OK`.

## Step 2: Check Cooldown

```bash
if [ -f /tmp/oc_emotion_cooldown.txt ]; then
  last=$(cat /tmp/oc_emotion_cooldown.txt)
  now=$(date +%s)
  diff=$((now - last))
  if [ "$diff" -lt 120 ]; then
    rm -f /tmp/oc_emotion_frame.jpg
    # Still in cooldown, skip
    exit 0
  fi
fi
```

If cooldown is active (< 120 seconds since last nudge), delete the frame and reply `HEARTBEAT_OK`.

## Step 3: Encode and Analyze

Base64-encode the captured frame:

```bash
base64 -i /tmp/oc_emotion_frame.jpg > /tmp/oc_emotion_frame_b64.txt
```

Then call MiniMax-VL-01 with the image. Use this exact system prompt:

```
You are a facial stress analysis engine. Analyze the face in the image and return ONLY a JSON object. No explanation, no markdown, no code fences.
```

And this user prompt:

```
Analyze this person's facial expression for stress and tension signals. Return this exact JSON format:
{
  "has_face": true/false,
  "emotion": "neutral|tense|anxious|sad|angry|happy",
  "brow_furrow": 0.0-1.0,
  "lip_press": 0.0-1.0,
  "eye_squint": 0.0-1.0,
  "expression_freeze": 0.0-1.0,
  "stress_score": 0-100,
  "dominant_signal": "brow_furrow|lip_press|eye_squint|expression_freeze|none",
  "note": "one sentence observation"
}

Scoring guide:
- brow_furrow: eyebrows pulled down/together (frowning)
- lip_press: lips pressed tight or jaw clenched
- eye_squint: eyes narrowed with tension (not smiling squint)
- expression_freeze: face unusually still/flat/locked — high neutral with no micro-expressions
- stress_score: weighted = 50% brow_furrow + 20% lip_press + 10% eye_squint + 20% expression_freeze, scaled 0-100
- dominant_signal: whichever of the four scores highest
```

## Step 4: Clean Up Frame

Immediately after getting the API response:

```bash
rm -f /tmp/oc_emotion_frame.jpg /tmp/oc_emotion_frame_b64.txt
```

**Privacy first.** No image is ever kept on disk.

## Step 5: Parse Response & Apply Rules

Parse the JSON response from MiniMax.

**If `has_face` is false:** reply `HEARTBEAT_OK` — user is away or camera is blocked.

**If `stress_score` < 60:** Reset consecutive counter and reply `HEARTBEAT_OK`.

```bash
echo "0" > /tmp/oc_emotion_count.txt
```

**If `stress_score` >= 60:** Increment consecutive counter:

```bash
count=0
if [ -f /tmp/oc_emotion_count.txt ]; then
  count=$(cat /tmp/oc_emotion_count.txt)
fi
count=$((count + 1))
echo "$count" > /tmp/oc_emotion_count.txt
```

**Only trigger a message if count >= 2** (stress sustained for ~1 minute).

## Step 6: Send Message

If triggered (count >= 2), select a message based on `dominant_signal`:

| dominant_signal | Message |
|---|---|
| brow_furrow | "Your forehead's been working hard. Try releasing your jaw and letting your shoulders drop." |
| expression_freeze | "You've gone really still — that can be a sign of overload. Step away for just 2 minutes." |
| lip_press | "There's some tension around your mouth. Three slow breaths — in through nose, out through mouth." |
| eye_squint | "Your eyes look strained. Look at something 20 feet away for 20 seconds." |

**If stress_score >= 80** (regardless of dominant signal):
"Hey — your face is showing something your mind might not have caught yet. Take a real break. Walk away from the screen for 5 minutes."

**If no single signal dominates** (all below 0.6), pick randomly from:
1. "Quick check-in: grab some water and look away from the screen for a moment."
2. "Your body's picking up stress before you are. Stand up and stretch for 60 seconds."
3. "Take a breath. Look at something far away for one minute."
4. "Small pause — how are you actually doing right now? A short walk might help."
5. "You've been locked in for a while. Five minutes away will pay back double."

After sending the message, set cooldown and reset counter:

```bash
date +%s > /tmp/oc_emotion_cooldown.txt
echo "0" > /tmp/oc_emotion_count.txt
```

## One-Shot Mode

If the user asks "how am I doing?" or "check my stress" or similar — run Steps 1-4 immediately (skip cooldown check) and report the full JSON result conversationally. Don't just dump JSON — interpret it like a caring friend would.

## Notes

- Requires `imagesnap` (install via `brew install imagesnap`)
- Uses `OPENCLAW_MINIMAX_API_KEY` for MiniMax-VL-01 vision API
- All processing is local capture + cloud vision — no images stored
- Designed for macOS with built-in webcam
