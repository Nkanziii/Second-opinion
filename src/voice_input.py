"""
Voice input for Second Opinion: record from the microphone, then turn the
speech into text with Whisper (faster-whisper, runs on this Mac, no API).

Used by run_experiment.py when you pass --voice.

- listen_until_silence(): waits for the visitor to start talking, records
  until they stop, and returns what they said (empty string if they said
  nothing). This is what the live conversation uses.
- listen(seconds): the older fixed-length recording, kept for quick tests.
"""

import queue

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000  # Whisper expects 16 kHz audio
BLOCK_SECONDS = 0.1
_model = None


def _get_model():
    # Load the model once, the first time it's needed, then reuse it.
    global _model
    if _model is None:
        _model = WhisperModel("base", device="cpu", compute_type="int8")
    return _model


def _transcribe(audio) -> str:
    print("Transcribing...")
    segments, _info = _get_model().transcribe(audio.flatten(), language="en")
    return " ".join(s.text.strip() for s in segments).strip()


def _rms(block) -> float:
    return float(np.sqrt(np.mean(np.square(block))))


def listen(seconds: int = 8) -> str:
    """Record exactly `seconds` of audio from the mic and return what was said."""
    print(f"Speak now ({seconds} seconds)...")
    audio = sd.rec(int(seconds * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                   channels=1, dtype="float32")
    sd.wait()
    text = _transcribe(audio)
    print(f"Heard: {text}\n")
    return text


def listen_until_silence(max_seconds: float = 20, silence_seconds: float = 1.4,
                         wait_seconds: float = 10) -> str:
    """Wait for the visitor to start talking, record until they pause for
    `silence_seconds`, and return what they said.

    - Gives up and returns "" if nobody starts talking within `wait_seconds`.
    - Never records more than `max_seconds` of actual speech.
    - Measures the room's background noise for the first half second, so don't
      talk the instant it says Listening.
    """
    q = queue.Queue()

    def callback(indata, frames, time_info, status):
        q.put(indata[:, 0].copy())

    block = int(BLOCK_SECONDS * SAMPLE_RATE)
    recent = []      # last few quiet blocks, kept so the first word isn't clipped
    speech = []
    started = False
    quiet_run = 0
    waited = 0.0
    spoken = 0.0
    loud_blocks = 0

    print("Listening...")
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                        blocksize=block, callback=callback):
        ambient = [_rms(q.get()) for _ in range(5)]
        threshold = max(0.015, 3 * float(np.mean(ambient)))
        while True:
            b = q.get()
            loud = _rms(b) > threshold
            if not started:
                recent.append(b)
                recent = recent[-3:]
                waited += BLOCK_SECONDS
                if loud:
                    started = True
                    loud_blocks = 1
                    speech.extend(recent)
                elif waited >= wait_seconds:
                    break
            else:
                speech.append(b)
                spoken += BLOCK_SECONDS
                loud_blocks += loud
                quiet_run = 0 if loud else quiet_run + 1
                if quiet_run * BLOCK_SECONDS >= silence_seconds or spoken >= max_seconds:
                    break

    if loud_blocks < 2:   # a single click or cough, not speech (a short 'yes' still counts)
        print("(nothing heard)\n")
        return ""
    text = _transcribe(np.concatenate(speech))
    print(f"Heard: {text}\n")
    return text
