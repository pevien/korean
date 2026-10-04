"""IELTS Speaking mock test — end-to-end tests (see docs/ielts.md).

Drives the real index.html in headless Chromium. Gemini, the microphone and (in one
scenario) the speech voice are faked, so it needs no key, no mic and no network.

Run from the repo root (add scenario letters to run only those, e.g. `... ielts_test.py C U`):
    python3 -m venv .venv && .venv/bin/pip install playwright && .venv/bin/playwright install chromium
    .venv/bin/python tests/ielts_test.py

Screenshots of failures (and a few key screens) land in  (default: a temp folder).
Exit code 1 when anything fails.
"""
import functools, http.server, os, sys, tempfile, threading, traceback
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SP = os.environ.get("IELTS_TEST_OUT") or os.path.join(tempfile.gettempdir(), "ielts-test")
os.makedirs(SP, exist_ok=True)
_srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT))
_srv.RequestHandlerClass.log_message = lambda *a: None
threading.Thread(target=_srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{_srv.server_address[1]}/index.html"

def init(course="en", key="FAKE", ui="vi"):
    return r"""
if (!sessionStorage.getItem("seeded")) {
  sessionStorage.setItem("seeded", "1");
  localStorage.setItem("hangulCards.v1", JSON.stringify({ cards: [], settings: { course: "%s", apiKey: "%s", uiLang: "%s", model: "gemini-2.5-flash-lite" } }));
  localStorage.setItem("hangulCards.welcomed", "1");
}
window.__calls = []; window.__mock = { fail: 0, silent: false, bad: 0 };
if (localStorage.getItem("fakeVoice")) {
  const v = { name: "Fake English", lang: "en-GB", localService: true, default: true, voiceURI: "fake" };
  speechSynthesis.getVoices = () => [v];
  speechSynthesis.speak = u => { window.__spoken = (window.__spoken || 0) + 1; setTimeout(() => u.onend && u.onend(), 50); };
  window.SpeechSynthesisUtterance = class { constructor(t){ this.text = t; } };
}
const realFetch = window.fetch;
window.fetch = async (url, opts) => {
  if (String(url).includes("generativelanguage")) {
    if (String(url).includes("/models?")) return new Response(JSON.stringify({ models: [{ name: "models/gemini-2.5-flash-lite", supportedGenerationMethods: ["generateContent"] }] }));
    const body = JSON.parse(opts.body), p = body.contents[0].parts[0].text;
    const kind = p.includes("preparing a realistic") ? "gen" : p.includes("attached recording") ? "ans" : p.includes("strict IELTS") ? "band" : "other";
    window.__calls.push(kind);
    if (kind === "ans") window.__ansSchema = body.generationConfig.responseSchema;
    if (kind === "band") window.__bandPrompt = p;
    if (kind === "gen") window.__genPrompt = p;
    await new Promise(r => setTimeout(r, 200));
    if (kind === "band" && window.__mock.bad > 0) { window.__mock.bad--; return new Response(JSON.stringify({ candidates: [{ content: { parts: [{ text: '{"fc":{"band":6,"note":"x"}, "lr" {"band"' + '}' }] } }] })); }
    if (kind === "ans" && window.__mock.fail > 0) { window.__mock.fail--; return new Response(JSON.stringify({ error: { message: "quota" } }), { status: 429 }); }
    let out;
    if (kind === "gen" && window.__mock.objs) out = { p1: [{ topic: "Work or study", question: "Do you work or study?" }, { topic: "Food", q: { text: "What do you usually eat for breakfast?" } }],
      card: { topic: "Describe a book you enjoyed.", points: [{ point: "what it was" }, { text: "when you read it" }, "who wrote it"], end: "and explain why you enjoyed it." },
      follow: { q: "Do you read often?" }, p3: [{ q: "Why do fewer young people read books today?" }, { question: "Will e-books replace paper books?" }, "Should schools make reading compulsory?"] };
    else if (kind === "gen") out = { p1: [{ topic: "Work or study", q: "Do you work or are you a student?" }, { topic: "Music", q: "What kind of music do you like?" }, { topic: "Music", q: "Did you learn an instrument as a child?" }],
      card: { topic: "Describe a place you visited that you would like to go back to.", points: ["where it is", "when you went there", "what you did there"], end: "and explain why you would like to go back." },
      follow: "Do you often travel?", p3: ["Why do people like to travel?", "How has tourism changed in your country?"] };
    else if (kind === "ans" && window.__mock.partial) out = { heard: "I work as a nurse.", fixes: [], upgrades: [], note: "", issues: [] };   // Gemini leaving fields out
    else if (kind === "ans") out = window.__mock.silent ? { heard: "" } : { heard: "um I am work in a software company since three years, uh it is very good job", fixes: [{ from: "I am work", to: "I work", why: "Không dùng 'am' trước động từ thường." }],
      upgrades: [{ from: "very good job", to: "a rewarding job", why: "Tự nhiên hơn." }], note: "Đúng ý nhưng hơi ngắn.", score: 72, issues: [{ part: "three", tip: "Âm /θ/: /θriː/" }],
      sample: "I work as a software engineer and I find it really rewarding.",
      checks: [{ key: "x0", ok: true, tip: "" }, { key: "x1", ok: false, tip: "Thêm một lý do vì sao bạn thích công việc này." }, { key: "x2", ok: true, tip: "" }, { key: "x3", ok: false, tip: "Nối ý bằng 'because', 'for example'." }, { key: "x4", ok: true, tip: "" }],
      ideas: ["Kể thêm một dự án cụ thể bạn từng làm."] };
    else if (kind === "band") out = { fc: { band: 6, note: "Khá trôi chảy." }, lr: { band: 6.5, note: "Từ vựng ổn." }, gra: { band: 5.5, note: "Sai thì." }, p: { band: 6.5, note: "Dễ hiểu." },
      strengths: ["Đúng trọng tâm", "Phát âm rõ"], next: ["Luyện thì", "Mở rộng ý", "Giảm um/uh"] };
    else out = { t: [] };
    return new Response(JSON.stringify({ candidates: [{ content: { parts: [{ text: JSON.stringify(out) }] } }] }));
  }
  return realFetch(url, opts);
};
navigator.mediaDevices.getUserMedia = async () => { const ac = new AudioContext(), o = ac.createOscillator(), d = ac.createMediaStreamDestination(); o.connect(d); o.start(); return d.stream; };
if (navigator.permissions) { const q = navigator.permissions.query.bind(navigator.permissions); navigator.permissions.query = d => d && d.name === "microphone" ? Promise.resolve({ state: "granted" }) : q(d); }
""" % (course, key, ui)

results = []
def check(name, cond, info=""):
    results.append((name, bool(cond), info))

ONLY = {x.upper() for x in sys.argv[1:]}   # e.g. `tests/ielts_test.py C U` runs just those scenarios

def run(pw, name, fn, **kw):
    if ONLY and name not in ONLY: return
    b = pw.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
    page = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.add_init_script(init(**kw))
    try:
        page.goto(URL); page.wait_for_timeout(1200)
        fn(page)
    except Exception as e:
        check(name + ": ran without exception", False, traceback.format_exc().splitlines()[-1])
        page.screenshot(path=f"{SP}/fail-{name}.png")
    check(name + ": no page errors", not errs, "; ".join(errs)[:300])
    b.close()

def goto_ielts(page):
    page.click('nav [data-v="read"]'); page.wait_for_timeout(300)
    page.click('#spHome .sp-pick[data-s="ielts"]'); page.wait_for_timeout(300)

def answer(page, ms=1800, wait=900):
    page.click("#ieRec"); page.wait_for_timeout(ms)
    page.click("#ieRec"); page.wait_for_timeout(wait)

def reveal(page):   # questions are hidden while the examiner reads them out: tap "Show the question"
    if page.query_selector("#ieShowQ"): page.click("#ieShowQ"); page.wait_for_timeout(150)
    return txt(page, "#ielts")

def calls(page): return page.evaluate("window.__calls")
def saved(page): return page.evaluate("(JSON.parse(localStorage.getItem('hangulCards.v1')).ielts || [])")
def txt(page, sel): return page.inner_text(sel) if page.query_selector(sel) else ""

# A. other course: no IELTS
def t_ko(page):
    page.click('nav [data-v="read"]'); page.wait_for_timeout(300)
    check("A. Korean course hides the IELTS pick", not page.query_selector('#spHome .sp-pick[data-s="ielts"]'))

# B. no key
def t_nokey(page):
    goto_ielts(page)
    check("B. no key → 'Needs a Gemini key' card", "Gemini key" in txt(page, "#ielts"))
    check("B. no key → no mode picks", not page.query_selector('#ielts .sp-pick[data-m]'))

# C. full test + target band + rounding
def t_full(page):
    goto_ielts(page)
    page.click('#ieBand button[data-b="7.5"]'); page.wait_for_timeout(100)
    page.click('#ielts .sp-pick[data-m="full"]'); page.wait_for_timeout(900)
    check("C. Part 1 question shown", "Do you work" in reveal(page))
    check("C. tab bar hidden during the test", page.evaluate("document.body.classList.contains('talking')"))
    for _ in range(3): answer(page)
    check("C. Part 2 prep: cue card + timer", "Describe a place" in txt(page, "#ielts") and page.query_selector("#ieClock") is not None)
    t1 = txt(page, "#ieClock"); page.wait_for_timeout(1200); t2 = txt(page, "#ieClock")
    check("C. prep timer counts down", t1 != t2, f"{t1} → {t2}")
    page.fill("#ieNotes", "beach, 2019, swim")
    page.click("#ieReady"); page.wait_for_timeout(300)
    answer(page, 2500)
    check("C. Part 2 follow-up question", "Do you often travel" in reveal(page))
    answer(page)
    check("C. Part 3 reached", "Part 3" in txt(page, "#ielts .sub-head"))
    answer(page); answer(page, wait=4000)
    c = calls(page)
    check("C. AI calls: 1 gen + 7 answers + 1 band", c.count("gen") == 1 and c.count("ans") == 7 and c.count("band") == 1, str(c))
    s = saved(page)
    check("C. test saved once", len(s) == 1)
    if s:
        r = s[0]["result"]
        check("C. overall = 6.0 (mean 6.125 rounds down)", r["overall"] == 6, r["overall"])
        check("C. target 7.5 stored", s[0]["target"] == "7.5")
        check("C. no temp fields in history", not any(k in q for q in s[0]["qs"] for k in ("busy", "err", "seq", "dur")) and "notes" not in s[0])
        check("C. lang en", s[0]["lang"] == "en")
    t = txt(page, "#ielts")
    check("C. result shows band + 4 criteria", "6.0" in t and all(k in t for k in ["Fluency", "Lexical", "Grammatical", "Pronunciation"]))
    check("C. result shows target gap", "7.5" in t)
    tone = lambda sel: page.get_attribute(sel, "class") or ""
    check("C. overall 6.0 vs target 7.5 → red", "t-bad" in tone(".ie-big"))
    pills = [page.get_attribute(e, "class") for e in ["#ielts .ie-crit:nth-child(%d) .ie-pill" % k for k in (1, 2, 3, 4)]]
    check("C. criteria pills: 6.0 red · 6.5 amber · 5.5 red · 6.5 amber", ["t-bad" in pills[0], "t-warn" in pills[1], "t-bad" in pills[2], "t-warn" in pills[3]] == [True] * 4, str(pills))
    check("C. 'New test' is the purple main button", (page.get_attribute("#ieAgain", "class") or "").split() == ["btn"])
    page.screenshot(path=f"{SP}/t-result.png")
    # open part details + model answer
    page.click("#ielts details[data-p='1'] summary"); page.wait_for_timeout(200)
    page.click("#ielts details[data-p='1'] [data-a='more']"); page.wait_for_timeout(200)
    check("C. details stay open after expanding an answer", page.evaluate("document.querySelector(\"#ielts details[data-p='1']\").open"))
    check("C. model answer + my recording buttons", page.query_selector("#ielts [data-a='sample']") is not None and page.query_selector("#ielts [data-a='mine']") is not None)
    # band choice persists after reload; history still there
    page.reload(); page.wait_for_timeout(1200)
    goto_ielts(page)
    check("C. after reload: target band still 7.5", page.query_selector('#ieBand button.on').get_attribute("data-b") == "7.5")
    check("C. after reload: history button shows 1", page.query_selector("#ieHistOpen") is not None and "1" in txt(page, "#ieHistOpen"))
    # H. history open + delete
    page.click("#ieHistOpen"); page.wait_for_timeout(200)
    check("H. history list item", page.query_selector("#ieHist li") is not None)
    page.click("#ieHist li"); page.wait_for_timeout(200)
    check("H. past test: no 'my recording' (audio not kept)", page.query_selector("#ielts [data-a='mine']") is None)
    # T. retake the same questions from history
    page.click("#ieRetake"); page.wait_for_timeout(600)
    c0 = calls(page).count("gen")
    check("T. retake starts at Part 1 of the same test, no new AI script", "1/7" in txt(page, "#ielts .sub-head") and c0 == 0 and "Do you work" in reveal(page), str(calls(page)))
    for _ in range(3): answer(page)
    check("T. retake has the same cue card", "Describe a place you visited" in txt(page, "#ielts"))
    page.click("#ieEnd"); page.wait_for_timeout(100); page.click("#ieEnd"); page.wait_for_timeout(2500)
    s2 = saved(page)
    check("T. retake saved as a new test, the old one kept", len(s2) == 2 and s2[1]["from"] == s2[0]["id"] and s2[1]["qs"][0]["q"] == s2[0]["qs"][0]["q"] and s2[0]["qs"][0].get("a"))
    check("T. finished retake offers Retake + New test", page.query_selector("#ieRetake") is not None and page.query_selector("#ieAgain") is not None)
    page.click("#ieHistOpen"); page.wait_for_timeout(200)
    page.click("#ieHist li:last-child"); page.wait_for_timeout(200)
    page.click("#ieDel"); page.wait_for_timeout(100)
    check("H. first tap only arms delete", len(saved(page)) == 2)
    page.click("#ieDel"); page.wait_for_timeout(300)
    check("H. second tap deletes", len(saved(page)) == 1)

# D. Part 2 practice
def t_p2(page):
    goto_ielts(page)
    page.click('#ielts .sp-pick[data-m="2"]'); page.wait_for_timeout(900)
    check("D. starts in prep", page.query_selector("#ieReady") is not None)
    h = page.evaluate("document.querySelector('#ieNotes').getBoundingClientRect().bottom"); c = page.evaluate("document.querySelector('.ie-ctl').getBoundingClientRect().top")
    check("D. notes box reaches down to the controls", 0 <= c - h <= 20, f"gap {c-h:.0f}px")
    page.screenshot(path=os.path.join(SP, "t-notes.png"))
    page.click("#ieReady"); page.wait_for_timeout(200)
    answer(page, 2500, 1500)
    check("D. feedback shown after answer", "I work" in txt(page, "#ielts") and page.query_selector("#ieNext") is not None)
    page.click("#ieRedo"); page.wait_for_timeout(200)
    check("D. 'Try again' on the cue card goes back to ready (no new prep)", page.query_selector("#ieRec") is not None and page.query_selector("#ieReady") is None)
    answer(page, 2500, 1500)
    page.click("#ieNext"); page.wait_for_timeout(500)
    check("D. follow-up question next", "Do you often travel" in reveal(page))
    answer(page, 1800, 1500)
    page.click("#ieNext"); page.wait_for_timeout(2500)
    c = calls(page)
    check("D. calls: gen + 3 answers (incl. retry) + band", c.count("ans") == 3 and c.count("band") == 1, str(c))
    s = saved(page)
    check("D. saved with 2 questions", len(s) == 1 and len(s[0]["qs"]) == 2)
    check("D. Part 2 length stat shown", "0:02" in txt(page, "#ielts") or "0:03" in txt(page, "#ielts"), txt(page, ".stats"))

# E. redo race: redo while scoring must not land the old answer
def t_redo_race(page):
    goto_ielts(page)
    page.click('#ielts .sp-pick[data-m="3"]'); page.wait_for_timeout(900)
    page.evaluate("window.__mock.silent = true")
    page.click("#ieRec"); page.wait_for_timeout(1500); page.click("#ieRec"); page.wait_for_timeout(50)
    page.click("#ieRedo"); page.wait_for_timeout(800)
    check("E. after redo, the old (still scoring) answer doesn't appear", page.query_selector("#ielts .ie-fb") is None and page.query_selector("#ieRec") is not None)
    answer(page, 1500, 1200)
    check("J. silent answer → 'No answer was heard'", "Không nghe được" in txt(page, "#ielts"))
    page.evaluate("window.__mock.silent = false")

# F. back mid-test → resume
def t_resume(page):
    goto_ielts(page)
    page.click('#ielts .sp-pick[data-m="1"]'); page.wait_for_timeout(900)
    answer(page, 1500, 1200)
    page.click("#ieNext"); page.wait_for_timeout(300)
    page.click("#ieBack"); page.wait_for_timeout(300)
    check("F. back → setup with 'In progress'", page.query_selector("#ieResume") is not None, txt(page, "#ielts")[:200])
    check("F. tab bar back on setup", not page.evaluate("document.body.classList.contains('talking')"))
    page.click("#ieBack"); page.wait_for_timeout(300)
    check("F. Speak home shows 'Đang thi dở'", "Đang thi dở" in txt(page, "#spHome"))
    page.click('#spHome .sp-pick[data-s="ielts"]'); page.wait_for_timeout(300)
    page.click("#ieResume"); page.wait_for_timeout(300)
    check("F. resumes at question 2", "2/3" in txt(page, "#ielts .sub-head"), txt(page, "#ielts .sub-head"))
    # K. too short
    page.click("#ieRec"); page.wait_for_timeout(500); page.click("#ieRec"); page.wait_for_timeout(500)
    check("K. too-short answer → message, still on question 2", "Ngắn quá" in txt(page, "#ieStatus") and "2/3" in txt(page, "#ielts .sub-head"))
    # M. switching tab while recording stops the mic
    page.click("#ieRec"); page.wait_for_timeout(700)
    page.evaluate("document.querySelector('nav [data-v=\"study\"]').click()")
    page.wait_for_timeout(1500)
    check("M. leaving the tab: no answer sent", calls(page).count("ans") == 1, str(calls(page)))
    # G. submit early (2 taps)
    page.click('nav [data-v="read"]'); page.wait_for_timeout(300)
    if page.query_selector('#spHome .sp-pick[data-s="ielts"]') and page.is_visible('#spHome'): page.click('#spHome .sp-pick[data-s="ielts"]'); page.wait_for_timeout(300)
    page.click("#ieResume"); page.wait_for_timeout(300)
    check("M. back on question 2, mic idle", "2/3" in txt(page, "#ielts .sub-head") and "on" not in (page.get_attribute("#ieRec", "class") or ""))
    page.click("#ieEnd"); page.wait_for_timeout(100)
    check("G. first tap on Submit only arms it", page.query_selector("#ieRec") is not None)
    page.click("#ieEnd"); page.wait_for_timeout(2000)
    s = saved(page)
    check("G. early submit scores answered questions only", len(s) == 1 and sum(1 for q in s[0]["qs"] if q.get("a")) == 1)
    bp = page.evaluate("window.__bandPrompt") or ""
    check("G. band prompt: only the answered question, no penalty for the rest", bp.count("ANSWER (") == 1 and "do NOT lower" in bp)
    check("G. result says 'scored on 1/3 answers'", "1/3" in txt(page, "#ielts"))

# I. a 429 answer is retried at submit
def t_retry(page):
    goto_ielts(page)
    page.click('#ielts .sp-pick[data-m="full"]'); page.wait_for_timeout(900)
    page.evaluate("window.__mock.fail = 1")
    answer(page)
    page.click("#ieEnd"); page.wait_for_timeout(100); page.click("#ieEnd"); page.wait_for_timeout(7000)
    s = saved(page)
    check("I. failed answer retried and scored", len(s) == 1 and s[0]["qs"][0].get("a") and s[0]["qs"][0]["a"]["heard"], str(calls(page)))

# P. all silent → no save, back to list
def t_silent(page):
    goto_ielts(page)
    page.click('#ielts .sp-pick[data-m="full"]'); page.wait_for_timeout(900)
    page.evaluate("window.__mock.silent = true")
    answer(page)
    page.click("#ieEnd"); page.wait_for_timeout(100); page.click("#ieEnd"); page.wait_for_timeout(1500)
    check("P. nothing heard → not saved", len(saved(page)) == 0)
    check("P. nothing heard → back to setup with resume", page.query_selector("#ieResume") is not None)

# Q. Gemini wraps lines in objects
def t_objs(page):
    goto_ielts(page)
    check("Q. disclaimer merged into the target band card", "±0.5" in txt(page, "#ielts .card") and len(page.query_selector_all("#ielts > p.small")) == 0)
    page.evaluate("window.__mock.objs = true")
    page.click('#ielts .sp-pick[data-m="full"]'); page.wait_for_timeout(900)
    seen = []
    for k in range(8):
        t = reveal(page); seen.append(t)
        w = page.evaluate("[document.documentElement.scrollWidth, innerWidth]")
        if w[0] > w[1]: check(f"Q. no sideways scroll (screen {k})", False, str(w)); break
        if page.query_selector("#ieReady"): page.click("#ieReady"); page.wait_for_timeout(200)
        if not page.query_selector("#ieRec"): break
        answer(page)
    allt = " | ".join(seen)
    check("Q. no [object Object] anywhere", "object Object" not in allt)
    for q in ["Do you work or study?", "What do you usually eat", "what it was", "when you read it", "Do you read often?", "Why do fewer young people", "Will e-books replace", "Should schools make"]:
        check(f"Q. shows: {q}", q in allt)
    page.screenshot(path=os.path.join(SP, "t-objs.png"))

# R. listen first: question hidden while a voice reads it; broken JSON is asked again
def t_listen(page):
    page.evaluate("localStorage.setItem('fakeVoice', '1')"); page.reload(); page.wait_for_timeout(1200)
    goto_ielts(page)
    page.click('#ielts .sp-pick[data-m="1"]'); page.wait_for_timeout(900)
    check("R. examiner speaks the question", (page.evaluate("window.__spoken") or 0) >= 1)
    check("R. question text hidden at first", "Do you work" not in txt(page, "#ielts") and page.query_selector("#ieShowQ") is not None)
    page.click("#ieShowQ"); page.wait_for_timeout(200)
    check("R. 'Show the question' reveals it", "Do you work" in txt(page, "#ielts"))
    answer(page, 1500, 1200)
    page.click("#ieNext"); page.wait_for_timeout(400)
    check("R. next question hidden again", "What kind of music" not in txt(page, "#ielts") and page.query_selector("#ieShowQ") is not None)
    page.evaluate("window.__mock.bad = 1")
    page.click("#ieEnd"); page.wait_for_timeout(100); page.click("#ieEnd"); page.wait_for_timeout(2500)
    c = calls(page)
    check("R. broken JSON on scoring → asked again, saved", c.count("band") == 2 and len(saved(page)) == 1, str(c))
    page.evaluate("window.__mock.bad = 2")
    page.click("#ieAgain"); page.wait_for_timeout(900)
    gp = page.evaluate("window.__genPrompt") or ""
    check("R. new test avoids recent topics (Part 2 + Part 1)", "Describe a place you visited" in gp and '"Music"' in gp)
    page.click("#ieShowQ"); answer(page, 1500, 1200)
    page.click("#ieEnd"); page.wait_for_timeout(100); page.click("#ieEnd"); page.wait_for_timeout(2500)
    check("R. broken twice → error with 'Try again' button", page.query_selector("#ieRetry") is not None)
    page.click("#ieRetry"); page.wait_for_timeout(2000)
    check("R. 'Try again' then scores it", len(saved(page)) == 2)

# S. answer schema forces score + model answer; a missing score shows "—", never 0
def t_schema(page):
    goto_ielts(page)
    page.click('#ielts .sp-pick[data-m="1"]'); page.wait_for_timeout(900)
    page.evaluate("window.__mock.partial = true")
    answer(page, 1500, 1500)
    req = page.evaluate("(window.__ansSchema || {}).required || []")
    check("S. schema requires every answer field", all(k in req for k in ["heard", "fixes", "upgrades", "note", "score", "issues", "sample"]), str(req))
    t = txt(page, "#ielts")
    check("S. missing score → '—/100', not 0/100", "—/100" in t and "0/100" not in t, t[-300:])
    check("S. no 'Model answer' label when there is none", "Câu trả lời mẫu" not in t)
    page.evaluate("window.__mock.partial = false")
    page.click("#ieRedo"); page.wait_for_timeout(200); answer(page, 1500, 1500)
    page.click("[data-a='more']"); page.wait_for_timeout(200)
    t = txt(page, "#ielts")
    check("S. full answer → score + model answer shown", "72/100" in t and "rewarding" in t)

# U. content & development checks, per part
def t_content(page):
    goto_ielts(page)
    page.click('#ielts .sp-pick[data-m="full"]'); page.wait_for_timeout(900)
    answer(page); answer(page); answer(page)
    page.click("#ieReady"); page.wait_for_timeout(200); answer(page, 2000)
    answer(page); answer(page); answer(page, wait=3000)
    ap = page.evaluate("window.__ansSchema") or {}
    check("U. schema requires checks + ideas", all(k in ap.get("required", []) for k in ["checks", "ideas"]))
    for p in (1, 2, 3):
        page.click(f"#ielts details[data-p='{p}'] summary"); page.wait_for_timeout(150)
    t = txt(page, "#ielts")
    check("U. 'Content & development' section shown", t.count("Nội dung & mạch ý") == 7)
    check("U. Part 1 checks", "Trả lời thẳng vào câu hỏi" in t and "Mở rộng bằng lý do/chi tiết" in t)
    check("U. Part 2 checks = each card point + structure", "Ý thẻ đề: where it is" in t and "Ý thẻ đề: what you did there" in t and "Có mở – thân – kết" in t)
    check("U. Part 3 checks", all(k in t for k in ["Nêu rõ quan điểm", "Có ví dụ cụ thể", "Mạch ý logic", "không sa đà"]))
    check("U. tip shown only for unmet checks + ideas", "Thêm một lý do" in t and "Kể thêm một dự án" in t)
    check("U. content section sits above the corrections", t.index("Nội dung & mạch ý") < t.index("Sửa lỗi"))
    # past test from history keeps its own card points
    page.click("#ieRetake"); page.wait_for_timeout(500); page.click("#ieBack"); page.wait_for_timeout(200)
    page.click("#ieHistOpen"); page.wait_for_timeout(200); page.click("#ieHist li"); page.wait_for_timeout(200)
    page.click("#ielts details[data-p='2'] summary"); page.wait_for_timeout(150)
    check("U. history view labels its own card points", "Ý thẻ đề: where it is" in txt(page, "#ielts"))
    page.screenshot(path=os.path.join(SP, "t-content.png"), full_page=True)

# L. English UI
def t_en_ui(page):
    goto_ielts(page)
    t = txt(page, "#ielts")
    check("L. English UI labels", "Target band" in t and "Full mock test" in t, t[:120])

with sync_playwright() as pw:
    run(pw, "A", t_ko, course="ko")
    run(pw, "B", t_nokey, key="")
    run(pw, "C", t_full)
    run(pw, "D", t_p2)
    run(pw, "E", t_redo_race)
    run(pw, "F", t_resume)
    run(pw, "I", t_retry)
    run(pw, "P", t_silent)
    run(pw, "Q", t_objs, ui="en")
    run(pw, "R", t_listen)
    run(pw, "S", t_schema)
    run(pw, "U", t_content)
    run(pw, "L", t_en_ui, ui="en")

ok = sum(1 for r in results if r[1])
for n, c, i in results: print(("PASS " if c else "FAIL ") + n + ("" if c or not i else "  →  " + str(i)))
print(f"\n{ok}/{len(results)} passed")
