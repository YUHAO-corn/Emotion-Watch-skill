# Emotion Watch

An OpenClaw skill that silently monitors your facial stress signals and sends gentle nudges before you hit a breaking point.

Built for people with alexithymia — a neurological condition where you can't feel your own emotions building up. Job coaches watch for the signs you can't see yourself. This skill does the same thing, running quietly in the background.

> Your face is always talking. You just can't hear it.
> Emotion Watch listens for you.

## Demo

🎬 *Coming soon*

<!-- TODO: add demo video/GIF/screenshots -->

## How it works

Every 30 seconds, OpenClaw's cron fires this skill:

```
imagesnap → capture one webcam frame
    ↓
MiniMax-VL-01 → analyze facial tension (brow, lips, eyes, expression freeze)
    ↓
Rule engine → check stress score + consecutive count + cooldown
    ↓
Stress sustained? → send a caring nudge in chat
    ↓
Delete the frame. Nothing stored. Ever.
```

You don't start it. You don't interact with it. It just watches — and only speaks up when it matters.

### What the nudge looks like

The message changes based on what your face is doing:

| Signal | Nudge |
|---|---|
| Brow tension | "Your forehead's been working hard. Try releasing your jaw and letting your shoulders drop." |
| Expression freeze | "You've gone really still — that can be a sign of overload. Step away for just 2 minutes." |
| Lip pressing | "There's some tension around your mouth. Three slow breaths — in through nose, out through mouth." |
| Eye strain | "Your eyes look strained. Look at something 20 feet away for 20 seconds." |
| High stress (≥80) | "Hey — your face is showing something your mind might not have caught yet. Take a real break. Walk away from the screen for 5 minutes." |

Every message uses body sensation language, not emotion labels. "Your forehead's been working hard" instead of "you seem stressed." Because for someone with alexithymia, "stressed" means nothing. But a tight forehead? That you can feel.

### Safeguards

- Stress must sustain for 2 consecutive readings (~1 minute) before triggering
- 120-second cooldown after each nudge — no repeated interruptions
- No face detected? Skip silently. You stepped away, that's fine.

## Privacy

Non-negotiable when the user has a disability.

- **Fully local capture.** `imagesnap` grabs the frame on your machine.
- **Vision via API, no storage.** MiniMax analyzes the frame and returns a JSON score. The image is not stored on their end.
- **Frame deleted immediately.** The jpg and base64 are removed right after the API call. Nothing persists on disk.
- **No history.** No logs, no photo archive, no emotion timeline. Each cycle is independent.
- **Lid = off.** Close the laptop and it stops.

## Setup

### Prerequisites

- macOS with built-in camera
- [OpenClaw](https://github.com/openclaw/openclaw) installed
- `imagesnap` — `brew install imagesnap`
- MiniMax API key set as `OPENCLAW_MINIMAX_API_KEY`

### Install

```bash
git clone https://github.com/YUHAO-corn/emotion-watch-skill.git
```

Copy the skill into your OpenClaw workspace, then set up a cron that fires every 30 seconds with the prompt:

```
Run emotion-watch skill: capture a webcam frame, analyze stress, and respond if needed.
```

### One-shot mode

Ask OpenClaw "how am I doing?" or "check my stress" — it'll run a single check immediately and tell you the result conversationally, skipping cooldown.

## Project structure

```
emotion-watch-skill/
├── SKILL.md           # The entire skill logic (prompt-driven)
├── DESIGN.md          # Architecture and design decisions
├── _meta.json         # OpenClaw metadata
├── scripts/
│   └── capture.sh     # Webcam capture + base64 encode
└── README.md
```

The whole thing is prompt-driven. SKILL.md tells the OpenClaw agent exactly what to do each cron tick. No separate process, no daemon, no Python runtime.

## Why this exists

People with alexithymia don't get the internal signal that says "I need a break." The warning signs show up on their face — furrowed brows, frozen expression, clenched jaw — but they can't read their own face.

Job coaches solve this by sitting beside them and watching. But coaches are scarce, and the goal is for them to eventually step back.

Emotion Watch keeps that early warning system running after the coach leaves.

## License

MIT
