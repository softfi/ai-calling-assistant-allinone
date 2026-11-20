"""S1 voice spike (THROWAWAY — not production; see docs/milestones/S1-voice-spike.md).

A Hinglish lead-qualification bot on LiveKit Agents 1.8:
  - greets the caller, asks 3 qualification questions (need, budget, timeline),
  - calls `save_qualification` (prints/stores JSON) and `transfer_to_human` (logs the request),
  - logs per-turn latency metrics to results/metrics-<combo>.jsonl for the S1-T4 benchmark.

Pipelines ("combos") are picked with VOICE_COMBO=A|B|C — see COMBOS below.

Run (after filling .env.local from .env.example):
    uv run python agent.py dev        # registers the worker; talk to it from the Agents Playground
    uv run python agent.py console    # talk to it from this terminal (local mic/speaker)
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    MetricsCollectedEvent,
    RunContext,
    TurnHandlingOptions,
    function_tool,
    inference,
    room_io,
)
from livekit.agents.inference.realtime import RealtimeModel
from livekit.plugins import ai_coustics, sarvam

load_dotenv(".env.local")
log = logging.getLogger("voice-spike")
RESULTS = Path(__file__).parent / "results"

LLM_MODEL = os.getenv("LLM_MODEL", "google/gemma-4-31b-it")

# Each combo: (stt, llm, tts) factories. Model ids are LiveKit Inference ids unless noted.
COMBOS: dict[str, Callable[[], dict[str, Any]]] = {
    # A — Inference only: Speechmatics Oak-1 multi (best Hinglish in bench_speech; Deepgram
    # Nova-3 multi decoded Hinglish as Indonesian/Malay) + Gemma 4 + Cartesia Sonic-3 Hindi.
    "A": lambda: {
        "stt": inference.STT(model="speechmatics/oak-1", language="multi"),
        "llm": inference.LLM(model=LLM_MODEL),
        "tts": inference.TTS(
            model="cartesia/sonic-3",
            language="hi",
            # Default Cartesia voice is an American male; set a female Indian voice id.
            **({"voice": os.environ["CARTESIA_VOICE"]} if os.getenv("CARTESIA_VOICE") else {}),
        ),
    },
    # B — Sarvam (Indian stack, own API key): Saaras v4 in codemix mode + Bulbul v4 flash.
    "B": lambda: {
        "stt": sarvam.STT(language="hi-IN", model="saaras:v4", mode="codemix"),
        "llm": inference.LLM(model=LLM_MODEL),
        "tts": sarvam.TTS(
            target_language_code="hi-IN",
            model="bulbul:v4-flash",
            speaker=os.getenv("SARVAM_SPEAKER", "priya"),
        ),
    },
    # C — Inference only: OpenAI GPT-Live Transcribe (multi) + Gemini flash-lite + Gemini TTS.
    "C": lambda: {
        "stt": inference.STT(model="openai/gpt-live-transcribe", language="multi"),
        "llm": inference.LLM(model=os.getenv("LLM_MODEL", "google/gemini-3.5-flash-lite")),
        "tts": inference.TTS(
            model="google/gemini-3.8-flash-tts",
            voice=os.getenv("GEMINI_VOICE", "Leda"),
            language="hi",
        ),
    },
    # D — female voice today without extra keys: A's STT + LLM, Gemini TTS female voice
    # ("Leda" ≈ 216 Hz, "Kore" ≈ 198 Hz in bench_voices). ~0.7 s slower first audio than Cartesia.
    "D": lambda: {
        "stt": inference.STT(model="speechmatics/oak-1", language="multi"),
        "llm": inference.LLM(model=LLM_MODEL),
        "tts": inference.TTS(
            model="google/gemini-3.8-flash-tts",
            voice=os.getenv("GEMINI_VOICE", "Leda"),
            language="hi",
        ),
    },
}

# G — Gemini Live speech-to-speech (Dev suggestion, 2026-11-20): hears and speaks Hindi/Hinglish
# natively — no separate STT/TTS, so no "American TTS reading Hinglish". Female voice by default.
REALTIME = {"G": "google/gemini-3.8-live"}
GEMINI_LIVE_VOICE = os.getenv("GEMINI_LIVE_VOICE", "Leda")
COMBOS["G"] = lambda: {
    "llm": RealtimeModel(model=REALTIME["G"], voice=GEMINI_LIVE_VOICE),
}


def describe(combo: str, parts: dict[str, Any]) -> str:
    """One line naming the models in use (no secrets) — printed at startup."""
    if combo in REALTIME:
        return f"combo {combo}: {REALTIME[combo]} (speech-to-speech), voice {GEMINI_LIVE_VOICE}"
    names = []
    for key in ("stt", "llm", "tts"):
        part = parts.get(key)
        model = getattr(part, "model", None) or type(part).__name__
        names.append(f"{key}={model}")
    voice = getattr(getattr(parts.get("tts"), "_opts", None), "voice", None)
    return f"combo {combo}: " + ", ".join(names) + (f", voice={voice}" if voice else "")


# Noise (2026-11-20): enhanced noise cancellation on the caller's audio, applied in LiveKit Cloud
# rooms (browser playground, and later SIP calls). Console mode reads the mic itself and only has
# basic WebRTC suppression — test noise in the playground. NOISE=quail (default; background noise
# suppression, free on LiveKit Cloud) | voicefocus (voice isolation: also removes other people
# talking nearby; paid) | off.
NOISE_MODELS = {
    "quail": ai_coustics.EnhancerModel.QUAIL_L,
    "voicefocus": ai_coustics.EnhancerModel.QUAIL_VF_S,
}
NOISE = os.getenv("NOISE", "quail").lower()


def noise_filter() -> Any:
    model = NOISE_MODELS.get(NOISE)
    return ai_coustics.audio_enhancement(model=model) if model is not None else None


# Listening (2026-11-20 tuning): callers pause mid-sentence ("Mujhe... 2 BHK chahiye"), and the
# default 0.5 s silence ended their turn early. Dynamic endpointing starts at 0.8 s and adapts to
# the caller's own pause pattern; 2.5 s caps the wait. Short backchannels ("haan", "hmm") while
# Riya speaks no longer interrupt her.
ENDPOINTING_MIN = float(os.getenv("ENDPOINTING_MIN", "0.8"))
ENDPOINTING_MAX = float(os.getenv("ENDPOINTING_MAX", "2.5"))

INSTRUCTIONS = """
Aap "Riya" hain, ek property consultancy ki friendly phone assistant. Caller ne abhi call kiya hai
aur team ka koi member free nahi tha, isliye aap baat kar rahi hain.

