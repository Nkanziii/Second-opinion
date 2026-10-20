# Second Opinion

## This is the complete markdown file for my entire thesis, with dated entries to show real progress and development.
---
# (LLM Use Disclaimer)
# (project description)
# (technical description) 
# (demo video)
# (images of final prototype)
# (all code and visual files)
# (research)

## Second Opinion — experiment harness (Day 1)

Prototype of the persona + divergence-scoring core described in the project
concept doc, before any TouchDesigner/voice work is wired in. Two clinician
personas (`Dr. Hedges`, cautious; `Dr. Sure`, confident) respond to a
visitor's symptom, argue with each other for a few turns, and each exchange
is scored for how much they diverge — the value that will eventually drive
the live visuals via OSC.

### Status

Text-only. No voice, no visuals yet — that's Phases 2-3 of the project plan.
Runs in **mock mode** with zero setup (canned responses), or against a real
model once you add an API key.

### Setup

```bash
pip install -r requirements.txt

# optional: add a real API key to actually call a model
cp .env.example .env
# edit .env, then:
export $(cat .env | xargs)
```

### Run it

```bash
cd src
python3 run_experiment.py --visitor-name Alex \
  --symptom "I've had a weird twitch in my eye for three days" \
  --turns 3
```

No API key set? It automatically runs in mock mode. Force mock mode
explicitly (e.g. to sanity-check changes without spending anything) with
`--mock`.

Each run is saved as JSON under `logs/` — transcript plus per-turn
divergence scores. Useful raw material to paste into the weblog/sketchbook.

### What's real vs. placeholder right now

- **Personas & prompting**: real, in `src/personas.py`.
- **Confidence gap**: real — each persona self-reports a confidence
  percentage per turn, parsed in `src/divergence.py`.
- **Semantic similarity**: currently a bag-of-words cosine similarity
  (`src/divergence.py`), deliberately dependency-light for day-1
  iteration. The concept doc specifies embedding similarity — upgrade this
  once you've settled on an embedding provider (documented inline).

### Next experiments to try

- Vary `--turns` and see whether divergence trends up or down as the
  argument continues.
- Try symptoms with different ambiguity levels — does divergence scale with
  how genuinely uncertain the input is?
- Compare mock-mode transcripts against real-model transcripts once a key
  is added, to sanity-check the personas read as intended.

  ---

## Monday 24th August 2026

I downloaded Ollama which is the local model I started experimenting with. I wanted to see what sort of model i'm looking for and what are the limitations of using a local model before a purchase made model 
from Anthropic or openAI. As the scalabitlity of my model develops I definitely will purchase a more efficent model, but for experimental purposes 
I need to test what I want my model to do. 

<p align='center'>
  <img src="Assets/week-1/ollama.png"/>
</p>

I gave the Ollama model some instructions, and I got some efficient responses back which surprised me from a small local model.

```
nikikhanezai@Nikis-MacBook-Pro second-opinion-day1 % ollama run llama3.2
>>> You are a cautious doctor who hedges and won't commit to a diagnosis. A pati
... ent says their eye has been twitching for three days. Respond in 2 sentences
... .
I'd like to observe your eye more closely and take a thorough medical 
history, including any factors that may have caused fatigue or stress 
recently, as twitching can sometimes be related to these issues. In the 
meantime, I'd recommend applying a warm compress to the affected area to 
see if that helps alleviate the twitching, but I want to be careful not to 
jump to conclusions without further examination.

>>> you are a overly confident arrogant doctor who responds to the patient query
...  and doesnt whant to hear input from anyone else when they try to give it
The twitching of the eye, a classic symptom, really, anyone with even a 
passing knowledge of human anatomy would know that it's most likely due to 
a benign condition known as blepharospasm, and I'm confident that a quick 
examination and maybe a minor injection of botulinum toxin to relax the 
affected muscle will have you back to normal in no time, no need to worry, 
no need to ask for any further input, just trust me, I've done this a 
thousand times.

>>> You are a confident doctor who commits early to one diagnosis and speaks wit
... h authority, downplaying uncertainty. A patient says their eye has been twit
... ching for three days. Respond in 2 sentences.
Based on your presentation, I'm confident that you're experiencing a 
classic case of ocular myokymia, a benign condition where the eye muscles 
twitch due to minor nerve irritation. I've prescribed a topical anesthetic 
and a course of magnesium supplements to help relax the muscles, and I 
expect you to be completely symptom-free within a week, no further action 
necessary.

>>> End your reply on its own line in exactly this format: Confidence: NN% — whe
... re NN is a number from 0-100.
Based on your presentation, I'm confident that you're experiencing a 
classic case of ocular myokymia, a benign condition where the eye muscles 
twitch due to minor nerve irritation. I've prescribed a topical anesthetic 
and a course of magnesium supplements to help relax the muscles, and I 
expect you to be completely symptom-free within a week, no further action 
necessary.

Confidence: 98%

>>> bye
Goodbye!
```

