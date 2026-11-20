# S1 voice spike (throwaway)

Learning code for [S1](../../docs/milestones/S1-voice-spike.md) — **not production**. The real
agent lives in `apps/voice-agent` once ADR-007 is decided.

## What it is
A Hinglish lead-qualification bot ("Riya") on LiveKit Agents 1.8.13: greets the caller, asks what
they need, their budget and timeline, then calls `save_qualification` (JSON to the terminal and
`results/`) or `transfer_to_human` (logged; a real SIP transfer comes in S1-T3).

Three pipelines to compare (`VOICE_COMBO`):

| Combo | STT | LLM | TTS | Keys needed |
|---|---|---|---|---|
| A | Speechmatics Oak-1, `multi` (LiveKit Inference) | Gemma 4 31B (Inference) | Cartesia Sonic-3, Hindi (Inference) | LiveKit only |
| B | Sarvam Saaras v4, `codemix` | Gemma 4 31B (Inference) | Sarvam Bulbul v4 flash | LiveKit + Sarvam |
| G | Gemini 3.8 Live — speech-to-speech (hears and speaks Hindi natively) | — | voice `GEMINI_LIVE_VOICE` (default Leda, female) | LiveKit only |
| D | Speechmatics Oak-1 | Gemma 4 31B | Gemini 3.8 flash TTS, voice Leda (female) | LiveKit only |
| C | OpenAI GPT-Live Transcribe, `multi` (Inference) | Gemini 3.5 flash-lite (Inference) | Gemini 3.8 flash TTS (Inference) | LiveKit only |

Every turn's latency (end of caller speech → first audio byte) is logged to
`results/metrics-<combo>.jsonl`; `summarize.py` prints p50/p90 per combo.

## Quick start (talk to it)
`uv run python talk.py` — Gemini Live (combo G) on the built-in mic. Other combos: `uv run python talk.py A` (A/B/C/D/G); other mic: `uv run python talk.py G <device id>`.
Browser (with noise cancellation): `uv run python talk.py G web`, then LiveKit Cloud dashboard → Agents → Agent Console → start a session.

## Run
1. `cp .env.example .env.local` and fill in the LiveKit Cloud keys (and `SARVAM_API_KEY` for B,
   `CARTESIA_VOICE` for A). `.env.local` is gitignored.
2. `uv sync` then `uv run python agent.py download-files` (turn-detector model, once).
3. `uv run python agent.py console --input-device <id>` — talk from this machine's mic
   (`--list-devices` shows ids; on the dev laptop the built-in "Microphone Array" is 2, the
   default jack input is silent — symptom: greeting plays, your speech gets no reply), or
   `uv run python agent.py dev` and open the Agents Playground for your LiveKit project.
4. Switch pipelines with `VOICE_COMBO` — in PowerShell: `$env:VOICE_COMBO="G"` before the run command (overrides .env.local). The bot prints `=== combo … ===` at start so you can see what is running.
5. `uv run python summarize.py` — latency table per combo.

No-microphone benchmarks: `bench_llm.py` (scripted Hinglish caller vs 3 LLMs) and
`bench_speech.py` (TTS time-to-first-audio + WAVs in `results/audio/`, STT on that audio).
Findings so far: [FINDINGS.md](FINDINGS.md).
