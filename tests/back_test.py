"""The phone's Back button / back swipe — end-to-end tests (see docs/architecture.md, "Views and navigation").

Drives the real index.html in headless Chromium; `page.go_back()` stands in for Android's Back. Back goes one
screen back like the in-app ←; things open on top close first; another tab goes to Vocab; only Vocab's main
screen leaves the app. Gemini is faked; no key or network needed.

Run from the repo root (add scenario letters to run only those, e.g. `... back_test.py B`):
    .venv/bin/python tests/back_test.py

Screenshots land in $BACK_TEST_OUT (default: a temp folder). Exit code 1 when anything fails.
"""
import functools, http.server, json, os, sys, tempfile, threading, traceback
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SP = os.environ.get("BACK_TEST_OUT") or os.path.join(tempfile.gettempdir(), "back-test")
os.makedirs(SP, exist_ok=True)
_srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT))
_srv.RequestHandlerClass.log_message = lambda *a: None
threading.Thread(target=_srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{_srv.server_address[1]}/index.html"

MODES = { m: m == "ko2m" for m in ["ko2m", "listen2m", "listen2kc", "m2ko", "listen2ko", "ko2say", "m2say"] }
def card(i, due):
    w = ["apple", "banana", "house", "river", "teacher", "window"][i]
    return { "id": f"c{i}", "lang": "en", "ko": w, "meaning": f"nghĩa {w}", "ex": "", "exMean": "", "ease": 2.5, "interval": 1, "reps": 1,
             "lapses": 0, "due": due, "last": 1 if due else 0, "created": 1 }

def init(due=True, welcomed=True):
    st = { "cards": [card(i, 1 if due else 9e15) for i in range(6)],
           "passages": [{ "id": "p1", "lang": "en", "title": "Test", "titleMean": "", "created": 1, "vocab": [],
                          "sentences": [{ "ko": "I like apples.", "meaning": "Tôi thích táo." }] }],
           "talk": { "id": "t1", "lang": "en", "created": 1, "scene": "cafe", "topic": "", "turns": [{ "who": "ai", "ko": "Hi!", "mean": "Chào!" }] },
           "settings": { "course": "en", "apiKey": "FAKE", "uiLang": "vi", "model": "gemini-2.5-flash-lite", "newPerDay": 0, "autoPlay": False, "talkTts": False, "speakAuto": True, "modes": MODES } }   # speakAuto: the one-time "key added → speaking questions on" already happened
    return r"""
if (location.protocol === "http:" && !sessionStorage.getItem("seeded")) {
  sessionStorage.setItem("seeded", "1");
  localStorage.setItem("hangulCards.v1", %s);
  %s
}
const realFetch = window.fetch;
window.fetch = async (url, opts) => {
  if (String(url).includes("generativelanguage")) {
    if (String(url).includes("/models?")) return new Response(JSON.stringify({ models: [{ name: "models/gemini-2.5-flash-lite", supportedGenerationMethods: ["generateContent"] }] }));
    return new Response(JSON.stringify({ candidates: [{ content: { parts: [{ text: "{}" }] } }] }));
  }
  return realFetch(url, opts);
};
""" % (json.dumps(json.dumps(st)), 'localStorage.setItem("hangulCards.welcomed", "1");' if welcomed else "")

results = []
def check(name, cond, info=""): results.append((name, bool(cond), info))
ONLY = {x.upper() for x in sys.argv[1:]}

def run(pw, name, fn, width=390, **kw):
    if ONLY and name not in ONLY: return
    b = pw.chromium.launch()
    page = b.new_page(viewport={"width": width, "height": 844})
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.add_init_script(init(**kw))
    try:
        page.goto("about:blank"); page.goto(URL); page.wait_for_timeout(1000)
        page.evaluate("speechSynthesis.speak = () => {}")
        fn(page)
    except Exception:
        check(name + ": ran without exception", False, " / ".join(l.strip() for l in traceback.format_exc().splitlines() if "Error" in l or "back_test.py" in l or "waiting" in l)[-400:])
        page.screenshot(path=f"{SP}/fail-{name}.png")
    check(name + ": no page errors", not errs, "; ".join(errs)[:300])
    b.close()

def back(page):
    page.go_back(wait_until="commit"); page.wait_for_timeout(350)
def vis(page, sel): return bool(page.query_selector(sel)) and page.is_visible(sel)
def view(page): return page.evaluate("[...document.querySelectorAll('section[id^=v-]')].filter(s => !s.classList.contains('hidden')).map(s => s.id).join()")
def in_app(page): return page.url.startswith(URL)
def vocab_home(page):
    page.click('nav [data-v="study"]'); page.wait_for_timeout(300)

def A(page):
    """Vocab: My words → Add words, then Back, Back to the home; Back on the home leaves the app."""
    vocab_home(page)
    page.click("#sLearn"); page.wait_for_timeout(300)
    page.click("#goAddBig"); page.wait_for_timeout(300)
    check("A: on Add words", view(page) == "v-add", view(page))
    back(page); check("A: Back → My words", view(page) == "v-words", view(page))
    back(page); check("A: Back → Vocab", view(page) == "v-study", view(page))
    back(page); page.wait_for_timeout(300)
    check("A: Back on Vocab's main screen leaves the app", not in_app(page), page.url)

def B(page):
    """Speak: picker → passages → passage → coach; each Back goes up one; then Vocab."""
    page.click('nav [data-v="read"]'); page.wait_for_timeout(300)
    page.click('#spHome .sp-pick[data-s="read"]'); page.wait_for_timeout(300)
    page.click('#passList li[data-id="p1"]'); page.wait_for_timeout(300)
    page.click("#sentList .sent .smic"); page.wait_for_timeout(300)
    check("B: coach open", vis(page, "#coach"))
    back(page); check("B: Back closes the coach, passage stays", not vis(page, "#coach") and vis(page, "#reader"))
    back(page); check("B: Back → passage list", vis(page, "#passList") and not vis(page, "#reader"))
    back(page); check("B: Back → Speak picker", vis(page, "#spHome"), view(page))
    back(page); check("B: Back from another tab → Vocab", view(page) == "v-study" and in_app(page), view(page))

def C(page):
    """Things on top close first: tutor, player options, course sheet, word menu, Translate."""
    vocab_home(page)
    page.click("#tuFab"); page.wait_for_timeout(300)
    back(page); check("C: Back closes the tutor", page.is_hidden("#tu") and view(page) == "v-study" and in_app(page))
    page.click(".co-btn"); page.wait_for_timeout(300)
    back(page); check("C: Back closes the course sheet", page.is_hidden("#courseModal") and in_app(page))
    page.click("#sLearn"); page.wait_for_timeout(300)
    page.click("#wordList .more-btn"); page.wait_for_timeout(200)
    back(page); check("C: Back closes the word menu, list stays", not page.query_selector("#wordList .menu") and view(page) == "v-words", view(page))
    page.click('nav [data-v="read"]'); page.wait_for_timeout(300)
    page.click('#spHome .sp-pick[data-s="read"]'); page.wait_for_timeout(300)
    page.click('#passList li[data-id="p1"]'); page.wait_for_timeout(300)
    page.click("#pOptBtn"); page.wait_for_timeout(200)
    back(page); check("C: Back closes player options, passage stays", page.is_hidden("#pOpts") and vis(page, "#reader"))
    page.click('nav [data-v="tr"]'); page.wait_for_timeout(500)
    check("C: Translate open", bool(page.query_selector("#arConvRoot *")))
    back(page); check("C: Back closes Translate, the tab below shows", not page.query_selector("#arConvRoot *") and view(page) == "v-read" and in_app(page), view(page))

def D(page):
    """A study round: Back ends it (answers already saved) and stays in the app."""
    vocab_home(page)
    page.wait_for_selector("#qBox .choice:not([disabled])", timeout=5000)
    page.locator("#qBox .choice").first.click(); page.wait_for_timeout(300)
    if vis(page, ".dock .grades button[data-q]"): page.locator(".dock .grades button[data-q]").last.click(); page.wait_for_timeout(300)
    check("D: in a full round", vis(page, "#endBtn"))
    back(page)
    check("D: Back ends the round, still in the app", not vis(page, "#endBtn") and in_app(page) and vis(page, "nav"))

def E(page):
    """Talk with AI: Back from the chat goes to the Speak picker and keeps the conversation."""
    page.click('nav [data-v="read"]'); page.wait_for_timeout(300)
    page.click('#spHome .sp-pick[data-s="talk"]'); page.wait_for_timeout(300)
    if vis(page, "#tkResume"): page.click("#tkResume"); page.wait_for_timeout(300)
    check("E: in the chat", vis(page, "#tkRec"))
    back(page); check("E: Back → Speak picker", vis(page, "#spHome"))
    page.click('#spHome .sp-pick[data-s="talk"]'); page.wait_for_timeout(300)
    check("E: conversation kept (straight back in it, or offered to resume)", vis(page, "#tkRec") or vis(page, "#tkResume"))

def F(page):
    """ARMY: Songs → Back → ARMY home → Back → Vocab."""
    page.click('nav [data-v="army"]'); page.wait_for_timeout(300)
    page.click("#arSongsOpen"); page.wait_for_timeout(300)
    back(page); check("F: Back → ARMY home", vis(page, "#arSongsOpen"), view(page))
    back(page); check("F: Back → Vocab", view(page) == "v-study" and in_app(page), view(page))

def G(page):
    """Welcome: Back on step 2 goes to step 1."""
    check("G: welcome shown", vis(page, "#welcome"))
    page.click("#wNext"); page.wait_for_timeout(300)
    check("G: on step 2", vis(page, "#wBack"))
    back(page); check("G: Back → step 1", vis(page, "#welcome") and not vis(page, "#wBack") and in_app(page))

def H(page):
    """Desktop: same rules (Back closes the tutor window, then goes up a screen)."""
    page.click('nav [data-v="set"]'); page.wait_for_timeout(300)
    page.click("#tuFab"); page.wait_for_timeout(300)
    back(page); check("H: Back closes the tutor", page.is_hidden("#tu") and view(page) == "v-set")
    back(page); check("H: Back → Vocab", view(page) == "v-study" and in_app(page))

if __name__ == "__main__":
    with sync_playwright() as pw:
        run(pw, "A", A, due=False)
        run(pw, "B", B)
        run(pw, "C", C, due=False)
        run(pw, "D", D)
        run(pw, "E", E)
        run(pw, "F", F)
        run(pw, "G", G, welcomed=False)
        run(pw, "H", H, width=1200)
    fails = [r for r in results if not r[1]]
    for n, ok, info in results:
        print(("PASS " if ok else "FAIL ") + n + ("" if ok else f"  ← {info}"))
    print(f"\n{len(results) - len(fails)}/{len(results)} passed  (screenshots: {SP})")
    sys.exit(1 if fails else 0)
