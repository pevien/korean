# Architecture

## Files

| File | Role |
|---|---|
| `index.html` | The whole app: HTML, CSS, an inline Phosphor icon sprite and all JavaScript. There is no build step and no dependencies. |
| `sw.js` | Service worker. Serves the app from cache (offline use) and sends review reminders. |
| `manifest.webmanifest` | PWA manifest: name "Grow with PV", standalone display, theme `#4f46e5`, background `#12131a` |
| `icon-*.png`, `apple-touch-icon.png` | App icons; the 512 px icon also has a maskable version |

**Deployment:** the app is plain static files on GitHub Pages at <https://pevien.github.io/korean/>, so pushing to `main` publishes it. When a change touches the app shell, bump `CACHE` in `sw.js` (currently `hangul-v20`). Old caches are then removed on activate.

## Views and navigation

**The bottom nav** (`nav button[data-v]`):

| Button | `data-v` | Section |
|---|---|---|
| Vocab | `study` | `#v-study`; sub-pages `#v-add`, `#v-words`, `#v-abc` |
| Speak | `read` | `#v-read`, which holds `#spHome`, `#readHome`/`#reader` and `#talk` |
| Translate | `tr` | Not a section. `arInterpOpen()` renders an overlay into `#arConvRoot`. |
| ARMY | `army` | `#v-army` |
| Settings | `set` | `#v-set` |

**Switching views:**

- `show(v)` switches the section and closes the Translate overlay.
- `navRoot(v)` handles tapping a nav button, including auto-starting a review on Vocab.

**Navigation state:**

- Saved in **sessionStorage**, key `hangulCards.nav`.
- Fields: `{v, p, y, sp, tr}`, which are the tab, open passage, scroll position, Speak screen, and whether Translate is open.
- A reload returns to the same place.

## State

All data is in one object, `S`. `load()` deep-merges it with `defaults()`, and `save()` writes it to localStorage under `hangulCards.v1`.

```text
S
├─ cards[]     { id, lang, ko, meaning, ex, exMean,
│                ease, interval, reps, lapses, due, last, created, mod }
├─ passages[]  { id, lang, created, title, titleMean, level, prompt,
│                sentences[{ko, meaning, best}], vocab[{ko, meaning}] }
├─ talk        the conversation in progress
├─ talks[]     finished Talk-with-AI conversations (latest 60)
├─ lives[]     saved ARMY / interpreter transcripts
├─ settings    see below
├─ daily       { date, newCount, reviews, result, c: { <course>: {...} } }
├─ streak      { last, count, days: ["Y-M-D", …] }   // days: every studied day, for the calendar
└─ deleted     { <id>: timestamp }   // tombstones used by sync
```

**Courses:**

- Every card, passage and talk has a `lang`. A missing `lang` means `ko`.
- The word field is named `ko` in every course; it holds the word in the course language.
- `CUR` is the current course. `deck()` returns `S.cards.filter(inCourse)`.
- The per-course pieces are:
  - `courseSet()`: holds the level. Korean uses `S.settings` itself; other courses use `S.settings.byCourse[code]`.
  - `DY()`: daily counters. Korean uses `S.daily`; other courses use `S.daily.c[code]`.
- A course's definition in `COURSES` covers:
  - the speech locale and voice-matching patterns
  - the script detector (`is` / `strict`)
  - the unit for speech scoring and its native pace
  - its levels
  - the text the AI prompts need

**Settings:**

- `newPerDay`, `modes`, `autoPlay`, `rate`, `voice` and `voiceBy`, `apiKey`, `model`, `autoEx`, `uiLang`, `course`, `byCourse`, `coachGrade`, `talkTts`, `speakAuto`
- the `army*` options: engine, audio source, read-aloud, font size, hide original, language pairs
- `_mod`: the last time settings changed

**`save()` does these steps in order:**

1. Runs `autoSpeakModes()`.
2. Runs `track()`. It stamps changed items with `mod`, records tombstones for deleted ids, and stamps `settings._mod`. Changes to voice and course are left out because they are per device.
3. Writes to localStorage.
4. Asks Drive sync to push (debounced).
5. Refreshes the reminder snapshot.

### Other storage

**localStorage:**

| Key | Contents |
|---|---|
| `hangulCards.v1` | `S` |
| `hangulCards.sync` | Drive config `{clientId, on, last, fileId}` |
| `hangulCards.gtoken` | Google OAuth token and its expiry |
| `hangulCards.keyOk` | Fingerprint of the verified Gemini key |
| `hangulCards.models` | Cached Gemini model list |
| `hangulCards.notify` | Whether reminders are on for this device |
| `hangulCards.welcomed` | Set once the welcome screen has been closed |
| `hangulCards.nudge` | When each nudge was snoozed |
| `hangulCards.voiceGoogle` | One-time switch to the Google voice |
| `hangulCards.army` | Live transcripts of the interpreter and BTS Live |
| `hangulCards.armyTr` | Translation phrase cache (400 entries) |