Bolne ka tareeka:
- Aap ek Indian ladki ki tarah, garamjoshi aur izzat se baat karein ("ji", "aap").
- Natural Hinglish mein baat karein — jis bhasha mein caller bole (Hindi, English ya mix), usi mein.
- Chhote, simple sentences. Ek baar mein ek hi sawaal. Koi emoji, list, ya symbols nahi.
- Numbers bolkar kahein ("pachas lakh", "fifty lakh"), digits nahi.

Kaam (in teen sawaalon ka jawaab lena hai):
1. Unhe kya chahiye — kaunsi property (flat, plot, villa) aur kis area mein.
2. Budget kitna hai.
3. Kab tak lena chahte hain (timeline).

Teeno jawaab milte hi `save_qualification` tool call karein, phir bataayein ki team jaldi call back
karegi aur shukriya kahein. Agar caller kisi insaan se baat karna chahe, gussa ho, ya sawaal aapke
bas ka na ho, to `transfer_to_human` call karein. Kabhi bhi price, availability ya legal baaton ka
vaada na karein.
""".strip()


class QualificationAgent(Agent):
    def __init__(self, combo: str) -> None:
        super().__init__(instructions=INSTRUCTIONS)
        self.combo = combo

    @function_tool
    async def save_qualification(
        self,
        context: RunContext,
        requirement: str,
        budget: str,
        timeline: str,
        language: str,
    ) -> str:
        """Save the caller's answers once all three are known.

        Args:
            requirement: What they want (property type and area), in the caller's words.
            budget: Their budget, as said (e.g. "50 lakh").
            timeline: When they want to buy (e.g. "3 mahine mein").
            language: The language the caller mostly used: hindi, english or hinglish.
        """
        record = {
            "at": time.time(),
            "combo": self.combo,
            "requirement": requirement,
            "budget": budget,
            "timeline": timeline,
            "language": language,
        }
        print("QUALIFICATION", json.dumps(record, ensure_ascii=False))
        _append(f"qualifications-{self.combo}.jsonl", record)
        return "saved"

    @function_tool
    async def transfer_to_human(self, context: RunContext, reason: str) -> str:
        """Hand the call to a human agent.

        Args:
            reason: Why the caller needs a person (asked for one, upset, out of scope).
        """
        print("TRANSFER", json.dumps({"combo": self.combo, "reason": reason}))
        _append(f"transfers-{self.combo}.jsonl", {"at": time.time(), "reason": reason})
        # S1-T3 replaces this with a real SIP transfer; in the playground we only log it.
        return "Transfer requested. Tell the caller you are connecting them to a team member now."


def _append(name: str, record: dict[str, Any]) -> None:
    RESULTS.mkdir(exist_ok=True)
    with (RESULTS / name).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


server = AgentServer()


@server.rtc_session(agent_name=os.getenv("AGENT_NAME", ""))
async def entrypoint(ctx: agents.JobContext) -> None:
    combo = os.getenv("VOICE_COMBO", "A").upper()
    if combo not in COMBOS:
        raise SystemExit(f"VOICE_COMBO must be one of {sorted(COMBOS)}, got {combo!r}")
    parts = COMBOS[combo]()
    banner = f"{describe(combo, parts)}, noise={NOISE}"
    print(f"\n=== {banner} ===\n")
    log.info(banner)
    if combo in REALTIME:
        # The realtime model does its own turn detection (server-side VAD).
        session: AgentSession = AgentSession(**parts)
    else:
        session = AgentSession(
            **parts,
            turn_handling=TurnHandlingOptions(
                turn_detection=inference.TurnDetector(),
                endpointing={
                    "mode": "dynamic",
                    "min_delay": ENDPOINTING_MIN,
                    "max_delay": ENDPOINTING_MAX,
                },
                interruption={"min_duration": 0.6, "min_words": 2},
            ),
        )

    @session.on("metrics_collected")
    def _on_metrics(ev: MetricsCollectedEvent) -> None:
        # EOU delay (end of caller speech → turn committed), LLM TTFT, TTS TTFB: their sum is the
        # "end of caller speech → first audio byte" latency we benchmark (target < 1.2 s p50).
        metrics = ev.metrics
        data = metrics.model_dump() if hasattr(metrics, "model_dump") else vars(metrics)
        _append(f"metrics-{combo}.jsonl", {"type": type(metrics).__name__, **data})

    await session.start(
        room=ctx.room,
        agent=QualificationAgent(combo),
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(noise_cancellation=noise_filter()),
        ),
    )
    await session.generate_reply(
        instructions="Caller ko Hinglish mein namaste karke greet karein, apna naam Riya bataayein "
        "aur poochhein ki aap unki kya madad kar sakti hain."
    )


if __name__ == "__main__":
    agents.cli.run_app(server)