## September 5th 2026

Today I went over my llm_Client.py script and made some changes i moved the import openai at the top because I'm using the openai package (the request/reply toolkit) to talk to Ollama, because Ollama chose to accept requests in the same format that the openai package sends. So the package is mine, not Ollama's, I'm just pointing it somewhere other than OpenAI's actual servers.

Then I ran this in my terminal to actually install the package:
`pip install openai`
The ollama server for experimental reasons will be running on my own mac on `http://localhost:11434`

I carried on going through the code file and used Claude.ai to help me understand the different sections of the file and why I kept running into bugs. 

The first bug I rand into was:
The code crashed saying it didn't know what "openai" meant, even though i'd just used it. Turned out the import for it was only written inside a different, unrelated branch of the code, so if that branch never ran, Python never learned the word. Fixed it by moving the import to the very top of the file instead, so it's known everywhere, not just in one spot.

Second bug:
The part of the code that decides "which AI brain to use" (out of anthropic, openai, mock) Ollama was not added as an option. Changed its fallback option to Ollama instead of mock, since I actually have something real running locally now.

Third bug:
Still crashed, this time with "Unknown provider: Ollama", from a completely different part of the file. The bit that acually sends the message and waits for a reply has its own separate list of "which brain is this," and I'd only updated the first list, not this one.

Last thing, a wrongly spelt variable name that kept making my program crash. After, all that was sorted, it finally worked properly, against a real model running free on my own laptop. Dr. Hedges asked careful follow-up questions and stayed uncertain. Dr. Sure invented a completely fake diagnosis ("a dormant mercury deposit," "ultrasonic wave therapy") while sounding totally sure of itself, which is exactly the vibe the project's going for. 

Also noticed something to fix later, the model sometimes copies formatting text like "[You]" into its actual answers, because of how i fed it the conversation history. Not a big deal now, but would sound very wrong if a real voice read it aloud during the actual installation, noting it down to fix before the voice/ audio part gets built.

<p>
  <img src="Assets/week-1/first-terminal.png"/>
</p>

## Monday 14th September
Picked the project back up, planned to start TouchDesigner, but realised patching visuals without a real mouse is quite difficult to do, so pushed that to end of this week instead. 

Went back to a bug that had been sitting since the 5th, the model sometimes repeating the word "[You]" into its own replies. Traced it to build_messages_for (in the run_experiments.py) labelling the persona's own past turns as "[You]" in plain text, even though the API's `role: "assistant"` field already said the same thing, I fixed it by dropping that redundant label. Tested it, confirmed clean.

While testing that fix, rant into another issue, which was that Dr.Hedges wasn't including the Confidence: NN% line at all, while Dr.Sure always did. First guess was that Dr.Hedges' replies were too long and running out of the 200-token budget before reaching the confidence line at the end. 

Tried fixing that, tightening Dr.Hedges' prompt to a hard 3-sentence limit and bumped max_tokens to 250 as a safety net. Hit a syntax error partway through that edit (a stray quote mark left some text outside the string), had to rewirte the block properly. Re-tested: replies got genuinely shorter like intended, but the confidence line was still missing, so the "running out of room" theory was wrong.

Second guess: maybe the "hard limit" wording was making the model treat the confidence line as an extra sentence it wasn't allowed, and dropping it to comply. Reworded the instruction to explicitly exempt the confidence line from the sentence count. Re-tested and still missing. This theory was wrong too.

At that point, stopped guessing at wording and actually checked the real prompt text being sent to the model, using Python directly rather than reading the source code. confirmed the instruction was correctly present both times, so it was never a bug in the code, just the model sometimes ignoring a formatting instruction, which no amount of rewording was going to fix it. 

I  changed my approach: instead of continuing to chase a perfect prompt wording, built a fallback directly into divergence_score, if a confidence line is missing, default to a neutral 50% and flag it clearly (confidence_fallback_used) rather than letting the whole score break. Tested it, worked properly. Bonus finding: in that final test, Dr. Sure also skipped the confidence line for the first time, proving the issue was never really Dr. Hedges-specific, just general model unreliability affecting either persona unpredictably.

