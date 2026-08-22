"""
Day-1 experiment runner for Second Opinion.

Runs a visitor's opening statement past both clinician personas, then lets
them go back and forth for a set number of turns, scoring divergence after
every exchange. Prints a live transcript and saves the full run (transcript
+ scores) as JSON in logs/ — useful raw material for the weblog/sketchbook.

Usage:
    python3 src/run_experiment.py --visitor-name Alex --symptom "I've had a
        weird twitch in my eye for three days" --turns 3

    # force mock mode even if you have an API key set, e.g. to sanity-check
    # the pipeline without spending anything:
    python3 src/run_experiment.py --mock

With no ANTHROPIC_API_KEY or OPENAI_API_KEY set, it automatically runs in
mock mode using canned responses, so this works right now with zero setup.
"""

import argparse
import json
import os
from datetime import datetime, timezone

from divergence import divergence_score
from llm_client import LLMClient, get_provider
from personas import CAUTIOUS_PERSONA, CONFIDENT_PERSONA


def build_messages_for(persona_id: str, transcript: list) -> list:
    messages = []
    for turn in transcript:
        role = "assistant" if turn["speaker"] == persona_id else "user"
        label = "You" if role == "assistant" else turn["speaker"]
        messages.append({"role": role, "content": f"[{label}] {turn['text']}"})
    return messages


def run(visitor_name: str, symptom: str, turns: int, force_mock: bool):
    llm = LLMClient(force_mock=force_mock)
    provider = llm.provider
    print(f"--- provider: {provider} ---\n")

    transcript = [{"speaker": "visitor", "text": symptom}]
    scores = []

    for turn_index in range(turns):
        turn_responses = {}
        for persona in (CAUTIOUS_PERSONA, CONFIDENT_PERSONA):
            system_prompt = persona["system_prompt"].format(visitor_name=visitor_name)
            messages = build_messages_for(persona["id"], transcript)
            reply = llm.reply(
                system_prompt=system_prompt,
                conversation=messages,
                persona_id=persona["id"],
                visitor_name=visitor_name,
                turn_index=turn_index,
            )
            transcript.append({"speaker": persona["id"], "text": reply})
            turn_responses[persona["id"]] = reply
            print(f"[{persona['label']}] {reply}\n")

        score = divergence_score(turn_responses["cautious"], turn_responses["confident"])
        score["turn"] = turn_index
        scores.append(score)
        print(f"  -> divergence_score: {score['divergence_score']:.2f} "
              f"(confidence_gap={score['confidence_gap']}, "
              f"semantic_similarity={score['semantic_similarity']:.2f})\n")

    return transcript, scores, provider


def main():
    parser = argparse.ArgumentParser(description="Second Opinion — persona experiment")
    parser.add_argument("--visitor-name", default="Alex")
    parser.add_argument(
        "--symptom",
        default="I've had a weird twitch in my eye for the past three days.",
    )
    parser.add_argument("--turns", type=int, default=3)
    parser.add_argument("--mock", action="store_true", help="force mock mode")
    args = parser.parse_args()

    transcript, scores, provider = run(args.visitor_name, args.symptom, args.turns, args.mock)

    os.makedirs("logs", exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = f"logs/run_{timestamp}.json"
    with open(out_path, "w") as f:
        json.dump(
            {
                "provider": provider,
                "visitor_name": args.visitor_name,
                "symptom": args.symptom,
                "turns": args.turns,
                "transcript": transcript,
                "scores": scores,
            },
            f,
            indent=2,
        )
    print(f"Saved run to {out_path}")


if __name__ == "__main__":
    main()
