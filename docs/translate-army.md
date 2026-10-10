# Translate and ARMY tabs

Both tabs run on one live speech-translation engine, the `AR` object. Its `AR.mode` decides which tab is using it:

| Mode | Tab | What it is |
|---|---|---|
| `talk` | **Translate** | Face-to-face interpreter for two people. Turn-based: you tap the mic, speak, and the app translates and reads the translation aloud. |
| `bts` | **ARMY** | Continuous one-way subtitles for BTS livestreams (Weverse, YouTube), styled like fan subs |

Each mode keeps its own transcript and its own language pair. Both use the same 6 languages: ko, vi, en, zh, ja, th.

---

## Translate tab (interpreter)

The Translate tab is a full-screen overlay (`arInterpOpen`), not a normal page. It opens over whichever tab you were on.

- **Opening:** the overlay always opens clean. Tapping Translate also stops BTS Live if it's running.
- **Closing:** tap any other tab.
- **Reload:** if the overlay was open, it reopens after a reload.

### Layout (Papago-style)

- **Two halves:**
  - **Bottom half:** you, in your language.
  - **Top half:** the other person, in theirs.
  - Each half has a flag, the language name in that language (한국어, Tiếng Việt, …), its own language picker and its own 🎙.
- **↻ Rotate** turns the top half upside down for someone sitting across the table. It resets the next time Translate opens.
- **⇄ Swap** exchanges the two languages.
- **Default pair:** your UI language (Vietnamese or English) ⇄ Korean. The pair you pick is remembered.
- **Toolbar:**
  - **✨ Translate with AI:** shows 🔒 without a key; tapping it then opens the key setup.
  - **Read aloud:** on by default.
- **What each half shows:** only the latest turn.
  - While someone speaks, a wave animation or the live text appears in the speaker's half, and a draft translation in the other half.
  - After the turn, each person sees the text in their own language.

### Turns

1. Tap your half's 🎙 and speak.
2. The turn ends in any of these cases:
   - you tap the mic again
   - you pause for **1.5 s**
   - the turn reaches **30 s**
   - nothing is said for **10 s**
3. The translation appears and is read aloud.

The mic is only open during a turn. It is paused while a translation is being read, so the app doesn't translate its own voice.

### Read-aloud voices

- **Correct language only:** translations are read only with a voice in the right language. A Vietnamese line read by an English voice is worse than silence.
- **Missing voice:** if the device has no voice for one of the languages, a notice explains how to install one, then reload:
  - **iOS:** Settings → Accessibility → Spoken Content → Voices
  - **Android:** Settings → Text-to-speech → Google engine → Install voice data
  - **Mac:** System Settings → Accessibility → Spoken Content → System voice → Manage voices
  - **Windows:** Settings → Time & language → Speech → Add voices

---

## ARMY tab

**Home screen:**

- **ARMY Borahae** banner.
- **BTS Live:** "Live subs for BTS lives."
- **🎵 BTS Songs:** sing along and understand a song (see below).
- **💾 Saved conversations (n):** review a saved conversation, or turn it into a reading passage.

### BTS Live

| Control | Notes |
|---|---|
| Spoken language ⇄ Translate to | Default: Korean → your UI language |
| Listening mode | ⚡ Basic, or ✨ AI (🔒 without a key) |
| Audio source (AI mode, desktop) | 🎙 Microphone, or 🖥 **Tab audio**. For tab audio, share the browser tab and tick "Share tab audio". |
| ▶ Start / ⏹ Stop | The screen stays awake while listening (Wake Lock) |
| Subtitle box | A− / A+ text size (0.8–1.8×), and an **Original** toggle to show or hide the source line |
| 📝 Conversation | Every line, newest first. **💾 Save** (no audio is kept) and **🗑 Clear**. Clear asks for a second tap if there are unsaved lines. |

- **While listening:** the controls collapse to a slim row.
- **Context for the AI:** a BTS glossary is included in its prompts. It lists the members' stage names and Korean nicknames, plus fandom words (보라해 = "I purple you", 아미, 막내, 위버스…).

### Saved conversations

- **Saving** (💾):
  - The app waits up to 20 s for translations that are still coming in.
  - It stores the transcript as "💜 BTS Live · d/m hh:mm", or "🌐 Interpreter · …" for interpreter conversations.
  - Saving clears the screen: lines heard afterwards start a new transcript, saved separately next time.
  - Tapping **Translate** while a save is finishing shows "Saving the conversation, one moment…" and opens the interpreter once it's done.
- **The list:** two tabs, **BTS Live** and **🌐 Interpreter**.
- **Opening a saved conversation:**
  - Tap the title to rename it.
  - Change the text size, or toggle **Original**.
  - **📖 Save to Read** turns it into a reading passage.
  - **🗑 Delete** (two taps).

