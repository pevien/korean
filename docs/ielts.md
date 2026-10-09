# IELTS Speaking mock test

A simulated IELTS Speaking test inside the **Speak** tab. It covers all three parts, uses an AI examiner and gives band scores on the four official criteria. It lives in the `#ielts` container of `#v-read`, and the code sits in `index.html` under `🎓 IELTS Speaking mock test`. The end-to-end tests are in [`tests/ielts_test.py`](../tests/ielts_test.py).

- **Course:** English only. The card is hidden in every other course.
- **Needs a Gemini key:** without one, the screen shows a "Needs a Gemini key" card with a button to Settings, the same as Talk with AI. There is no copy/paste fallback, because one test makes 10–20 AI calls and needs audio.

---

## Entry and setup

**Speak → IELTS Speaking mock test**: "All 3 parts, with a band score on the 4 criteria and feedback on every answer." If a test is unfinished, the card shows "In progress: {mode}".

The setup screen (`renderIeSetup`) has:

| Element | Behaviour |
|---|---|
| **Target band** | 6 · 6.5 · 7 (default) · 7.5 · 8 · 8.5+. Saved per course (`courseSet().ieltsBand`). Model answers and vocabulary upgrades are written at this band, and results are coloured against it. The note under it says AI scores can be ±0.5–1 off. |
| **Full mock test** | Parts 1→2→3 in one go (~12 min). No feedback until the end. |
| **Practise Part 1 / 2 / 3** | One part only. Feedback after every answer. |
| **In progress** | Shown when you left a test with ←. Tap it to continue at the same question. |
| 🕘 **{n}** (top right) | Past tests. |

---

## The test script

One AI call (`ieBegin`) writes the whole test before the first question, so moving to the next question never waits for AI.

| Part | Content |
|---|---|
| 1 | One "work or study" question, then 2 everyday topics with 3–4 short questions each |
| 2 | A cue card ("Describe…", 3–4 *You should say* points, "and explain…"), plus one rounding-off question |
| 3 | 5 abstract discussion questions on the Part 2 theme, from easier to harder |

**A new test every time:**
- The script is written fresh each time, at temperature 1.
- The prompt lists the last 15 Part 2 topics and the Part 1 topics of the last 8 tests (apart from "work or study") as topics to avoid.
- A practice test only uses its own part, but the whole script is still generated.

---

## Taking the test

### The examiner

- **Speaking:** questions are read aloud by the course's English voice (`speak`).
- **What the examiner says:** the openings of the real test (`ieSpoken`):
  - Part 1: "In this first part, I'd like to ask you some questions about yourself."
  - A new Part 1 topic: "Now let's talk about {topic}."
  - The cue card instructions.
  - Part 3: "We've been talking about {theme}. I'd like to discuss with you…"
- **Listen first:** the question text is hidden, as in the real test. **Show the question** reveals it, and 🔊 plays it again.
  - It shows automatically when the device has no English voice.
  - After answering a practice question, it is always shown.
  - The Part 2 cue card is always shown, because the real test hands it over on paper.

### Answering

- **Recording:** tap 🎙 to answer and ⏹ when done. A clock shows the elapsed time against the limit.
- **Auto-stop:** Part 1 at 0:45, Part 2 at 2:00, Part 3 at 1:30.
- **Too short:** recordings under 1.2 s are dropped with "That was too short — try again".
- **Tab bar:** hidden during the test (`body.talking`), as in Talk.

### Part 2

1. The cue card and a notes box appear. The notes box fills the screen down to the controls and is only kept for this test.
2. A **1:00 countdown** runs for preparation. **Start talking now** ends it early.
3. When preparation ends, the examiner says "Please start speaking now", and you tap 🎙.
4. After the long turn comes the rounding-off question.

### Full test and practice

| | Full mock test | Practice |
|---|---|---|
| After an answer | On to the next question at once. Scoring runs in the background ("scoring {n}"). | Waits for the feedback, then **Try again** or **Next question** / **See results** |
| Try again | — | Discards the answer, including one still being scored |

