"""Every feature that records — switching between them must leave no mic open — end-to-end tests.

Recording features: Vocab speaking question (FR), Reading coach (C), Talk with AI (TK), IELTS mock test (IE),
AI tutor (TU), Translate interpreter (AR talk), ARMY live listening (AR bts).

Drives the real index.html in headless Chromium. Gemini and the microphone are faked, so it needs no key,
no mic and no network. Every getUserMedia stream, MediaRecorder and AudioContext is tracked, so after each step
the test can check that nothing is still listening.

Run from the repo root (add scenario letters to run only those, e.g. `... mic_switch_test.py A B`):
    .venv/bin/python tests/mic_switch_test.py

Screenshots of failures land in $MIC_TEST_OUT (default: a temp folder). Exit code 1 when anything fails.
"""
import functools, http.server, json, os, sys, tempfile, threading, traceback
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SP = os.environ.get("MIC_TEST_OUT") or os.path.join(tempfile.gettempdir(), "mic-test")
os.makedirs(SP, exist_ok=True)
_srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT))
_srv.RequestHandlerClass.log_message = lambda *a: None
threading.Thread(target=_srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{_srv.server_address[1]}/index.html"

MODES = { m: False for m in ["ko2m", "listen2m", "listen2kc", "m2ko", "listen2ko", "m2say"] }

def init():
    st = { "cards": [{ "id": "c1", "lang": "en", "ko": "apple", "meaning": "quả táo", "ex": "I eat an apple.", "exMean": "Tôi ăn táo.", "ease": 2.5, "interval": 1,
                       "reps": 1, "lapses": 0, "due": 1, "last": 1, "created": 1 }],
           "passages": [{ "id": "p1", "lang": "en", "title": "Test", "titleMean": "", "created": 1, "vocab": [], "sentences": [{ "ko": "I like apples.", "meaning": "Tôi thích táo." }] }],
           "settings": { "course": "en", "apiKey": "FAKE", "uiLang": "vi", "model": "gemini-2.5-flash-lite", "newPerDay": 0, "coachGrade": "ai",
                         "speakAuto": True, "autoPlay": False, "talkTts": False, "armyEngine": "ai", "modes": { **MODES, "ko2say": True } } }
    return r"""
if (!sessionStorage.getItem("seeded")) {
  sessionStorage.setItem("seeded", "1");
  localStorage.setItem("hangulCards.v1", %s);
  localStorage.setItem("hangulCards.welcomed", "1");
}
/* ---- tracking: every mic stream, recorder, audio context and speech recogniser the app opens ---- */
const RealAC = window.AudioContext, RealMR = window.MediaRecorder;
window.__streams = []; window.__recs = []; window.__acs = []; window.__srs = []; window.__gum = 0;
navigator.mediaDevices.getUserMedia = async () => {
  window.__gum++;
  const ac = new RealAC(), o = ac.createOscillator(), d = ac.createMediaStreamDestination(); o.connect(d); o.start();
  d.stream.__ac = ac; window.__streams.push(d.stream); return d.stream;
};
window.MediaRecorder = class extends RealMR { constructor(...a){ super(...a); window.__recs.push(this); } };
window.AudioContext = window.webkitAudioContext = class extends RealAC { constructor(...a){ super(...a); window.__acs.push(this); } };
class FakeSR { constructor(){ this.on = false; window.__srs.push(this); } start(){ this.on = true; } stop(){ this.on = false; setTimeout(() => this.onend && this.onend(), 10); } abort(){ this.on = false; } }
window.SpeechRecognition = window.webkitSpeechRecognition = FakeSR;
window.__state = () => ({
  live: window.__streams.flatMap(s => s.getTracks()).filter(t => t.readyState === "live").length,
  recs: window.__recs.filter(r => r.state !== "inactive").length,
  acs: window.__acs.filter(a => a.state !== "closed").length,   // includes the app's one reusable TTS-wake context
  srs: window.__srs.filter(r => r.on).length,
  gum: window.__gum,
});
if (navigator.permissions) { const q = navigator.permissions.query.bind(navigator.permissions); navigator.permissions.query = d => d && d.name === "microphone" ? Promise.resolve({ state: "granted" }) : q(d); }
window.__kinds = [];
const realFetch = window.fetch;
window.fetch = async (url, opts) => {
  if (String(url).includes("generativelanguage")) {
    if (String(url).includes("/models?")) return new Response(JSON.stringify({ models: [{ name: "models/gemini-2.5-flash-lite", supportedGenerationMethods: ["generateContent"] }] }));
    const body = JSON.parse(opts.body), parts = body.contents[body.contents.length - 1].parts, p = body.contents[0].parts[0].text || "";
    const kind = p.startsWith("Transcribe this") ? "hear" : p.includes("preparing a realistic") ? "ieGen" : p.includes("strict IELTS") ? "ieBand"
      : p.includes("live interpreter") ? "ar" : p.includes("role-playing") ? "talk" : p.includes("attached recording") ? "grade"
      : body.generationConfig && body.generationConfig.responseMimeType === "text/plain" ? "tutor" : "other";
    window.__kinds.push(kind);
    await new Promise(r => setTimeout(r, 150));
    let out;
    if (kind === "ieGen") out = { p1: [{ topic: "Work", q: "Do you work or are you a student?" }, { topic: "Music", q: "What music do you like?" }, { topic: "Music", q: "Do you sing?" }],
      card: { topic: "Describe a place you visited.", points: ["where", "when", "what"], end: "and explain why." }, follow: "Do you travel?", p3: ["Why travel?", "How has tourism changed?"] };
    else if (kind === "ieBand") out = { fc: { band: 6, note: "" }, lr: { band: 6, note: "" }, gra: { band: 6, note: "" }, p: { band: 6, note: "" }, strengths: [], next: [] };
    else if (kind === "ar") out = { lines: [{ src: "hello", tr: "xin chào" }] };
    else out = { heard: "I like apples", score: 80, note: "Tốt.", fixes: [], upgrades: [], issues: [], checks: [], ideas: [], sample: "I like apples.",
      ko: "Hello! How are you?", mean: "Xin chào! Bạn khoẻ không?", reply: "Nice!", fix: "", ok: true, t: [] };
    const txt = kind === "tutor" ? "HEARD: \"hello\"\nXin chào!" : JSON.stringify(out);
    if (String(url).includes("alt=sse")) {
      const enc = new TextEncoder();
      return new Response(new ReadableStream({ start(c){ c.enqueue(enc.encode("data: " + JSON.stringify({ candidates: [{ content: { parts: [{ text: txt }] } }] }) + "\r\n\r\n")); c.close(); } }),
        { headers: { "content-type": "text/event-stream" } });
    }
    return new Response(JSON.stringify({ candidates: [{ content: { parts: [{ text: txt }] } }] }));
  }
  return realFetch(url, opts);
};
""" % json.dumps(json.dumps(st))

results = []
def check(name, cond, info=""): results.append((name, bool(cond), info))
ONLY = {x.upper() for x in sys.argv[1:]}

def run(pw, name, fn):
    b = pw.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
    page = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.add_init_script(init())
    try:
        page.goto(URL); page.wait_for_timeout(1000)
        page.evaluate("speechSynthesis.speak = () => {}")
        fn(page)
    except Exception:
        check(name + ": ran without exception", False, " | ".join(l.strip() for l in traceback.format_exc().strip().splitlines() if "Error" in l or "waiting for" in l or "intercept" in l)[:500])
        page.screenshot(path=f"{SP}/fail-{name}.png")
    check(name + ": no page errors", not errs, "; ".join(errs)[:300])
    b.close()

def state(page): return page.evaluate("window.__state()")
def on(page, sel): return "on" in (page.get_attribute(sel, "class") or "")

# ---- one helper per feature: open it, ready to record ----
def open_fr(page):
    page.click('nav [data-v="study"]'); page.wait_for_timeout(300)
    if page.query_selector("#startBtn") and page.is_visible("#startBtn"): page.click("#startBtn")
    page.wait_for_selector("#sayRec, #sayAgain", timeout=5000); page.wait_for_timeout(200)
    return "#sayAgain" if page.query_selector("#sayAgain") else "#sayRec"
def open_c(page):
    page.click('nav [data-v="read"]'); page.wait_for_timeout(300)
    page.click('#spHome .sp-pick[data-s="read"]'); page.wait_for_timeout(300)
    page.click('#passList li[data-id="p1"]'); page.wait_for_timeout(300)
    page.click("#sentList .sent .smic"); page.wait_for_timeout(300)
    return "#cRec"
def open_tk(page):
    page.click('nav [data-v="read"]'); page.wait_for_timeout(300)
    page.click('#spHome .sp-pick[data-s="talk"]'); page.wait_for_timeout(300)
    if page.query_selector("#tkResume"): page.click("#tkResume")
    else: page.click("#tkChips .chip"); page.click("#tkGo")
    page.wait_for_function("document.querySelector('#tkRec') && !document.querySelector('#talk .tk-msg .spinner') && !document.querySelector('#tkRec').disabled", timeout=6000)
    page.wait_for_timeout(200)
    return "#tkRec"
def open_ie(page):
    page.click('nav [data-v="read"]'); page.wait_for_timeout(300)
    page.click('#spHome .sp-pick[data-s="ielts"]'); page.wait_for_timeout(300)
    if page.query_selector('#ielts .sp-pick[data-m="p1"]'): page.click('#ielts .sp-pick[data-m="p1"]')
    elif page.query_selector('#ielts .sp-pick[data-m="full"]'): page.click('#ielts .sp-pick[data-m="full"]')
    else: page.locator("#ielts .sp-pick").first.click()   # "in progress": resume
    page.wait_for_selector("#ieRec", timeout=6000); page.wait_for_timeout(200)
    return "#ieRec"
def open_tu(page):
    if not page.is_visible("#tu"): page.click("#tuFab")
    page.wait_for_timeout(200)
    return "#tuMic"
def open_tr(page):
    page.click('nav [data-v="tr"]'); page.wait_for_timeout(400)
    return "#arConv .ar-pane.me .ar-mic"
def open_ar(page):
    page.click('nav [data-v="army"]'); page.wait_for_timeout(300)
    page.click('#v-army .ar-pick[data-m="bts"]'); page.wait_for_timeout(300)
    return "#arGo"
def close_overlays(page):   # the tutor and Translate sit over a tab, Talk / IELTS / a study round hide the tab bar: leave them like a user would
    if page.is_visible("#tu"): page.click("#tuClose"); page.wait_for_timeout(200)
    if page.evaluate("document.body.classList.contains('ar-conv-on')"): page.click('nav [data-v="set"]'); page.wait_for_timeout(300)
    for _ in range(3):
        if not page.evaluate("document.body.classList.contains('talking')"): break
        page.click("#tkBack:visible, #ieBack:visible"); page.wait_for_timeout(300)
    for _ in range(2):   # a round started from Study has an End button (one opened by itself keeps the tab bar)
        if page.evaluate("document.body.classList.contains('in-session')") and page.is_visible("#endBtn"): page.click("#endBtn"); page.wait_for_timeout(300)

FEAT = { "FR": open_fr, "C": open_c, "TK": open_tk, "IE": open_ie, "TU": open_tu, "TR": open_tr, "AR": open_ar }

def record(page, f, ms=1500):
    """record ~ms with feature f, stop, wait until the answer is handled; returns the button selector"""
    sel = FEAT[f](page)
    k0 = page.evaluate("window.__kinds.length")
    page.click(sel); page.wait_for_timeout(ms)
    s = state(page)
    check(f"{f}: recording is live", s["live"] >= 1 and s["recs"] >= 1, str(s))
    page.click(sel); page.wait_for_timeout(1800)
    k = page.evaluate(f"window.__kinds.slice({k0})")
    check(f"{f}: the recording reached the AI ({'/'.join(SENT[f])})", any(x in SENT[f] for x in k), str(k))
    return sel

def idle(page, label, extra_ac=0):
    s = state(page)
    check(f"{label}: mic released (no live track, no recorder, no recogniser)", s["live"] == 0 and s["recs"] == 0 and s["srs"] == 0, str(s))
    check(f"{label}: no audio context left open", s["acs"] <= 1 + extra_ac, str(s))   # 1 = the TTS wake context, kept on purpose

SENT = { "FR": ["hear", "grade"], "C": ["hear", "grade"], "TK": ["talk", "hear", "grade"], "IE": ["hear", "grade"], "TU": ["tutor"], "TR": ["ar"], "AR": ["ar"] }
ORDER = ["FR", "C", "TK", "IE", "TU", "TR", "AR"]

# A. each feature alone: record → stop → nothing left open
def t_alone(page):
    for f in ORDER:
        record(page, f); close_overlays(page)
        idle(page, f"A {f} after stop")

# B. finish recording in one feature, then record in every other one (all ordered pairs, a fresh page per first feature)
def make_pairs(first):
    def t(page):
        record(page, first); close_overlays(page)
        for f in ORDER:
            if f == first: continue
            g0 = state(page)["gum"]
            record(page, f); close_overlays(page)
            s = state(page)
            check(f"B {first}→{f}: second feature opened its own mic once", s["gum"] - g0 == 1, f"{s['gum'] - g0} opens")
            idle(page, f"B {first}→{f}")
    return t

# C. leave a feature by the tab bar while it is still recording → its mic is closed
def t_leave(page):
    for f in ["FR", "C", "TK", "IE", "AR"]:
        sel = FEAT[f](page); page.click(sel); page.wait_for_timeout(1200)
        check(f"C {f}: recording before leaving", state(page)["live"] >= 1)
        close_overlays(page)
        if page.evaluate("document.body.classList.contains('ar-listening')"): page.click("#arGo"); page.wait_for_timeout(1500)   # ARMY live hides the tab bar and ←: Stop is the way out
        if page.is_visible('nav [data-v="set"]'): page.click('nav [data-v="set"]'); page.wait_for_timeout(500)
        idle(page, f"C {f} left mid-recording")

# D. overlays over a feature that is recording: does the first mic keep going?
def t_overlay(page):
    for f in ["FR", "C", "AR"]:
        sel = FEAT[f](page); page.click(sel); page.wait_for_timeout(1000)
        if not page.is_visible('nav [data-v="tr"]'):   # a study round, Talk, IELTS and ARMY live hide the tab bar: Translate can't open over them
            page.click(sel); page.wait_for_timeout(1500); close_overlays(page)
            if page.is_visible("#arHome"): page.click("#arHome"); page.wait_for_timeout(300)
            continue
        trsel = open_tr(page)   # the Translate tab opens over the current tab
        s = state(page)
        check(f"D {f}: opening Translate stops {f}'s recording", s["live"] == 0 and s["recs"] == 0, str(s))
        page.click(trsel); page.wait_for_timeout(1000)
        s = state(page)
        check(f"D {f}→TR: only one mic open while the interpreter listens", s["live"] == 1, str(s))
        page.click(trsel); page.wait_for_timeout(1500)
        close_overlays(page); page.wait_for_timeout(300)
        idle(page, f"D {f}→TR closed")
    for f in ["FR", "C", "TK", "IE"]:
        sel = FEAT[f](page); page.click(sel); page.wait_for_timeout(1000)
        open_tu(page); page.click("#tuMic"); page.wait_for_timeout(1000)
        s = state(page)
        check(f"D {f}+TU: only one mic open when the tutor starts recording over {f}", s["live"] == 1, str(s))
        page.click("#tuMic"); page.wait_for_timeout(1500); close_overlays(page)
        s = state(page)
        if s["live"]: page.click('nav [data-v="set"]'); page.wait_for_timeout(400)
        idle(page, f"D {f}+TU cleaned up")

# E. the reported case: a mic still open in Translate / ARMY live, then the tutor records
def t_tutor_over(page):
    trsel = open_tr(page); page.click(trsel); page.wait_for_timeout(1000)   # the interpreter is listening
    page.click('nav [data-v="read"]'); page.wait_for_timeout(400)   # Translate covers the tutor's bubble: leave it by a tab
    open_tu(page); page.click("#tuMic"); page.wait_for_timeout(1000)
    s = state(page)
    check("E Translate listening → Speak tab → tutor records: only the tutor's mic is open", s["live"] == 1 and s["recs"] == 1, str(s))
    page.click("#tuMic"); page.wait_for_timeout(1800)
    close_overlays(page); idle(page, "E after Translate + tutor")
    sel = open_ar(page); page.click(sel); page.wait_for_timeout(1500)   # ARMY live listening
    open_tu(page); page.click("#tuMic"); page.wait_for_timeout(1000)
    s = state(page)
    check("E ARMY live running → tutor records: only the tutor's mic is open", s["live"] == 1 and s["recs"] == 1, str(s))
    page.click("#tuMic"); page.wait_for_timeout(1800)
    a = page.get_attribute("#tu .tu-m.me audio", "src") or ""
    dur = page.evaluate("""async u => { const a = new Audio(u); await new Promise(r => a.onloadedmetadata = r); return a.duration; }""", a) if a else None
    check("E tutor replays a WAV with its real length (~1 s)", dur is not None and 0.5 < dur < 2, str(dur))
    close_overlays(page); idle(page, "E end")

TESTS = [("A", t_alone)] + [("B" + f, make_pairs(f)) for f in ORDER] + [("C", t_leave), ("D", t_overlay), ("E", t_tutor_over)]

with sync_playwright() as pw:
    for name, fn in TESTS:
        if ONLY and name not in ONLY and name[0] not in ONLY: continue
        run(pw, name, fn)

fails = [r for r in results if not r[1]]
for n, ok, info in results:
    print(("PASS " if ok else "FAIL ") + n + ("" if ok or not info else f"   [{info}]"))
print(f"\n{len(results) - len(fails)}/{len(results)} passed")
sys.exit(1 if fails else 0)
