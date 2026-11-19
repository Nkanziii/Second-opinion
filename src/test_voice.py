"""Voice cut-off test. Makes Dr. Sure's greeting three times with the same settings the
installation uses, prints how long each sound is, and plays it exactly like the installation does.
Listen: does each one end with "First, what's your name?"

Run it from the src folder:  python3 test_voice.py
"""
import os
import subprocess
import tempfile
import wave

from speech import start_session, synthesize_openai, make_panned, end_level, says_last_word

TEXT = ("And I'm Dr. Sure, and I like answers. Here's how this works: tell us a health worry, "
        "and at the end you decide which of us to believe. First, what's your name?")

start_session()
words = len(TEXT.split())
for n in range(1, 4):
    path = os.path.join(tempfile.gettempdir(), f"voice_test_{n}.wav")
    if not synthesize_openai("confident", TEXT, path, 0):
        print("The OpenAI voice did not work, so there is nothing to test.")
        break
    stereo = make_panned(path, "confident")
    with wave.open(stereo, "rb") as w:
        seconds = w.getnframes() / w.getframerate()
    print(f"Try {n}: {seconds:.1f} seconds for {words} words, end loudness {end_level(path):.2f} (cut off if above 0.25), last word heard: {says_last_word(path, TEXT)}")
    subprocess.run(["afplay", stereo])
print("Done. A normal reading of this is about 10 to 12 seconds. A cut-off one is shorter.")