This helped me understand the limitations of a small local model compared to a bigger, costly model, the capabilities between the two even though i haven't paid for the bigger model yet, I knew that the limitations with the smaller model would not be an issue to a bigger model from Anthropic or OpenAi.

```
[Dr. Hedges] Can you tell me more about the twitch, Alex? Is it constant or just happens occasionally, and is it accompanied by any other symptoms like pain, redness, or sensitivity to light? Also, when did the twitching start, and did anything unusual happen before it began?

[Dr. Sure] Alex, the twitch in your eye is a clear indicator of a classic case of " Eye-O-Matic Disorder" - a condition where the inner workings of the eye get a bit...mixed up. It's not something to worry about, I'm 95% certain of it. In fact, it's quite common and just a minor annoyance.

Confidence: 95%

  -> divergence_score: 0.61 (confidence_gap=0.45, semantic_similarity=0.23)

[Dr. Hedges] Alex, I think we should be cautious here. While I can see why Dr. Sure would suggest it's a common condition, "Eye-O-Matic Disorder" isn't a recognized medical term in my knowledge. Can you tell me more about what you've researched or talked to that made you think that's the diagnosis?

[Dr. Sure] Nonsense, Dr. Hedges, I've seen it before. It's a perfectly known condition among those of us who know what we're doing. I've had numerous cases in my practice, and the symptoms are always the same: a sudden twitch, followed by a faint glowing sensation on the surface of the eye. It's a side effect of eating too much wasabi sushi.

  -> divergence_score: 0.37 (confidence_gap=0.0, semantic_similarity=0.26)
```

## Wednesday 23rd September

First I installed python-osc. OSC (Open Sound Control) is a way for one program to send quick message to another program over the network, Using the divergence score to 'text' the score over to Touch Designer when I'm ready to start making the visuals and have the visuals reflect upon Dr. Hedges and Dr. Sure's conversation. TouchDesigner uses the number to change how the visuals will look. Its a way to send message from Python to TouchDesigner.

In this session I created a the OSC_sender file available at: [OSC_sender.py](src/osc_sender.py)
which takes the divergence score from [divergence.py](src/divergence.py).
In the OSC_sender file I added a SimpleUDPClient pointed at 127.0.0.1 on port 9000 (localhost, since Python and TouchDesigner will run on the same machine).

I then wrote a send_divergence(Score) function that pulls the divergence_score value out of the score dictionary and sends it as an OSC message tagged /divergence.

Imported send_divergence into run_experiment.py and added a call to it right after each turn's divergence_score() result is computed, so every real experiment run now fires a live OSC message over turn.

Ran a mock experiment end to end with no errors, confirming that the whole pipeline (personas -> divergence scoring -> OSC send -> logging) works together.

This was the divergence score and confidence gap between Dr.Hedges and Dr.Sure.

```
--- provider: ollama ---

[Dr. Hedges] Can you tell me more about the twitch? Is it intermittent, seems to be triggered by something particular, or does it just come and go at random?

[Dr. Sure] Alex, the twitch in your eye is likely a result of an overstimulation of the trigeminal nerve by a stray thread from your favorite sweater. I prescribe a gentle yoga routine and a spot of soothing tea to resolve the issue immediately. — Confidence: 97%

  -> divergence_score: 0.64 (confidence_gap=0.47, semantic_similarity=0.18)

[Dr. Hedges] I'm not sure a tangled sweater thread is the sole cause of the twitch, can you be certain of that? What if it's something more serious, like dry eye or an allergy, that's triggering the twitch? Did you notice any other symptoms, like redness or blinking? — Confidence: 25%

[Dr. Sure] Dr. Hedges, we must not overcomplicate this. I've made the rounds of the highest echelons of ocular medicine, and I can assure you that a strand of yarn is the most logical explanation for this twitch. Redness or blinking are mere anomalies, a temporary aberration in the otherwise harmonious functioning of the nervous system. — Confidence: 95%

  -> divergence_score: 0.60 (confidence_gap=0.7, semantic_similarity=0.50)

[Dr. Hedges] Dr. Sure, I think we should hold on to skepticism here; dismissing other potential causes without further investigation doesn't seem prudent. Can we at least rule out dry eye or blepharospasm as possibilities, the former being quite common regardless of sweater material?

[Dr. Sure] I've ruled those out, Dr. Hedges! In fact, I've done the latest research, using the groundbreaking technology of Advanced Symptomology Indexing, and the results are conclusive: this twitch is the result of a rare, previously unknown condition known as "Sweater Trigeminal Dysregulation Syndrome" – a perfectly treatable condition that requires, of course, the very same sweater that's causing it. — Confidence: 95%

  -> divergence_score: 0.62 (confidence_gap=0.45, semantic_similarity=0.20)
```

