from pythonosc.udp_client import SimpleUDPClient

client = SimpleUDPClient("127.0.0.1", 9000)  

def send_divergence(score: dict):
    score_value = score["divergence_score"]
    client.send_message("/divergence", score_value)

