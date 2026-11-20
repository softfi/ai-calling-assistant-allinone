"""Talk to the bot from this PC with one command (spike convenience).

    uv run python talk.py            # Gemini Live (combo G), built-in mic (device 2)
    uv run python talk.py A          # another combo: A | B | C | D | G
    uv run python talk.py G 5        # another input device id (see: agent.py console --list-devices)

The combo given here wins over VOICE_COMBO in .env.local.
"""

from __future__ import annotations

import os
import sys

combo = (sys.argv[1] if len(sys.argv) > 1 else "G").upper()
device = sys.argv[2] if len(sys.argv) > 2 else "2"
os.environ["VOICE_COMBO"] = combo  # set before agent.py loads .env.local (which won't override it)
sys.argv = ["agent.py", "console", "--input-device", device]

from livekit import agents

import agent

agents.cli.run_app(agent.server)
