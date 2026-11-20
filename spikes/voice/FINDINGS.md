# S1 findings (running notes → S1-T5 report / ADR-007)

Environment: LiveKit Cloud project, region **India South**; LiveKit Agents 1.8.13; all models via
LiveKit Inference unless noted. Runs from a dev PC in India, 2026-11-19.

## 1. LLM — `bench_llm.py` (scripted 4-turn Hinglish caller, same prompt + tools as the bot)
| Model | TTFT p50 | TTFT max | Saved qualification correctly | Style |
|---|---|---|---|---|
| google/gemma-4-31b-it | **0.66 s** | 3.44 s (first call) | yes (budget, timeline, Hinglish) | natural, warm Hinglish |
| google/gemini-3.5-flash-lite | 1.04 s | 3.55 s (first call) | yes | natural, slightly longer |
| openai/gpt-5.4-mini | 0.95 s | 1.43 s | yes | correct but terse ("Theek hai. Kab tak…") |

All three followed the script: one question at a time, numbers in words, tool called after the
third answer, no transfer. Cold first call is slow (~3.4 s) for Gemma/Gemini → keep the session
warm (greeting already pre-warms it on a real call).

## 2. TTS — `bench_speech.py` (4 lines: Roman Hinglish ×3, Devanagari ×1; WAVs in results/audio/)
| Model | Time to first audio p50 | Notes |
|---|---|---|
| cartesia/sonic-3 (`hi`, default voice) | **0.51 s** | fastest by far; fits the 1.2 s budget |
| google/gemini-3.8-flash-tts (`hi`) | 1.37 s | too slow alone for the budget |
| inworld/inworld-tts-2-flash (`hi`) | 1.92 s | too slow |

Naturalness (Roman vs Devanagari input, pronunciation of "pachas lakh", "Gomti Nagar"): **Dev to
listen** to `results/audio/*.wav` and score 1–5.

## 3. STT — Cartesia audio transcribed back (clean synthetic speech, so an upper bound)
| Model (`multi`) | Hinglish result |
|---|---|
| speechmatics/oak-1 | **near-perfect**: Devanagari + English words kept ("आप ये property कब तक लेना चाहते हैं?") |
| openai/gpt-live-transcribe | good, occasional slips ("Theek hai" → "Take care, write") |
| deepgram/nova-3 | **fails**: decodes Hinglish as Indonesian/Malay ("Apa dia properti ketik lain acak tahan?") |

→ Combo A switched from Deepgram to Speechmatics Oak-1.

## Provisional pipeline (pending live-call latency + real accents)
**Speechmatics Oak-1 (multi) → Gemma 4 31B → Cartesia Sonic-3 (hi)**, all through LiveKit
Inference (one bill, one key). Estimated response latency ≈ EOU delay + 0.66 + 0.51 s; live calls
must confirm EOU/turn-detection delay keeps the p50 under 1.2 s.

## 4. Live mic test (Dev, 2026-11-19) — combo A, 22 turns
- Response latency p50 **1.18 s** (target < 1.2 s), p90 3.11 s. Components p50: EOU 0.58, LLM 0.41, TTS 0.15 s. The tail is all end-of-turn detection (2.5–5.1 s on 3 turns).
- Transfer to human worked (2×). No full qualification completed yet.
- Dev feedback: (1) voice is **male** — Riya must be female; (2) **American accent** — must sound Indian; (3) the bot **cuts in before the caller finishes** a sentence.

## 5. Tuning (2026-11-20)
- Voice gender by pitch (`bench_voices.py`): Cartesia default 139 Hz (male), community Hindi ids ac7ee4fa/7f423809 male; Gemini **Leda 216 Hz, Kore 198 Hz, Aoede 168 Hz (female)**, first audio 1.2–1.3 s. No public source lists ids for Cartesia's Indian female voices (Arushi, Riya, Aarti, …) → Dev picks one at play.cartesia.ai → `CARTESIA_VOICE`. Sarvam Bulbul (native Indian female speakers) needs `SARVAM_API_KEY`.
- New combo **D** = Oak-1 + Gemma 4 + Gemini TTS "Leda" (female, works now; ~0.7 s slower first audio than Cartesia).
- Listening: endpointing **dynamic, min 0.8 s / max 2.5 s** (was fixed 0.5 / 3.0) so mid-sentence pauses don't end the turn and long waits are capped; interruptions need ≥ 0.6 s and ≥ 2 words (backchannels like "haan" no longer cut Riya off). Tunable via `ENDPOINTING_MIN/MAX`.

## 6. Dev test of "D" + Gemini Live (2026-11-20)
- Dev's "combo D" run actually ran **A** (metrics: speechmatics/oak-1 + gemma-4 + cartesia default male voice) — `VOICE_COMBO=D` wasn't picked up from .env.local. The bot now prints the active pipeline at startup; a shell `VOICE_COMBO` overrides .env.local.
- Endpointing tuning was active in that run: Dev found responses better than before; first complete qualification saved (30 turns total, p50 1.23 s).
- New combo **G** = **Gemini 3.8 Live** (speech-to-speech via LiveKit Inference), voice "Leda" (female): text-mode check: natural Hinglish ("Namaste ji. Main Riya hoon…"), one question at a time, `save_qualification` with correct values. Needs a live mic test for voice/accent and latency.

## Still to do
- Live conversations (mic or phone) per combo → real EOU delay, barge-in, p50/p90 (`summarize.py`).
- Sarvam (combo B) once `SARVAM_API_KEY` is available — the Indian-built alternative.
- Real accents / noise (Lucknow, Delhi), 10 scripted calls per combo (S1-T4).
- S1-T1 provider matrix (Exotel / Plivo / Twilio: numbers, KYC, SIP, transfer, ₹/min) and S1-T3
  real number with human-first ring → AI fallback.
- Cost per minute (Inference pricing + telephony).
- Note: `metrics_collected` is deprecated in 1.8 (use `ChatMessage.metrics` /
  `session_usage_updated`) — fine for the spike, matters for the production agent.
