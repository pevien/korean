"""🔊 read aloud — the start of a word must not be cut off (see speak() in index.html).

Drives the real index.html in headless Chromium with speechSynthesis faked, and checks that a word is never
spoken in the same tick as cancel() (that clips its first syllable), that rapid taps only read the last word,
and that stopping also drops a word still waiting to start.

Run from the repo root:
    .venv/bin/python tests/tts_test.py
"""
import functools, http.server, json, os, sys, threading, traceback
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT))
_srv.RequestHandlerClass.log_message = lambda *a: None
threading.Thread(target=_srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{_srv.server_address[1]}/index.html"

ST = { "cards": [], "settings": { "course": "ko", "uiLang": "en", "voice": "Yuna", "rate": 1 } }
INIT = r"""
if (!sessionStorage.getItem("seeded")) {
  sessionStorage.setItem("seeded", "1");
  localStorage.setItem("hangulCards.v1", %s);
  localStorage.setItem("hangulCards.welcomed", "1");
  localStorage.setItem("hangulCards.voiceGoogle", "1");
}
// fake TTS: each utterance "plays" for 300 ms; log every cancel / speak with its time
window.__log = [];
const fake = { speaking: false, pending: false, cur: null, t: null,
  getVoices: () => [{ name: "Yuna", lang: "ko-KR" }],
  addEventListener(){}, onvoiceschanged: null,
  cancel(){ __log.push({ a: "cancel", t: performance.now() }); clearTimeout(this.t);
    const u = this.cur; this.cur = null; this.speaking = false; if (u && u.onerror) u.onerror({}); },
  speak(u){ __log.push({ a: "speak", text: u.text, t: performance.now() }); this.cur = u; this.speaking = true;
    if (u.onstart) u.onstart({});
    this.t = setTimeout(() => { this.speaking = false; this.cur = null; if (u.onend) u.onend({}); }, 300); } };
Object.defineProperty(window, "speechSynthesis", { value: fake, configurable: true });
window.SpeechSynthesisUtterance = function(text){ this.text = text; };
""" % json.dumps(json.dumps(ST))

results = []
def check(name, cond, info=""): results.append((name, bool(cond), info))

def log(page): return page.evaluate("__log")
def reset(page): page.evaluate("__log.length = 0")

SAY = "document.querySelector('#testVoice').click()"          # Settings → Test voice: speak(\"안녕하세요\")
STOP = "document.querySelector('button[data-v=\"study\"]').click()"   # switching tabs stops reading aloud
def spoken(page): return [x["text"] for x in log(page) if x["a"] == "speak"]

def tests(page):
    # idle for long: a short wait to wake the speakers, no cancel needed, and the word is read
    reset(page); page.evaluate(SAY); page.wait_for_timeout(400)
    check("idle: nothing cancelled", not any(x["a"] == "cancel" for x in log(page)), log(page))
    check("idle: word read", spoken(page) == ["안녕하세요"], log(page))

    # while a word is playing: cancel, then the new word only after a pause
    page.evaluate(SAY); page.wait_for_timeout(250); reset(page)
    page.evaluate(SAY); page.wait_for_timeout(300)
    l = log(page)
    c = next((x for x in l if x["a"] == "cancel"), None); s = next((x for x in l if x["a"] == "speak"), None)
    check("busy: old word cancelled", c is not None, l)
    check("busy: new word read", s is not None, l)
    check("busy: not in the same tick as cancel", c and s and s["t"] - c["t"] >= 60, l)

    # rapid taps while busy: read once, not once per tap
    page.evaluate(SAY); page.wait_for_timeout(250); reset(page)
    page.evaluate(SAY + "; " + SAY + "; " + SAY); page.wait_for_timeout(300)
    check("rapid: read once", len(spoken(page)) == 1, log(page))

    # leaving the screen drops a word still waiting to start
    page.evaluate(SAY); page.wait_for_timeout(250); reset(page)
    page.evaluate(SAY + "; " + STOP); page.wait_for_timeout(300)
    check("stop: waiting word dropped", not spoken(page), log(page))

with sync_playwright() as pw:
    b = pw.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
    page = b.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.add_init_script(INIT)
    try:
        page.goto(URL); page.wait_for_timeout(1000)
        tests(page)
    except Exception:
        check("ran without exception", False, traceback.format_exc()[-600:])
    check("no page errors", not errs, "; ".join(errs)[:300])
    b.close()

fails = [r for r in results if not r[1]]
for n, ok, info in results: print(("PASS " if ok else "FAIL ") + n + ("" if ok else f"  — {info}"))
print(f"\n{len(results) - len(fails)}/{len(results)} passed")
sys.exit(1 if fails else 0)
