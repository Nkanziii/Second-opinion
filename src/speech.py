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
import random

import numpy as np

from osc_sender import send_level

VOICES = {
    "cautious": "Samantha",   # Dr. Hedges
    "confident": "Daniel",    # Dr. Sure
}

PAN = {
    "cautious": (1.0, 0.15),   # Dr. Hedges: mostly the left speaker
    "confident": (0.15, 1.0),  # Dr. Sure: mostly the right speaker
}

VOICE_POOLS = {
    "cautious": ["sage"],              # Dr. Hedges
    "confident": ["ballad"],     # Dr. Sure
}

STYLE_BASE = {
    "cautious": "You are Dr. Hedges, a nervous, over-cautious doctor in a comedy. Hesitant and worried.",
    "confident": "You are Dr. Sure, a wildly overconfident doctor in a comedy. Absolute certainty and showmanship.",
}

MOOD_STYLE = {
    "cautious": {
        "anxious": "Today you are extra anxious: quick, breathless, trailing off.",
        "gentle": "Today you are gentle: soft, kind and reassuring, but still timid.",
        "tired": "Today you are exhausted: slow, weary, with long sighs between phrases.",
        "fussy": "Today you are fussy: precise, prim, correcting yourself.",
    },
    "confident": {
        "smug": "Today you are smug: pleased with yourself, savouring your own cleverness.",
        "impatient": "Today you are impatient: clipped and hurried, as if the visitor wastes your time.",
        "warm": "Today you are warm: jovial, with a big friendly bedside manner.",
        "theatrical": "Today you are theatrical: grand pauses and dramatic pronouncements.",
    },
}

SESSION_VOICES = {}


def start_session(moods=None) -> dict:
    """Pick a voice for each doctor for this visitor, with an acting direction that follows today's mood."""
    SESSION_VOICES.clear()
    for persona_id, pool in VOICE_POOLS.items():
        mood = (moods or {}).get(persona_id)
        style = STYLE_BASE[persona_id] + " " + MOOD_STYLE[persona_id].get(mood, "")
        SESSION_VOICES[persona_id] = {"voice": random.choice(pool), "style": style}
    return {persona_id: v["voice"] for persona_id, v in SESSION_VOICES.items()}


_openai = None


def synthesize_openai(persona_id: str, spoken: str, path: str) -> bool:
    """Save the line with an OpenAI voice. Returns False if it can't, so the caller uses the Mac voice."""
    global _openai
    pick = SESSION_VOICES.get(persona_id)
    if not pick:
        return False
    try:
        if _openai is None:
            import llm_client  # loads the keys from .env
            from openai import OpenAI
            _openai = OpenAI()
        reply = _openai.audio.speech.create(model="gpt-4o-mini-tts", voice=pick["voice"],
                                            input=spoken, instructions=pick["style"],
                                            response_format="wav")
        with open(path, "wb") as f:
            f.write(reply.content)
        return True
    except Exception as e:
        print(f"(OpenAI voice failed, using the Mac voice: {e})")
        return False

def make_panned(path: str, persona_id: str) -> str:
    """Copy a mono WAV into a stereo WAV with the voice mostly in one speaker."""
    left, right = PAN.get(persona_id, (1.0, 1.0))
    with wave.open(path, "rb") as w:
        rate = w.getframerate()
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    stereo = np.empty(len(data) * 2, dtype=np.int16)
    stereo[0::2] = (data * left).astype(np.int16)
    stereo[1::2] = (data * right).astype(np.int16)
    out = path.replace(".wav", "_stereo.wav")
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(stereo.tobytes())
    return out


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


def prepare_audio(persona_id: str, text: str) -> dict:
    """Make the sound for one reply (voice, loudness levels, left/right panning) without playing it.
    Can run in the background while the other doctor is still speaking."""
    spoken = clean_for_speech(text)
    if not spoken:
        return {"kind": "empty"}
    path = os.path.join(tempfile.gettempdir(), f"second_opinion_{persona_id}.wav")
    if not synthesize_openai(persona_id, spoken, path):
        voice = VOICES.get(persona_id)
        cmd = ["say"] + (["-v", voice] if voice else []) + [
            "-o", path, "--file-format=WAVE", "--data-format=LEI16@22050", spoken]
        if subprocess.run(cmd).returncode != 0:
            return {"kind": "say_only", "spoken": spoken}  # could not save the sound: just speak it, no levels
    levels = loudness_levels(path)
    path = make_panned(path, persona_id)
    return {"kind": "audio", "path": path, "levels": levels}


def speak_reply(persona_id: str, text: str, allow_interrupt: bool = False, prepared: dict = None) -> float:
    """Speak one reply, sending its loudness to TouchDesigner as it plays. Returns how much was spoken, 0 to 1 (less than 1 if the visitor passed Enter.)
    If the sound was already made with prepare_audio, pass it as `prepared` so it starts straight away."""
    if prepared is None:
        prepared = prepare_audio(persona_id, text)
    if prepared["kind"] == "empty":
        return 1.0
    if prepared["kind"] == "say_only":
        subprocess.run(["say", prepared["spoken"]])
        return 1.0
    path = prepared["path"]
    levels = prepared["levels"]
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
