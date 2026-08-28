"""
BONUS: Voice Debate Session

Synthesizes the debate transcript into a single narrated audio file so judges
can literally *listen* to the panel argue. Uses gTTS (no API key needed) so it
works out of the box; each turn is prefixed with the speaker's name so it
reads like a radio panel discussion.

This is best-effort: if gTTS/network is unavailable, we fail soft and the
rest of the pipeline (text report) still works fine.
"""

import os
import uuid
from typing import Optional

from app.config import ENABLE_VOICE, OUTPUT_DIR
from app.models import DebateResult


def synthesize_debate_audio(debate: DebateResult, candidate_name: str) -> Optional[str]:
    if not ENABLE_VOICE:
        return None
    if not debate.transcript:
        return None

    try:
        from gtts import gTTS
    except ImportError:
        return None

    script_lines = []
    for turn in debate.transcript:
        addressed = f", responding to {turn.addressed_to}" if turn.addressed_to else ""
        script_lines.append(f"{turn.speaker}{addressed}: {turn.message}")
    script = f"HireLens panel debate for candidate {candidate_name}. " + " ... ".join(script_lines)

    filename = f"debate_{uuid.uuid4().hex[:10]}.mp3"
    filepath = os.path.join(OUTPUT_DIR, filename)

    try:
        tts = gTTS(text=script, lang="en")
        tts.save(filepath)
        return filepath
    except Exception:
        # Network issues / rate limits shouldn't break the whole pipeline
        return None
