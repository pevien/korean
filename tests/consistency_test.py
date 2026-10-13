"""Cheap consistency checks — docs vs code, the service worker's file list, and untranslated English in the Vietnamese UI.

The first three read files only; the last one drives the real index.html in headless Chromium (no key or network needed).

Run from the repo root (add scenario letters to run only those, e.g. `... consistency_test.py D`):
    .venv/bin/python tests/consistency_test.py

Exit code 1 when anything fails.
"""
import functools, glob, http.server, json, os, re, sys, threading, traceback
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def read(p): return open(os.path.join(ROOT, p), encoding="utf-8").read()
SW = read("sw.js")

def A():
    """docs/architecture.md names the cache sw.js actually uses (it is bumped on every shell change)."""
    cache = re.search(r'const CACHE = "([^"]+)"', SW).group(1)
    named = set(re.findall(r"hangul-v\d+", read("docs/architecture.md")))
    assert named == { cache }, f"sw.js uses {cache}, docs name {sorted(named)}"

def B():
    """Every file the service worker pre-caches exists."""
    shell = json.loads(re.search(r"const SHELL = (\[[^\]]*\])", SW).group(1).replace("'", '"'))
    missing = [u for u in shell if u != "./" and not os.path.exists(os.path.join(ROOT, u))]
    assert not missing, missing

def C():
    """Every tests/*.py the docs mention exists, and every test file is mentioned somewhere in the docs."""
    docs = "".join(read(p) for p in glob.glob(os.path.join(ROOT, "docs", "*.md")))
    named = set(re.findall(r"tests/(\w+\.py)", docs))
    files = { os.path.basename(p) for p in glob.glob(os.path.join(ROOT, "tests", "*_test.py")) }
    assert not named - files, f"named in docs but missing: {sorted(named - files)}"
    assert not files - named, f"not mentioned in docs: {sorted(files - named)}"

# proper nouns that stay in English in the Vietnamese UI
KEEP = { "Gemini API key", "Google OAuth Client ID" }
VI_CHARS = "àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ"
PROBE = r"""() => {
  const out = new Set(), skip = '[data-noi18n],:not(html)[lang],script,style,textarea,.exm,.exl', vi = /[%s]/i, en = /[a-z]{3,} [a-z]{2,}/i;
  const seen = el => el.offsetParent || getComputedStyle(el).position === 'fixed';
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n; n = w.nextNode();) {
    const el = n.parentElement, t = n.textContent.trim();
    if (el && !el.closest(skip) && seen(el) && en.test(t) && !vi.test(t)) out.add(t.slice(0, 100));
  }
  document.querySelectorAll('[placeholder],[title],[aria-label]').forEach(e => {
    if (e.closest(skip) || !seen(e)) return;
    ['placeholder', 'title', 'aria-label'].forEach(a => { const t = e.getAttribute(a); if (t && en.test(t) && !vi.test(t)) out.add('@' + a + ': ' + t.slice(0, 100)); });
  });
  return [...out];
}""" % VI_CHARS

def D():
    """Vietnamese UI: no English left on the main tabs or in Settings (all sections open). Also sanity-checks the probe on the English UI."""
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT))
    srv.RequestHandlerClass.log_message = lambda *a: None
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/index.html"
    def scan(b, ui):
        st = { "cards": [], "settings": { "course": "en", "uiLang": ui, "apiKey": "FAKE" } }
        ctx = b.new_context(viewport={ "width": 390, "height": 844 }, service_workers="block")
        ctx.add_init_script('if (!sessionStorage.getItem("seeded")) { sessionStorage.setItem("seeded", "1"); localStorage.setItem("hangulCards.v1", %s); localStorage.setItem("hangulCards.welcomed", "1"); }' % json.dumps(json.dumps(st)))
        p = ctx.new_page(); errs = []
        p.on("pageerror", lambda e: errs.append(str(e)))
        p.route(re.compile(r"^https?://(?!127\.0\.0\.1)"), lambda r: r.abort())
        p.goto(url); p.wait_for_timeout(1200)
        found = {}
        for v in ["study", "read", "tr", "army", "set"]:
            p.click(f'nav [data-v="{v}"]'); p.wait_for_timeout(400)
            if v == "set": p.evaluate("document.querySelectorAll('#v-set details').forEach(d => d.open = true)"); p.wait_for_timeout(300)
            if v == "tr": p.keyboard.press("Escape"); p.wait_for_timeout(200)
            left = [t for t in p.evaluate(PROBE) if t.lstrip("@placeholdertitlearia-: ") not in KEEP and t not in KEEP]
            if left: found[v] = left
        ctx.close(); srv_errs.extend(errs)
        return found
    srv_errs = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        assert scan(b, "en"), "the probe finds nothing even on the English UI — it is broken"
        vi = scan(b, "vi")
        b.close()
    srv.shutdown()
    assert not vi, "English left in the Vietnamese UI:\n" + "\n".join(f"  [{k}] {t}" for k, v in vi.items() for t in v)
    assert not srv_errs, srv_errs

SCEN = { "A": A, "B": B, "C": C, "D": D }

if __name__ == "__main__":
    pick = [a.upper() for a in sys.argv[1:]] or list(SCEN)
    fails = 0
    for name in pick:
        try: SCEN[name](); print(f"✓ {name} {SCEN[name].__doc__.strip().splitlines()[0]}")
        except Exception: fails += 1; print(f"✗ {name}"); traceback.print_exc()
    print(f"\n{len(pick) - fails}/{len(pick)} passed")
    sys.exit(1 if fails else 0)
