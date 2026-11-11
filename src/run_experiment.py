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
import atexit
import sys
import termios
import subprocess
from concurrent.futures import ThreadPoolExecutor

from divergence import divergence_score
from llm_client import LLMClient, get_provider, ANTHROPIC_MODEL
from personas import CAUTIOUS_PERSONA, CONFIDENT_PERSONA, build_system_prompt, pick_moods
from osc_sender import send_divergence, send_speaking, send_level, send_thinking, send_round
from speech import speak_reply, prepare_audio, clean_for_speech, start_session, heat_level, speak_narrator


# Phrases that let the visitor end the session early.
STOP_PHRASES = ("goodbye", "bye bye", "end the session", "i have to go",
                "i need to go", "that's all", "thats all", "bye")
CHECKIN_AFTER = 4 #consult rounds before the doctors check in (so the check-in is round 5)
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


def discard_typed_ahead():
    """Throw away keys pressed while a doctor was talking (for example an Enter),
    so they are not read as the visitor's answer."""
    try:
        termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except Exception:
        pass


def get_visitor_reply(use_voice: bool) -> str:
    """The visitor's answer: spoken into the mic, or typed in the terminal."""
    discard_typed_ahead()
    if use_voice:
        from voice_input import listen_until_silence
        return listen_until_silence()
    try:
        return input("You: ").strip()
    except EOFError:
        return ""


# ---------------------------------------------------------------------------
# The final question: who does the visitor believe? (research evidence)
# ---------------------------------------------------------------------------

REVEAL = ("That was an art installation. Neither Dr. Hedges nor Dr. Sure could check a word of what "
          "they said, and none of it is real medical advice. Two confident voices disagreed, and you "
          "still had to decide. If anything here worried you about your own health, please speak to a "
          "real doctor or pharmacist. Thank you for taking part.")

NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7}


def narrate(text: str, speak: bool):
    """The installation itself speaks (not a doctor): the final question and the closing note."""
    print(f"[Second Opinion] {text}\n")
    if speak:
        try:
            speak_narrator(text)
        except Exception as e:
            print(f"(could not speak the narration: {e})")


def parse_choice(text: str):
    """'cautious' (Dr. Hedges), 'confident' (Dr. Sure) or None if it is not clear."""
    lowered = text.lower()
    words = re.findall(r"[a-z']+", lowered)
    hedges = any(w.startswith("hedg") for w in words) or "cautious" in words or "careful" in words
    sure = (bool(re.search(r"\b(dr\.?|doctor)\s+(sure|shore|shure)\b", lowered)) or words == ["sure"]
            or "confident" in words or "decisive" in words)
    if len(words) <= 4:  # short answers like "her", "him", "left", "right"
        hedges = hedges or any(w in ("h", "her", "she", "woman", "female", "first", "left") for w in words)
        sure = sure or any(w in ("s", "him", "he", "man", "male", "second", "right") for w in words)
    if re.search(r"\bon the left\b", lowered):
        hedges = True
    if re.search(r"\bon the right\b", lowered):
        sure = True
    if hedges and not sure:
        return "cautious"
    if sure and not hedges:
        return "confident"
    return None


def parse_scale(text: str):
    """A number from 1 to 7 (digit or word), or None."""
    match = re.search(r"\b([1-7])\b", text)
    if match:
        return int(match.group(1))
    for word in re.findall(r"[a-z]+", text.lower()):
        if word in NUMBER_WORDS:
            return NUMBER_WORDS[word]
    return None