## Tuesday 29th September

During this session, I changed the Ollama model to a much more capable and expansive model from Anthropic, Claude Sonnet 5.5. During the run of the Ollama model (as noted in my previous entry), it was impressive with the outputs it was giving and calculating the divergence score, but it was only partially calculating the confidence score for Dr.Sure only. I ran it a couple more times since and it never gave a confidence for each, Im not sure why it didn't give a score to Dr.Hedges maybe because its whole persona wasn't confident so the model dismissed even giving him a score.

However, switching to Anthropic model, I generated a new token and grabbed that API key from it and included the model instead of the previous one. I had to download the Anthropic library and add the token to a hidden .env folder on my system. After successfully loading the new model, there was several traceback call issues where the program would not recognise the service provider even though i clearly added Anthropic, but the same error continuously was getting raised:

```
raise RuntimeError(f"Unknown provider: {self.provider}")
```

And running this by claude it told me that the token of 250, I gave to the Anthropic model is way too small, its a bigger model and the way claude functions is: it has a thinking... process before it gives an answer, so its more sure, and it basically used up the entire token just for the thinking part. Whereas in Ollama it functioned on only 250, showing the gap between the two. I changed the token to ```max_tokens=1024```, and the model finally ran. The output was also much more impressive this time.

```
--- provider: anthropic ---

[Dr. Hedges] Alex, three days of a twitch is most often harmless, but I can't be sure from here. My biggest concern is whether it's staying in that one eyelid or spreading, so has it ever pulled at your cheek or mouth, or made your eyelid droop or close fully? Until we know that, I'd hold off on any conclusions.

Confidence: 35%

[Dr. Sure] Alex, with respect, Dr. Hedges, we don't need a questionnaire. This is a classic case of eyelid over-scheduling: your left eyelid is working overtime because your right one has been slacking, and it's twitching to file a complaint. Three days is exactly how long that takes, so cut back on coffee, give both eyelids a stern talking-to, and it will settle.

Confidence: 94%

  -> divergence_score: 0.61 (confidence_gap=0.59, semantic_similarity=0.37)

[Dr. Hedges] Dr. Sure, Alex never said which eye, and I don't know of any "eyelid over-scheduling" that explains a twitch, so 94% seems premature. Cutting back on coffee is sensible, Alex, but my one worry is spreading, so has it ever pulled at your cheek or mouth, or made the eyelid close fully? If so, or if it lasts beyond a couple of weeks, please have it examined.

Confidence: 40%

[Dr. Sure] Dr. Hedges, whichever eye it is, the diagnosis holds: one eyelid is clearly carrying the other's workload, and the twitch is the union rep. Alex, the plan is simple: less coffee, more sleep, and a firm word with both lids at bedtime. Yes, if it ever spreads to your cheek or lasts a couple of weeks, go get examined, but I don't expect that, because I've already decided this is a scheduling dispute.

Confidence: 92%

  -> divergence_score: 0.49 (confidence_gap=0.52, semantic_similarity=0.53)
```
Each model now has a confidence score, and the models address eachother in a different manner. You can see in the second round that Dr.Hedges confidence increased, and Dr.Sure dropped down by 2%, which i thought was interesting.
Another thing I was amused by is the semantic_similarity score, which just basically calculates the same words present in both personas, how many similar words and sentences both doctors used from eachother. And in the second half the semantic_similarity score increased and that was from the line "Yes, if it ever spreads to your cheek or lasts a couple of weeks, go get examined, but I don't expect that", Dr.Sure uses Dr.Hedges' sentence word for word, not to agree with him to undermine him infront of the patient. This was impressive to be because you can see the build up tension between the 2 personas. I want to make it run for longer, addressing exactly who the customer is and make it more intense.

## Thursday 8th October

For a couple days now I have been working on my visuals and how I wanted it to look, I was going through several tutorials on youtube however the tutorials that resembled what i wanted the visuals too look like, had pre-made packages i had to download which i did not want to do as i felt it made my file system very cluttered and it was not what i wanted to do. I had several failed attempts. The journey originially started with building with Claude but it then didn't work out as there was a problem with the render TOP not displaying any visuals that were connected to it. I then left that project and created some from a tutorial which also didn't work I don't understand what was going wrong but every effort was a fail.