**sessionStorage:** `hangulCards.nav` and `wStep` (the welcome-screen step).

**Cache Storage:**

| Cache | Contents |
|---|---|
| `hangul-v20` | The app shell |
| `hangul-notify` | The snapshot of what is due (`./__notify-state`) that the service worker reads for reminders |

## Interface language (i18n)

- **The page is written in English.** `UI` (`vi` or `en`) is read once at startup, and changing it reloads the app.
- **Strings built in JavaScript** use `L(vi, en)`.
- **The static and generated English DOM**, when the UI is Vietnamese:
  - A `MutationObserver` translates text nodes plus `placeholder`, `title` and `aria-label` attributes.
  - Lookups go through the `VI` dictionary, then the `VI_RX` regex rules.
  - `VI_UI_ONLY` words are translated only inside controls.
- **Not auto-translated:** `[data-noi18n]`, elements with a `lang` attribute, `script`, `style`, `textarea`, `.exm` and `.exl`. Sections built with `L()` carry `data-noi18n`.
- **Other courses:** outside the Korean course, "Korean" and "Seoul" in page text are swapped for the course's language and city.

## Icons

- **The sprite:** Phosphor icons (MIT, regular and fill) in an inline SVG sprite. `ic(name)` returns `<use href="#i-name">`.
- **Emoji become icons:** `iconize()` and an observer replace emoji in controls (🎙 🔊 🗑 🔑 🌐 …) with sprite icons, using the `EMOJI_IC` map.
  - Opt out with `[data-noicon]`. The welcome screen and the ARMY subtitles are also exempt.
  - Emoji are kept deliberately for ARMY/BTS content and for celebrations.
- **`fitRow()`** tightens rows of buttons that overflow.

## Service worker

**Caching:**

- On **install**, the app shell is pre-cached, bypassing the browser's HTTP cache (`cache: "reload"`). Each file is cached separately, so one missing file doesn't break install.
- `skipWaiting` and `clients.claim` let a new service worker take over immediately.
- **Fetch** handles same-origin GET requests only:
  - It answers from the cache first, so a weak connection never stalls the app.
  - Any page navigation, with or without a query string, gets `index.html`.
  - In the background it always fetches a fresh copy and updates the cache. **A new version therefore shows up the time after it has downloaded.**
  - That background fetch uses `cache: "no-cache"`: the server is asked whether the file changed (a small 304 if not), so GitHub Pages' 10-minute HTTP cache doesn't delay updates.
- **Not touched:** cross-origin requests, such as Gemini, the translation APIs and Google sign-in.
- The service worker is registered only over https.

**Reminders:**

1. A `periodicsync` event with the tag `review-reminder` (minimum interval 4 h) runs `remind()`.
2. `remind()` reads the snapshot and checks four conditions:
   - reminders are on and notification permission is granted
   - it is not 00:00–05:00
   - at least 6 h have passed since the last notification
   - something is due, or new words are left (counted per course against `newPerDay`)
3. If all pass, it shows a notification in the UI language.
4. Tapping the notification focuses the app, or opens it.

## External services

| Service | Used for | Key? |
|---|---|---|
| Gemini API (`generativelanguage.googleapis.com/v1beta`) | Everything AI: text, vision (screenshots), audio (pronunciation, Talk, AI translation) | User's own key, sent in the `x-goog-api-key` header |
| Google Translate web endpoint (`translate.googleapis.com`, `client=gtx`) | Meanings for words and sentences | No |
| MyMemory (`api.mymemory.translated.net`) | Fallback translation | No |
| Google Identity Services (`accounts.google.com/gsi/client`, loaded only when needed) and Drive v3 | Sync | User's own OAuth Client ID |

**Browser APIs:**

- Web Speech: both speech recognition and speech synthesis
- Chrome's on-device `Translator`
- MediaRecorder, Web Audio, getDisplayMedia (tab audio)
- Wake Lock
- Periodic Background Sync and Notifications

**Gemini calls:**

- `gemini()` asks for JSON output. Temperature is 0.9 for text and 0.3 when audio or an image is attached.
- `askAI()` uses the key when there is one. Otherwise it opens the copy/paste dialog (`manualAI`).
- `extractJSON()` pulls the JSON out of either kind of reply.
- **Feedback language:** feedback is requested in the UI language, and `fixFeedbackLang()` corrects replies that come back in the wrong language.
