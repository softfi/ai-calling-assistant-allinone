# S1-T4 — Voice stack benchmark (Hinglish) + cost per AI minute

Sources: `spikes/voice/FINDINGS.md`, `spikes/voice/results/*` (runs 2026-11-19/20, LiveKit Cloud
India South, Agents 1.8.13, models via LiveKit Inference). All live tests were browser/console
mic calls by Dev — **no phone (8 kHz PSTN) audio yet**, and not yet the 10 scripted calls per
combo with Lucknow/Delhi accents the milestone asks for → that remains part of S1-T3.

## 1. Component results
| Stage | Candidates | Result | Pick |
|---|---|---|---|
| LLM (TTFT p50, scripted 4-turn Hinglish) | Gemma 4 31B 0.66 s · GPT-5.4-mini 0.95 s · Gemini 3.5 flash-lite 1.04 s | all 3 saved the qualification correctly; Gemma warmest Hinglish; cold first call ~3.4 s | Gemma 4 |
| TTS (first audio p50) | Cartesia Sonic-3 0.51 s · Gemini TTS 1.37 s · Inworld 1.92 s | Cartesia default voices are male / US-accented; Gemini "Leda" female (216 Hz) | Cartesia speed, voice still open |
| STT (Hinglish, synthetic audio) | Speechmatics Oak-1 · GPT-Live Transcribe · Deepgram Nova-3 multi | Oak-1 near-perfect (Devanagari + English kept); GPT minor slips; **Deepgram decodes Hinglish as Indonesian** | Oak-1 |
| Noise | ai-coustics Quail vs console mode | browser Agent Console with Quail clearly better (Dev, 2026-11-20) | Quail default |

## 2. End-to-end (live mic)
| Combo | What | Turns | Response latency | Notes |
|---|---|---|---|---|
| **A** pipeline | Oak-1 → Gemma 4 → Cartesia Sonic-3 | 30 | **p50 1.23 s, p90 3.11 s** (EOU 0.64, LLM 0.41, TTS 0.16) | Tail = end-of-turn detection; after endpointing tuning (dyn. 0.8–2.5 s) Dev found turn-taking better; full qualification saved; transfer worked 2×; voice male/US |
| **G** speech-to-speech | Gemini 3.8 Live, voice Leda | ~50 responses | not comparable: realtime metrics only give model TTFT (p50 0.01 s after commit, p90 0.89 s), not user-perceived EOU→audio | Dev: natural, good Hinglish, female; picked up background noise (fixed with Quail); qualification saved |

Target was < 1.2 s p50: A is at the edge (1.18–1.23 s); G felt faster to Dev but must be measured
from recordings (EOU → first audio) in S1-T3.

## 3. Cost per AI minute (list prices 2026-11-20, USD→INR at ₹88, excl. GST)
LiveKit Cloud ([pricing](https://livekit.com/pricing)): agent session $0.01/min, SIP $0.004/min
(Ship tier, after included minutes; Build free tier includes 1,000 of each), Quail background
suppression no listed charge. Telephony: Plivo ₹0.38/min inbound, 30-s pulse
([Plivo IN](https://www.plivo.com/voice/pricing/in/)).

| Item | A (pipeline) | G (Gemini Live) |
|---|---|---|
| Models | Oak-1 $0.0038 + Gemma 4 $0.0014 + Cartesia $0.0300 | Gemini 3.8 Live $0.0182 |
| LiveKit session + SIP | $0.0140 | $0.0140 |
| **AI subtotal** | $0.0592 ≈ ₹5.21 | $0.0322 ≈ ₹2.83 |
| Plivo inbound | ₹0.38 | ₹0.38 |
| **Total per AI minute** | **≈ ₹5.6** | **≈ ₹3.2** |

Human-first adds an outbound leg to the agent's phone while it rings and while the human talks
(₹0.38/min + LiveKit SIP), i.e. a human-handled minute ≈ ₹1.4 telephony + SIP, no AI cost.
Cartesia is 51% of combo A; Scale tier ($0.0225) or a cheaper Indian TTS changes A materially.
Gemini Live is listed per minute by LiveKit; our 1 test session used 139k input / 11k output tokens
— check the invoice against the per-minute figure before quoting customers.

## 4. Open-source baseline — deferred
Not run: renting a GPU needs a new paid cloud account (none available in this spike), and a fair
test (IndicConformer / Whisper-large-v3 STT + Indic Parler-TTS, served with streaming) is more
than an afternoon. Plan it as a later benchmark (M4 or a cost-down spike) when volume justifies
self-hosting: one ~₹60–100/h GPU for 2–3 h stays < ₹200; measure WER on the same Hinglish clips,
first-audio latency, and ₹/min at 30% / 60% utilisation.
