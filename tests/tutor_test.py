"""AI tutor (floating chat) — end-to-end tests (see docs/README.md, "AI tutor").

Drives the real index.html in headless Chromium. Gemini, the microphone and photos are faked, so it needs
no key, no mic and no network. Checks the bubble only shows with a key, typed / voice / photo questions,
multi-turn history, the screen context and placement above the study sheet.

Run from the repo root (add scenario letters to run only those, e.g. `... tutor_test.py B`):
    .venv/bin/python tests/tutor_test.py

Screenshots land in $TUTOR_TEST_OUT (default: a temp folder). Exit code 1 when anything fails.
"""
import functools, http.server, json, os, sys, tempfile, threading, traceback
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SP = os.environ.get("TUTOR_TEST_OUT") or os.path.join(tempfile.gettempdir(), "tutor-test")
os.makedirs(SP, exist_ok=True)
_srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT))
_srv.RequestHandlerClass.log_message = lambda *a: None
threading.Thread(target=_srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{_srv.server_address[1]}/index.html"

ANSWER = "**사과** nghĩa là *quả táo*.\n- Ví dụ: **사과를 먹어요** (Tôi ăn táo)\n- Mẹo: nghe giống \"sa-goa\""

def init(key="FAKE"):
    st = { "cards": [{ "id": "c1", "lang": "ko", "ko": "사과", "meaning": "quả táo", "ex": "", "exMean": "", "ease": 2.5, "interval": 1,
                       "reps": 1, "lapses": 0, "due": 1, "last": 1, "created": 1 }],
           "settings": { "course": "ko", "apiKey": key, "uiLang": "vi", "model": "gemini-2.5-flash-lite", "newPerDay": 0, "speakAuto": True, "autoPlay": False } }
    return r"""
if (!sessionStorage.getItem("seeded")) {
  sessionStorage.setItem("seeded", "1");
  localStorage.setItem("hangulCards.v1", %s);
  localStorage.setItem("hangulCards.welcomed", "1");
}
window.__bodies = [];
const realFetch = window.fetch;
window.fetch = async (url, opts) => {
  if (String(url).includes("generativelanguage")) {
    if (String(url).includes("/models?")) return new Response(JSON.stringify({ models: [{ name: "models/gemini-2.5-flash-lite", supportedGenerationMethods: ["generateContent"] }] }));
    const body = JSON.parse(opts.body);
    if (body.generationConfig.responseMimeType === "text/plain") window.__bodies.push(body);
    await new Promise(r => setTimeout(r, 150));
    const lastParts = body.contents[body.contents.length - 1].parts, voice = lastParts.some(p => p.inline_data && p.inline_data.mime_type === "audio/wav");
    const txt = body.generationConfig.responseMimeType === "text/plain" ? (voice ? "HEARD: \"안녕하세요\"\n" : "") + %s : "{}";
    return new Response(JSON.stringify({ candidates: [{ content: { parts: [{ text: txt }] } }] }));
  }
  return realFetch(url, opts);
};
navigator.mediaDevices.getUserMedia = async () => { const ac = new AudioContext(), o = ac.createOscillator(), d = ac.createMediaStreamDestination(); o.connect(d); o.start(); return d.stream; };
if (navigator.permissions) { const q = navigator.permissions.query.bind(navigator.permissions); navigator.permissions.query = d => d && d.name === "microphone" ? Promise.resolve({ state: "granted" }) : q(d); }
""" % (json.dumps(json.dumps(st)), json.dumps(ANSWER))

results = []
def check(name, cond, info=""): results.append((name, bool(cond), info))
ONLY = {x.upper() for x in sys.argv[1:]}

def run(pw, name, fn, width=390, **kw):
    if ONLY and name not in ONLY: return
    b = pw.chromium.launch(args=["--autoplay-policy=no-user-gesture-required", "--use-fake-ui-for-media-stream"])
    page = b.new_page(viewport={"width": width, "height": 844}, device_scale_factor=2)
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

def ask(page, text):
    n = page.evaluate("window.__bodies.length")
    page.fill("#tuIn", text); page.press("#tuIn", "Enter")
    page.wait_for_function(f"window.__bodies.length > {n} && !document.querySelector('#tuList .tu-wait')", timeout=8000)
    return page.evaluate("window.__bodies[window.__bodies.length - 1]")

def A(page):
    """No key: no bubble. Adding one in Settings brings it; removing it hides it."""
    check("A: hidden without a key", page.is_hidden("#tuFab"))
    page.click("nav button[data-v=set]")
    page.fill("#setKey", "AIzaFAKEKEY123456"); page.dispatch_event("#setKey", "change"); page.wait_for_timeout(300)
    check("A: shown once a key is added", page.is_visible("#tuFab"))

def B(page):
    """Typed question: chat answer rendered, screen context + level in the system prompt, multi-turn history."""
    check("B: bubble visible with a key", page.is_visible("#tuFab"))
    page.click("#tuFab")
    check("B: panel open, bubble hidden", page.is_visible("#tu") and page.is_hidden("#tuFab"))
    check("B: welcome chips", page.eval_on_selector_all("#tuList .tu-chips button", "e => e.length") == 4)
    idol = page.inner_text("#tuTitle").split(" ")[0]
    check("B: Korean tutor is a BTS member", idol in ("RM", "Jin", "SUGA", "j-hope", "Jimin", "V", "Jung") and idol in page.inner_text("#tuList .tu-hi b"), page.inner_text("#tuTitle"))
    body = ask(page, "사과 là gì?")
    sysp = body["systemInstruction"]["parts"][0]["text"]
    check("B: input asks that member", page.get_attribute("#tuIn", "placeholder") == f"Hỏi {page.inner_text('#tuTitle').rsplit(' ', 1)[0]}…", page.get_attribute("#tuIn", "placeholder"))
    check("B: system prompt plays that member", f"of BTS" in sysp and idol in sysp, sysp[:200])
    check("B: no follow-up question at the end", "never end a reply with a follow-up question" in sysp)
    check("B: plain-text answer requested", body["generationConfig"]["responseMimeType"] == "text/plain")
    check("B: system prompt has course, level and UI language", "Korean teacher" in sysp and "Vietnamese" in sysp and "beginner" in sysp, sysp[:200])
    check("B: system prompt has the screen the learner is on", "What the app is showing them" in sysp and len(sysp.split('"""')[1].strip()) > 10, sysp[-300:])
    ai = page.inner_html("#tuList .tu-m.ai")
    check("B: markdown → bold / italic / list", "<b class=\"say\">사과</b>" in ai and "<i>quả táo</i>" in ai and ai.count("<li>") == 2, ai)
    page.screenshot(path=f"{SP}/B-chat.png")
    body = ask(page, "Cho thêm ví dụ")
    roles = [c["role"] for c in body["contents"]]
    check("B: second turn sends the history", roles == ["user", "model", "user"], roles)
    page.click("#tuNew"); page.wait_for_timeout(100)
    check("B: new chat clears", page.query_selector("#tuList .tu-hi") and not page.query_selector("#tuList .tu-m"))
    check("B: new chat → another member", page.inner_text("#tuTitle").split(" ")[0] != idol, page.inner_text("#tuTitle"))
    check("B: header shows the flag and level picker", page.inner_text("#tuTitle").endswith("🇰🇷") and page.input_value("#tuLv") == page.input_value("#genLevel"), page.input_value("#tuLv"))
    page.select_option("#tuLv", index=2); lv = page.input_value("#tuLv")
    check("B: level picker saves the app level", page.evaluate("JSON.parse(localStorage.getItem('hangulCards.v1')).settings.level") == lv, lv)
    page.screenshot(path=f"{SP}/B-pickers.png")
    page.click("#tuClose")
    check("B: close → bubble back", page.is_hidden("#tu") and page.is_visible("#tuFab"))

def C(page):
    """Voice question: recorded audio goes to Gemini as WAV; the bubble shows a player."""
    page.click("#tuFab")
    page.click("#tuMic"); page.wait_for_timeout(1500)
    check("C: recording state", "on" in page.get_attribute("#tuMic", "class"))
    page.click("#tuMic")
    page.wait_for_function("window.__bodies.length > 0 && !document.querySelector('#tuList .tu-wait')", timeout=8000)
    parts = page.evaluate("window.__bodies[0].contents[0].parts")
    check("C: audio part sent", any(p.get("inline_data", {}).get("mime_type") == "audio/wav" for p in parts), str([list(p) for p in parts]))
    check("C: player in the learner bubble", page.query_selector("#tuList .tu-m.me audio"))
    check("C: answer shown", page.query_selector("#tuList .tu-m.ai"))
    heard = page.query_selector("#tuList .tu-m.me .heard")
    check("C: transcript under the recording", heard and heard.inner_text() == "안녕하세요", heard and heard.inner_text())
    check("C: HEARD line not in the answer", "HEARD" not in page.inner_text("#tuList .tu-m.ai"))
    page.screenshot(path=f"{SP}/C-voice.png")

def D(page):
    """Photo question: attach, preview, sent as JPEG with the typed text."""
    page.click("#tuFab")
    png = os.path.join(SP, "pic.png")
    page.screenshot(path=png, clip={"x": 0, "y": 0, "width": 200, "height": 120})
    page.set_input_files("#tuFile", png); page.wait_for_selector("#tuAtt img")
    body = ask(page, "Chữ này đọc sao?")
    parts = body["contents"][0]["parts"]
    check("D: image + text sent", parts[0].get("inline_data", {}).get("mime_type") == "image/jpeg" and parts[-1]["text"] == "Chữ này đọc sao?")
    check("D: preview cleared, photo in bubble", page.is_hidden("#tuAtt") and page.query_selector("#tuList .tu-m.me img"))
    page.screenshot(path=f"{SP}/D-photo.png")

def E(page):
    """During a study round on a phone the bubble floats above the answer sheet, not on top of it."""
    if page.query_selector("#startBtn"): page.click("#startBtn")
    page.wait_for_timeout(600)
    dock = page.query_selector(".dock")
    fab = page.query_selector("#tuFab").bounding_box()
    if dock and dock.bounding_box():
        check("E: bubble above the study sheet", fab["y"] + fab["height"] <= dock.bounding_box()["y"], (fab, dock.bounding_box()))
    else:
        nav = page.query_selector("nav").bounding_box()
        check("E: bubble above the tab bar", fab["y"] + fab["height"] <= nav["y"], (fab, nav))
    page.screenshot(path=f"{SP}/E-session.png")

def F(page):
    """Desktop: floating panel at the corner."""
    page.click("#tuFab")
    r = page.query_selector("#tu").bounding_box()
    check("F: panel is a corner window", r["width"] <= 402 and r["x"] > 500, r)
    page.screenshot(path=f"{SP}/F-desktop.png")

with sync_playwright() as pw:
    run(pw, "A", A, key="")
    run(pw, "B", B)
    run(pw, "C", C)
    run(pw, "D", D)
    run(pw, "E", E)
    run(pw, "F", F, width=1200)

fails = [r for r in results if not r[1]]
for n, ok, info in results: print(("PASS " if ok else "FAIL ") + n + ("" if ok else "  →  " + str(info)))
print(f"\n{len(results) - len(fails)}/{len(results)} passed · screenshots in {SP}")
sys.exit(1 if fails else 0)