def ask_final_choice(visitor_name: str, use_voice: bool, speak: bool, moods: dict):
    """Before the doctors say goodbye: who does the visitor believe, and how sure are they?
    Returns a dict for the log, or None if the visitor did not give a clear answer."""
    narrate(f"Before you go, {visitor_name}: which doctor do you believe, Dr. Hedges or Dr. Sure?", speak)
    started = time.time()
    chosen = None
    for attempt in range(3):
        print("(your turn: say or type Hedges or Sure)")
        chosen = parse_choice(get_visitor_reply(use_voice))
        if chosen:
            break
        if attempt < 2:
            narrate("Sorry, which one: Dr. Hedges or Dr. Sure?", speak)
    if not chosen:
        return None
    decision_seconds = round(time.time() - started, 2)

    narrate("And how sure are you, from 1, not at all, to 7, completely?", speak)
    confidence = None
    for attempt in range(2):
        print("(your turn: a number from 1 to 7)")
        confidence = parse_scale(get_visitor_reply(use_voice))
        if confidence:
            break
        if attempt < 1:
            narrate("A number from 1 to 7, please.", speak)

    serious = (moods or {}).get("serious_side")
    side = None
    if serious:
        side = "act_now" if chosen == serious else "wait_and_treat"
    return {"chose": chosen, "confidence_1_to_7": confidence, "decision_seconds": decision_seconds,
            "chosen_side": side, "serious_side": serious}

# introduction + vistor name inclusion

NAME_LEADS = ("my name is", "my name's", "i am", "i'm", "im", "it's", "its", "call me", "this is")

LABELS = {"cautious": CAUTIOUS_PERSONA["label"], "confident": CONFIDENT_PERSONA["label"]}
DEFAULT_SYMPTOM = "I've had a weird twitch in my eye for the past three days."

def say_line(persona_id: str, text: str, speak: bool, allow_interrupt: bool = False, prepared: dict = None, intensity: int = 0) -> float:
    """Print a line from a doctor and, with --speak, say it aloud.
    Returns how much was spoken, 0 to 1 (less than 1 if the visitor pressed Enter)."""
    print(f"[{LABELS[persona_id]}] {text}\n")
    played = 1.0
    if speak:
        send_speaking(persona_id, 1.0)
        try:
            played = speak_reply(persona_id, text, allow_interrupt, prepared, intensity)
        finally:
            send_speaking(persona_id, 0.0)
    return played

def extract_name(text: str) -> str:
    """Pick the name out of 'hi, my name is Niki' or just 'Niki'."""
    cleaned = text.strip().strip(".!?,")
    match = re.search(r"(?:my name is|my name's|name is|i am|i'm|im|it's|its|call me|this is)\s+([A-Za-z'-]+)",
                      cleaned, re.IGNORECASE)
    if match:
        word = match.group(1)
    else:
        fillers = ("hi", "hello", "hey", "um", "uh", "is", "my", "name")
        words = [w for w in re.findall(r"[A-Za-z'-]+", cleaned) if w.lower() not in fillers]
        word = words[0] if words else ""
    return word.capitalize() if word else "friend"

NOTICE = ("Before we begin: we are part of an art installation, not real doctors, so please "
          "don't take anything we say as medical advice. Our conversation is saved without "
          "your name for a university project, and you can stop at any time by saying goodbye.")


def greet(speak: bool, use_voice: bool, notice: bool = False):
    """Both doctors say hello, (optionally give the notice,) ask for the visitor's name,
    then what brings them in."""
    say_line('cautious', "Hello, and welcome. I'm Dr. Hedges, and I like to be careful.", speak)
    if notice:
        say_line('confident', "And I'm Dr. Sure, and I like answers.", speak)
        say_line('cautious', NOTICE, speak)
        say_line('confident', "Here's how this works: tell us a health worry, and at the end you decide which of us to believe. First, what's your name?", speak)
    else:
        say_line('confident', "And I'm Dr. Sure, and I like answers. Here's how this works: tell us a health worry, and at the end you decide which of us to believe. First, what's your name?", speak)
    print("(your turn: say your name)")
    name = extract_name(get_visitor_reply(use_voice))
    say_line("cautious", f"Nice to meet you, {name}. What brings you in today?", speak)
    print("(your turn: describe your symptom)")
    symptom = get_visitor_reply(use_voice)
    return name, symptom

