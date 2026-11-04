"""Speak → Reading: AI key words for passages that have none — end-to-end tests (see docs/speak.md).

Drives the real index.html in headless Chromium. Gemini is faked, so it needs no key and no network.

Run from the repo root (add scenario letters to run only those, e.g. `... keywords_test.py B`):
    .venv/bin/python tests/keywords_test.py

Exit code 1 when anything fails.
"""
import functools, http.server, json, os, sys, threading, traceback
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT))
_srv.RequestHandlerClass.log_message = lambda *a: None
threading.Thread(target=_srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{_srv.server_address[1]}/index.html"
WORDS = [{ "ko": "사과", "meaning": "quả táo" }, { "ko": "먹다", "meaning": "ăn" }]

def passage(id, sentence, vocab=()):
    return { "id": id, "lang": "ko", "title": id, "titleMean": "", "created": 1, "vocab": list(vocab), "sentences": [{ "ko": sentence, "meaning": "" }] }

def init(key, passages, fails=0, delay=150):
    st = { "cards": [], "passages": passages, "settings": { "course": "ko", "apiKey": key, "uiLang": "vi", "model": "gemini-2.5-flash-lite" } }
    return r"""
if (!sessionStorage.getItem("seeded")) {
  sessionStorage.setItem("seeded", "1");
  localStorage.setItem("hangulCards.v1", %s);
  localStorage.setItem("hangulCards.welcomed", "1");
}
window.__prompts = []; window.__fails = %d;
const realFetch = window.fetch;
window.fetch = async (url, opts) => {
  if (String(url).includes("generativelanguage")) {
    if (String(url).includes("/models?")) return new Response(JSON.stringify({ models: [{ name: "models/gemini-2.5-flash-lite", supportedGenerationMethods: ["generateContent"] }] }));
    window.__prompts.push(JSON.parse(opts.body).contents[0].parts[0].text);
    await new Promise(r => setTimeout(r, %d));
    if (window.__fails-- > 0) return new Response("{}", { status: 500 });
    return new Response(JSON.stringify({ candidates: [{ content: { parts: [{ text: JSON.stringify({ vocab: %s }) }] } }] }));
  }
  return realFetch(url, opts);
};
""" % (json.dumps(json.dumps(st)), fails, delay, json.dumps(WORDS))

results = []
def check(name, cond, info=""): results.append((name, bool(cond), info))
ONLY = {x.upper() for x in sys.argv[1:]}

def run(pw, name, fn, **kw):
    if ONLY and name not in ONLY: return
    b = pw.chromium.launch()
    page = b.new_page(viewport={"width": 390, "height": 844})
    page.set_default_timeout(8000)
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.add_init_script(init(**kw))
    try:
        page.goto(URL); page.wait_for_timeout(800)
        page.click('nav [data-v="read"]'); page.wait_for_timeout(300)
        page.click('#spHome .sp-pick[data-s="read"]'); page.wait_for_timeout(300)
        fn(page)
    except Exception:
        check(name + ": ran without exception", False, traceback.format_exc().splitlines()[-1])
    check(name + ": no page errors", not errs, "; ".join(errs)[:300])
    b.close()

def opn(page, id):
    page.click(f'#passList li[data-id="{id}"]'); page.wait_for_timeout(50)
def back(page):
    page.click("#rdBack"); page.wait_for_timeout(100)
def calls(page): return page.evaluate("window.__prompts.length")
def card(page): return page.is_visible("#rdVocabCard")
def text(page): return page.inner_text("#rdVocab")
def saved(page, id): return page.evaluate("id => JSON.parse(localStorage.getItem('hangulCards.v1')).passages.find(p => p.id === id)", id)

def A(page):
    """First open: spinner, then the words, saved with a sync stamp; later opens don't call AI again."""
    opn(page, "p1")
    check("A: spinner while waiting", card(page) and "AI đang tìm từ vựng" in text(page), text(page))
    check("A: passage text sent", "저는 사과를 먹어요." in page.evaluate("window.__prompts[0]"))
    page.wait_for_selector("#rdVocab [data-add]", timeout=5000)
    check("A: words shown", "사과" in text(page) and "quả táo" in text(page), text(page))
    check("A: save-all button", page.is_visible("#rdAddVocab"))
    p = saved(page, "p1")
    check("A: saved", p["vocab"] == WORDS, p["vocab"])
    check("A: stamped for sync", p.get("mod"))
    back(page); opn(page, "p1"); page.wait_for_timeout(300)
    check("A: reopening costs no call", calls(page) == 1, calls(page))
    check("A: still shown", "사과" in text(page))

def B(page):
    """No key: nothing is asked and the card stays hidden."""
    opn(page, "p1"); page.wait_for_timeout(300)
    check("B: no call", calls(page) == 0, calls(page))
    check("B: card hidden", not card(page))

def C(page):
    """AI fails: the card disappears quietly, nothing is saved, the next open tries again."""
    opn(page, "p1"); page.wait_for_timeout(600)
    check("C: card hidden", not card(page))
    check("C: no toast", not page.is_visible("#toast.show"))
    check("C: nothing saved", not saved(page, "p1")["vocab"])
    back(page); opn(page, "p1")
    page.wait_for_selector("#rdVocab [data-add]", timeout=5000)
    check("C: retried", calls(page) >= 2 and "사과" in text(page), calls(page))

def D(page):
    """Leaving for another passage: the words land on the passage they belong to."""
    opn(page, "p1"); back(page); opn(page, "p2"); page.wait_for_timeout(50)
    check("D: other passage keeps its own words", "책" in text(page) and "사과" not in text(page), text(page))
    page.wait_for_timeout(500)
    check("D: answer doesn't touch the open passage", "사과" not in text(page), text(page))
    check("D: saved on the right passage", saved(page, "p1")["vocab"] == WORDS and saved(page, "p2")["vocab"][0]["ko"] == "책")
    check("D: one call", calls(page) == 1, calls(page))

def E(page):
    """Deleting the passage while AI answers doesn't bring it back or fail."""
    opn(page, "p1")
    page.click("#rdDel"); page.click("#rdDel"); page.wait_for_timeout(500)
    check("E: stays deleted", saved(page, "p1") is None)

OWN = passage("p1", "저는 사과를 먹어요.")
BOOK = passage("p2", "책을 읽어요.", [{ "ko": "책", "meaning": "sách" }])
with sync_playwright() as pw:
    run(pw, "A", A, key="FAKE", passages=[OWN])
    run(pw, "B", B, key="", passages=[OWN])
    run(pw, "C", C, key="FAKE", passages=[OWN], fails=1)
    run(pw, "D", D, key="FAKE", passages=[OWN, BOOK], delay=300)
    run(pw, "E", E, key="FAKE", passages=[OWN], delay=300)

bad = [r for r in results if not r[1]]
for n, ok, info in results: print(("✓ " if ok else "✗ ") + n + (f"  [{info}]" if not ok and info != "" else ""))
print(f"\n{len(results) - len(bad)}/{len(results)} passed")
sys.exit(1 if bad else 0)
