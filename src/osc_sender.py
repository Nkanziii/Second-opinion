from pythonosc.udp_client import SimpleUDPClient

client = SimpleUDPClient("127.0.0.1", 9000)  

def send_divergence(score: dict):
    score_value = score["divergence_score"]
    client.send_message("/divergence", score_value)



def send_speaking(persona_id: str, is_speaking: float):
    """Tell TouchDesigner whether a doctor is talking right now (1.0 or 0.0).
    Arrives as the channel 'cautious_speaking' or 'confident_speaking'."""
    client.send_message(f"/{persona_id}_speaking", float(is_speaking))