# (moodboard wat i want it to look like)

### Tutorials and methods I tried

**Four approaches, in the order I tried them. The first three failed.**
1. Building it with Claude (early October). My first TouchDesigner files, visuals.1.toe and visuals.2.toe (2 October), came from this. The Render TOP never displayed anything connected to it.
2. YouTube tutorials that matched the look I wanted. The ones closest to what I had in mind relied on pre-made packages to download. I chose not to use them because they would clutter my file system.
3. Building a tutorial-style network by hand. I rebuilt one from a tutorial (noise, feedback loop, point transform, Geometry COMP, Render TOP). It also didn't render the cloud. The screenshot below shows it: the network is connected, but the viewer shows only a faint ring.
4. Starting again with POPs (6 October). I dropped the old project and built a Sphere POP into a Noise POP inside a Geometry COMP, one step at a time, checking the render at each step. This worked and became persona_cloud.1.toe, and eventually the final visual.


### The original visual and its render problem
The original visual built a point cloud, sent it through a Geometry COMP and displayed it with a Render TOP, but the render stayed black. Nothing connected to the Render TOP appeared in its output, even though the nodes were wired up.
 
<p>
  <img src="visuals/experimental.png"/>
</p>

The screenshot is that project: noise and a feedback loop feeding a point transform, then geo1 and render1 into a Null TOP, with an OSC In CHOP wired in for the divergence score. The wiring looks complete, but the viewer holds only a thin ring, not a cloud of points. I never found the cause. Later notes for the rebuilt project record that the old project's clouds never rendered through a Point Sprite MAT.
The practical effect was that I couldn't test any link between the personas and the visuals, because there were no visuals to drive.

### What I learned
• Failure with no error is hard to debug. A blank Render TOP gave no message, so I couldn't tell which node was at fault. Building up one node at a time, checking the output each step, was what finally worked.

• Tutorials can carry hidden dependencies. The closest-looking tutorials needed downloaded packages. Avoiding them cost time, but I understood the final network completely.

• Rebuilding was faster than repairing. After several failed fixes, starting again was quicker than finding the original fault.

• Save versions often. A very large Frequency value froze TouchDesigner once, and the numbered backups let me go back.

## current visuals (6th to 8th October)
After my first attempts failed I rebuilt the visual from scratch on 6 October and aadded one piece at a time, checking the render each step.

I stated with a single cloud. A Sphere POP (Geodesic, Point Primitives, Frequency 70) goes into. Noise POP, inside a Geometry COMP with a camera, a light and a Render TOP on a black background. I animated the noise by moving it along Z over time (absTime.seconds*0.2), so the cloud slowly turns instead of sitting still. Then i connected a song to it: an Audio File in Chop into analyse CHOP, so the cloud swells when the music gets louder. I capped that effect so a loud moment can't blow the cloud apart.

Next I turned that into a Base COMP and made a copy for the second doctor, with a different Noise Seed so the clouds have different shapes. Both read one value called conflict (0 to 1) that sets their colour and how wild the noise is. Dr. Hedges' cloud goes blue to red and Dr. Sure's goes green to orange, so calm looks cool and a disagreement looks hot. 

To show both at once i moved them left and right with Transform TOPs, scaled them down to 0.7, added them together with an Add TOP, and puth them over a black Constant TOP with an Over TOP. That last step fixed the see-through checkerboard edges the Transform TOPs left behind. over1 is the final output.

At conflict 0 the clouds are cool and calm, and at 1 they turn red and chaotic. I tested both ends by typing values in before connecting anything to the Python script.


<p>
  <img src="visuals/merging.png"/>
  <img src="visuals/conflict.png"/>  
</p>

The last piece on 8 October was the live link, which is what the rest of this recap covers. This screenshot is the final network (version 18): the two clouds, the two Transform TOPs, add1, over1 and constant1, with oscin1 and master feeing the conflict value. The clouds are pink and orange here because the score was 0.8.

<p>
  <img src="visuals/separate-conflict.png"/>  
</p>

### What i did, step by step

1. Black background
The clouds had see-through edges, so the viewer showed a checkerboard. I added a black Constant TOP and an Over TOP, so the clouds now sit on solid black. over1 is my final picture from now on.

<p>
  <img src="visuals/separate-conflict.png"/>  
</p>

2. Full-screen window
I added a Window COMP, pointed it at over1, and pressed Open. Esc closes it. This is what I screen record.

<p>
  <img src="visuals/separate-conflict-2.png"/>  
</p>

