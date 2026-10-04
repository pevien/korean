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

def init(course, word, meaning, answer, ui="vi", mode="ko2say"):
    st = { "cards": [{ "id": "c1", "lang": course, "ko": word, "meaning": meaning, "ex": f"Example with {word}.", "exMean": "Câu ví dụ.", "ease": 2.5, "interval": 1,
                       "reps": 1, "lapses": 0, "due": 1, "last": 1, "created": 1 }],
           "settings": { "course": course, "apiKey": "FAKE", "uiLang": ui, "model": "gemini-2.5-flash-lite", "newPerDay": 0,
                         "coachGrade": "ai", "speakAuto": True, "autoPlay": False, "modes": { **MODES, "ko2say": False, mode: True } } }
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
    const ans = %s, n = window.__prompts.filter(x => x.includes("attached recording")).length - 1;
    const out = p.includes("attached recording") ? (Array.isArray(ans) ? ans[Math.min(n, ans.length - 1)] : ans) : { t: [] };
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

def record(page, btn):
    page.click(btn); page.wait_for_timeout(1200)
    page.click(btn)

def say(page, name):
    if page.query_selector("#startBtn"): page.click("#startBtn")
    page.wait_for_selector("#sayRec")
    record(page, "#sayRec")
    page.wait_for_selector("#fb .qfb", timeout=8000)
    page.screenshot(path=f"{SP}/{name}.png")
    return page.inner_text("#fb .qfb"), page.evaluate("window.__prompts.find(p => p.includes('attached recording'))")

ISSUES = [{ "part": "음", "type": "linking", "heard": "음.악", "tip": "Chưa nối âm: ㅁ phải chuyển sang âm sau, đọc [으막]." },
          { "part": "악", "type": "batchim", "tip": "ㄱ cuối bị bật hơi, giữ lưỡi lại không bật [으막]." },
          { "part": "", "type": "pace", "tip": "Đọc tách từng âm tiết, hơi chậm." }]

def A(page):
    """Korean, right word with 3 issues: the AI's score is shown unchanged; every issue listed with its type; strict prompt."""
    text, p = say(page, "A-ko")
    check("A: score on the title line", page.inner_text("#fb .fb-t > span") == "👍 Khá tốt · 78/100", page.inner_text("#fb .fb-t > span"))
    check("A: 78 → title 'Khá tốt', green", text.startswith("👍 Khá tốt") and page.query_selector("#fb .qfb.ok"), text[:80])
    check("A: AI score shown as-is", "78/100" in text, text[:120])
    check("A: standard pronunciation next to the word on top", "[으막]" in page.inner_text("#qBox .ko-mean") and "[으막]" not in page.inner_text("#fb .fb-t"), page.inner_text("#qBox .ko-mean"))
    check("A: issue shows how it sounded", "음 → bạn đọc 음.악" in text, text)
    check("A: prompt asks how each part sounded", '"heard" = how that part actually sounded' in p)
    check("A: all 3 issues listed", page.eval_on_selector_all("#fb .say-iss .issue", "e => e.length") == 3)
    check("A: issue types labelled in Vietnamese", all(t in text.lower() for t in ["nối âm", "patchim", "tốc độ"]), text)
    check("A: prompt checks linking & sound rules", "연음" in p and "비음화" in p and "EVERY way" in p)
    check("A: prompt has deduction rubric", "Start at 100" in p and "at most 90" in p and "must match them" in p)
    check("A: low temperature", page.evaluate("window.__temp") == 0.2)
    check("A: example sentence still shown", "Example with 음악." in text, text)
    check("A: Say again button", page.is_visible("#sayAgain"))

def B(page):
    """No issues: a native-like 98 is kept and the 'good' line shows instead of a list."""
    text, _ = say(page, "B-clean")
    check("B: score kept", "98/100" in text, text[:120])
    check("B: 98 → 'Chính xác!'", text.startswith("✅ Chính xác!"), text[:40])
    check("B: no issue list", not page.query_selector("#fb .say-iss"))
    check("B: good line", "Rõ ràng" in text)