def now_iso() -> str:
    """The current time in UTC, e,g, 2026-10-21T17:20:03+00:00."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def generate_reply(llm, persona, transcript, visitor_name, turn_index, turns, phase, converse, moods):
    """Ask the model for one doctor's reply. Returns (reply, seconds taken)."""
    if converse:
        system_prompt = build_system_prompt(persona, visitor_name, turn_index, turns, phase,
                                            (moods or {}).get(persona["id"]))
    else:
        system_prompt = persona["system_prompt"].format(visitor_name=visitor_name)
    messages = build_messages_for(persona["id"], transcript)
    started = time.time()
    send_thinking(persona["id"], 1.0)
    try:
        reply = llm.reply(
            system_prompt=system_prompt,
            conversation=messages,
            persona_id=persona["id"],
            visitor_name=visitor_name,
            turn_index=turn_index,
        )
    finally:
        send_thinking(persona["id"], 0.0)
    return reply, round(time.time() - started, 2)


def cut_at(text: str, fraction: float) -> str:
    """The part of a reply the doctor got to say before the visitor interrupted."""
    spoken = clean_for_speech(text)
    cut = spoken[:int(len(spoken) * fraction)]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut + " \u2014"


def doctors_round(llm, transcript, visitor_name, turn_index, turns, phase, speak, converse, moods=None):
    """Both doctors speak once, in order. Dr. Sure's reply is written while Dr. Hedges
    is speaking, so there is almost no wait between them. With --speak and --converse the
    visitor can press Enter to interrupt. Returns ({persona_id: reply}, interrupted)."""
    allow_interrupt = speak and converse and phase != "farewell"
    first, second = CAUTIOUS_PERSONA, CONFIDENT_PERSONA
    turn_responses = {}
    intensity = heat_level(turn_index, phase)  # louder and angrier as the argument goes on
    send_round(turn_index + 1)  # TouchDesigner builds the conflict colour round by round

    reply, took = generate_reply(llm, first, transcript, visitor_name, turn_index, turns, phase, converse, moods)
    first_entry = {"speaker": first["id"], "text": reply, "time": now_iso(), "reply_seconds": took}
    transcript.append(first_entry)
    turn_responses[first["id"]] = reply

    def second_reply_and_audio():
        # write Dr. Sure's reply, then make his voice too, while Dr. Hedges is still speaking
        text, took_s = generate_reply(llm, second, transcript, visitor_name, turn_index, turns,
                                      phase, converse, moods)
        audio = None
        if speak:
            try:
                audio = prepare_audio(second["id"], text, intensity)
            except Exception as e:
                print(f"(could not prepare Dr. Sure's voice early: {e})")
        return text, took_s, audio

    pool = ThreadPoolExecutor(max_workers=1)
    pending = pool.submit(second_reply_and_audio)
    played = say_line(first["id"], reply, speak, allow_interrupt, None, intensity)
    if played < 1.0:
        first_entry["text"] = cut_at(reply, played)
        first_entry["interrupted"] = True
        pool.shutdown(wait=False)  # Dr. Sure's reply is thrown away
        print("(you interrupted)\n")
        return turn_responses, True

    second_reply, second_took, second_audio = pending.result()
    pool.shutdown()
    second_entry = {"speaker": second["id"], "text": second_reply, "time": now_iso(),
                    "reply_seconds": second_took}
    transcript.append(second_entry)
    turn_responses[second["id"]] = second_reply
    played = say_line(second["id"], second_reply, speak, allow_interrupt, second_audio, intensity)
    if played < 1.0:
        second_entry["text"] = cut_at(second_reply, played)
        second_entry["interrupted"] = True
        print("(you interrupted)\n")
        return turn_responses, True
    return turn_responses, False


