# Settings tab

Settings (`#v-set`, `renderSettings`) has no app header; like every tab, it has its own icon-and-title row. The cards, from top to bottom, are described below.

## Language

The **VIE / ENG** switch sets the interface language. Changing it reloads the app.

## You're learning + Study

**Course grid:** six flag buttons for English, Korean, Japanese, Chinese, Thai and Vietnamese.

- Switching course reloads the app.
- The same picker also opens from:
  - the course button in the Vocab and Speak titles (it shows a sheet with a word count per course)
  - the welcome screen
- "Each course keeps its own words, progress and passages. Your streak and settings are shared."

**Study options:**

| Setting | Default | Notes |
|---|---|---|
| New words per day | 10 | 1–100; one limit for all courses, counted separately per course |
| Question types | All 7 on | Grouped as Choose / Type / Speak (see [study.md](study.md#question-types)); at least one must stay on |
| Auto-play audio for vocabulary | On | Reads the word aloud on new-word cards and "word → meaning" questions |

The **level** is not set here. Choose it in the Level menus in Add words, Reading and Talk. Those three menus share one level for each course.

## Voice

| Setting | Notes |
|---|---|
| Voice | Lists the device's voices for the course language, best first |
| Speed | Presets: 🐢 Slow 0.7, Learner 0.85, Native 1, plus a slider from 0.5 to 1.2. The reading player and Talk use the same speed. |
| Test | Says the course's greeting, for example 안녕하세요 |
| Test microphone | Checks mic access. If it fails, it gives the exact fix: no mic, mic in use, mic blocked (with steps for your OS), or a copy opened without https. |

- **The voice is not synced:** it is stored for each device and each course.
- **No voice for the language:** the app warns you and shows how to install one.

## AI (Gemini key)

The key powers word generation, example sentences, passages, AI pronunciation feedback, Talk, and AI translation.

**Gemini API key**

- **Getting a key:** free from <https://aistudio.google.com/apikey>. The built-in guide walks through it.
- **Masking:** after saving, the field shows only the first 4 characters followed by dots.
  - Tapping the field clears it so you can paste a new key. Leaving it empty keeps the old key.
  - Copying and dragging the key are blocked.
- **Checking:** the key is checked against Google's free model-list endpoint.
- **🗑 Remove key:** appears once the key has been verified. Tap twice to remove the key.
- **Syncing:** the key syncs through Google Drive if sync is on. It is never included in an exported backup.

**Model**

- The list comes live from Google and is limited to Gemini Flash and Flash-Lite models, with Flash-Lite first.
- **Automatic (recommended)** uses the first model in that list.
  - Before the list has loaded, the defaults are `gemini-2.5-flash-lite`, then `gemini-2.5-flash`.
- "Flash-Lite: cheapest, most free requests — fine for studying and ARMY. Flash: more accurate but fewer free requests."
- **Model not available:** if a model isn't found or is overloaded, the request is retried once with the next model.

**Test connection** sends a test translation request to check the key.

**Auto-add example sentences:** default on. When on, words you add get an example sentence. Needs a key.

**Errors:**

- **Rate limit (429):** "Gemini limit reached — wait a minute".
- **400 / 403:** "API key problem".

**No key: copy/paste fallback.** For AI text features, the app opens a "Use a free chatbot" dialog:

1. Copy the prompt.
2. Paste it into Gemini or ChatGPT (links are provided).
3. Paste the whole reply back and tap **Use answer**.

The dialog also has an **Add key** shortcut.

## Google Drive sync

Keeps words, progress, passages, conversations and settings (including the Gemini key) the same on all your devices. The data lives in a hidden app folder in **your own** Google Drive, in the file `hangul-cards-sync.json` (scope `drive.appdata`).

**Setup:**

- **You need your own OAuth Client ID.** The built-in guide has the six Google Cloud steps:
  1. Create a project.
  2. Enable the Drive API.
  3. Set the Auth Platform to External.
  4. Add yourself as a test user.
  5. Create a Web client with the origin `https://pevien.github.io`.
  6. Copy the Client ID.
- **Optional:** setting the `GOOGLE_CLIENT_ID` constant in the code hides the Client ID field.
- **Connect Google Drive** signs you in with Google Identity Services.
  - On other devices, use the same Client ID and the same Google account.

**Sync status:**

- A status pill shows ☁️ ✅ (synced), ☁️ … (syncing) or ☁️ ⚠️ (sign-in expired or error).
- Tap the pill to sync now.
- Sync status appears only in Settings.

**When syncing happens:**

- About 4 s after any change.
- When the app is opened or comes back to the foreground.
- When the app goes to the background, if changes are waiting.
- At startup.
- When the sign-in (about 1 hour) has expired, it renews on your next tap anywhere in the app.

**Merging:**

- **Words, passages, conversations, talks:**
  - For each item, the newer edit wins.
  - Deletions are remembered for 180 days, so a deleted item doesn't come back.
  - Duplicate words in a course are merged, keeping the one with more reviews.
- **Settings:**
  - The newer copy wins.
  - Not synced: voice and course, which stay per device.
- **Streak:** the later date wins.
- **Daily counts:** the higher number wins.

**🗑 Disconnect** (two taps) turns off sync and signs out. Your data stays on the device, and the Drive file is not deleted.

## Review reminders

**Remind me on this device**: sends a notification when there are words to review or new words left.

- **Where it works:**
  - Chrome or Edge with the app installed.
  - Over https.
  - With notification permission.
  - Using Periodic Background Sync, which checks about every 4 h.
- **When it stays quiet:**
  - 00:00–05:00.
  - Within 6 h of the last reminder.
  - When nothing is due.
- **The notification:**
  - Title: "🎯 Time to review!"
  - Body, for example: "3 words to review · 5 new words".
- **Not synced:** the setting is per device.
- **Unsupported setup:** when your browser or setup can't send reminders, the card explains why.

## Backup

**Export** downloads `grow-with-pv-backup-YYYY-MM-DD.json`. It contains all your data except the API key.

**Import** merges a backup into your current data:

- Words, passages and conversations you don't already have are added.
- Settings and streak are restored only if this device has no words yet. Your current key and course are kept.

**Delete all data** asks for a second tap within 4 s.

- **With sync on:** it also deletes the Drive copy.
- **If deleting the Drive copy fails:** nothing is deleted.
- Your key and Drive connection are removed as well.

## Guide

Expandable help topics are placed inside the card they relate to; the rest are collected in **General guide**. The topics are:

- **Quick start:** how the Vocab and Speak tabs work.
- **Install the app:** steps for Android, iPhone/iPad and computers. Always open the app from <https://pevien.github.io/korean/>.
- **How to get a free Gemini key.**
- **Drive sync setup and troubleshooting.**
- **Microphone & speaking:** permission steps for each OS.
- **Backup.**
- **FAQ:** privacy, cost, and "not seeing the latest version? Close the app fully and reopen it while online."

**↺ Show the welcome screen again** reopens the welcome screen.

## Welcome screen

The welcome screen appears on first launch and has a VI/EN switch. It has two steps:

1. **Introduction:**
   - "Grow a new language with PV 🌿"
   - Three highlights: flashcards, speaking feedback with AI talk, and live translation.
   - A personal note from PV ("보라해!").
2. **"What do you want to learn?":** choose one of the six courses.

Closing it saves the course you chose.

Installing the app is not part of the welcome screen. Instead, an install nudge appears later on the Vocab home screen.