def C(page):
    """English, wrong word: what was heard sits on the score line, the issues right after; English prompt uses COACH lists."""
    text, p = say(page, "C-en")
    check("C: verdict wrong", "❌" in text, text[:80])
    lines = [l.strip() for l in text.splitlines() if l.strip() and l.strip() != "Nghe lại"]
    i_score = next((i for i, l in enumerate(lines) if "/100" in l), -1)
    check("C: heard on its own line right under the score", i_score >= 0 and "acomodation" not in lines[i_score] and "acomodation" in lines[i_score + 1], lines)
    check("C: issues right after that", i_score >= 0 and lines[i_score + 2] == "1", lines)
    check("C: score from AI kept", "35/100" in text)
    check("C: standard pronunciation not on the score line", "/əˌkɒməˈdeɪʃn/" not in lines[i_score] and "/əˌkɒməˈdeɪʃn/" in page.inner_text("#qBox .ko-mean"), lines)
    check("C: issue listed", page.eval_on_selector_all("#fb .say-iss .issue", "e => e.length") == 1)
    check("C: prompt uses English stress / linking checks", "word stress" in p and "linking between words" in p)

def E(page):
    """Say it from the meaning, wrong word: the standard pronunciation sits after the right word, not after what was heard."""
    text, _ = say(page, "E-m2say")
    lines = [l.strip() for l in text.splitlines() if l.strip() and l.strip() != "Nghe lại"]
    score = next((l for l in lines if "/100" in l), "")
    ans = page.inner_text("#fb .fb-ans")
    i = lines.index(score) if score in lines else -1
    check("E: score line alone, then heard, then the right word", "get on" not in score and "/bɔːrd/" not in score and "get on" in lines[i + 1] and lines[i + 2].startswith("Từ đúng"), lines)
    check("E: pronunciation right after the word", "board /bɔːrd/" in ans, ans)

def F(page):
    """Say it again (from the meaning, first try wrong): AI grades again as reading the right word aloud; the new score + issues
    replace the old ones with "last time"; the verdict, right word, example and Continue stay from the first try."""
    text, _ = say(page, "F-1")
    record(page, "#sayAgain")
    page.wait_for_function("document.querySelector('#fb .fb-t').innerText.includes('lần trước')", timeout=8000)
    page.screenshot(path=f"{SP}/F-2.png")
    text2 = page.inner_text("#fb .qfb")
    p2 = page.evaluate("window.__prompts.filter(p => p.includes('attached recording'))[1]")
    check("F: graded twice", page.evaluate("window.__prompts.filter(p => p.includes('attached recording')).length") == 2)
    check("F: second prompt = read the word aloud", 'shown the English word "board" and asked to read it aloud' in p2, p2[:300])
    check("F: new score with last time", "85/100 · lần trước 20" in text2, text2)
    check("F: no 'heard' when the retry was right", not page.query_selector("#fb .fb-heard"), text2)
    check("F: new issues replace the old", "Âm /ɔː/" in text2 and "Nói nhầm" not in text2, text2)
    check("F: retry right word at 85 → 'Khá tốt'", text2.startswith("👍 Khá tốt"), text2[:40])
    check("F: right word line kept", "board /bɔːrd/" in page.inner_text("#fb .fb-ans"))
    check("F: example kept", "Example with board." in text2)
    check("F: Continue still there", page.is_visible("#contBtn"))

def G(page):
    """Right word but 60: under 70 counts as not known — 'Chưa đúng', I was right / Continue; practicing again to 92 → title 'Chính xác!', buttons stay."""
    text, _ = say(page, "G-1")
    check("G: 60 → 'Chưa đúng', red", text.startswith("❌ Chưa đúng") and page.query_selector("#fb .qfb.bad"), text[:60])
    marks = page.eval_on_selector_all("#fb .fb-heard .wrong", "els => els.map(e => e.tagName + ':' + e.textContent)")
    check("G: issue parts highlighted + numbered in what was heard", marks == ["B:음", "SUP:1", "B:악", "SUP:2"], marks)
    check("G: miss buttons (no Hard/Good/Easy)", page.query_selector("#fb .grades") is None and page.is_visible("#contBtn") and page.is_visible("#typoBtn"))
    record(page, "#sayAgain")
    page.wait_for_function("document.querySelector('#fb .fb-t').innerText.includes('lần trước')", timeout=8000)
    page.screenshot(path=f"{SP}/G-2.png")
    text2 = page.inner_text("#fb .qfb")
    check("G: retry 92 → 'Chính xác!', green", text2.startswith("✅ Chính xác!") and page.query_selector("#fb .qfb.ok"), text2[:60])
    check("G: miss buttons kept (first try counts)", page.query_selector("#fb .grades") is None and page.is_visible("#contBtn"))
    check("G: retry score with last time", "92/100 · lần trước 60" in text2, text2)

