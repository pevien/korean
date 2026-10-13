# AI tutor

A floating 💬 bubble in the bottom-right corner opens a chat with an AI tutor. It follows you around the app (except the screens with their own mic, below), so you can ask about whatever is on screen.

## When it shows

- **Needs a Gemini key.** The bubble only appears while a key is set; adding or removing the key in Settings shows or hides it straight away.
- **Hidden in Speak → Reading, Talk with AI and Translate.** Those screens have their own mic (and Reading / Talk their own AI coach). An open tutor closes when you go there and comes back elsewhere.
- **Placement:** on a phone the bubble moves up above whatever is pinned to the bottom of the screen (tab bar, study sheet, ARMY controls). On a desktop it opens as a floating panel in the corner.

## Asking

- **Typing.**
- **Voice:** 🎙, then ⏹ to send, up to 60 s.
- **Photo:** 📷, or paste an image into the box. It is sent as JPEG together with any typed text.

## Who the tutor is

- **Korean course:** a **BTS member**, picked at random for each chat (page load or the ✎ new-chat button), never the same one twice in a row: RM 🐨, Jin 🐹, SUGA 🐱, j-hope 🐿️, Jimin 🐥, V 🐻 or Jung Kook 🐰. Each has their own tone; the teaching rules stay the same.
- **Other courses:** the plain "AI tutor".
- **Header:** the course's flag follows the tutor's name (switch the course from the app header, since that reloads the app). Under the name, a **level** dropdown sets the app-wide level, and the next answers follow it.

## What it knows

- The course, the level and the interface language.
- The text of the screen you are on, so "what does this mean?" works without copying anything.

## Voice questions

- The recording goes straight to the tutor, with no separate transcription. With the chat in view it hears mixed Vietnamese/Korean far better.
- The reply starts with a `HEARD:` line, written in the language(s) you actually spoke and never translated. The app takes it out and shows it under your recording as a transcript.
- **Nothing heard:** the `HEARD:` line is empty, no transcript is shown, and the tutor asks you to say it again.

## Answers

- It answers and stops: no "want more examples?"-style question at the end of each reply.
- **During a quiz** it gives hints first and only gives the answer when you ask for it.
- Bold words in the course language are underlined; tap one to hear it.

## Chat history

- The chat is kept until you reload or tap ✎ (new chat).
- Only the last **50** messages are sent, and only the latest **6** still carry their photos and recordings. Older recordings are sent as their `HEARD:` text, older photos as "[earlier photo]".

## Code and test

- Code: the `TU` block (`TU_BTS`, `tuPickIdol`, `tuSync`, `tuPlace`, `tuSystem`, `tuAsk`) in `index.html`. `save()` calls `window.__tutorSync`, which is how adding or removing the key shows or hides the bubble.
- Test: `tests/tutor_test.py` (Gemini, the mic and photos faked).
