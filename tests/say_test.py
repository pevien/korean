"""Study speaking questions with ✨ AI grading — end-to-end tests (see docs/study.md, "Speaking questions").

Drives the real index.html in headless Chromium. Gemini and the microphone are faked, so it needs
no key, no mic and no network. Checks the strict prompt, that the AI's score is shown as-is, and the issue list.

Run from the repo root (add scenario letters to run only those, e.g. `... say_test.py B`):
    .venv/bin/python tests/say_test.py

Screenshots land in $SAY_TEST_OUT (default: a temp folder). Exit code 1 when anything fails.
"""
import functools, http.server, json, os, sys, tempfile, threading, traceback
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SP = os.environ.get("SAY_TEST_OUT") or os.path.join(tempfile.gettempdir(), "say-test")
os.makedirs(SP, exist_ok=True)
_srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT))
_srv.RequestHandlerClass.log_message = lambda *a: None
threading.Thread(target=_srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{_srv.server_address[1]}/index.html"

MODES = { m: False for m in ["ko2m", "listen2m", "listen2kc", "m2ko", "listen2ko", "m2say"] }

def init(course, word, meaning, answer, ui="vi"):
    st = { "cards": [{ "id": "c1", "lang": course, "ko": word, "meaning": meaning, "ex": "", "exMean": "", "ease": 2.5, "interval": 1,
                       "reps": 1, "lapses": 0, "due": 1, "last": 1, "created": 1 }],
           "settings": { "course": course, "apiKey": "FAKE", "uiLang": ui, "model": "gemini-2.5-flash-lite", "newPerDay": 0,
                         "coachGrade": "ai", "speakAuto": True, "autoPlay": False, "modes": dict(MODES, ko2say=True) } }
    return r"""
if (!sessionStorage.getItem("seeded")) {
  sessionStorage.setItem("seeded", "1");
  localStorage.setItem("hangulCards.v1", %s);
  localStorage.setItem("hangulCards.welcomed", "1");
}
window.__prompts = [];
const realFetch = window.fetch;
window.fetch = async (url, opts) => {
  if (String(url).includes("generativelanguage")) {
    if (String(url).includes("/models?")) return new Response(JSON.stringify({ models: [{ name: "models/gemini-2.5-flash-lite", supportedGenerationMethods: ["generateContent"] }] }));
    const body = JSON.parse(opts.body), p = body.contents[0].parts[0].text;
    window.__prompts.push(p); window.__temp = body.generationConfig.temperature;
    await new Promise(r => setTimeout(r, 150));
    const out = p.includes("attached recording") ? %s : { t: [] };
    return new Response(JSON.stringify({ candidates: [{ content: { parts: [{ text: JSON.stringify(out) }] } }] }));
  }
  return realFetch(url, opts);
};
navigator.mediaDevices.getUserMedia = async () => { const ac = new AudioContext(), o = ac.createOscillator(), d = ac.createMediaStreamDestination(); o.connect(d); o.start(); return d.stream; };
if (navigator.permissions) { const q = navigator.permissions.query.bind(navigator.permissions); navigator.permissions.query = d => d && d.name === "microphone" ? Promise.resolve({ state: "granted" }) : q(d); }
""" % (json.dumps(json.dumps(st)), json.dumps(answer))

results = []
def check(name, cond, info=""): results.append((name, bool(cond), info))
ONLY = {x.upper() for x in sys.argv[1:]}

def run(pw, name, fn, **kw):
    if ONLY and name not in ONLY: return
    b = pw.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
    page = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.add_init_script(init(**kw))
    try:
        page.goto(URL); page.wait_for_timeout(1000)
        fn(page)
    except Exception:
        check(name + ": ran without exception", False, traceback.format_exc().splitlines()[-1])
        page.screenshot(path=f"{SP}/fail-{name}.png")
    check(name + ": no page errors", not errs, "; ".join(errs)[:300])
    b.close()

def say(page, name):
    if page.query_selector("#startBtn"): page.click("#startBtn")
    page.wait_for_selector("#sayRec")
    page.click("#sayRec"); page.wait_for_timeout(1200)
    page.click("#sayRec")
    page.wait_for_selector("#fb .qfb", timeout=8000)
    page.screenshot(path=f"{SP}/{name}.png")
    return page.inner_text("#fb .qfb"), page.evaluate("window.__prompts.find(p => p.includes('attached recording'))")

ISSUES = [{ "part": "음", "type": "linking", "tip": "Chưa nối âm: ㅁ phải chuyển sang âm sau, đọc [으막]." },
          { "part": "악", "type": "batchim", "tip": "ㄱ cuối bị bật hơi, giữ lưỡi lại không bật [으막]." },
          { "part": "", "type": "pace", "tip": "Đọc tách từng âm tiết, hơi chậm." }]

def A(page):
    """Korean, right word with 3 issues: the AI's score is shown unchanged; every issue listed with its type; strict prompt."""
    text, p = say(page, "A-ko")
    check("A: verdict correct", "Correct" in text or "Chính xác" in text or "✅" in text, text[:80])
    check("A: AI score shown as-is", "78/100" in text, text[:120])
    check("A: standard pronunciation shown", "[으막]" in text)
    check("A: all 3 issues listed", page.eval_on_selector_all("#fb .say-iss > .small", "e => e.length") == 3)
    check("A: issue types labelled in Vietnamese", all(t in text.lower() for t in ["nối âm", "patchim", "tốc độ"]), text)
    check("A: prompt checks linking & sound rules", "연음" in p and "비음화" in p and "EVERY way" in p)
    check("A: prompt has deduction rubric", "Start at 100" in p and "at most 90" in p and "must match them" in p)
    check("A: low temperature", page.evaluate("window.__temp") == 0.2)

def B(page):
    """No issues: a native-like 98 is kept and the 'good' line shows instead of a list."""
    text, _ = say(page, "B-clean")
    check("B: score kept", "98/100" in text, text[:120])
    check("B: no issue list", not page.query_selector("#fb .say-iss"))
    check("B: good line", "Rõ ràng" in text)

def C(page):
    """English, wrong word: what was heard sits on the score line, the issues right after; English prompt uses COACH lists."""
    text, p = say(page, "C-en")
    check("C: verdict wrong", "❌" in text, text[:80])
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    i_score = next((i for i, l in enumerate(lines) if "/100" in l), -1)
    check("C: heard on the score line", i_score >= 0 and "acomodation" in lines[i_score], lines)
    check("C: issues right after the score line", i_score >= 0 and lines[i_score + 1] == "1", lines)
    check("C: score from AI kept", "35/100" in text)
    check("C: issue listed", page.eval_on_selector_all("#fb .say-iss > .small", "e => e.length") == 1)
    check("C: prompt uses English stress / linking checks", "word stress" in p and "linking between words" in p)

def D(page):
    """Gemini leaving fields out (no issues, no score): nothing breaks, no score line."""
    text, _ = say(page, "D-partial")
    check("D: no score line", "/100" not in text, text[:120])
    check("D: verdict shown", "✅" in text, text[:80])

with sync_playwright() as pw:
    run(pw, "A", A, course="ko", word="음악", meaning="âm nhạc",
        answer={ "heard": "음악", "correct": True, "pron": "[으막]", "score": 78, "issues": ISSUES, "good": "" })
    run(pw, "B", B, course="ko", word="음악", meaning="âm nhạc",
        answer={ "heard": "음악", "correct": True, "pron": "[으막]", "score": 98, "issues": [], "good": "Rõ ràng, nối âm tự nhiên." })
    run(pw, "C", C, course="en", word="accommodation", meaning="chỗ ở",
        answer={ "heard": "acomodation", "correct": False, "pron": "/əˌkɒməˈdeɪʃn/", "score": 35,
                 "issues": [{ "part": "accommodation", "type": "stress", "tip": "Trọng âm rơi vào 'DAY': /əˌkɒməˈdeɪʃn/." }], "good": "" })
    run(pw, "D", D, course="ko", word="음악", meaning="âm nhạc", answer={ "heard": "음악", "correct": True })

ok = sum(1 for r in results if r[1])
for n, c, i in results: print(("PASS " if c else "FAIL ") + n + ("" if c or not i else "  →  " + str(i)))
print(f"\n{ok}/{len(results)} passed  (screenshots: {SP})")
sys.exit(0 if ok == len(results) else 1)
