# Vocab tab (Study)

The Vocab tab (`#v-study`) is a flashcard trainer that uses spaced repetition. It has three sub-pages: **Add words** (`#v-add`), **My words** (`#v-words`) and **Alphabet** (`#v-abc`). The tab stays highlighted on all three.

## Home screen

**Title row:** "Vocab:" followed by the course button (tap it to switch course). "+ Add words" appears in the title row once the deck has words.

**Stat tiles** (`refreshStats`):

| Tile | Meaning |
|---|---|
| Due today (Cần học) | Reviews due now + new words still allowed today. Shown as `left/total`; the tile is highlighted while work remains. |
| Learning (Đang học) | Cards studied at least once with an interval under 21 days |
| Mastered (Đã thuộc) | Cards with an interval of 21 days or more |
| Day streak (Chuỗi ngày) | Consecutive days with at least one review |

Tapping one of the first three tiles opens My words filtered to that group.

**Auto-start:** tapping the Vocab tab when there is work goes straight to the first question. No Start screen is shown.

**States of the home card** (`refreshHome`):

- **Empty deck:** a prompt to add words, plus buttons for the Alphabet and "+ Add words".
- **Work pending:** "Ready to study", the count of reviews and new words, and "▶ Start".
- **All done, some missed:** "X/Y correct — let's lock in the words you missed" with **Practice N missed words**. Each missed word comes up twice. This practice does not change the schedule.
- **All done, none missed:** the time until the next review, plus **Extra practice** and **Learn 5 more**. Learn 5 more raises today's new-word allowance by 5.

**Nudge card** (`renderNudge`). At most one appears at a time:

- **Install:** shown in the browser (not the installed app) after you have studied. Gives platform-specific steps or an Install button.
- **Backup:** shown when Drive sync is off and the course has 20 or more words. The button opens the sync guide in Settings.
- ✕ ("Later") hides that nudge for 14 days.

## Streaks and celebrations

- Any graded answer counts toward today. Studying yesterday adds one to the streak. A missed day resets it to 1.
- **Milestones:** 7, 14, 30, 50, 100, 200 and 365 days, then every 100 days.
  - Reaching one plays a large confetti burst and shows a "🔥 N-day streak!" toast.
  - When a milestone is close, a countdown cheer appears: within 1 day for targets under 30, 2 days for 30 and up, 3 days for 100 and up.
- **Cheers** appear in the course language with a 🔊 button and a translation, plus a random BTS emoji. Korean has its own set ("보라해 💜").
- A perfect session plays confetti. Confetti is skipped when the device asks for reduced motion.

## Review session

`startSession` builds one of three queues:

| Session | Contents | Changes the schedule? |
|---|---|---|
| Normal | All due cards, plus today's new words mixed in about every 3rd item | Yes |
| Extra practice | 15 cards weighted toward shaky ones (`pickWeak`): many lapses, low ease, short interval or due soon. If nothing has been studied yet, 10 random cards. | No |
| Practice missed | Each missed word twice, shuffled | No |

- The tab bar is hidden during a session. **End** stops early.
- **Keyboard shortcuts:** 1–4 pick an answer, Space replays audio, Enter presses the main button.

### New words

A new word first appears as a **NEW WORD** card. It shows the word, 🔊, the meaning and an example. Tap **Got it →** to continue. The word comes back as a quiz 2–3 items later. Letters from the alphabet table are introduced before ordinary words, oldest first.

### Question types

Turn these on or off in Settings → Study. At least one must stay on.

| Key | Settings label | The question |
|---|---|---|
| `ko2m` | Korean → meaning | See the word, choose 1 of 4 meanings |
| `listen2m` | 🔊 → meaning | Hear the word, choose 1 of 4 meanings |
| `listen2kc` | 🔊 → Korean word | Hear the word, choose 1 of 4 look-alike or sound-alike words |
| `m2ko` | Meaning → Korean | See the meaning, type the word |
| `listen2ko` | 🔊 Dictation | Hear the word, type it |
| `ko2say` | 🎙 Read aloud | See the word, say it |
| `m2say` | 🎙 From meaning | See the meaning, say the word (has a Hint button) |

