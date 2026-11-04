from pythonosc.udp_client import SimpleUDPClient

client = SimpleUDPClient("127.0.0.1", 9000)  

def send_divergence(score: dict):
    score_value = score["divergence_score"]
    client.send_message("/divergence", score_value)

def send_speaking(persona_id: str, is_speaking: float):
    """Tell TouchDesigner whether a doctor is talking right now (1.0 or 0.0).
    Arrives as the channel 'cautious_speaking' or 'confident_speaking'."""
    client.send_message(f"/{persona_id}_speaking", float(is_speaking))

def send_level(persona_id: str, level: float):
    """How loud a doctor is right now, 0 to 1. Arrives as 'cautious_level' / 'confident_level'."""
    client.send_message(f"/{persona_id}_level", float(level))

def send_thinking(persona_id: str, is_thinking: float):
    """1.0 while a doctor's reply is being written, 0.0 otherwise. Arrives as 'cautious_thinking' / 'confident_thinking'."""
    client.send_message(f"/{persona_id}_thinking", float(is_thinking))

def send_round(round_number: float):
    """Which round of the conversation it is (1, 2, 3 ...; 0 = no conversation). Arrives as the channel 'round'.
    TouchDesigner uses it to let the conflict colour build up round by round."""
    client.send_message("/round", float(round_number))
