"""
Experiment runner for Second Opinion.

Runs a visitor's opening statement past both clinician personas, then lets
them go back and forth, scoring divergence after every round. Prints a live
transcript and saves the full run (transcript + scores) as JSON in logs/ —
useful raw material for the weblog/sketchbook.

Usage (from the src folder):

    # the old batch mode: typed symptom, fixed number of rounds, no visitor replies
    python3 run_experiment.py --visitor-name Alex --symptom "I've had a weird
        twitch in my eye for three days" --turns 3

    # the full installation loop: you speak, the doctors reply out loud, and
    # after each round you answer their questions, until the doctors decide
    # they have heard enough (or the round limit is reached)
    python3 run_experiment.py --voice --speak --converse

    # same conversation but typing your answers instead of speaking
    python3 run_experiment.py --converse

    # force mock mode even if you have an API key set, e.g. to sanity-check
    # the pipeline without spending anything:
    python3 run_experiment.py --mock

With no ANTHROPIC_API_KEY or OPENAI_API_KEY set, it falls back to Ollama
(local), or to canned mock responses with --mock.
"""

import argparse
import json
import os
from datetime import datetime, timezone
import re
import time
import uuid

from divergence import divergence_score
from llm_client import LLMClient, get_provider, ANTHROPIC_MODEL
from personas import CAUTIOUS_PERSONA, CONFIDENT_PERSONA, build_system_prompt
from osc_sender import send_divergence, send_speaking
from speech import speak_reply


# Phrases that let the visitor end the session early.
STOP_PHRASES = ("goodbye", "bye bye", "end the session", "i have to go",
                "i need to go", "that's all", "thats all", "bye")
CHECKIN_AFTER = 3 #consult rounds before the doctors check in
MAX_ROUNDS = 12  # safety limit for one session
DONE_WORDS = {"no", "nope", "nothing", "satisfied", "thanks", "thank", "fine", "good"}

def is_done(text: str) -> bool:
    """A shhort 'no thanks / I'm good' answer to the doctors' check-in."""
    words = re.findall(r"[a-z]+", text.lower())
    return len(words) <= 6 and any(w in DONE_WORDS for w in words)

def build_messages_for(persona_id: str, transcript: list) -> list: # the function that determins what each persona sees of the convo so far
    messages = []
    for turn in transcript:
        if turn["speaker"] == persona_id:
            messages.append({"role": "assistant", "content": turn["text"]})
        else:
            messages.append({"role": "user", "content": f"[{turn['speaker']}] {turn['text']}"})
    return messages


def wants_to_stop(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in STOP_PHRASES)


def get_visitor_reply(use_voice: bool) -> str:
    """The visitor's answer: spoken into the mic, or typed in the terminal."""
    if use_voice:
        from voice_input import listen_until_silence
        return listen_until_silence()
    try:
        return input("You: ").strip()
    except EOFError:
        return ""

# introduction + vistor name inclusion

NAME_LEADS = ("my name is", "my name's", "i am", "i'm", "im", "it's", "its", "call me", "this is")

LABELS = {"cautious": CAUTIOUS_PERSONA["label"], "confident": CONFIDENT_PERSONA["label"]}
DEFAULT_SYMPTOM = "I've had a weird twitch in my eye for the past three days."

def say_line(persona_id: str, text: str, speak: bool):
    """Print a fixed line from a doctor and, with --speak, say it aloud."""
    print(f"[{LABELS[persona_id]}] {text}\n")
    if speak:
        send_speaking(persona_id, 1.0)
        try: 
            speak_reply(persona_id, text)
        finally:
            send_speaking(persona_id, 0.0)

def extract_name(text: str) -> str:
    """Pick the name out of 'my name is Niki' or just 'Niki'."""
    cleaned = text.strip().strip(".!?,").lower()
    for lead in NAME_LEADS:
        if cleaned.startswith(lead):
            cleaned = cleaned[len(lead):].strip()
            break
    words = cleaned.split()[:1]
    return " ".join(w.capitalize() for w in words) if words else "friend"

def greet(speak: bool, use_voice: bool):
    """Both doctors say hello, ask for the visitor's name, then what brings them in."""
    say_line('cautious', "Hello, and welcome. I'm Dr. Hedges, and I like to be careful.", speak)
    say_line('confident', "And I'm Dr. Sure, and I like answers. What's your name?", speak)
    print("(your turn: say your name)")
    name = extract_name(get_visitor_reply(use_voice))
    say_line("cautious", f"Nice to meet you, {name}. What brings you in today?", speak)
    print("(your turn: describe your symptom)")
    symptom = get_visitor_reply(use_voice)
    return name, symptom

