"""
Speech output for Second Opinion: each doctor speaks with its own voice,
using the macOS built-in `say` command (free, offline, no packages).

Used by run_experiment.py when you pass --speak.
Change the voice names below to taste. In Terminal, `say -v '?'` lists every
voice installed on your Mac. If a voice isn't installed, it falls back to the
default system voice instead of crashing.
"""

import re
import subprocess

VOICES = {
    "cautious": "Samantha",   # Dr. Hedges
    "confident": "Daniel",    # Dr. Sure
}


def clean_for_speech(text: str) -> str:
    """Drop the trailing 'Confidence: NN%' line (it's data for the score,
    not something the visitor should hear) and any markdown asterisks."""
    text = re.sub(r"[\s*_]*Confidence\s*:\s*\d+\s*%.*$", "", text,
                  flags=re.IGNORECASE | re.DOTALL)
    return text.replace("*", "").strip()


def speak_reply(persona_id: str, text: str) -> None:
    """Speak one reply and wait until it has finished."""
    spoken = clean_for_speech(text)
    if not spoken:
        return
    voice = VOICES.get(persona_id)
    cmd = ["say", "-v", voice, spoken] if voice else ["say", spoken]
    if subprocess.run(cmd).returncode != 0:
        subprocess.run(["say", spoken])  # voice missing: use the default voice