def H(page):
    """Right at 75 ('Khá tốt', counts as known); practicing again at 55 → title 'Chưa đúng' but the grade buttons stay."""
    text, _ = say(page, "H-1")
    check("H: 75 → 'Khá tốt' + grades", text.startswith("👍 Khá tốt") and page.query_selector("#fb .grades") is not None, text[:40])
    record(page, "#sayAgain")
    page.wait_for_function("document.querySelector('#fb .fb-t').innerText.includes('lần trước')", timeout=8000)
    text2 = page.inner_text("#fb .qfb")
    check("H: retry 55 → 'Chưa đúng', red, grades kept", text2.startswith("❌ Chưa đúng") and page.query_selector("#fb .qfb.bad") and page.query_selector("#fb .grades"), text2[:40])

def I(page):
    """English UI, a miss: the title reads 'Incorrect' with the score on the same line."""
    say(page, "I-en-ui")
    t = page.inner_text("#fb .fb-t > span")
    check("I: '❌ Incorrect · 20/100'", t == "❌ Incorrect · 20/100", t)

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
    run(pw, "E", E, course="en", word="board", meaning="lên tàu xe máy bay", mode="m2say",
        answer={ "heard": "get on", "correct": False, "pron": "/bɔːrd/", "score": 20, "issues": [{ "part": "get on", "type": "missing", "tip": "Nói nhầm thành 'get on'." }], "good": "" })
    run(pw, "F", F, course="en", word="board", meaning="lên tàu xe máy bay", mode="m2say",
        answer=[{ "heard": "get on", "correct": False, "pron": "/bɔːrd/", "score": 20, "issues": [{ "part": "get on", "type": "missing", "tip": "Nói nhầm thành 'get on'." }], "good": "" },
                { "heard": "board", "correct": True, "pron": "/bɔːrd/", "score": 85, "issues": [{ "part": "board", "type": "sound", "tip": "Âm /ɔː/ cần tròn môi hơn." }], "good": "" }])
    run(pw, "G", G, course="ko", word="음악", meaning="âm nhạc",
        answer=[{ "heard": "음악", "correct": True, "pron": "[으막]", "score": 60, "issues": ISSUES[:2], "good": "" },
                { "heard": "음악", "correct": True, "pron": "[으막]", "score": 92, "issues": [], "good": "Tốt hơn nhiều." }])
    run(pw, "H", H, course="ko", word="음악", meaning="âm nhạc",
        answer=[{ "heard": "음악", "correct": True, "pron": "[으막]", "score": 75, "issues": ISSUES[:1], "good": "" },
                { "heard": "음악", "correct": True, "pron": "[으막]", "score": 55, "issues": ISSUES, "good": "" }])
    run(pw, "I", I, course="en", word="board", meaning="lên tàu xe máy bay", mode="m2say", ui="en",
        answer={ "heard": "get on", "correct": False, "pron": "/bɔːrd/", "score": 20, "issues": [], "good": "" })
    run(pw, "D", D, course="ko", word="음악", meaning="âm nhạc", answer={ "heard": "음악", "correct": True })

ok = sum(1 for r in results if r[1])
for n, c, i in results: print(("PASS " if c else "FAIL ") + n + ("" if c or not i else "  →  " + str(i)))
print(f"\n{ok}/{len(results)} passed  (screenshots: {SP})")
sys.exit(0 if ok == len(results) else 1)
