"""Speak → Talk with AI — end-to-end tests (see docs/speak.md, "Talk with AI").

Drives the real index.html in headless Chromium. Gemini and the microphone are faked, so it needs
no key, no mic and no network. Checks the one-call turn (heard + grading + reply), the prompt's
"keep their mistakes" rules and history, the empty-heard retry, hints, the summary and the history list.

Run from the repo root (add scenario letters to run only those, e.g. `... talk_test.py B`):
    .venv/bin/python tests/talk_test.py

Screenshots land in $TALK_TEST_OUT (default: a temp folder). Exit code 1 when anything fails.
"""
import functools, http.server, json, os, sys, tempfile, threading, traceback
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SP = os.environ.get("TALK_TEST_OUT") or os.path.join(tempfile.gettempdir(), "talk-test")
os.makedirs(SP, exist_ok=True)
_srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT))
_srv.RequestHandlerClass.log_message = lambda *a: None
threading.Thread(target=_srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{_srv.server_address[1]}/index.html"

OPEN = { "ko": "Hi! What would you like to drink?", "mean": "Chào bạn! Bạn muốn uống gì?" }
GOOD = { "heard": "I want an iced latte please", "ok": True, "fix": "", "why": "", "mean": "Tôi muốn một ly latte đá.", "score": 82, "pron": "",
         "issues": [], "ko": "Sure! What size?", "koMean": "Được! Cỡ nào?" }
BAD = { "heard": "I want big size", "ok": False, "fix": "I'd like a large one, please.", "why": "Dùng 'a large one' thay cho 'big size'.",
        "mean": "Tôi muốn cỡ lớn.", "score": 64, "pron": "", "issues": [{ "part": "size", "tip": "Kéo dài âm 'ai' [saɪz]." }],
        "ko": "Large it is. For here or to go?", "koMean": "Cỡ lớn nhé. Uống ở đây hay mang đi?" }
SILENT = { "heard": "", "ok": False, "fix": "", "why": "", "mean": "", "score": 0, "pron": "", "issues": [], "ko": "", "koMean": "" }

def init(key="FAKE", talks=None):
    st = { "cards": [], "talks": talks or [],
           "settings": { "course": "en", "apiKey": key, "uiLang": "vi", "model": "gemini-2.5-flash-lite", "newPerDay": 0, "talkTts": False } }
    return r"""
if (!sessionStorage.getItem("seeded")) {
  sessionStorage.setItem("seeded", "1");
  localStorage.setItem("hangulCards.v1", %s);
  localStorage.setItem("hangulCards.welcomed", "1");
}
window.__calls = []; window.__turns = []; window.__open = %s;
const realFetch = window.fetch;
window.fetch = async (url, opts) => {
  if (String(url).includes("generativelanguage")) {
    if (String(url).includes("/models?")) return new Response(JSON.stringify({ models: [{ name: "models/gemini-2.5-flash-lite", supportedGenerationMethods: ["generateContent"] }] }));
    const body = JSON.parse(opts.body), parts = body.contents[body.contents.length - 1].parts, p = parts.map(x => x.text || "").join("\n");
    const kind = p.startsWith("Transcribe this") ? "hear" : p.includes("Start the conversation now") ? "open"
      : p.includes("learner's next turn") ? "turn" : p.includes("learner is stuck") ? "hint" : "other";
    window.__calls.push({ kind, p, audio: parts.filter(x => x.inline_data).map(x => x.inline_data.mime_type), cfg: body.generationConfig });
    await new Promise(r => setTimeout(r, 150));
    const out = kind === "open" ? window.__open : kind === "turn" ? (window.__turns.shift() || {})
      : kind === "hint" ? { ask: "Họ hỏi bạn muốn uống gì.", hints: [{ ko: "A latte, please.", mean: "Cho một ly latte." }, { ko: "Can I get a tea?", mean: "Cho tôi trà." }, { ko: "I'd like an iced americano.", mean: "Cho americano đá." }, { ko: "extra", mean: "x" }] }
      : {};
    return new Response(JSON.stringify({ candidates: [{ content: { parts: [{ text: JSON.stringify(out) }] } }] }));
  }
  return realFetch(url, opts);
};
navigator.mediaDevices.getUserMedia = async () => { const ac = new AudioContext(), o = ac.createOscillator(), d = ac.createMediaStreamDestination(); o.connect(d); o.start(); return d.stream; };
if (navigator.permissions) { const q = navigator.permissions.query.bind(navigator.permissions); navigator.permissions.query = d => d && d.name === "microphone" ? Promise.resolve({ state: "granted" }) : q(d); }
""" % (json.dumps(json.dumps(st)), json.dumps(OPEN))

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
        page.evaluate("speechSynthesis.speak = () => {}")
        page.click('nav [data-v="read"]'); page.wait_for_timeout(300)
        page.click('#spHome .sp-pick[data-s="talk"]'); page.wait_for_timeout(300)
        fn(page)
    except Exception:
        check(name + ": ran without exception", False, traceback.format_exc().splitlines()[-1])
        page.screenshot(path=f"{SP}/fail-{name}.png")
    check(name + ": no page errors", not errs, "; ".join(errs)[:300])
    b.close()

def calls(page, kind=None): return [c for c in page.evaluate("window.__calls") if not kind or c["kind"] == kind]
def ready(page): page.wait_for_function("document.querySelector('#tkRec') && !document.querySelector('#talk .tk-msg .spinner') && !document.querySelector('#tkRec').disabled", timeout=6000)
def start_cafe(page):
    page.click('#tkChips .chip[data-k="cafe"]'); page.click("#tkGo"); ready(page)
def say(page, answer, ms=1000):
    page.evaluate(f"window.__turns.push({json.dumps(answer)})")
    page.click("#tkRec"); page.wait_for_timeout(ms); page.click("#tkRec")
    page.wait_for_timeout(300); ready(page); page.wait_for_timeout(200)
def mine(page): return page.query_selector_all("#tkList .tk-msg.me")
def saved(page): return page.evaluate("() => JSON.parse(localStorage.getItem('hangulCards.v1'))")

def A(page):
    """No key: a card points to Settings, nothing to start."""
    check("A: key card shown", page.is_visible("#tkKey") and "Gemini key" in page.inner_text("#talk"), page.inner_text("#talk")[:200])
    check("A: no start button", not page.query_selector("#tkGo"))
    page.click("#tkKey"); page.wait_for_timeout(400)
    check("A: the key button opens Settings", page.is_visible("#setKey"))

def B(page):
    """A scene: opening line in character; a correct turn (✅) then a wrong one (✏️ fix + reason); each turn is ONE call with the audio, the history and the keep-mistakes rules."""
    start_cafe(page)
    op = calls(page, "open")
    check("B: opening asked once, in the café role", len(op) == 1 and "barista" in op[0]["p"], op and op[0]["p"][:200])
    check("B: opening line shown with its meaning", OPEN["ko"] in page.inner_text("#tkList") and OPEN["mean"] in page.inner_text("#tkList"))
    check("B: tab bar hidden while chatting", page.evaluate("document.body.classList.contains('talking')"))
    say(page, GOOD)
    t = calls(page, "turn")
    check("B: one AI call per turn, no blind transcription first", len(t) == 1 and not calls(page, "hear"), [c["kind"] for c in calls(page)])
    check("B: the recording is attached as WAV", t and t[0]["audio"] == ["audio/wav"], t and t[0]["audio"])
    p = t[0]["p"] if t else ""
    check("B: prompt keeps the learner's mistakes", "Keep their grammar mistakes" in p and "never add, complete or \"fix\" words" in p, p[-1500:])
    check("B: prompt doesn't let it borrow words from its own lines", "never borrow words from the question or your own earlier messages" in p)
    check("B: prompt says silence → empty heard", '"heard":""' in p)
    check("B: the conversation so far is in the prompt", f"YOU: {OPEN['ko']}" in p)
    check("B: light thinking for grading", (t[0]["cfg"] or {}).get("thinkingConfig") not in (None, {}), t and t[0]["cfg"])
    m = mine(page)
    check("B: what was heard shown", m and GOOD["heard"] in m[-1].inner_text())
    check("B: correct → ✅", m and m[-1].query_selector(".ok") and not m[-1].query_selector(".fix"))
    check("B: AI reply added", GOOD["ko"] in page.inner_text("#tkList"))
    say(page, BAD)
    p2 = calls(page, "turn")[-1]["p"]
    check("B: second turn sees the first answer and reply", f"LEARNER: {GOOD['heard']}" in p2 and f"YOU: {GOOD['ko']}" in p2, p2[:600])
    m = mine(page)
    txt = m[-1].inner_text() if m else ""
    check("B: wrong → ✏️ corrected sentence + reason", m and m[-1].query_selector(".fix") and BAD["fix"] in txt and BAD["why"] in txt, txt)
    check("B: pronunciation score on the turn", "64" in txt, txt)
    page.click("#tkList .tk-msg.me:last-of-type [data-a=more]") if page.query_selector("#tkList .tk-msg.me:last-of-type [data-a=more]") else m[-1].query_selector("[data-a=more]").click()
    page.wait_for_timeout(200)
    det = mine(page)[-1].inner_text()
    check("B: expanding shows the issue + My recording / Model", BAD["issues"][0]["tip"] in det and mine(page)[-1].query_selector("[data-a=mine]") and mine(page)[-1].query_selector("[data-a=sayme]"), det)
    page.screenshot(path=f"{SP}/B-chat.png", full_page=True)

def C(page):
    """Nothing heard: 'Không nghe rõ', the turn is dropped, no reply; a too-short tap isn't sent at all."""
    start_cafe(page)
    say(page, SILENT)
    check("C: empty heard → asked to try again", "Không nghe rõ" in page.inner_text("#tkStatus"), page.inner_text("#tkStatus"))
    check("C: no turn left in the chat", not mine(page))
    check("C: nothing saved as said", not [x for x in saved(page)["talk"]["turns"] if x["who"] == "me"])
    n = len(calls(page, "turn"))
    page.click("#tkRec"); page.wait_for_timeout(200); page.click("#tkRec"); page.wait_for_timeout(500)
    check("C: under 0.6 s → 'too short', not sent", len(calls(page, "turn")) == n and "Ngắn quá" in page.inner_text("#tkStatus"), page.inner_text("#tkStatus"))

def D(page):
    """💡 hint: what was asked + 3 answers (no more), tap to hear; closing it clears them."""
    start_cafe(page)
    page.click("#tkHint"); page.wait_for_selector("#talk .tk-hint", timeout=5000)
    check("D: 3 suggested answers", len(page.query_selector_all("#talk .tk-hint")) == 3)
    check("D: explains what was asked", "Họ hỏi bạn muốn uống gì." in page.inner_text("#talk"))
    page.click("#tkHintX"); page.wait_for_timeout(200)
    check("D: closed", not page.query_selector("#talk .tk-hint"))

def E(page):
    """Finish: summary counts, the correction, pronunciation note; saved to history; Keep talking reopens it; history shows it."""
    start_cafe(page)
    say(page, GOOD); say(page, BAD)
    page.click("#tkEnd"); page.wait_for_timeout(400)
    st = page.eval_on_selector_all("#talk .stats .stat b", "e => e.map(x => x.textContent.trim())")
    check("E: 2 turns, 1 correct, average 73", st == ["2", "1", "73"], st)
    txt = page.inner_text("#talk")
    check("E: the correction listed wrong → right", BAD["heard"] in txt and BAD["fix"] in txt, txt[:400])
    check("E: pronunciation note listed", BAD["issues"][0]["tip"] in txt)
    s = saved(page)
    check("E: archived in history", len(s["talks"]) == 1 and len([x for x in s["talks"][0]["turns"] if x["who"] == "me"]) == 2, s.get("talks"))
    page.screenshot(path=f"{SP}/E-summary.png", full_page=True)
    page.click("#tkMore"); ready(page)
    check("E: keep talking → back in the chat", len(mine(page)) == 2)
    page.click("#tkEnd"); page.wait_for_timeout(300)
    check("E: finishing again updates the same entry", len(saved(page)["talks"]) == 1)
    page.click("#tkNew"); page.wait_for_timeout(300)
    page.click("#tkHistOpen"); page.wait_for_timeout(300)
    check("E: history list has it", len(page.query_selector_all("#tkHist li[data-id]")) == 1)

def F(page):
    """Finish without speaking: discarded, nothing in history."""
    start_cafe(page)
    page.click("#tkEnd"); page.wait_for_timeout(300)
    s = saved(page)
    check("F: no history entry", not s.get("talks"), s.get("talks"))
    check("F: back to the topics", page.is_visible("#tkGo"))

def G(page):
    """History keeps only the latest 60 conversations."""
    start_cafe(page)
    say(page, GOOD)
    page.click("#tkEnd"); page.wait_for_timeout(300)
    s = saved(page)
    check("G: capped at 60, the newest kept", len(s["talks"]) == 60 and any(x["id"] == s["talk"]["id"] for x in s["talks"]) and not any(x["id"] == "old0" for x in s["talks"]),
          (len(s["talks"]), sorted(x["id"] for x in s["talks"])[:3]))

def H(page):
    """Own topic: the prompt asks the AI to pick a fitting role for exactly that topic."""
    page.fill("#tkTopic", "Returning a broken phone"); page.click("#tkGo"); ready(page)
    p = calls(page, "open")[0]["p"]
    check("H: custom topic in the prompt", 'situation chosen by the learner: "Returning a broken phone"' in p, p[:300])

def I(page):
    """ok:false without a usable correction: the same sentence back or nothing → counts as correct; a reason only → wrong, shown without an empty correction."""
    start_cafe(page)
    same = dict(GOOD, heard="I want a latte", ok=False, fix="I want a latte", why="", ko="OK!")
    reason = dict(GOOD, heard="I want latte", ok=False, fix="", why="Thiếu mạo từ 'a'.", ko="Sure!")
    bare = dict(GOOD, heard="Thank you", ok=False, fix="", why="", ko="You're welcome!")
    for a in (same, reason, bare): say(page, a)
    m = mine(page)
    check("I: same sentence back → ✅", m and m[0].query_selector(".ok") and not m[0].query_selector(".fix"), m and m[0].inner_html()[:200])
    t = m[1].inner_text() if len(m) > 1 else ""
    check("I: reason only → marked to fix, with the reason, no empty sentence or play button", len(m) > 1 and m[1].query_selector(".fix") and not m[1].query_selector("[data-a=sayfix]")
          and "Chưa tự nhiên" in t and reason["why"] in t, t)
    check("I: nothing at all → ✅", len(m) > 2 and m[2].query_selector(".ok"), m and m[-1].inner_html()[:200])
    page.click("#tkEnd"); page.wait_for_timeout(400)
    st = page.eval_on_selector_all("#talk .stats .stat b", "e => e.map(x => x.textContent.trim())")
    check("I: summary counts the same way: 3 turns, 2 correct", st[:2] == ["3", "2"], st)
    sums = page.eval_on_selector_all("#talk .tk-sum", "e => e.map(x => x.innerText)")
    check("I: the one correction listed, without an empty '→'", len([x for x in sums if reason["heard"] in x]) == 1 and not any("→" in x for x in sums if reason["heard"] in x), sums)
    page.click("#tkAll summary"); page.wait_for_timeout(200)
    tr = page.query_selector_all("#tkAll .tk-msg.me")
    check("I: the whole-conversation view agrees", len(tr) == 3 and tr[0].query_selector(".ok") and tr[1].query_selector(".fix") and tr[2].query_selector(".ok"), len(tr))

OLD = [{ "id": f"old{i}", "lang": "en", "created": 1000 + i, "scene": "cafe", "topic": "",
         "turns": [{ "who": "ai", "ko": "Hi", "mean": "" }, { "who": "me", "heard": "Hi", "ok": True, "fix": "", "why": "", "mean": "", "score": 70, "pron": "", "issues": [] }] } for i in range(60)]

if __name__ == "__main__":
    with sync_playwright() as pw:
        run(pw, "A", A, key="")
        run(pw, "B", B)
        run(pw, "C", C)
        run(pw, "D", D)
        run(pw, "E", E)
        run(pw, "F", F)
        run(pw, "G", G, talks=OLD)
        run(pw, "H", H)
        run(pw, "I", I)
    fails = [r for r in results if not r[1]]
    for n, ok, info in results:
        print(("PASS " if ok else "FAIL ") + n + ("" if ok else f"  ← {info}"))
    print(f"\n{len(results) - len(fails)}/{len(results)} passed  (screenshots: {SP})")
    sys.exit(1 if fails else 0)