In non-Korean courses, "Korean" in these labels is replaced by the course name.

**Choosing the question type** (`pickMode`):

- One enabled type is picked at random for each card.
- Speaking types are skipped when the browser can't record or recognise speech.
- Meaning-based types are skipped for cards that have no meaning.

**Wrong choices (distractors):**

- **Meaning questions:** 3 meanings from other cards. Letters are paired with letters and words with words.
- **"What you hear" questions:** sound-alikes (`soundAlikes`):
  - Deck words within an edit distance of 2.
  - For Korean, generated **minimal pairs** (`minimalPairs`). Each pair swaps one confusable sound, such as ㄱ/ㅋ/ㄲ, ㅓ/ㅗ or final consonants. Swaps that pronunciation rules would make sound identical are left out, for example tensing and nasalisation.
  - For letters, others from the same group.

**Typing:**

- Answers are checked ignoring spaces, punctuation and case.
- **Hint** reveals the first characters and the length.
- Using a hint removes the Easy grade for that card.

### Speaking questions

- Tap 🎙, say the word, then tap ⏹. Recording stops by itself after 8 s.
- **Grading:** choose **⚡ Basic** or **✨ AI**. This setting is shared with the reading coach.

| Grading | How it works | What you see |
|---|---|---|
| ⚡ Basic | The browser's speech recognition. It accepts any of its top 5 guesses that contains the word. If speech was detected but not understood, you get one retry. | A miss shows "Match N/100"; 70 or more adds a "close" hint. |
| ✨ AI | Needs a key. The recording is sent to Gemini. Tones count for Chinese, Thai and Vietnamese. | "N/100" with a tip, and a Replay button for your own recording |

- **Letters:** the letter's name or its sound is accepted. Korean vowels that have merged in speech count as equal: ㅐ/ㅔ, ㅒ/ㅖ and ㅙ/ㅚ/ㅞ.
- **Can't speak now** switches the card to a question type that doesn't need speaking.
- The first time a key is added, the speaking question types are switched on automatically (once).

### Feedback and grading

- **After each answer:** ✅ or ❌, the correct word and its meaning, what you typed or what was heard (wrong characters in red), and the example sentence. The word is read aloud.
- **I was right:** shown after a typed or spoken answer marked wrong. It counts the answer as correct and grades it Hard.
- **Correct answers** offer three grades. Each grade button shows its next interval.

| Button | Grade value |
|---|---|
| Hard (Khó) | 3 |
| Good (Tốt) | 4 |
| Easy (Dễ) | 5 |

- **Easy is hidden** right after a word is introduced, after a hint, and on a re-ask.
- **Wrong answers:** the card is graded "again" and asked again 3–5 items later. Getting it right then counts as relearned, and the card returns tomorrow.

### Spaced-repetition algorithm

`grade()` uses a modified SM-2. New cards start with ease 2.5.

| Event | Result |
|---|---|
| Wrong (again) | Repetitions reset; next review in **10 min**; lapses +1; ease −0.2, but never below 1.3 |
| 1st success | 1 day (Easy: 3 days) |
| 2nd success | Hard 3 / Good 6 / Easy 7 days |
| Later successes | `interval × ease × (Hard 0.8 / Good 1.0 / Easy 1.3)`, rounded, at least 1 day |
| Ease change | Hard −0.14, Good ±0, Easy +0.1; never below 1.3 |

A card is **New** until it has been graded once. It is **Learning** while its interval is under 21 days and **Mastered** from 21 days.

## Daily limit

- **New words per day** (Settings) can be 1–100. The default is 10.
- The limit is shared by all courses, but each course keeps its own count.
- Daily counters reset at local midnight.

## Add words

Open it from "+ Add words". It has four tabs. Before anything is added, a **preview** opens.