**Save to Read** keeps only lines that contain Korean. The Korean side becomes the sentence and the other side its meaning. The passage is always saved as a Korean passage.

---

## Engines

### ⚡ Basic (free)

- **Recognition:** the browser's speech recognition (Chrome/Safari). Recognition needs internet. On Android, repeated partial results are de-duplicated.
- **When a sentence counts as finished:**
  - **ARMY:** after the words stop changing for 0.9–1.1 s.
  - **Translate:** a turn ends after a 1.5 s pause.
- **Translation steps:**
  1. **Phrase cache**: the last 400 translations are kept, so repeated lines show instantly.
  2. **Chrome's on-device Translator**: gives an instant draft, even while the sentence is still being spoken. The first use may download a language pack, and progress is shown.
  3. **Gemini**, if a key exists: lines are re-translated in batches of up to 6, with the previous 4 lines as context. It also fixes speech-recognition mistakes, and its result replaces the draft.
  4. **Fallback**: the on-device Translator, then MyMemory. If both fail, the line shows "(not translated)".

### ✨ AI (needs a key)

- **Recording:**
  - **Translate:** each turn is recorded whole.
  - **ARMY:** audio is recorded in chunks of **3–8 s**, cut at the first pause of 1 s or more. Subtitles lag about 5–10 s.
- **Processing:** each recording becomes 16 kHz WAV and goes to Gemini, which transcribes it and translates it into subtitle lines.
  - It ignores music, singing, noise, and the app's own voice.
  - Chunks that are only silence are skipped, to save quota.
- **Slow connection:** if 3 chunks are already waiting, new ones are skipped ("Slow connection — skipped a chunk").
- **Out of quota:** after 3 errors in a row saying the Gemini quota is used up, the app switches to Basic by itself.

### Limits

- Each mode keeps at most **3000 lines**. After that the oldest lines are dropped, and a toast suggests saving.
- The live transcript is kept on the device (localStorage `hangulCards.army`).

---

## 🎵 BTS Songs

Lets a fan learn a song: who sings each line, the original, its romanization and its meaning, plus the story behind the song. Songs are kept in `S.songs` and sync like saved conversations.

- **The lyrics always come from the fan.** They type the title, tap **🔍 Find the lyrics on Google**, copy the lyrics and paste them. AI never writes the lyrics: it misremembers them, and Gemini blocks quoted lyrics.
- **Paste cleanup (`songParse`):**
  - Anything above the first `[section]` line is dropped (contributors, translations, blurb), and so are junk lines ("You might also like", "…Embed").
  - `[Chorus: Jimin & Jung Kook]` sets the singers of the lines that follow; so do `[Jimin]`, `[Verse 2 - SUGA]` and `[Chorus: V (뷔)]` (member names and aliases are found anywhere in the header).
- **Romanization (`songRom`)** is worked out in code, never by AI: Revised Romanization with the common sound changes (했어 → haesseo, 합니다 → hamnida, 같이 → gachi). It is computed from each line when shown.
- **✨ Analyse (`songAnalyze`, needs a key)** makes two kinds of calls, so one failure can't wipe out everything:
  - **Singers (`songSingers`):** the whole song goes in, and the answer is names only for the lines marked `?`. Gemini looks up the song's line distribution on Google first (Search grounding, `gemini(…, { search: true })`, with Flash rather than Lite); if searching fails it answers from memory. It must always pick a member, guessing from the song's structure only when nothing is found. A second round asks again for any still missing. Guesses are kept as `gw` and shown with `?`.
  - **Meanings (`songMeanings`):** 20 lines per call, in the app's language (not the course's meaning language). Gemini can block an answer that matches published text (`finishReason: RECITATION`, shown in the error toast), so a refused chunk is split in half and retried. A single line it still refuses gets its meaning from free Google Translate.
- **Lyrics tab:**
  - A colour bar per member, and a chip where the singer changes. Tap the chip to fix that run of lines.
  - A 🔊 on every Korean line reads it with a Korean voice (`arVoiceFor("ko")`), whatever course is open, for pronunciation practice.
  - **Original / Romanized / Meaning** toggles hide layers for practice (`settings.songHide`).
- **Story tab (`songStory`):** looked up on Google first (Search grounding, Flash; falls back to memory if searching fails), so every section is filled from what it finds; the album and release date are always given and shown at the top, and if nothing else turns up only those basics show, with a note. Sections: about, origin & inspiration, meaning, theories and fun facts, written by AI in the app's language without quoting the lyrics. It carries a "may not be accurate" note.
- **Without a key:** the AI buttons show 🔒 and lead to the key setup. Songs analysed earlier stay readable.

Test: `.venv/bin/python tests/songs_test.py` (Gemini faked, placeholder lyrics).
