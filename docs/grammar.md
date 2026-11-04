# Grammar

A list of Korean grammar points inside the **Speak** tab. Learners read each point, search the list and mark what they have learned. It works offline and needs no Gemini key.

## Where it is

**Speak → Grammar**, in the Korean course only. Other courses don't show the row, and a reload there returns to the Speak home screen.

The row shows progress once the lessons have loaded, for example "12 of 36 learned". The Back button goes from a lesson to the list, then to Speak. A reload returns to the list.

## The list

- **Search:** matches the pattern and its forms first, then meanings, then usage text and examples, in Vietnamese, English and Korean. Vietnamese marks are optional, so `muon` finds `muốn`.
- **Filters:** All / To learn / Learned.
- **Level chips:** All levels / Sơ cấp 1 / Sơ cấp 2 / Trung cấp. They are built from the levels in the file, and shown only when it has two or more.
- **The circle on a row** marks a point as learned, or undoes it.

## A lesson

Each lesson shows, in the interface language:

- the pattern and its short meaning
- when to use it, with examples for each use; 🔊 reads an example aloud
- the structure: a how-to line, what to add in each case, and examples that show the join (좋다 → 좋 + 아요 → 좋아요)
- irregulars and notes, when it has any; each note has examples, and wrong sentences are marked ✗ and aren't read aloud
- vowel contraction, in lessons built on 아/어: it sits in Notes and says it isn't an irregular
- **My notes:** a private box for how the learner understands the point, or anything that looks wrong; it saves while typing
- a button to mark it as learned

## Content

`grammar-ko.json` holds 190 points: 36 at Sơ cấp 1, 32 at Sơ cấp 2 and 122 at Trung cấp. Every text field comes as `{ vi, en }`:

```text
{ id, level, pattern, meaning,
  how,                             // optional: one how-to line for the structure
  structure[{ when, form, ex, add, change }],   // add: "add <form>"; change: "change 하다 to <form>"; ex: " · " between examples
  uses[{ when, ex[{ ko, vi, en }] }],
  irregular[{ name, note, ex }],   // optional
  notes,                           // optional
  notesEx[{ ko, vi, en, wrong }],  // with notes; wrong marks a sentence not to copy
  vowels[{ rule, ex }] }           // optional: vowel contraction, spelled for this lesson's ending
```

- **Levels:** `s1` (Sơ cấp 1), `s2` (Sơ cấp 2), `i1` (Trung cấp).
- **Never change an `id`:** progress is stored under it.
- **To change content:** edit the file and bump `CACHE` in `sw.js`. A new point or level needs no code change, but update the counts in `tests/grammar_test.py`. A new level also needs its label in `GR_LEVELS`.
- **Correcting mistakes:** learners can't edit a lesson; My notes is their own place for a correction. Fixes for everyone are made in the file.
- **Sources:** the choice of points follows common lists for TOPIK 1, TOPIK 2 and intermediate Korean. Explanations and examples were written for this app and have not yet been reviewed by a Korean teacher.

## Progress

`S.grammar[]` holds `{ id, lang, learned, note, mod }`, where `learned` is a timestamp or 0. A record is created the first time a point is marked or gets a note. Un-marking sets `learned` to 0 and keeps the record, so the newest change wins on Drive sync. The mark and the note travel as one record, so if both devices change the same point before syncing, the newer record replaces the other. Backups include it, and importing never overwrites progress already on the device. Marking a point doesn't count towards the streak.

## AI tutor

- **The open lesson:** the tutor reads the visible screen, so it can see it.
- **What was learned:** in the Korean course, the patterns marked as learned go into its system prompt (`tuGrammar()`). With nothing marked, that line is left out and the tutor works as before.
- **Only a hint:** a pattern that isn't marked may still be known, so the prompt tells it not to assume a gap, avoid a pattern, or send the learner to study grammar.

## Loading

The lessons are fetched once per app start, when Speak opens or at startup if something is marked as learned. The service worker pre-caches the file. If the first download fails, the screen offers **Try again**.

## Tests

`tests/grammar_test.py` drives the real `index.html` in headless Chromium and checks the shape of `grammar-ko.json`. It can't check whether the Korean is right. Sync is covered by `tests/sync_test.py`, import by `tests/backup_test.py` and the tutor hint by `tests/tutor_test.py`.