| Tab | How it works |
|---|---|
| **✨ AI** | Enter a topic, or pick one of 15 topic chips plus one course-specific chip (e.g. "K-drama phrases"). Choose a Level and How many (3–40, default 10). Results skip words you already have; the prompt also sends your 400 most recent words so they aren't suggested. **Needs a key** (otherwise copy/paste fallback). |
| **Single** | Fill in the word and its meaning. **Fill meaning** translates for free. Words not written in the course's script are rejected. |
| **Paste list** | One word per line. Separate the word and its meaning with `-`, `:`, `=` or a tab. Lines without a meaning are translated automatically. |
| **Screenshot** | Choose or take a photo, or paste an image with Ctrl/Cmd+V. Gemini reads the words, keeping the layout and skipping headings and romanisation. **Needs a key.** |

**Paste list details** (`parseLines` / `parseLinesOther`):

- Numbering and bullets are removed.
- A line with no course-language text becomes the meaning of the word on the line above.
- Spreadsheet rows with several word/meaning pairs are split into separate words.

**The preview** ("Review before adding"):

- Each row has a checkbox, an editable word, an editable meaning, 🔊, and the example sentence if there is one.
- Words that already exist are marked.
- **Fill meanings** translates any rows that are missing a meaning.
- **Add (N)** saves the ticked rows. Duplicates are skipped and counted in the confirmation message.

**Example sentences:** if "Auto-add example sentences" is on and a key is set, new words without an example get one at your current level. Words are processed in batches of 30.

**Free translation** (`translate`) uses the Google Translate web endpoint first, then MyMemory. Results are rejected when they come back untranslated or in the wrong script.

**Alphabet bar:** "Learn the alphabet? (N left)" sits above the tabs until every letter is in the deck. ✕ hides it for the course.

## Alphabet

**What it shows:**

- The course's letters, grouped. Tap a letter to hear it.
- **Add N letters** puts the whole table in your deck. Letters are reviewed like words.
- Each letter card holds the letter, its sound, an example word, and, where it helps, the letter's name.

| Course | Groups |
|---|---|
| Korean | Basic vowels (10), basic consonants (14), tense consonants (5), compound vowels (11) |
| English | Vowels (5), consonants (21) |
| Vietnamese | Vowels, consonants, letter pairs (ch, gh, gi…), tone marks. Letters are read by their sound (bờ, cờ); the name is shown alongside. |
| Japanese | Hiragana, hiragana with ゛゜, katakana |
| Chinese | Pinyin: tones, initials, simple finals, nasal finals |
| Thai | Middle-, high- and low-class consonants (each with its word, e.g. ก ไก่), vowels, tone marks |

## My words

**What's on the page:**

- **Search** looks in both the word and the meaning.
- **Filters:**
  - Due today, New, Learning, Mastered.
  - Tapping the active filter again shows all words.
  - "Due today" lists exactly what the next session will ask.
- **Each row** shows 🔊, the word, a badge (New / `interval/21 d` / `interval d`), the meaning and the example. Newest words come first.
- **Missing examples bar:** "N words without an example sentence — ✨ Add now".
- **Bottom button:** Study, or Extra practice when nothing is due.

**The ⋯ menu on each row:**

- **Edit:** change the word, meaning, example and example translation.
  - **Reset** clears that word's progress.
  - Enter saves.
- **Delete:** tap twice. The first tap changes the button to "Tap again to delete" and disarms after 3 s. A deleted word is also removed from a session that is running.

## Text-to-speech

- The app uses the browser's built-in voices (`speechSynthesis`).
- **Voice ranking:**
  - Voices are ranked by quality.
  - Korean uses a hand-made list of good voices, e.g. Yuna Premium.
  - Google, "natural", "neural" and "premium" voices rank higher.
  - Google's voice is the default when the device has it.
- **Voice choice and speed:**
  - The voice is stored per device and per course.
  - Speed is set in Settings (0.5–1.2×, default 0.85).
  - Short single words of up to 3 syllables play at 0.8× that speed.
- **Before reading aloud:** speaker labels such as "민수:" and symbols are removed.
- **No voice installed:** if the device has no voice for the course, a toast points to Settings → Voice. Settings lists the steps to install one on each OS.
- **Auto-play** (Settings): reads the word aloud when a new word is introduced and on "Korean → meaning" questions. Listening questions always play.
