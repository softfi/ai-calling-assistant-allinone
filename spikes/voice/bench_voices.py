"""Find a female, Indian-sounding voice: synthesize one Hinglish line per candidate, measure time
to first audio and median pitch (female speech ≈ 165–255 Hz, male ≈ 85–155 Hz), save WAVs to
results/voices/ for listening.

    uv run python bench_voices.py
"""

from __future__ import annotations

import asyncio
import os

import numpy as np
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents.utils import http_context

from bench_speech import save_wav, synth

load_dotenv(".env.local")
OUT = __import__("pathlib").Path(__file__).parent / "results" / "voices"
LINE = (
    "Namaste, main Riya bol rahi hoon. Aapko kaunse area mein flat chahiye, aur budget kitna hai?"
)

CANDIDATES: list[tuple[str, str, dict[str, str]]] = [
    ("cartesia-default", "cartesia/sonic-3", {"language": "hi"}),
    (
        "cartesia-ac7ee4fa",
        "cartesia/sonic-3",
        {"language": "hi", "voice": "ac7ee4fa-25db-420d-bfff-f590d740aeb2"},
    ),
    (
        "cartesia-7f423809",
        "cartesia/sonic-3",
        {"language": "hi", "voice": "7f423809-0011-4658-ba48-a411f5e516ba"},
    ),
    ("gemini-Kore", "google/gemini-3.8-flash-tts", {"language": "hi", "voice": "Kore"}),
    ("gemini-Leda", "google/gemini-3.8-flash-tts", {"language": "hi", "voice": "Leda"}),
    ("gemini-Aoede", "google/gemini-3.8-flash-tts", {"language": "hi", "voice": "Aoede"}),
]
if os.getenv("CARTESIA_VOICE"):
    CANDIDATES.append(
        (
            "cartesia-env",
            "cartesia/sonic-3",
            {"language": "hi", "voice": os.environ["CARTESIA_VOICE"]},
        )
    )


def median_pitch(frames: list[rtc.AudioFrame]) -> float | None:
    """Median F0 (Hz) over voiced 40 ms windows, by autocorrelation (75–400 Hz)."""
    merged = rtc.combine_audio_frames(frames)
    sr = merged.sample_rate
    x = np.frombuffer(merged.data, dtype=np.int16).astype(np.float32)
    if merged.num_channels > 1:
        x = x.reshape(-1, merged.num_channels).mean(axis=1)
    win = int(0.04 * sr)
    lo, hi = int(sr / 400), int(sr / 75)
    pitches = []
    for start in range(0, len(x) - win, win):
        seg = x[start : start + win]
        seg = seg - seg.mean()
        if np.sqrt((seg**2).mean()) < 300:  # skip silence / unvoiced
            continue
        ac = np.correlate(seg, seg, mode="full")[win - 1 :]
        lag = lo + int(np.argmax(ac[lo:hi]))
        if ac[lag] > 0.3 * ac[0]:
            pitches.append(sr / lag)
    return float(np.median(pitches)) if pitches else None


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    async with http_context.open():
        for name, model, opts in CANDIDATES:
            try:
                ttfb, frames = await synth(model, opts, LINE)
            except Exception as exc:  # noqa: BLE001 (spike)
                print(f"{name:<20} ERROR {exc!r}"[:160])
                continue
            save_wav(OUT / f"{name}.wav", frames)
            f0 = median_pitch(frames)
            guess = "?" if f0 is None else ("female" if f0 >= 160 else "male")
            pitch = f"{f0:.0f} Hz" if f0 else "n/a"
            print(f"{name:<20} first audio {ttfb:.2f}s   pitch {pitch:>7}  → {guess}")


if __name__ == "__main__":
    asyncio.run(main())
