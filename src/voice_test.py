import sounddevice as sd
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
SECONDS = 6

print("Speak now...")
audio = sd.rec(int(SECONDS * SAMPLE_RATE), samplerate=SAMPLE_RATE,
               channels=1, dtype="float32")
sd.wait()

print("Transcribing...")
model = WhisperModel("base", device="cpu", compute_type="int8")
segments, info = model.transcribe(audio.flatten(), language="en")
text = " ".join(s.text.strip() for s in segments)
print("You said:", text)