**Submit** (top right, tap twice) ends the test early. At least one answer is needed. It hides while an answer is being recorded.

**← mid-test:**
- Goes back to setup and keeps the test in memory, with recordings.
- Leaving the tab stops a recording without sending it.
- A reload loses an unfinished test.

---

## Feedback on each answer

Two AI calls per answer (`ieScoreAnswer`). First the WAV recording is transcribed blind (`aiHear`, without the question, so the AI can't fill in words that fit the question). If nothing was heard, the answer counts as unanswered and the second call is skipped. The second call sends the recording plus that transcript, marked as final, and returns the following:

| Field | Shown as |
|---|---|
| `heard` | The transcript from the first call, mistakes and fillers (um, uh) kept |
| `note` | One sentence overall |
| `checks` | **Content & development**, shown first. Each check is ✓ or ! with a concrete tip when it isn't met. Part 1: answers directly · extends with a reason/detail · stays on topic. Part 2: each cue-card point · opening–body–wrap-up · on topic. Part 3: clear opinion · reasons · concrete example · logical flow/linking · no rambling. |
| `ideas` | 0–2 ways to develop this answer: an example to add, or a part to cut |
| `fixes` | Up to 4 corrections: ~~their words~~ → correct words, plus why |
| `upgrades` | Up to 3 "Band {target}+ vocabulary" suggestions, plus when to use them |
| `score`, `issues` | Pronunciation 0–100, with up to 2 tips (IPA). A missing score shows "—", never 0. |
| `sample` | A model answer at the target band, with 🔊 to play it. Length depends on the part: 2–4 sentences, ~200–250 words, or 4–6 sentences. |

**Computed on the device:**
- **Duration.**
- **Speaking rate (wpm):** words ÷ minutes.
- **Fillers:** um / uh / er / erm / ah / hmm in the transcript.

**More:** the "Pronunciation · Model answer ▾" row opens the pronunciation tips, the model answer, **Hear it** and **My recording**. My recording is only available in this session.

Explanations are written in the interface language, using `feedbackLangRule` and `fixFeedbackLang` like the rest of the app.

---

## Band score

When the test ends (`ieFinish`):

1. **Wait for scoring:** the app waits for all background scoring.
2. **Retry failed answers:** an answer whose scoring failed (e.g. the 429 per-minute limit) gets one more try, 4 s apart. That's why Submit accepts a failed answer.
3. **Nothing heard:** if no answer was heard at all, nothing is saved, a toast explains why, and the test stays resumable.
4. **Band call:** one text-only call rates the **answered questions only**: transcript, length, wpm and pronunciation score of each.
   - After an early submit, the prompt tells the AI not to lower any band for questions that weren't reached.
   - The result then says "scored on {x}/{y} answers".
   - It returns a band and a note per criterion (Fluency & Coherence, Lexical Resource, Grammatical Range & Accuracy, Pronunciation), 2 strengths and 3 next steps.
5. **Overall:** the mean of the four criteria, rounded the IELTS way (`ieOverall`):

| Fraction of the mean | Rounds to |
|---|---|
| below .25 | the whole band below |
| .25 to below .75 | .5 |
| .75 and above | the next whole band |

For example, 6, 6.5, 5.5 and 6.5 give a mean of 6.125, which is reported as **6.0**.

### Results screen

- **Estimated band** in large type, with "Target {t} · {gap} to go" or "🎉 Target reached".
- **The four criteria:** each with its band and note.
- **Stats:** average wpm, total fillers, and the length of the Part 2 long turn against 2:00.
- **Strengths, and steps to reach band {target}.**
- **Each part:** folded into a section with every question and its full feedback.
- **Retake** (also on past tests): the same questions again, with no AI call for a new script, saved as a new test.
- **New test:** the purple main button. It starts the same mode with a fresh script.

**Colours against the target** (`ieTone`) apply to the big number, the criterion pills and the history list:

| Band vs. target | Colour |
|---|---|
| At or above | Green |
| Up to 1 band below | Amber |
| More than 1 below | Red |

---

## History and sync

- **What's stored:** finished tests go into `S.ielts`, as text only, without recordings or Part 2 notes. Fields: `id`, `lang`, `created`, `mode`, `target`, `card`, `qs[]` (each with `part`, `q`, `topic`/`kind` and `a`), and `result`.
- **Sync:** they sync through Google Drive and are restored from backups, the same way as `talks` (`track`, `applyRemote`, import).
- **🕘 list:** newest first, with mode, date, target and a coloured band.
- **Opening a test:** shows its results screen. **Delete** needs two taps.

---

## AI calls and reliability

| Call | When | Sends |
|---|---|---|
| `gen` | Start | Text |
| `ans` | Every answer | Text + WAV audio, 16 kHz mono (~4 MB for a 2-minute Part 2) |
| `band` | Submit | Text |

A full test makes about 10–20 calls, typically 1 + 13 + 1.

- **Structured output:** every call sends a `responseSchema` (`IE_SCHEMA`) with all fields required. Without it, Gemini sometimes:
  - returned broken JSON on long answers;
  - wrapped lines as `{"q": …}` objects ("[object Object]");
  - left out `score` and `sample`.
- **Retry:** `ieAsk` asks once more when the reply still isn't valid JSON. If the band call fails twice, the screen shows the error with **Try again**.
- **Object-wrapped lines:** the parser also unwraps `{"q"|"question"|"text"|…}` objects, in case the schema is ignored.

---

## Tests

`tests/ielts_test.py` drives the real `index.html` in headless Chromium.

- **What's faked:** Gemini (with switches for 429s, broken JSON, missing fields, object-wrapped questions and silence), the microphone (an oscillator) and, for one scenario, an English voice. No key, mic or network is needed.

```bash
python3 -m venv .venv && .venv/bin/pip install playwright && .venv/bin/playwright install chromium
.venv/bin/python tests/ielts_test.py        # all scenarios: PASS/FAIL per check, exit 1 on any failure
.venv/bin/python tests/ielts_test.py C U    # only the scenarios a change touches
```

| Scenario | Checks |
|---|---|
| A | Hidden in the Korean course |
| B | No key → key card, no modes |
| C | Full test end to end: Part 2 prep timer and notes, call counts, rounding, target band, saved shape, colours, purple button, details/model answer, reload keeps band + history |
| D | Part 2 practice: notes fill the screen, Try again goes back to "ready", follow-up question, stats |
| E / J | Try again while scoring drops the old answer; a silent answer shows "No answer was heard" |
| F / K / M / G | Back and resume at the same question, too-short recording, leaving the tab stops the mic, two-tap early submit, the band prompt rates only answered questions, "scored on 1/3" |
| H | History: open, no recordings in past tests, two-tap delete |
| I | A 429'd answer is retried at submit |
| P | Nothing heard → nothing saved, resumable |
| Q | Object-wrapped questions shown as text; no sideways scrolling |
| R | Listen first (question hidden, then revealed, hidden again on the next one); broken JSON retried once, then the error with Try again; new tests avoid recent topics |
| S | The answer schema requires every field; a missing score shows "—" |
| T | Retake a past test: same questions, no new script, saved as a new test next to the old one |
| U | Content & development checks per part (card points in Part 2), tips only for unmet checks, ideas, shown above the corrections, history uses its own card |
| L | English interface labels |

---

## Limits

- **Estimates only:** bands come from the AI, not a certified examiner, and pronunciation is the least reliable criterion.
- **Unfinished tests:** they aren't saved; a reload loses them.
- **Part 3 questions:** written in advance, not adapted to your answers. That is planned for phase 2, together with a band chart and saving upgraded words to the deck.
