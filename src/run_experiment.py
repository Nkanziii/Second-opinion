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
import re
from datetime import datetime, timezone

from divergence import divergence_score
from llm_client import LLMClient, get_provider
from personas import CAUTIOUS_PERSONA, CONFIDENT_PERSONA, build_system_prompt
from osc_sender import send_divergence, send_speaking
from speech import speak_reply

# Phrases that let the visitor end the session early.
STOP_PHRASES = ("goodbye", "bye bye", "end the session", "i have to go",
                "i need to go", "that's all", "thats all")

# Dr. Sure's "Final verdict: yes/no" line (see personas.build_system_prompt).
VERDICT_PATTERN = re.compile(r"^[ \t]*Final verdict:\s*(yes|no)[ \t]*\n?",
                             re.IGNORECASE | re.MULTILINE)


def build_messages_for(persona_id: str, transcript: list) -> list: # the function that determins what each persona sees of the convo so far
    messages = []
    for turn in transcript:
        if turn["speaker"] == persona_id:
            messages.append({"role": "assistant", "content": turn["text"]})
        else:
            messages.append({"role": "user", "content": f"[{turn['speaker']}] {turn['text']}"})
    return messages


def split_verdict(reply: str):
    """Remove the 'Final verdict' line from a reply. Returns (clean reply,
    True if the doctor said yes, i.e. is concluding the consultation)."""
    match = VERDICT_PATTERN.search(reply)
    concluding = bool(match and match.group(1).lower() == "yes")
    return VERDICT_PATTERN.sub("", reply).strip(), concluding


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


def run(visitor_name: str, symptom: str, turns: int, force_mock: bool,
        speak: bool = False, converse: bool = False, use_voice: bool = False):
    llm = LLMClient(force_mock=force_mock)
    provider = llm.provider
    print(f"--- provider: {provider} ---\n")

    transcript = [{"speaker": "visitor", "text": symptom}]
    scores = []
    silent_in_a_row = 0
    ended_by = "round limit"

    for turn_index in range(turns):
        turn_responses = {}
        concluding = False
        for persona in (CAUTIOUS_PERSONA, CONFIDENT_PERSONA):
            if converse:
                system_prompt = build_system_prompt(persona, visitor_name, turn_index, turns)
            else:
                system_prompt = persona["system_prompt"].format(visitor_name=visitor_name)
            messages = build_messages_for(persona["id"], transcript)
            reply = llm.reply(
                system_prompt=system_prompt,
                conversation=messages,
                persona_id=persona["id"],
                visitor_name=visitor_name,
                turn_index=turn_index,
            )
            if converse and persona["id"] == "confident":
                reply, concluding = split_verdict(reply)
            transcript.append({"speaker": persona["id"], "text": reply})
            turn_responses[persona["id"]] = reply
            print(f"[{persona['label']}] {reply}\n")
            if speak:
                send_speaking(persona["id"], 1.0)
                try:
                    speak_reply(persona["id"], reply)
                finally:
                    send_speaking(persona["id"], 0.0)

        score = divergence_score(turn_responses["cautious"], turn_responses["confident"])
        send_divergence(score)
        score["turn"] = turn_index
        scores.append(score)
        print(f"  -> divergence_score: {score['divergence_score']:.2f} "
              f"(confidence_gap={score['confidence_gap']}, "
              f"semantic_similarity={score['semantic_similarity']:.2f})\n")

        if not converse:
            continue
        if concluding:
            ended_by = "doctors concluded"
            break
        if turn_index == turns - 1:
            break  # round limit reached: the final verdict was just given

        # Visitor's turn to answer.
        print("(your turn to answer)")
        answer = get_visitor_reply(use_voice)
        if not answer:
            silent_in_a_row += 1
            if silent_in_a_row >= 2:
                ended_by = "visitor went quiet"
                break
            answer = "(the visitor stayed silent)"
            print(f"[You] {answer}\n")
        else:
            silent_in_a_row = 0
            if wants_to_stop(answer):
                transcript.append({"speaker": "visitor", "text": answer})
                ended_by = "visitor ended it"
                break
        transcript.append({"speaker": "visitor", "text": answer})

    return transcript, scores, provider, ended_by


def main():
    parser = argparse.ArgumentParser(description="Second Opinion — persona experiment")
    parser.add_argument("--visitor-name", default="Alex")
    parser.add_argument(
        "--symptom",
        default="I've had a weird twitch in my eye for the past three days.",
    )
    parser.add_argument("--turns", type=int, default=None,
                        help="number of rounds (default 3, or 5 with --converse)")
    parser.add_argument("--mock", action="store_true", help="force mock mode")
    parser.add_argument("--voice", action="store_true",
                        help="speak the symptom (and your answers, with --converse) into the microphone")
    parser.add_argument("--speak", action="store_true",
                        help="have each doctor speak their reply out loud (macOS)")
    parser.add_argument("--converse", action="store_true",
                        help="after each round the visitor answers, and the doctors decide when to wrap up")
    parser.add_argument("--listen-seconds", type=int, default=20,
                        help="longest your opening statement can be in --voice mode")
    args = parser.parse_args()

    turns = args.turns if args.turns is not None else (5 if args.converse else 3)

    symptom = args.symptom
    if args.voice:
        from voice_input import listen_until_silence
        symptom = listen_until_silence(max_seconds=args.listen_seconds)
        if not symptom:
            print("Did not catch anything. Try again, a bit closer to the mic.")
            return

    transcript, scores, provider, ended_by = run(
        args.visitor_name, symptom, turns, args.mock,
        args.speak, args.converse, args.voice,
    )
    print(f"--- session ended: {ended_by} ---")

    os.makedirs("logs", exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = f"logs/run_{timestamp}.json"
    with open(out_path, "w") as f:
        json.dump(
            {
                "provider": provider,
                "visitor_name": args.visitor_name,
                "symptom": symptom,
                "turns": turns,
                "converse": args.converse,
                "ended_by": ended_by,
                "transcript": transcript,
                "scores": scores,
            },
            f,
            indent=2,
        )
    print(f"Saved run to {out_path}")


if __name__ == "__main__":
    main()