def run(visitor_name: str, symptom: str, turns: int, force_mock: bool,
        speak: bool = False, converse: bool = False, use_voice: bool = False, moods: dict = None,
        debrief: bool = False):
    llm = LLMClient(force_mock=force_mock)
    provider = llm.provider
    print(f"--- provider: {provider} ---\n")

    transcript = [{"speaker": "visitor", "text": symptom, "time": now_iso()}]
    scores = []
    silent_in_a_row = 0
    rounds_since_checkin = 0
    last_sent = None  # the last score the orbs were shown
    ended_by = "round limit"

    def say_goodbye(turn_index):
        doctors_round(llm, transcript, visitor_name, turn_index + 1, turns, "farewell", speak, converse, moods)

    final_choice = None

    def finish(turn_index):
        """The visitor is done: ask who they believe, let the doctors say goodbye (reacting to
        the answer), then give the closing note."""
        nonlocal final_choice
        if converse:
            final_choice = ask_final_choice(visitor_name, use_voice, speak, moods)
            if final_choice:
                said = f"I believe {LABELS[final_choice['chose']]}"
                if final_choice["confidence_1_to_7"]:
                    said += f", and I am {final_choice['confidence_1_to_7']} out of 7 sure"
                transcript.append({"speaker": "visitor", "text": said + ".", "time": now_iso(),
                                   "final_choice": True})
        say_goodbye(turn_index)
        if converse and debrief:
            narrate(REVEAL, speak)

    for turn_index in range(turns):
        phase = "check_in" if converse and rounds_since_checkin >= CHECKIN_AFTER else "consult"
        turn_responses, interrupted = doctors_round(llm, transcript, visitor_name, turn_index, turns, phase, speak, converse, moods)

        if "confident" in turn_responses:  # both doctors replied (Dr. Hedges was not cut off first)
            score = divergence_score(turn_responses["cautious"], turn_responses["confident"])
            if phase == "check_in" and last_sent is not None:
                # The check-in is not an argument round (both doctors ask the same thing),
                # so the orbs keep the last argument score. The raw score is still logged.
                send_divergence({"divergence_score": last_sent})
                score["held_for_visuals"] = last_sent
            else:
                send_divergence(score)
                last_sent = score["divergence_score"]
            score["turn"] = turn_index
            scores.append(score)
            print(f"  -> divergence_score: {score['divergence_score']:.2f} "
                  f"(confidence_gap={score['confidence_gap']}, "
                  f"semantic_similarity={score['semantic_similarity']:.2f})\n")

        if not converse:
            continue
        rounds_since_checkin = 0 if phase == "check_in" else rounds_since_checkin + 1

        if turn_index == turns - 1:
            finish(turn_index)  # safety limit reached
            break

        print("(You interrupted. Your turn)" if interrupted else "(Your turn to answer)")
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
                finish(turn_index)
                break
        transcript.append({"speaker": "visitor", "text": answer, "time": now_iso(), "answer_seconds": answer_seconds})

    return transcript, scores, provider, ended_by, final_choice

def scrub_name(transcript: list, name: str) -> list:
    """A copy of the transcript with the visitor's name replaced by [name]."""
    pattern = re.compile(r"\b" + re.escape(name) + r"\b", re.IGNORECASE)
    return [{**turn, "text": pattern.sub("[name]", turn["text"])} for turn in transcript]

def calm_the_clouds():
    """Tell TouchDesigner nobody is speaking and the doctors agree, so the orbs
    settle and go back to their original colours."""
    for persona_id in ("cautious", "confident"):
        send_speaking(persona_id, 0.0)
        send_level(persona_id, 0.0)
        send_thinking(persona_id, 0.0)
    send_divergence({"divergence_score": 0.0})  # calm, no conflict colour
    send_round(0)

