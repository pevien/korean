"""My words: tick words and study just those — end-to-end tests (see docs/study.md, "My words").

Drives the real index.html in headless Chromium; no key or network needed. New words go through the usual intro,
quiz and schedule; a known word's schedule only moves on a wrong answer, once per round, without touching the streak.

Run from the repo root (add scenario letters to run only those, e.g. `... pick_test.py B`):
    .venv/bin/python tests/pick_test.py

Screenshots land in $PICK_TEST_OUT (default: a temp folder). Exit code 1 when anything fails.
"""
import functools, http.server, json, os, sys, tempfile, threading, time, traceback
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SP = os.environ.get("PICK_TEST_OUT") or os.path.join(tempfile.gettempdir(), "pick-test")
os.makedirs(SP, exist_ok=True)
_srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT))
_srv.RequestHandlerClass.log_message = lambda *a: None
threading.Thread(target=_srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{_srv.server_address[1]}/index.html"

DAY = 86400000
FAR = int(time.time() * 1000) + 40 * DAY
MODES = { m: m == "ko2m" for m in ["ko2m", "listen2m", "listen2kc", "m2ko", "listen2ko", "ko2say", "m2say"] }
WORDS = ["apple", "banana", "house", "river", "teacher", "window"]
def card(i):
    w, known = WORDS[i], i >= 2   # apple, banana are new; the rest are mastered, due in 40 days
    return { "id": f"c{i}", "lang": "en", "ko": w, "meaning": f"nghĩa {w}", "ex": "", "exMean": "", "ease": 2.5, "interval": 40 if known else 0, "reps": 5 if known else 0,
             "lapses": 0, "due": FAR if known else 0, "last": 1000 if known else 0, "created": i + 1 }

def init():
    st = { "cards": [card(i) for i in range(6)], "settings": { "course": "en", "uiLang": "vi", "newPerDay": 2, "modes": MODES } }
    return r"""
if (location.protocol === "http:" && !sessionStorage.getItem("seeded")) {
  sessionStorage.setItem("seeded", "1");
  localStorage.setItem("hangulCards.v1", %s);
  localStorage.setItem("hangulCards.welcomed", "1");
}
""" % json.dumps(json.dumps(st))

results = []
def check(name, cond, info=""): results.append((name, bool(cond), info))
ONLY = {x.upper() for x in sys.argv[1:]}

def run(pw, name, fn, dark=False):
    if ONLY and name not in ONLY: return
    b = pw.chromium.launch()
    page = b.new_page(viewport={"width": 390, "height": 844}, color_scheme="dark" if dark else "light")
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.add_init_script(init())
    try:
        page.goto("about:blank"); page.goto(URL); page.wait_for_timeout(800)
        page.evaluate("speechSynthesis.speak = () => {}")
        fn(page)
    except Exception:
        check(name + ": ran without exception", False, " / ".join(l.strip() for l in traceback.format_exc().splitlines() if "Error" in l or "pick_test.py" in l or "waiting" in l)[-400:])
        page.screenshot(path=f"{SP}/fail-{name}.png")
    check(name + ": no page errors", not errs, "; ".join(errs)[:300])
    b.close()

def state(page): return page.evaluate("JSON.parse(localStorage.getItem('hangulCards.v1'))")
def get(page, id): return next(c for c in state(page)["cards"] if c["id"] == id)
def daily(page): return state(page)["daily"].get("c", {}).get("en", {})
def open_words(page, tab):
    page.click('#v-study .st-go[data-f="today"]'); page.wait_for_selector("#wordList")
    page.click(f'#filterTabs [data-f="{tab}"]')
def tick(page, word): page.click(f'#wordList li:has(b:text-is("{word}")) .t div:nth-child(2)')
def word(page): return page.inner_text("#qBox .ko").strip()
def answer(page, right):
    """Multiple choice: the right meaning, or any other. Returns the word asked."""
    w = word(page)
    btn = [b for b in page.query_selector_all("#qBox .choice") if (f"nghĩa {w}" in b.inner_text()) == right][0]
    btn.click(); page.wait_for_selector("#fb .dock")
    return w
def cont(page): page.click("#contBtn"); page.wait_for_timeout(120)

def A(page):
    """Pick mode: a tap ticks a row, ticks survive changing tab and search, select all covers what's on screen, Back leaves."""
    open_words(page, "new")
    check("A: starts without ticks", not page.query_selector(".wsel") and page.is_visible("#wordsPick") and page.is_hidden("#wordsSel"))
    page.click("#wordsPick")
    check("A: ticks replace ⋯", len(page.query_selector_all(".wsel")) == 2 and not page.query_selector(".more-btn"))
    check("A: nothing picked, nothing to start", page.is_disabled("#pickGo") and "(0)" in page.inner_text("#pickGo"))
    tick(page, "apple")
    check("A: a row tap ticks it", "(1)" in page.inner_text("#pickGo") and page.is_checked('li[data-id="c0"] .wsel'))
    page.click('li[data-id="c1"] .speak')
    check("A: 🔊 doesn't tick", "(1)" in page.inner_text("#pickGo"))
    page.click('#filterTabs [data-f="master"]')
    tick(page, "house")
    check("A: ticks kept across tabs", "(2)" in page.inner_text("#pickGo"))
    page.click("#searchBtn"); page.fill("#search", "river"); tick(page, "river"); page.click("#searchBtn")
    check("A: ticks kept across a search", "(3)" in page.inner_text("#pickGo"))
    page.click("#pickAll")
    check("A: select all = rows on screen", "(5)" in page.inner_text("#pickGo") and "Đã chọn 5" in page.inner_text("#pickN") and "Bỏ chọn" in page.inner_text("#pickAll"))
    page.click("#pickAll")
    check("A: clear all = rows on screen", "(1)" in page.inner_text("#pickGo"))
    page.click("#wordList li:first-child .t div:nth-child(2)"); page.click("#wordList li:first-child .t div:nth-child(2)")
    page.screenshot(path=f"{SP}/pick.png")
    page.go_back(wait_until="commit"); page.wait_for_timeout(350)
    check("A: Back leaves pick mode, stays on the page", page.is_visible("#v-words") and page.is_visible("#wordsPick") and not page.query_selector(".wsel"))
    page.click("#wordsPick"); page.click("#pickX")
    check("A: ✕ leaves pick mode", page.is_visible("#wordsCta") and not page.query_selector(".wsel"))

def B(page):
    """A mixed pick: the new word gets intro + quiz + schedule and spends today's allowance; the known word answered right is left alone."""
    open_words(page, "new")
    page.click("#wordsPick"); tick(page, "apple")
    page.click('#filterTabs [data-f="master"]'); tick(page, "house"); page.click("#pickGo")
    page.wait_for_timeout(200)
    check("B: session opened", page.is_visible("#studySession"))
    asked = []
    for _ in range(4):
        if page.query_selector("#gotIt"): asked.append("intro " + word(page)); page.click("#gotIt"); page.wait_for_timeout(120); continue
        w = answer(page, True); asked.append(w)
        if w == "house":
            check("B: known word shows Continue, no grades", page.query_selector("#contBtn") and not page.query_selector("#fb .grades"))
            cont(page)
        else:
            check("B: new word gets Hard/Good", page.query_selector("#fb .grades button[data-q='4']") and not page.query_selector("#fb .grades button[data-q='5']"))
            page.click("#fb .grades button[data-q='4']"); page.wait_for_timeout(120)
        if not page.is_visible("#studySession"): break
    check("B: only the picked words, each once", sorted(asked) == ["apple", "house", "intro apple"], asked)
    check("B: back on the home page", page.is_visible("#studyHome"))
    h, a = get(page, "c2"), get(page, "c0")
    check("B: known word's schedule untouched", (h["due"], h["interval"], h["reps"], h["ease"], h["lapses"], h["last"]) == (FAR, 40, 5, 2.5, 0, 1000), h)
    check("B: new word is on the schedule", a["last"] and a["interval"] == 1, a)
    check("B: counts toward today's new words", daily(page).get("newCount") == 1, daily(page))
    check("B: the other new word isn't touched", get(page, "c1")["last"] == 0)

def C(page):
    """A known word answered wrong: one lapse however often it's missed, back in the round until right, then tomorrow; no streak or review count."""
    open_words(page, "master")
    page.click("#wordsPick"); tick(page, "house"); page.click("#pickGo"); page.wait_for_timeout(200)
    answer(page, False)
    check("C: wrong → Continue only", page.query_selector("#contBtn") and not page.query_selector("#fb .grades"))
    cont(page)
    h = get(page, "c2")
    check("C: wrong resets the word", (h["interval"], h["reps"], h["lapses"], round(h["ease"], 2)) == (0, 0, 1, 2.3), h)
    check("C: due in about 10 min", h["due"] - int(time.time() * 1000) < 11 * 60000, h)
    check("C: asked again", page.is_visible("#studySession") and word(page) == "house")
    answer(page, False); cont(page)
    h = get(page, "c2")
    check("C: a second miss isn't a second lapse", h["lapses"] == 1 and round(h["ease"], 2) == 2.3, h)
    answer(page, True); cont(page)
    h = get(page, "c2")
    check("C: right again → tomorrow", h["interval"] == 1 and abs(h["due"] - int(time.time() * 1000) - DAY) < 60000, h)
    check("C: left Mastered", h["interval"] < 21)
    check("C: round over", page.is_visible("#studyHome"))
    d = daily(page)
    check("C: not a review of the day, no streak", not d.get("reviews") and not state(page).get("streak", {}).get("count"), (d, state(page).get("streak")))

def D(page):
    """The extra-practice and missed-word rounds stay schedule-free: a wrong answer there changes nothing."""
    # finish today's two new words, then Extra practice is on offer
    page.click('#v-study .st-go[data-f="today"]'); page.click("#wordsStudy"); page.wait_for_timeout(200)
    for _ in range(8):
        if page.query_selector("#gotIt"): page.click("#gotIt"); page.wait_for_timeout(120); continue
        if not page.is_visible("#studySession"): break
        answer(page, True); page.click("#fb .grades button[data-q='4']"); page.wait_for_timeout(120)
        if not page.is_visible("#studySession"): break
    page.wait_for_timeout(200)
    page.click("#pracBtn"); page.wait_for_timeout(200)
    before = { c["id"]: (c["due"], c["interval"], c["lapses"]) for c in state(page)["cards"] }
    answer(page, False); cont(page)
    after = { c["id"]: (c["due"], c["interval"], c["lapses"]) for c in state(page)["cards"] }
    check("D: wrong in Extra practice changes nothing", before == after)

def E(page):
    """Dark mode at phone width: the pick bar fits and shows the last row."""
    open_words(page, "master")
    page.click("#wordsPick"); tick(page, "house"); page.wait_for_timeout(100)
    page.evaluate("scrollTo(0, 9999)"); page.wait_for_timeout(100)
    bar = page.evaluate("document.querySelector('#wordsSel').getBoundingClientRect().toJSON()")
    last = page.evaluate("document.querySelector('#wordList li:last-child').getBoundingClientRect().bottom")
    check("E: last row clears the bar", last <= bar["top"], (last, bar["top"]))
    check("E: no sideways scroll", page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
    page.screenshot(path=f"{SP}/pick-dark.png")

if __name__ == "__main__":
    with sync_playwright() as pw:
        run(pw, "A", A)
        run(pw, "B", B)
        run(pw, "C", C)
        run(pw, "D", D)
        run(pw, "E", E, dark=True)
    fails = [r for r in results if not r[1]]
    for n, ok, info in results:
        print(("PASS " if ok else "FAIL ") + n + ("" if ok else f"  ← {info}"))
    print(f"\n{len(results) - len(fails)}/{len(results)} passed  (screenshots: {SP})")
    sys.exit(1 if fails else 0)
