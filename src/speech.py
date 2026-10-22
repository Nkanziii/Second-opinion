"""
Speech output for Second Opinion: each doctor speaks with its own voice,
using the macOS built-in `say` command (free, offline, no packages).

Used by run_experiment.py when you pass --speak.
Change the voice names below to taste. In Terminal, `say -v '?'` lists every
voice installed on your Mac. If a voice isn't installed, it falls back to the
default system voice instead of crashing.
"""

import os
import re
import subprocess
import tempfile
import time
import wave

import numpy as np

from osc_sender import send_level

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

LEVEL_HZ = 30 #loudness readings per second

def loudness_levels(path: str):
    """Read the sound file and return a loudness from 0 yo 1 for every 1/30 s."""
    with wave.open(path, "rb") as w:
        rate = w.getframerate()
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    step = int(rate / LEVEL_HZ)
    count = len(data) // step
    chunks = data[:count * step].reshape(count, step)
    loudness = np.sqrt((chunks ** 2).mean(axis=1))
    loud = np.percentile(loudness, 95) if count else 0
    if loud <= 0:
        return np.zeros(count)
    return np.clip(loudness / loud, 0, 1)

def speak_reply(persona_id: str, text: str) -> None:
    """Speak one reply and wait until it has finished."""
    spoken = clean_for_speech(text)
    if not spoken:
        return
    voice = VOICES.get(persona_id)
    path = os.path.join(tempfile.gettempdir(), f"second_opinion_{persona_id}.wav")
    cmd = ["say"] + (["-v", voice] if voice else []) + [
        "-o", path, "--file-format=WAVE", "--data-format=LEI16@22050", spoken]                                                
    if subprocess.run(cmd).returncode != 0:
        subprocess.run(["say", spoken])  # could not save the sound: just speak it, no levels
        return
    levels = loudness_levels(path)
    player = subprocess.Popen(["afplay", path])
    start = time.time()
    try:
        for i, level in enumerate(levels):
            wait = start + i / LEVEL_HZ - time.time()
            if wait > 0:
                time.sleep(wait)
            send_level(persona_id, level)
        player.wait()
    finally:
        send_level(persona_id, 0.0)
        if player.poll() is None:
            player.terminate()