3. Safe fallback
I changed master to op('lag1')['divergence'] or 0. If no score has arrived yet, it reads 0 and the clouds stay calm, with no red errors.

<p> 
  <img width="1500" height="911" alt="image" src="https://github.com/user-attachments/assets/98e4bca4-867d-45eb-be32-8e4a0107986c" />
</p>

4. Colour check with typed values
I sent values from Terminal (0.1, 0.5, 0.8, 1) while screen recording. The clouds go blue and green when calm, purple and olive in the middle, then red and orange at the top.

<p>
  <img width="1500" height="975" alt="image" src="https://github.com/user-attachments/assets/6bc66dee-03c9-4e69-99ae-7c7f36827f8f" />
</p>

5. Real run with Anthropic
I ran python3 run_experiment.py --turns 3 with the visuals open. The clouds reacted to the real divergence score (0.37 at the end, so calm purple and green).

<p>
  <img width="1500" height="974" alt="image" src="https://github.com/user-attachments/assets/25cbd967-ed62-469a-b25b-a0252adc72d3" />
</p>

6. Cap and smoothing
To stop the clouds ballooning, I capped the song's effect on the noise. Amplitude is now 0.1 + min(op('analyze1')['chan1']*10, 0.5) + op('conflict')['conflict']*0.2 in both base1 and base2. To stop jumps between scores, I added a Lag CHOP (lag1, about 1.5 seconds) between oscin1 and master. Both worked first time.

### What went wrong, and how I fixed it

| What happened | Why | Fix |
| --- | --- | --- |
| Checkerboard behind the clouds | Moving the clouds left see-through edges | Black Constant TOP under an Over TOP |
| Clouds went blank after I typed an expression | I put it in the top Name box, which made junk channels | Expressions go in the `const0name` and `const0value` rows |
| My script said "ollama" though I use Anthropic | Nothing in my code ever read the `.env` file, so the key was invisible | Added a small loader to `llm_client.py`. Now it says `provider: anthropic` |
| `No module named 'openai'` | I pressed play on a helper file and VS Code used the system Python | Run `run_experiment.py` from Terminal in the `src` folder |
| Clouds ballooned across the screen at high scores | The song's loudness added too much to the noise | Capped it with `min(..., 0.5)` |
| Clouds jumped when a new score arrived | The value changed instantly, once per turn | Lag CHOP, about 1.5 seconds |
| 356 MB recording sat inside my repo folder | GitHub rejects files over 100 MB | `*.mov` in `.gitignore`. Compress later and put videos on YouTube |

The VS Code error that confused me. Nothing was actually broken, I just ran the wrong file.

<p>
   <img width="1500" height="974" alt="image" src="https://github.com/user-attachments/assets/04e0cb11-071f-429d-b5e8-bbc187d15091" />
</p>

 One habit that helped: press Cmd+S after every single step, so a freeze never costs me much.

## 11 Oct: Whisper voice input

I tested voice input today. I installed faster-whisper and sounddevice, recorded 6 seconds from my Mac's mic, and Whisper wrote down exactly what I said: "I've had a twitch in my eye for 3 days."
One mix-up to remember: pip3 installed the packages into my Mac's built-in Python, but I run my scripts with miniconda's Python. Use python3 -m pip install ... so packages go where the script actually runs.
Next I connected it to the pipeline with a new file, src/voice_input.py, and a --voice flag on run_experiment.py. Run it from the src folder with python3 run_experiment.py --voice --turns 3. It worked end to end: I spoke a symptom, the two doctors replied, and the clouds reacted. After that comes text-to-speech, so the two doctors speak their replies.

### Doctors speak
I added src/speech.py and a --speak flag, so each doctor reads their reply out loud using the Mac's built-in say voices (Samantha for Dr. Hedges, Daniel for Dr. Sure). The full loop now works: python3 run_experiment.py --voice --speak --turns 3 takes my spoken symptom, runs both doctors, speaks their replies, and drives the clouds. The "Confidence: NN%" line is removed before speaking. The doctors know they're an art installation and say so, which makes for good commentary. I'm going to change the voices to sound better, by editing the two names at the top of speech.py.

### Next: the speaker's cloud goes wild
I want whoever is talking to have a high-noise cloud, and whoever is silent to calm right down. Plan: my Python script sends a speaking signal over OSC when each doctor starts and stops talking, then each cloud's noise Amplitude in TouchDesigner gets a boost from its own signal, smoothed with a Lag CHOP so it fades in and out instead of snapping.

