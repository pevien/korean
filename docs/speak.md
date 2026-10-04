# Speak tab

The Speak tab is the `#v-read` section, opened by the nav button `data-v="read"`. Its home screen offers two activities:

- **Reading (Luyện đọc):** "Read aloud, get your pronunciation scored."
- **Talk with AI (Trò chuyện với AI):** "Speak {language}, the AI replies and corrects you." If a conversation is unfinished, this card shows "In progress: {scene}".

The current screen is remembered when the page reloads (sessionStorage). The title row has the course button.

---

## Reading

### Passage list

- **What's listed:** passages for the current course, newest first. Each row shows the title, its translation and the level.
- **"+ New"** opens the create form.
- **No passages yet:** the create form opens directly.

### Creating a passage

There are three sources:

**✨ AI writes**

| Option | Values |
|---|---|
| Topic | Free text, or one of 10 chips: café, introducing yourself, weekend, directions, school, clothes shopping, weather, a cat story, texting a friend, at the doctor |
| Level | Same level setting as Add words and Talk |
| Length | Short (~4 sentences), Medium (~8, the default), Long (~14) |
| Use words I'm learning | Mixes in up to 40 of your words that aren't mastered yet |

- **What you get:** the title and its translation, the sentences with their translations, and 5–10 **key words**.
- **Dialogue:** dialogue lines start with "Speaker:".
- **Without a key:** this works through the copy/paste fallback.

**Add my own**

- **Paste the text, then tap Split into sentences:**
  - Sentences split at `. ! ? 。 ？ ！` and at line breaks.
  - A short first line with no ending punctuation becomes the title.
  - Lines of romanisation and labels ending in ":" are dropped.
- **Or type sentence by sentence.**
- **Translations:**
  - **With a key:** Gemini supplies exactly one translation per sentence. It can't change the sentences themselves.
  - **Without a key:** if the pasted text contains as many translation lines as sentences, they are paired in order.
  - Anything still missing is filled by free translation, one sentence at a time.
- **Title when there is none:**
  - Korean: the topic phrase is used, for example 제 취미는 becomes 제 취미.
  - Otherwise: the first few words.

**Screenshot**

- **Requires a Gemini key.**
- Pick or take a photo, or paste one with Ctrl/Cmd+V.
- **What Gemini does:**
  - Copies the sentences exactly.
  - Pairs each with the translation printed on the page, or writes one.
  - Drops romanisation, furigana and pinyin.
  - Uses the page heading as the title.
- **Several photos:** each photo appends more rows.

**Review editor:** "Add my own" and "Screenshot" both open the same editor.

- Each row has a drag handle, the sentence, its translation and ✕.
- **＋ Add sentence** adds a row. **Create passage** saves.
- Empty translations are filled automatically.
- Passages made this way have no key words and no level.

### Reader

**Top bar:**

- ← back, the title and its translation.
- ✏️ **Edit**: opens the same editor. A sentence you don't change keeps its best score.
- 🗑 **Delete**: tap twice.

**Sentences:**

- Each sentence shows its translation, the best score ("🎙 best N/100") and a 🎙 button.
- Tap a sentence to hear just that one.

**Key words:**

- Each key word has 🔊.
- Words already in your deck show their status (New / Learning / Mastered).
- Words not yet in your deck get a **＋** button.
- **+ Save N words** adds all of them at once. It appears when at least 2 words are unsaved.
- A saved word's example sentence is the first passage sentence that contains it.

### Audio player

| Control | What it does |
|---|---|
| ⏮ ▶/⏸ ⏭ | Previous / play-pause / next sentence. When the coach is open, ⏮ and ⏭ move the coach instead. |
| Speed | 0.6×, 0.75×, 0.85× or 1×. This is the same speed as Settings → Voice. |
| ⚙ Options | Repeat each sentence 1×, 2× or 3×; **Shadow mode**; Hide Korean; Hide translation |

- **Shadow mode** (Nói đuổi):
  - After each sentence, a "🎤 Your turn — repeat it! (n)" countdown appears.
  - The pause lasts 1.4 × the sentence length + 0.6 s, between 1.5 s and 12 s.
- **Without shadow mode:** sentences are 0.45 s apart.
- **Hide Korean / Hide translation:** tap a row to show its hidden text.
- The current sentence is highlighted and kept in view.
- **Keyboard:** Space plays or pauses; ← and → move between sentences.

### Pronunciation coach

Tap 🎙 on a sentence to open the coach underneath it. The coach has:

- the sentence and its translation
- 🔊 **Listen to the model**
- 🎙 **Record** (tap again to stop; recording stops by itself after 30 s)
- 🎧 **Play my recording**
- a grading switch: **⚡ Basic** or **✨ AI** (shared with the Vocab speaking questions)

