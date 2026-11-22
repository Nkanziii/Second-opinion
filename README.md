# Second Opinion

An interactive installation about trust in AI advice. Two AI doctors, one cautious and one confident, listen to a visitor's health worry, give different diagnoses and argue about whose is right. Each doctor is a glowing orb in TouchDesigner that changes colour and shape as their disagreement grows. At the end the visitor chooses which doctor they believe and how sure they are.

**Research question:** how does viewing multi-agent systems disagreeing affect user trust in AI-generated advice, explored through healthcare?

MSc Creative Computing final project, UAL Creative Computing Institute. Author: Niki Khanezai. Supervisor: Louis Busby.

## Where to look first

- **[`Second-opinion.md`](Second-opinion.md)** is the project weblog: the project and technical descriptions, demo videos, final prototype images, dated entries showing how the project developed, a list of every file, and the references.
- **Demo videos:** [Demo video 1](https://youtube.com/shorts/U_fWN9pFOxY) and [Demo video 2](https://youtu.be/20xMTaUQ-HQ).

## How it works

1. The visitor speaks into a microphone. Whisper (faster-whisper, running on the laptop) turns the speech into text.
2. Claude Sonnet 5.5 writes each doctor's reply from two prompts in `src/personas.py`: Dr. Hedges (cautious) and Dr. Sure (confident).
3. `src/divergence.py` scores how much the doctors disagree, from 0 to 1.
4. `src/osc_sender.py` sends the score, who is speaking, loudness and the round number to TouchDesigner over OSC (localhost, port 9000).
5. TouchDesigner (`visuals/persona_cloud.toe`) draws the two orbs, which change with the disagreement.
6. OpenAI text-to-speech reads the replies aloud, with Dr. Hedges on the left speaker and Dr. Sure on the right.
7. Each session is saved as an anonymised JSON log.

## What you need

- A Mac (the program uses the macOS `afplay` and `say` commands), a microphone and speakers.
- Python 3 and the packages in `requirements.txt`.
- [TouchDesigner](https://derivative.ca/).
- An Anthropic API key (for the doctors) and an OpenAI API key (for the voices).

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env     # then add your API keys to .env
```

The `.env` file is not in the repo and must never be committed.

## Running it

The easiest way is to double-click `launch-second-opinion.command`. It opens the TouchDesigner project, waits for the orbs to load, then starts the doctors in loop mode.

To run it yourself, open `visuals/persona_cloud.toe` in TouchDesigner, then:

```bash
cd src
python3 run_experiment.py --converse --speak --voice --loop
```

Press Enter to start a session. Other useful options:

| Option | What it does |
|---|---|
| `--converse` | A back-and-forth consultation, with the visitor answering after each round. |
| `--speak` | The doctors speak aloud (otherwise they only print text). |
| `--voice` | The visitor answers by microphone (otherwise they type). |
| `--loop` | Resets after each visitor and waits for the next one. |
| `--mock` | Uses canned replies, with no API calls. |
| `--notice` | The doctors say the "art installation, not medical advice" notice. |

To test only the visuals, with no microphone, doctors or API, run `python3 test_orbs.py` from the `src` folder. It plays a fake argument into TouchDesigner.

## What is in this repo

| Folder or file | What it is |
|---|---|
| `src/` | The Python program: conversation, personas, scoring, voices, speech input and OSC. |
| `visuals/` | The TouchDesigner project, screenshots from the build, user testing photos and the moodboard. |
| `hardware/mat_leonardo/` | The Arduino sketch for the pressure mat prototype, which starts a session when stepped on. |
| `Second-opinion.md` | The weblog. |
| `launch-second-opinion.command` | One-click launcher. |

The weblog has a full table of every file and what it does.

## Privacy

Participants were given an information sheet and consent form. Names are replaced by `[name]` in the saved logs, and the voice is never recorded. The session logs (`src/logs/`) are deliberately not in this repo.

## Status

This is a prototype. It was tested with four participants on 20 November 2026, and the results are exploratory. The pressure mat was not used in testing. The doctors were changed after that test so that neither takes an extreme position, and the new version has not yet been tested with participants. The weblog explains both versions.

## AI use

I used an AI assistant (Claude Sonnet 5.5) throughout this project. The disclosure at the top of the weblog records what it did and what I did.