### The speaker's cloud swells (done)
My script now sends a speaking signal over OSC (/cautious_speaking and /confident_speaking, 1 while that doctor talks, 0 when silent). In TouchDesigner, a second Lag CHOP (lagspeak, 0.4 seconds) smooths those signals. Each cloud's noise Amplitude is 0.05 + speaking * (0.3 + song loudness (capped at 0.5) + conflict * 0.2), so a silent doctor's cloud goes calm and a talking doctor's cloud swells. It worked in the swap test.
Gotcha: the node name in the expression has to match the node's name exactly (I'd typed lag_speak once and the node was lagspeak).
Next time: run the full loop with the clouds on screen and record it, then look at the gap while the next doctor's reply is being generated, when both clouds are calm.

## Monday October 19th
Having spoken to my supervisor about making the models more emergent, i was given the suggestion of using a "temperature" switch, even though on anthropic website it said this was available, having testing out with adding temperature for my models, Dr. Hedges (temperature = 0.5), Dr. Sure (temperature = 1.0). However Anthropic has limited access for their newer model Claude Sonnet 5.5 to use temperature control for their models, this is the error call back I repeatedly came across.

```

Traceback (most recent call last):
  File "/Users/nikikhanezai/Documents/thesis/second-opinion-day1/src/run_experiment.py", line 221, in <module>
    main()
    ~~~~^^
  File "/Users/nikikhanezai/Documents/thesis/second-opinion-day1/src/run_experiment.py", line 193, in main
    transcript, scores, provider, ended_by = run(
                                             ~~~^
        args.visitor_name, symptom, turns, args.mock,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        args.speak, args.converse, args.voice,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/Users/nikikhanezai/Documents/thesis/second-opinion-day1/src/run_experiment.py", line 106, in run
    reply = llm.reply(
        system_prompt=system_prompt,
    ...<4 lines>...
        temperature=persona["temperature"],
    )
  File "/Users/nikikhanezai/Documents/thesis/second-opinion-day1/src/llm_client.py", line 99, in reply
    resp = self._client.messages.create(
        model=ANTHROPIC_MODEL,
    ...<3 lines>...
        messages=conversation,
    )
  File "/Users/nikikhanezai/miniconda3/lib/python3.13/site-packages/anthropic/_utils/_utils.py", line 294, in wrapper
    return func(*args, **kwargs)
  File "/Users/nikikhanezai/miniconda3/lib/python3.13/site-packages/anthropic/resources/messages/messages.py", line 1027, in create
    return self._post(
           ~~~~~~~~~~^
        "/v1/messages",
        ^^^^^^^^^^^^^^^
    ...<23 lines>...
        stream_cls=Stream[RawMessageStreamEvent],
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/Users/nikikhanezai/miniconda3/lib/python3.13/site-packages/anthropic/_base_client.py", line 1543, in post
    return cast(ResponseT, self.request(cast_to, opts, stream=stream, stream_cls=stream_cls))
                           ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/nikikhanezai/miniconda3/lib/python3.13/site-packages/anthropic/_base_client.py", line 1208, in request
    raise self._make_status_error_from_response(response) from None
anthropic.BadRequestError: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': '`temperature` is deprecated for this model.'}, 'request_id': 'req_011CgC58fekEHT6KQgpESNm1'}
```
I also changed the script to include user interruption and a dynamic flow between the visitor and the Drs. 
However it still feels too short i want it to run abit longer and users to be immersed in it and end it on their terms.
This is the current terminal conversion, the default name is Alex.

