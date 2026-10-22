"""
Quick test for the orbs: no doctors, no microphone, no API calls.

Plays a fake conversation straight into TouchDesigner:
  - Dr. Hedges "speaks" for 4 seconds, then Dr. Sure does, and so on
  - the disagreement score goes from low (calm) up to high (conflict)
Stop it any time with Ctrl+C; the orbs settle back to calm.

Run from the src folder:   python3 test_orbs.py
"""

import math
import random
import time

from osc_sender import send_divergence, send_speaking, send_level

SPEAK_SECONDS = 4
PAUSE_SECONDS = 2

# a made-up disagreement score for each round: calm -> high conflict -> calm
SCORES = [0.30, 0.45, 0.60, 0.70, 0.60, 0.40]


def calm():
    for persona_id in ("cautious", "confident"):
        send_speaking(persona_id, 0.0)
        send_level(persona_id, 0.0)

def fake_voice(persona_id, seconds):
    """Pretend to talk: a loudness that rises and falls like words."""
    start = time.time()
    while time.time() - start < seconds:
        t = time.time() - start
        level = 0.5 + 0.5 * math.sin(t * 9) * random.uniform(0.6, 1.0)
        send_level(persona_id, max(0.0, min(1.0, level)))
        time.sleep(1 / 30)
    send_level(persona_id, 0.0)

try:
    for score in SCORES:
        send_divergence({"divergence_score": score})
        for persona_id in ("cautious", "confident"):
            print(f"score {score:.2f}: {persona_id} speaking")
            send_speaking(persona_id, 1.0)
            fake_voice(persona_id, SPEAK_SECONDS)
            send_speaking(persona_id, 0.0)
            time.sleep(PAUSE_SECONDS)
finally:
    calm()
    print("done, orbs calm")