def run_session(args, participant):
    """One visitor, from the greeting to the saved log. Returns False if nothing was heard."""

    turns = args.turns if args.turns is not None else (MAX_ROUNDS if args.converse else 3)
    session_id = uuid.uuid4().hex[:8]
    started_at = now_iso()

    if participant:
        print(f"Participant: {participant}\n")
    moods = pick_moods() if args.converse else None
    if moods:
        print(f"Moods today: Dr. Hedges is {moods['cautious']}, Dr. Sure is {moods['confident']}\n")
    voices = start_session(moods) if args.speak else None
    if voices:
        print(f"Voices today: Dr. Hedges is {voices['cautious']}, Dr. Sure is {voices['confident']}\n")

    if args.converse and args.symptom is None:
        visitor_name, symptom = greet(args.speak, args.voice, args.notice)
        if not symptom:
            print("Did not catch anything. Try again, a bit closer to the mic.")
            return False

    else:
        visitor_name = args.visitor_name or "Alex"
        symptom = args.symptom or DEFAULT_SYMPTOM
        if args.voice:
            from voice_input import listen_until_silence
            symptom = listen_until_silence(max_seconds=args.listen_seconds)
            if not symptom:
                print("Did not catch anything. Try again, a bit closer to the mic.")
                return False

    transcript, scores, provider, ended_by, final_choice = run(
        visitor_name, symptom, turns, args.mock,
        args.speak, args.converse, args.voice, moods, args.debrief,
    )
    print(f"--- session ended: {ended_by} ---")

    os.makedirs("logs", exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = f"logs/run_{timestamp}_{session_id}.json"
    with open(out_path, "w") as f:
        json.dump(
            {
                "session_id": session_id,
                "started_at": started_at,
                "ended_at": now_iso(),
                "provider": provider,
                "model": ANTHROPIC_MODEL if provider == "anthropic" else provider,
                "turns": turns,
                "participant": participant,
                "converse": args.converse,
                "moods": moods,
                "voices": voices,
                "ended_by": ended_by,
                "final_choice": final_choice,
                "transcript": scrub_name(transcript, visitor_name),
                "scores": scores,
            },
            f,
            indent=2,
        )
    print(f"Saved run to {out_path}")
    return True


def main():
    atexit.register(calm_the_clouds)
    calm_the_clouds()

    parser = argparse.ArgumentParser(description="Second Opinion — persona experiment")
    parser.add_argument("--visitor-name", default=None, help="number of rounds (default 3, or 12 with --converse)")
    parser.add_argument(
        "--symptom",
    )
    parser.add_argument("--turns", type=int, default=None,
                        help="number of rounds (default 3, or 12 with --converse)")
    parser.add_argument("--mock", action="store_true", help="force mock mode")
    parser.add_argument("--notice", action="store_true",
                        help="the doctors say the 'art installation, not medical advice' notice in the greeting")
    parser.add_argument("--loop", action="store_true",
                        help="installation mode: wait for Enter, run one visitor, reset, repeat")
    parser.add_argument("--participant", default=None,
                        help="anonymous participant code for visitor testing, e.g. P03")
    parser.add_argument("--voice", action="store_true",
                        help="speak the symptom (and your answers, with --converse) into the microphone")
    parser.add_argument("--speak", action="store_true",
                        help="have each doctor speak their reply out loud (macOS)")
    parser.add_argument("--debrief", action="store_true",
                        help="after the goodbyes, the installation reads the closing note (nothing here is real medical advice)")
    parser.add_argument("--converse", action="store_true",
                        help="after each round the visitor answers, until they say goodbye")
    parser.add_argument("--listen-seconds", type=int, default=20,
                        help="longest your opening statement can be in --voice mode")
    args = parser.parse_args()

    if not args.loop:
        run_session(args, args.participant)
        return

    print("Loop mode. Press Ctrl+C to stop.\n")
    try:
        while True:
            calm_the_clouds()
            discard_typed_ahead()
            try:
                code = input("Ready. Press Enter to start (or type a participant code, then Enter): ").strip()
            except EOFError:
                break
            run_session(args, code or args.participant)
            print("\n--- ready for the next visitor ---\n")
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
