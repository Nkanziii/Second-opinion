"""
Voice input for Second Opinion: record from the microphone, then turn the
speech into text with Whisper (faster-whisper, runs on this Mac, no API).

Used by run_experiment.py when you pass --voice.
"""

import sounddevice as sd
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000  # Whisper expects 16 kHz audio
_model = None


def _get_model():
    # Load the model once, the first time it's needed, then reuse it.
    global _model
    if _model is None:
        _model = WhisperModel("base", device="cpu", compute_type="int8")
    return _model


def listen(seconds: int = 8) -> str:
    """Record `seconds` of audio from the mic and return what was said."""
    print(f"Speak now ({seconds} seconds)...")
    audio = sd.rec(int(seconds * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                   channels=1, dtype="float32")
    sd.wait()
    print("Transcribing...")
    segments, _info = _get_model().transcribe(audio.flatten(), language="en")
    text = " ".join(s.text.strip() for s in segments).strip()
    print(f"Heard: {text}\n")
    return text
