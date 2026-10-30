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
import select
import sys

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
    text = re.sub(r"\*[^*]*\*", "", text)  # drop anything written between asterisks, like *sigh*
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

def _enter_pressed() -> bool:
    """True if the visitor pressed Enter (the line is read and thrown away)."""
    if not sys.stdin.isatty():
        return False
    ready, _, _ = select.select([sys.stdin], [], [], 0)
    if ready:
        sys.stdin.readline()
        return True
    return False

def _clear_typed_keys():
    """Forget any Enter presses from before the doctor started speaking."""
    while _enter_pressed():
        pass


def speak_reply(persona_id: str, text: str, allow_interrupt: bool = False) -> float:
    """Speak one reply, sending its loudness to TouchDesigner as it plays. Returns how much was spoken, 0 to 1 (less than 1 if the visitor passed Enter.)"""
    spoken = clean_for_speech(text)
    if not spoken:
        return 1.0
    voice = VOICES.get(persona_id)
    path = os.path.join(tempfile.gettempdir(), f"second_opinion_{persona_id}.wav")
    cmd = ["say"] + (["-v", voice] if voice else []) + [
        "-o", path, "--file-format=WAVE", "--data-format=LEI16@22050", spoken]                                                
    if subprocess.run(cmd).returncode != 0:
        subprocess.run(["say", spoken])  # could not save the sound: just speak it, no levels
        return 1.0
    levels = loudness_levels(path)
    if allow_interrupt:
        _clear_typed_keys()
    player = subprocess.Popen(["afplay", path])
    start = time.time()
    played = 1.0
    try:
        for i, level in enumerate(levels):
            if allow_interrupt and _enter_pressed():
                played = i / len(levels)
                break
            wait = start + i / LEVEL_HZ - time.time()
            if wait > 0:
                time.sleep(wait)
            send_level(persona_id, level)
        if played == 1.0:
            player.wait()
    finally:
        send_level(persona_id, 0.0)
        if player.poll() is None:
            player.terminate()
    return played