def now_iso() -> str:
    """The current time in UTC, e,g, 2026-10-21T17:20:03+00:00."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def doctors_round(llm, transcript, visitor_name, turn_index, turns, phase, speak, converse):
    """Both doctors speak once, in order. Returns {persona_id: reply}."""
    turn_responses = {}
    for persona in (CAUTIOUS_PERSONA, CONFIDENT_PERSONA):
        if converse:
            system_prompt = build_system_prompt(persona, visitor_name, turn_index, turns, phase)

        else:
            system_prompt = persona["system_prompt"].format(visitor_name=visitor_name)
        messages = build_messages_for(persona["id"], transcript)
        started=time.time()
        reply = llm.reply(
            system_prompt=system_prompt,
            conversation=messages,
            persona_id=persona["id"],
            visitor_name=visitor_name,
            turn_index=turn_index,  
        )
        took = round(time.time() - started, 2)
        transcript.append({"speaker": persona["id"], "text": reply, "time": now_iso(), "reply_seconds": took})
        turn_responses[persona["id"]] = reply
        say_line(persona["id"], reply, speak)
    return turn_responses


def run(visitor_name: str, symptom: str, turns: int, force_mock: bool,
        speak: bool = False, converse: bool = False, use_voice: bool = False):
    llm = LLMClient(force_mock=force_mock)
    provider = llm.provider
    print(f"--- provider: {provider} ---\n")

    transcript = [{"speaker": "visitor", "text": symptom, "time": now_iso()}]
    scores = []
    silent_in_a_row = 0
    rounds_since_checkin = 0
    ended_by = "round limit"

    def say_goodbye(turn_index):
        doctors_round(llm, transcript, visitor_name, turn_index + 1, turns, "farewell", speak, converse)

    for turn_index in range(turns):
        phase = "check_in" if converse and rounds_since_checkin >= CHECKIN_AFTER else "consult"
        turn_responses = doctors_round(llm, transcript, visitor_name, turn_index, turns, phase, speak, converse)

        score = divergence_score(turn_responses["cautious"], turn_responses["confident"])
        send_divergence(score)
        score["turn"] = turn_index
        scores.append(score)
        print(f"  -> divergence_score: {score['divergence_score']:.2f} "
              f"(confidence_gap={score['confidence_gap']}, "
              f"semantic_similarity={score['semantic_similarity']:.2f})\n")

        if not converse:
            continue
        rounds_since_checkin = 0 if phase == "check_in" else rounds_since_checkin + 1

        if turn_index == turns - 1:
            say_goodbye(turn_index)  # safety limit reached
            break

        print("(Your turn to answer)")
        asked = time.time()
        answer = get_visitor_reply(use_voice)
        answer_seconds = round(time.time() - asked, 2)

        if not answer:
            silent_in_a_row += 1
            if silent_in_a_row >= 2:
                ended_by = "visitor went quiet"
                say_goodbye(turn_index)
                break
            answer = "(the visitor stayed silent)"
            print(f"[You] {answer}\n")
        else:
            silent_in_a_row = 0
            if wants_to_stop(answer) or (phase == "check_in" and is_done(answer)):
                transcript.append({"speaker": "visitor", "text": answer, "time": now_iso(), "answer_seconds": answer_seconds})
                ended_by = "visitor ended it"
                say_goodbye(turn_index)
                break
        transcript.append({"speaker": "visitor", "text": answer, "time": now_iso(), "answer_seconds": answer_seconds})

    return transcript, scores, provider, ended_by

def scrub_name(transcript: list, name: str) -> list:
    """A copy of the transcript with the visitor's name replaced by [name]."""
    pattern = re.compile(re.escape(name), re.IGNORECASE)
    return [{**turn, "text": pattern.sub("[name]", turn["text"])} for turn in transcript]

def main():
    parser = argparse.ArgumentParser(description="Second Opinion — persona experiment")
    parser.add_argument("--visitor-name", default=None, help="number of rounds (default 3, or 12 with --converse)")
    parser.add_argument(
        "--symptom",
    )
    parser.add_argument("--turns", type=int, default=None,
                        help="number of rounds (default 3, or 12 with --converse)")
    parser.add_argument("--mock", action="store_true", help="force mock mode")
    parser.add_argument("--voice", action="store_true",
                        help="speak the symptom (and your answers, with --converse) into the microphone")
    parser.add_argument("--speak", action="store_true",
                        help="have each doctor speak their reply out loud (macOS)")
    parser.add_argument("--converse", action="store_true",
                        help="after each round the visitor answers, until they say goodbye")
    parser.add_argument("--listen-seconds", type=int, default=20,
                        help="longest your opening statement can be in --voice mode")
    args = parser.parse_args()

    turns = args.turns if args.turns is not None else (MAX_ROUNDS if args.converse else 3)
    session_id = uuid.uuid4().hex[:8]
    started_at = now_iso()

    if args.converse and args.symptom is None:
        visitor_name, symptom = greet(args.speak, args.voice)
        if not symptom:
            print("Did not catch anything. Try again, a bit closer to the mic.")
            return

    else:
        visitor_name = args.visitor_name or "Alex"
        symptom = args.symptom or DEFAULT_SYMPTOM
        if args.voice:
            from voice_input import listen_until_silence
            symptom = listen_until_silence(max_seconds=args.listen_seconds)
            if not symptom:
                print("Did not catch anything. Try again, a bit closer to the mic.")
                return

    transcript, scores, provider, ended_by = run(
        visitor_name, symptom, turns, args.mock,
        args.speak, args.converse, args.voice,
    )
    print(f"--- session ended: {ended_by} ---")

    os.makedirs("logs", exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = f"logs/run_{timestamp}.json"
    with open(out_path, "w") as f:
        json.dump(
            {
                "session_id": session_id,
                "started_at": started_at,
                "ended_at": now_iso(),
                "provider": provider,
                "model": ANTHROPIC_MODEL if provider == "anthropic" else provider,
                "turns": turns,
                "converse": args.converse,
                "ended_by": ended_by,
                "transcript": scrub_name(transcript, visitor_name),
                "scores": scores,
            },
            f,
            indent=2,
        )
    print(f"Saved run to {out_path}")


if __name__ == "__main__":
    main()