| | ⚡ Basic | ✨ AI |
|---|---|---|
| Needs | A browser with speech recognition (Chrome/Safari). Speech recognition itself may need internet. | A Gemini key |
| Scores | Accuracy and fluency | Accuracy, fluency, intonation, native-like (0–100) |
| How | Lines up what was heard against the sentence, then applies built-in rules | The recording (16 kHz WAV) goes to Gemini with a prompt for the language |

**⚡ Basic in detail:**

- **Accuracy:** matched units minus half the extra units, divided by the sentence length.
  - A unit is a syllable in Korean, a character in Japanese, Chinese and Thai, and a word in English and Vietnamese.
- **Fluency:** your speaking pace compared with native pace, for example 4.5 syllables per second for Korean. Scores stay between 20 and 100.
- **Korean tips** come from analysing the Hangul. They cover:
  - plain, aspirated and tense consonants
  - ㄹ/ㄴ
  - vowel pairs
  - final consonants (받침)
  - sound-change rules (연음, 비음화, 유음화, 격음화, 경음화), each with an example such as 한국말 → [한궁말]
- **Other languages** get "missing" or "came out as X instead of Y" tips.
- **Android:** Android can't record and recognise speech at the same time. Without a key, only the recognised text is checked and 🎧 stays disabled.

**✨ AI in detail:**

- All courses share one prompt (`coachPrompt`) with a per-language checklist (`COACH`). For Korean that's consonant series, vowels, 받침, sound-change rules including 연음 across words, fluency (word-by-word reading counts) and intonation.
- **Strict grading.** Gemini lists every deviation from a native speaker, small ones included (up to 10), and each score starts at 100 with deductions per issue. 95+ is only for native-like speech, and an aspect with any issue gets at most 90.
- The prompt spells out the deductions per score (e.g. a wrong sound −10 to −20 on Accuracy, each hesitation −5 to −10 on Fluency), says Native-like can't be more than 10 above the lowest of the other three, and that the scores must match the issues listed. The scores shown are Gemini's own — the app doesn't adjust them.
- You also get the standard pronunciation, what was heard, and an overall comment in your UI language. Issue types are labelled in the UI language (Nối âm, Patchim, Tốc độ…).

**The result shows:**

- Problem parts marked in the sentence with numbers.
- Score tiles.
- "We heard", "Correct pronunciation" with 🔊, the numbered tips, and 💡 an overall note.
- A headline based on the average score:

| Average | Headline |
|---|---|
| 85+ | 🌟 Excellent |
| 70+ | 👍 Good |
| 50+ | 💪 Getting there |
| Below 50 | Keep practising |

- A new best score is saved on the sentence.

**Microphone problems:** the app explains the exact fix for each case:

- not opened over https (for example a downloaded copy on Android)
- mic blocked for the site
- no mic found, or the mic is in use by another app
- mic blocked at the OS level

---

## Talk with AI

**Requires a Gemini key.** Without one, a card explains this and links to Settings.

### Setup

- **What situation do you want to practise?** Type anything, or pick a scene:

| Scene | Scene |
|---|---|
| 👋 Meeting someone | 🍜 At a restaurant |
| ☕ Ordering at a café | 💊 At the pharmacy |
| 🛍 Shopping | 🎧 Hobbies |
| 🗺 Asking the way | ✨ Free talk |
| 🚕 Taking a taxi | |

- **Where scenes are set:** in the course's city with local characters, for example Seoul with 지민 and 수빈, London with Emma, Tokyo with さくら.
- **Your own topic:** the AI picks a fitting role.
- **Level:** the AI keeps to the level you choose.

### Conversation

- **The AI's lines:**
  - The AI opens with a line in character.
  - Its replies are 1–2 short sentences and usually end with a question.
  - It sees the last 14 turns.
- **Your turn:** tap 🎙, speak, then tap again. Recording stops by itself after 30 s.
- **What the AI sends back for each turn:**
  - What it heard, word for word, mistakes included.
  - ✅ "Correct and natural!", or ✏️ a corrected sentence with a one-line reason.
  - A translation.
  - A **pronunciation** score with up to 2 issues. Tap the score to expand it, with "My recording" and "Model" playback.
  - Its reply in character, which is read aloud.
- **💡 Hint:** explains what was asked and offers 3 answers, from simple to richer. Tap one to hear it.
- **Bottom bar:** speed, 💡, 🎙, and 🔊/🔇 to turn read-aloud on or off.
- **While chatting:** the tab bar is hidden.
- **Recordings** are kept in memory only and never saved.

### Summary and history

- **Finish** shows a summary:
  - turns, correct sentences, average pronunciation
  - **Corrections** (wrong → fixed, with the reason)
  - up to 8 pronunciation notes
  - the whole conversation, which you can expand
- **Summary buttons:** **Keep talking** or **New conversation**.
- **If you never spoke:** the conversation is discarded.
- **🕘 History:** keeps the latest **60** conversations. Each shows the scene, date, number of fixes and average score. From History you can **Keep talking** or delete one (two taps).