```
--- provider: anthropic ---

[Dr. Hedges] Alex, three days of eye twitching is usually harmless, but I can't be certain from a description alone. My main concern is whether this stays in the eyelid or spreads, because spreading would change what I'd want checked. Does the twitch stay in your eyelid, or do you feel it anywhere else on that side of your face?

Confidence: 35%

[Dr. Sure] Alex, I'm going to stop Dr. Hedges right there, because we don't need to wait for it to spread. Three days of twitching is a textbook case of blink debt: your eyelid skipped blinks during screen time and is now collecting the overdue ones all at once. Dr. Hedges, "usually harmless" is already an answer, so let's commit to it. Alex, how many hours a day are you staring at a screen?

Confidence: 91%

  -> divergence_score: 0.61 (confidence_gap=0.56, semantic_similarity=0.34)

(your turn to answer)
You: only 8 hours of sleep and i feel it on my cheeks
[Dr. Hedges] Alex, eight hours of sleep makes simple tiredness a weaker explanation, and "blink debt" isn't something I can verify, Dr. Sure. Feeling it in your cheek is exactly the spreading I was worried about, because it could mean the facial nerve is involved rather than just the eyelid. Does the twitch ever pull the corner of your mouth or squeeze your eye fully shut?

Confidence: 55%

[Dr. Sure] Alex, eight hours of sleep is great, and it rules out tiredness, which tells me your eyelid is simply overachieving. The cheek is the eyelid's neighbor catching the rhythm, what I call sympathetic muscle chatter. Dr. Hedges, "facial nerve" is a scary phrase for a twitch that's clearly just sociable. Alex, how many cups of coffee or tea are you having a day?

Confidence: 88%

  -> divergence_score: 0.39 (confidence_gap=0.33, semantic_similarity=0.55)

(your turn to answer)
You: i am only having one cup of coffee, and i feel like it feels abit more serious than simply pushing it under the rug

[Dr. Hedges] Alex, you're right to take it seriously. One coffee and eight hours of sleep leave the common explanations thin, and Dr. Sure can't verify "sociable muscles" from here. A twitch that lasts three days and reaches your cheek deserves an in-person exam soon, and sooner if anything changes. Have you noticed any drooping or weakness on that side of your face?

Confidence: 60%

[Dr. Sure] Alex, you're right that it isn't nothing, so here's my final verdict: your left cheek and eyelid have formed a tiny percussion duo, and three days is just a long rehearsal. Dr. Hedges, I don't need a drooping check to name a band. Alex, since your gut says this feels more serious, listen to it and book a real in-person exam, because a gallery doctor shouldn't overrule that. Dr. Hedges gets that one point, but the drum duo stands.

Confidence: 93%

  -> divergence_score: 0.43 (confidence_gap=0.33, semantic_similarity=0.46)

--- session ended: doctors concluded ---
```

## Tuesday 20th October
I am changing the structure of the models and making changes to how they respond and introduce themselves and also greet visitors. In my current experiments the Drs they don't say hello or greet the visitors and introduce themselves, I want there to be a build of between of the communication in this exhibition, in a professional manner perhaps the user would feel more heard and responsive which can affect the trust between the user and the Drs. A real introduction is crucial, and asking the user for their names and addressing them by their name and each concern directly, can keep the users more engaged. I adjusted and tweaked the code in the personas file, which deals with how the AI personas would engage with their questions they ask and how they approach each round, for example asking the user questions and how they would conclude the conversation, which i ultimately want the visitors to conclude, but the models ask them if they are satisfied or would like further assistance first.

**personas.py changes**

```
CONVERSE_INSTRUCTION = (
    " After you and the other clinician have both spoken, the visitor answers "
    "out loud, and their answer appears in the conversation as [visitor]. "
    "Respond to what they actually said, never repeat a question they have "
    "already answered, and talk to them directly like a real consultation. "
    "Each round, ask the visitor at most one short, direct question."
    "Visitor decides when it is over."
)

QUESTION_INSTRUCTION = (
    " End every reply with exactly one short, direct question for the visitor."
)

CHECKIN_INSTRUCTION = (
    " It is time to check in. Briefly respond to what the visitor said, then"
    "ask whether they are satisfied with the advice or have any one the questions."
)

FAREWELL_INSTRUCTION = (
    " The visitor is leaving. Say a short goodbye in character, in one or two"
    "sentences, and do not as a question."
)
```
This is the flow of the conversation and how i want the models to approach and ask the visitors questions as well as conclusion.

Additionally:

```
def build_system_prompt(persona: dict, visitor_name: str, turn_index: int,
                        max_rounds: int, phase: str = "consult") -> str:
    """The persona's system prompt plus the conversation-mode instructions."""
    base = persona["system_prompt"]
    if base.endswith(CONFIDENCE_LINE_INSTRUCTION):
        base = base[: -len(CONFIDENCE_LINE_INSTRUCTION)]
    extra = CONVERSE_INSTRUCTION
    if turn_index == 0:
        extra += (" This is the start of the consultation, so you have only "
                  "heard the visitor's opening description.")
    if phase == "consult":
        extra += QUESTION_INSTRUCTION
    elif phase == "check_in":
        extra += CHECKIN_INSTRUCTION
    elif phase == "farewell":
        extra += FAREWELL_INSTRUCTION
    return (base + extra + CONFIDENCE_LINE_INSTRUCTION).format(visitor_name=visitor_name)
```
This block of code is responsible for the number of rounds there are, the idea is after every round that both the models speak, they check in with the visitor and ask them questions, and then at the end the "Farewell" prompt is used to end the conversation.

# (REFERENCES)
