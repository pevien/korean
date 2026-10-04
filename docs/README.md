# Grow with PV — Feature documentation

Grow with PV is a single-file PWA for learning vocabulary, reading aloud and speaking practice in six languages, plus a live interpreter and BTS-livestream subtitles. It runs fully in the browser; an optional (free) Gemini API key unlocks the AI features.

Live app: <https://pevien.github.io/korean/> (GitHub Pages, served straight from `main` — no build step).

## Contents

| Page | Covers |
|---|---|
| [study.md](study.md) | **Vocab** tab: daily review, spaced repetition, quiz types, adding words, My words, Alphabet, streaks, text-to-speech |
| [speak.md](speak.md) | **Speak** tab: reading passages, audio player and shadowing, pronunciation coach, Talk with AI |
| [translate-army.md](translate-army.md) | **Translate** tab (face-to-face interpreter) and **ARMY** tab (live BTS subtitles, saved conversations) |
| [settings.md](settings.md) | **Settings** tab: language, course, study options, voice, Gemini key, Google Drive sync, reminders, backup, guide, welcome |
| [architecture.md](architecture.md) | Files, state and storage, i18n, icons, service worker, external services, deployment |

## Courses

One app holds several courses. Each course has its own words, progress, passages and level; the streak and most settings are shared. The current course is picked per device (Settings, the welcome screen, or the course button in the Vocab/Speak titles), and switching reloads the app.

| Code | Course | Levels | Meanings shown in |
|---|---|---|---|
| `en` 🇬🇧 | English | CEFR A1–C1 | Vietnamese |
| `ko` 🇰🇷 | Korean | Absolute beginner, TOPIK 1–4 | English |
| `ja` 🇯🇵 | Japanese | Absolute beginner, JLPT N5–N2 | English |
| `zh` 🇨🇳 | Chinese (Simplified) | HSK 1–5/6 | English |
| `th` 🇹🇭 | Thai | Beginner – Upper-intermediate | English |
| `vi` 🇻🇳 | Vietnamese | A1–B2 | English |

A fresh install starts on English. Data from before courses existed has no `lang` field and is treated as Korean.

## Interface language

The UI is Vietnamese (default) or English. Change it in **Settings → Language** or in the welcome screen.

## Tabs

| Tab | Purpose |
|---|---|
| **Vocab** (Từ vựng) | Flashcard review with spaced repetition; add and manage words |
| **Speak** (Luyện nói) | Reading passages with pronunciation scoring; spoken conversation with an AI |
| **Translate** (Dịch) | Split-screen two-person interpreter, Papago-style |
| **ARMY** | Live translated subtitles for BTS livestreams; saved conversations |
| **Settings** (Cài đặt) | Everything configurable, plus the built-in guide |

## What needs a Gemini key

A key is free from <https://aistudio.google.com/apikey>. Without one, most AI text features still work through a **copy/paste fallback**: the app shows the prompt, you run it in any chatbot, and you paste the JSON reply back.

| Feature | Without a key | With a key |
|---|---|---|
| AI word lists by topic | Copy/paste fallback | Direct |
| Example sentences for words | Copy/paste (30 words at a time) | Automatic on add |
| Add words: single / paste list | Free (Google Translate → MyMemory fills meanings) | Same |
| Add words / passage from screenshot | ✗ | ✓ (Gemini vision) |
| AI-written reading passage | Copy/paste fallback | Direct |
| Own text → passage | Free (local split + free translation) | AI pairs translations |
| Reader, player, shadowing | ✓ (browser TTS) | Same |
| Speaking checks, "⚡ Basic" | ✓ (browser speech recognition; accuracy + fluency only) | Same |
| Speaking checks, "✨ AI" | ✗ | ✓ (4 scores and detailed tips) |
| Talk with AI | ✗ | ✓ |
| Translate / ARMY, Basic engine | ✓ (speech recognition + on-device translator / MyMemory) | Gemini improves the translations |
| Translate / ARMY, AI engine; tab audio | ✗ | ✓ |
