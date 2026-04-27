# Emotion Monitor — Design Doc
> OpenClaw Skill · Hackathon build · 2026-04-27

## What It Does

A silent guardian that runs in the background via OpenClaw's cron system. It watches your face through the webcam, detects early stress signals (brow tension, expression freezing, lip pressing), and sends a gentle nudge in the chat — before you even realize you're stressed.

Built for people with alexithymia (difficulty perceiving their own emotional state) — the same group that job coaches support in the workplace. When the coach isn't there, this skill fills the gap.

---

## Architecture

```
OpenClaw Cron (every 30s)
    │
    ▼
SKILL.md instructs agent to:
    │
    ├─ 1. imagesnap → capture frame to /tmp
    ├─ 2. base64 encode → send to MiniMax-VL-01
    ├─ 3. Parse JSON response (emotion signals)
    ├─ 4. Rule engine: check thresholds + cooldown
    ├─ 5. If triggered → send caring message in chat
    └─ 6. Delete frame from /tmp (privacy)
```

**Key**: The user does nothing. OpenClaw cron fires every 30 seconds. The skill tells the agent exactly what to do. The agent is the "electronic job coach."

---

## Trigger: Fully Automatic

| Parameter | Value | Reason |
|---|---|---|
| Trigger | OpenClaw cron, every 30 seconds | Silent, no user action needed |
| Capture | `imagesnap -q -w 1 /tmp/oc_emotion_frame.jpg` | macOS native, zero deps |
| Privacy | Frame deleted immediately after API call | Never persisted |
| Cooldown state | `/tmp/oc_emotion_cooldown.txt` (timestamp) | Prevents repeated nudges |
| Consecutive count | `/tmp/oc_emotion_count.txt` | Tracks consecutive high readings |

The user never starts or stops anything. The skill activates the moment it's installed. To pause, the user simply removes the cron — but the default is always-on.

---

## MiniMax Vision API Call

**Model**: `MiniMax-VL-01` (multimodal, already configured in OpenClaw)

**System prompt**:
```
You are a facial stress analysis engine. Analyze the face in the image and return ONLY a JSON object. No explanation, no markdown, no code fences.
```

**User prompt**:
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

---

## Rule Engine

### Thresholds
- **Trigger**: stress_score >= 60
- **Consecutive**: must be >= 60 for **2 consecutive readings** (~1 minute) before sending a message
- **Cooldown**: 120 seconds after sending a message — no new nudges during cooldown

### Message Selection (English)

Based on `dominant_signal` from the API response:

| dominant_signal | Message |
|---|---|
| brow_furrow | "Your forehead's been working hard. Try releasing your jaw and letting your shoulders drop." |
| expression_freeze | "You've gone really still — that can be a sign of overload. Step away for just 2 minutes." |
| lip_press | "There's some tension around your mouth. Three slow breaths — in through nose, out through mouth." |
| eye_squint | "Your eyes look strained. Look at something 20 feet away for 20 seconds." |

**High stress override** (stress_score >= 80, any signal):
"Hey — your face is showing something your mind might not have caught yet. Take a real break. Walk away from the screen for 5 minutes."

**Default pool** (stress 60-79, no dominant signal > 0.6):
1. "Quick check-in: grab some water and look away from the screen for a moment."
2. "Your body's picking up stress before you are. Stand up and stretch for 60 seconds."
3. "Take a breath. Look at something far away for one minute."
4. "Small pause — how are you actually doing right now? A short walk might help."
5. "You've been locked in for a while. Five minutes away will pay back double."

### No-face handling
If `has_face` is false — do nothing, skip silently. User stepped away, camera blocked, etc.

---

## File Structure

```
~/.openclaw/workspace/skills/emotion-monitor/
├── SKILL.md          ← Agent instructions (the entire logic)
├── _meta.json        ← OpenClaw metadata
└── scripts/
    └── capture.sh    ← imagesnap + base64 helper
```

The skill is **entirely prompt-driven** — the SKILL.md tells the OpenClaw agent step-by-step what to do each cron tick. No separate Python process needed since MiniMax handles the vision analysis.

---

## Cron Setup

Add to OpenClaw cron: fire every 30 seconds with prompt:
```
Run emotion-monitor skill: capture a webcam frame, analyze stress, and respond if needed.
```

---

## Submission

- Prompt: **OpenClaw in Action**
- Post title: "I built an emotion monitor for OpenClaw — it watches your face so you don't have to"
- Key angle: alexithymia use case, silent background guardian, privacy-first, pure OpenClaw skill
