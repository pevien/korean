"""Speak → Reading coach with ✨ AI grading — end-to-end tests (see docs/speak.md).

Drives the real index.html in headless Chromium. Gemini and the microphone are faked, so it needs
no key, no mic and no network. Checks the strict prompt, that the AI's scores are shown as-is, and the issue list.

Run from the repo root (add scenario letters to run only those, e.g. `... coach_test.py B`):
    .venv/bin/python tests/coach_test.py

Screenshots land in $COACH_TEST_OUT (default: a temp folder). Exit code 1 when anything fails.
"""
import functools, http.server, json, os, sys, tempfile, threading, traceback
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SP = os.environ.get("COACH_TEST_OUT") or os.path.join(tempfile.gettempdir(), "coach-test")
os.makedirs(SP, exist_ok=True)
_srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT))
_srv.RequestHandlerClass.log_message = lambda *a: None
threading.Thread(target=_srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{_srv.server_address[1]}/index.html"

def init(course, sentence, meaning, answer, ui="vi"):
    st = { "cards": [], "passages": [{ "id": "p1", "lang": course, "title": "Test", "titleMean": "", "created": 1, "vocab": [], "sentences": [{ "ko": sentence, "meaning": meaning }] }],
           "settings": { "course": course, "apiKey": "FAKE", "uiLang": ui, "model": "gemini-2.5-flash-lite", "coachGrade": "ai" } }
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

def read(page, name):
    page.click('nav [data-v="read"]'); page.wait_for_timeout(300)
    page.click('#spHome .sp-pick[data-s="read"]'); page.wait_for_timeout(300)
    page.click('#passList li[data-id="p1"]'); page.wait_for_timeout(300)
    page.click("#sentList .sent .smic"); page.wait_for_timeout(400)
    page.click("#cRec"); page.wait_for_timeout(1500)
    page.click("#cRec")
    page.wait_for_selector("#cResult .scores", timeout=8000)
    page.wait_for_timeout(300)
    page.screenshot(path=f"{SP}/{name}.png", full_page=True)
    sc = page.eval_on_selector_all("#cResult .scores .stat b", "els => els.map(e => e.textContent.trim())")
    return sc, page.inner_text("#cResult"), page.evaluate("window.__prompts.find(p => p.includes('attached recording'))")

KO = "저는 음악을 좋아해요."
def issue(part, ty, tip): return { "part": part, "type": ty, "heard": "", "tip": tip }
ISSUES = [issue("음악을", "linking", "Chưa nối âm: đọc [으마글]."), issue("좋아해요", "sound", "ㅎ phải gần như mất: [조아해요]."),
          issue("악", "batchim", "ㄱ cuối không bật hơi."), issue("저는", "pace", "Ngập ngừng sau 저는."),
          issue("좋아해요", "intonation", "Cuối câu kể phải hạ giọng.")]

def A(page):
    """Korean, 5 issues: the AI's 4 scores shown unchanged; all issues listed; strict prompt."""
    sc, text, p = read(page, "A-ko")
    check("A: AI scores shown as-is", sc == ["72", "85", "88", "70"], sc)
    check("A: all 5 issues listed", page.eval_on_selector_all("#cResult .issue", "e => e.length") == 5)
    check("A: issue types in Vietnamese", all(t in text.lower() for t in ["nối âm", "patchim", "tốc độ", "ngữ điệu"]), text)
    check("A: issues numbered on the sentence", page.eval_on_selector_all("#cTarget sup", "e => e.length") >= 4)
    check("A: status no longer 'Excellent'", "Excellent" not in page.inner_text("#cStatus") and "Xuất sắc" not in page.inner_text("#cStatus"), page.inner_text("#cStatus"))
    check("A: best saved from the average", page.evaluate("JSON.parse(localStorage.getItem('hangulCards.v1')).passages[0].sentences[0].best") == 79)
    check("A: Korean prompt lists sound rules", "연음" in p and "비음화" in p and "batchim|sound-rule|linking" in p)
    check("A: strict prompt", "EVERY way" in p and "max 10" in p and "at most 90" in p and "they must match" in p and "encouraging" not in p)
    check("A: low temperature", page.evaluate("window.__temp") == 0.2)

def B(page):
    """Native-like, no issues: high scores kept."""
    sc, text, _ = read(page, "B-clean")
    check("B: scores kept", sc == ["98", "97", "96", "97"], sc)
    check("B: no issues", not page.query_selector("#cResult .issue"))

def C(page):
    """English: same strict prompt with the English checklist; 11 issues → only 10 kept; Gemini leaving a score out shows –, the rest unchanged."""
    sc, text, p = read(page, "C-en")
    check("C: English checklist", "word stress" in p and "linking between words" in p and "EVERY way" in p)
    check("C: max 10 issues", page.eval_on_selector_all("#cResult .issue", "e => e.length") == 10)
    check("C: missing score shows –", sc[2] == "–", sc)
    check("C: other scores shown as-is", sc[0] == "90" and sc[1] == "80" and sc[3] == "85", sc)

with sync_playwright() as pw:
    run(pw, "A", A, course="ko", sentence=KO, meaning="Tôi thích âm nhạc.",
        answer={ "heard": "저는 음악을 좋아해요", "pron": "[저는 으마글 조아해요]", "scores": { "accuracy": 72, "fluency": 85, "intonation": 88, "native": 70 }, "issues": ISSUES, "good": "Rõ ràng", "overall": "" })
    run(pw, "B", B, course="ko", sentence=KO, meaning="Tôi thích âm nhạc.",
        answer={ "heard": "저는 음악을 좋아해요", "pron": "[저는 으마글 조아해요]", "scores": { "accuracy": 98, "fluency": 97, "intonation": 96, "native": 97 }, "issues": [], "good": "Rất tự nhiên", "overall": "" })
    run(pw, "C", C, course="en", sentence="I would like a cup of coffee.", meaning="Tôi muốn một tách cà phê.",
        answer={ "heard": "I would like a cup of coffee", "pron": "/aɪ wəd ˈlaɪk ə ˈkʌp əv ˈkɒfi/", "scores": { "accuracy": 90, "fluency": 80, "native": 85 },
                 "issues": [issue("coffee", "sound", f"tip {i}") for i in range(11)], "good": "", "overall": "" })

ok = sum(1 for r in results if r[1])
for n, c, i in results: print(("PASS " if c else "FAIL ") + n + ("" if c or not i else "  →  " + str(i)))
print(f"\n{ok}/{len(results)} passed  (screenshots: {SP})")
sys.exit(0 if ok == len(results) else 1)
