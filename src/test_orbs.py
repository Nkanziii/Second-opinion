"""
Quick test for the orbs: no doctors, no microphone, no API calls.

Plays a fake conversation straight into TouchDesigner:
  - Dr. Hedges "speaks" for 4 seconds, then Dr. Sure does, and so on
  - the disagreement score goes from low (calm) up to high (conflict)
Stop it any time with Ctrl+C; the orbs settle back to calm.

Run from the src folder:   python3 test_orbs.py
"""

import time

from osc_sender import send_divergence, send_speaking

SPEAK_SECONDS = 4
PAUSE_SECONDS = 2

# a made-up disagreement score for each round: calm -> high conflict -> calm
SCORES = [0.30, 0.45, 0.60, 0.70, 0.60, 0.40]


def calm():
    send_speaking("cautious", 0.0)
    send_speaking("confident", 0.0)


try:
    for score in SCORES:
        send_divergence({"divergence_score": score})
        for persona_id in ("cautious", "confident"):
            print(f"score {score:.2f}: {persona_id} speaking")
            send_speaking(persona_id, 1.0)
            time.sleep(SPEAK_SECONDS)
            send_speaking(persona_id, 0.0)
            time.sleep(PAUSE_SECONDS)
finally:
    calm()
    print("done, orbs calm")
