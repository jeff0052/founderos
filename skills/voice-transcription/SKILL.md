---
name: voice-transcription
description: "Transcribe voice messages to text using OpenAI Whisper (local). Supports Chinese, English and other languages. Processes audio files from Telegram/messaging platforms."
metadata: {"openclaw":{"requires":{"bins":["python3"]}}}
---

# Voice Transcription

Transcribe voice messages to text using locally-installed OpenAI Whisper.

## When to Use

- User sends a voice message / audio file
- Media type is `audio/ogg`, `audio/mp3`, `audio/wav`, etc.
- User asks to transcribe audio

## Dependencies

- `openai-whisper`: `pip3 install openai-whisper`
- Binary path: `/Users/jeff/Library/Python/3.9/bin/whisper`
- Model: `base` (auto-downloaded on first use, ~1.5GB)

## Workflow

### Step 1: Identify Audio File
Audio files from Telegram are saved to: `~/.openclaw/media/inbound/`
Format is typically `.ogg` (Opus codec).

### Step 2: Transcribe
```bash
export PATH=$PATH:/Users/jeff/Library/Python/3.9/bin
whisper "<audio_file>" --language zh --task transcribe --output_format txt
```

For auto language detection (non-Chinese), omit `--language zh`.

### Step 3: Process Result
- Read the transcription output
- Present to user for confirmation
- If user gives tasks/info, record to appropriate files (TODO.md, memory, etc.)

## Important Notes
- **Name accuracy**: Whisper often mis-transcribes proper nouns (people, companies). Always confirm with user.
- **CPU warning**: "FP16 is not supported on CPU; using FP32 instead" is normal, ignore it.
- **Processing time**: ~5-15 seconds per message depending on length.
- **Language**: Default to `--language zh` for Jeff's messages. Remove flag for auto-detect.
- **Poll timeout**: Use `poll` with `timeout=15000` to wait for completion.

## Lessons Learned
- Whisper transcribed "Camille" as "Cameron" — always verify names
- Whisper transcribed "Onta" as various forms — user corrected to "Onta Network"
- Company names like "Paymongo", "Netstar", "Uniweb" need user verification
- Short audio (<5s) transcribes faster and more accurately
