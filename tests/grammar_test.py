"""Speak → Grammar — end-to-end tests (see docs/grammar.md).

Drives the real index.html in headless Chromium; no key or network needed. The lessons come from the real
grammar-ko.json, except in the scenarios that fake a failed download or a second level.

Run from the repo root (add scenario letters to run only those, e.g. `... grammar_test.py B`):
    .venv/bin/python tests/grammar_test.py

Screenshots land in $GRAMMAR_TEST_OUT (default: a temp folder). Exit code 1 when anything fails.
"""
import functools, http.server, json, os, re, sys, tempfile, threading, traceback
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SP = os.environ.get("GRAMMAR_TEST_OUT") or os.path.join(tempfile.gettempdir(), "grammar-test")
os.makedirs(SP, exist_ok=True)
_srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT))
_srv.RequestHandlerClass.log_message = lambda *a: None
threading.Thread(target=_srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{_srv.server_address[1]}/index.html"
DATA = json.load(open(os.path.join(ROOT, "grammar-ko.json"), encoding="utf-8"))
N = len(DATA)

def page_for(b, course="ko", ui="vi", grammar=None, dark=False):
    ctx = b.new_context(viewport={ "width": 390, "height": 844 }, service_workers="block", color_scheme="dark" if dark else "light")
    st = { "cards": [], "grammar": grammar or [], "settings": { "course": course, "uiLang": ui } }
    ctx.add_init_script(r"""
if (!sessionStorage.getItem("seeded")) {
  sessionStorage.setItem("seeded", "1");
  localStorage.setItem("hangulCards.v1", %s);
  localStorage.setItem("hangulCards.welcomed", "1");
}""" % json.dumps(json.dumps(st)))
    p = ctx.new_page()
    errs = []
    p.on("pageerror", lambda e: errs.append(str(e)))
    return p, errs

def open_home(p):
    p.goto(URL); p.wait_for_selector("#goCal", state="attached")
    p.click('nav [data-v="read"]'); p.wait_for_selector("#spHome .sp-pick")

def open_list(p):
    open_home(p)
    p.click('#spHome .sp-pick[data-s="grammar"]'); p.wait_for_selector("#grList .gr-row")

def saved(p): return p.evaluate("JSON.parse(localStorage.getItem('hangulCards.v1'))")
def rows(p): return p.locator("#grList .gr-row").count()
def row(id): return f'#grList .gr-row[data-id="{id}"]'

def A(b):
    """The lessons are complete: all three levels, unique ids, both languages, Korean in every example."""
    assert [sum(g["level"] == l for g in DATA) for l in ("s1", "s2", "i1")] == [36, 32, 122]
    assert len({ g["id"] for g in DATA }) == N
    hangul = re.compile(r"[가-힣]")
    both = lambda o: o and o.get("vi", "").strip() and o.get("en", "").strip()
    for g in DATA:
        i = g["id"]
        assert hangul.search(g["pattern"]) and both(g["meaning"]), i
        assert g["structure"] and all(both(x["when"]) and x["form"] and hangul.search(x["ex"]) for x in g["structure"]), i
        assert "how" not in g or both(g["how"]), i
        assert not any("gốc từ" in x["when"]["vi"].lower() for x in g["structure"]), (i, "plain labels: the how-to line explains the rest")
        assert not any("(으)" in x["form"] or "(이)" in x["form"] for x in g["structure"]), (i, "one row per case, not a merged form")
        assert g["uses"] and all(both(u["when"]) and u["ex"] for u in g["uses"]), i
        assert all(hangul.search(x["ko"]) and both(x) for u in g["uses"] for x in u["ex"]), i
        assert all(both(x["name"]) and both(x["note"]) and hangul.search(x["ex"]) for x in g.get("irregular", [])), i
        assert "notes" not in g or (both(g["notes"]) and g.get("notesEx")), (i, "a note comes with examples")
        assert all(hangul.search(x["ko"]) and both(x) for x in g.get("notesEx", [])), i
        assert all("→" in x["rule"] and hangul.search(x["ex"]) for x in g.get("vowels", [])), i
        if i != "ko-mot":   # its note shows how 못 먹어요 is pronounced
            assert not any(x["ko"].rstrip(".?!") in g["notes"][l] for x in g.get("notesEx", []) for l in ("vi", "en")), (i, "a note doesn't repeat its examples")

def B(b):
    """Only the Korean course has it, also after a reload that lands on the grammar screen."""
    p, errs = page_for(b, course="en")
    open_home(p)
    assert p.locator('#spHome .sp-pick[data-s="grammar"]').count() == 0
    p.evaluate("sessionStorage.setItem('hangulCards.nav', JSON.stringify({ v: 'read', sp: 'grammar' }))")
    p.reload(); p.wait_for_selector("#spHome .sp-pick")
    assert p.is_visible("#spHome") and not p.is_visible("#grammar")
    p2, errs2 = page_for(b)
    open_list(p2)
    assert rows(p2) == N
    assert not errs and not errs2, errs + errs2

def C(b):
    """Search finds patterns, Vietnamese with or without marks, English and examples; an unknown word says so."""
    p, errs = page_for(b)
    open_list(p)
    def find(q):
        p.fill("#grSearch", q)
        return [r.get_attribute("data-id") for r in p.locator("#grList .gr-row").all()]
    assert find("아서")[0] == "ko-aseo", find("아서")
    assert "ko-go-sipda" in find("muốn"), find("muốn")
    assert "ko-go-sipda" in find("muon"), find("muon")
    assert "ko-go-sipda" in find("want"), find("want")
    assert "ko-do" in find("일요일에도")
    assert p.is_visible("#grSearch") and p.evaluate("document.activeElement.id") == "grSearch", "typing keeps the field focused"
    assert find("zzzz") == [] and p.is_visible("#grNone")
    assert not errs, errs

def D(b):
    """Marking learned: from the list and the detail page, survives a reload, filters and counts follow, un-marking keeps the record."""
    p, errs = page_for(b)
    open_list(p)
    assert p.get_attribute(row("ko-do") + " .gr-tick", "aria-pressed") == "false"
    p.click(row("ko-do") + " .gr-tick")
    assert p.inner_text("#grCount") == f"1/{N}"
    p.click(row("ko-man") + " .gr-open"); p.wait_for_selector("#grLearn")
    p.click("#grLearn")
    assert "Bỏ" in p.inner_text("#grLearn")
    p.click("#grBack"); p.wait_for_selector("#grList")
    assert p.inner_text("#grCount") == f"2/{N}"
    p.click('#grTabs [data-f="done"]')
    assert rows(p) == 2
    p.click('#grTabs [data-f="todo"]')
    assert rows(p) == N - 2
    p.click('#grTabs [data-f="all"]')
    recs = { x["id"]: x for x in saved(p)["grammar"] }
    assert set(recs) == { "ko-do", "ko-man" } and recs["ko-do"]["lang"] == "ko" and recs["ko-do"]["learned"] and recs["ko-do"]["mod"]
    p.reload(); p.wait_for_selector("#grList .gr-row")
    assert p.inner_text("#grCount") == f"2/{N}", "a reload stays on the list"
    p.click(row("ko-do") + " .gr-tick")
    assert p.inner_text("#grCount") == f"1/{N}"
    assert next(x for x in saved(p)["grammar"] if x["id"] == "ko-do")["learned"] == 0
    p.click("#grBack"); p.wait_for_selector("#spHome .sp-pick")
    assert f"1/{N}" in p.inner_text('#spHome .sp-pick[data-s="grammar"]')
    assert not errs, errs

def E(b):
    """The detail page shows every part, in the UI language, and examples read themselves aloud."""
    g = next(x for x in DATA if x["id"] == "ko-aseo")
    for ui, other in (("vi", "en"), ("en", "vi")):
        p, errs = page_for(b, ui=ui)
        open_list(p)
        p.click(row("ko-aseo") + " .gr-open"); p.wait_for_selector("#grLearn")
        t = p.inner_text("#grammar")
        for s in (g["pattern"], g["meaning"][ui], g["structure"][0]["form"], g["uses"][1]["when"][ui], g["uses"][0]["ex"][0]["ko"], g["uses"][0]["ex"][0][ui], g["irregular"][0]["ex"], g["notes"][ui]):
            assert s in t, (ui, s)
        assert g["meaning"][other] not in t and g["uses"][0]["ex"][0][other] not in t, ui
        for h in { "vi": ("Cấu trúc", "Khi dùng", "Bất quy tắc", "Lưu ý", "Đánh dấu đã học"), "en": ("Structure", "When to use it", "Irregulars", "Notes", "Mark as learned") }[ui]:
            assert h in t, h
        assert p.locator("#grammar .gr-wrong").count() == 2 and p.locator("#grammar .gr-wrong .speak").count() == 0, "wrong sentences aren't read aloud"
        heads = [h.inner_text() for h in p.locator("#grammar .card h3").all()]
        assert heads[:2] == { "vi": ["Khi dùng", "Cấu trúc"], "en": ["When to use it", "Structure"] }[ui], heads
        p.evaluate("() => { window.__said = []; speechSynthesis.speak = u => window.__said.push(u.text); }")
        p.click("#grammar .ex .speak"); p.wait_for_timeout(300)
        assert p.evaluate("window.__said").count(g["uses"][0]["ex"][0]["ko"]), p.evaluate("window.__said")
        assert not errs, errs

def M(b):
    """Structure reads as steps: a how-to line, what to add for each case, and the join in each example."""
    p, errs = page_for(b)
    open_list(p)
    p.click(row("ko-ayo") + " .gr-open"); p.wait_for_selector("#grNote")
    t = p.inner_text("#grammar .card:has(.gr-form) >> nth=0")
    assert "Bỏ 다, nhìn nguyên âm cuối" in t, t
    assert "Nguyên âm là ㅏ, ㅗ → thêm 아요" in t and "좋다 → 좋 + 아요 → 좋아요" in t and "Có 하다 → đổi 하다 thành 해요" in t, t
    p.click("#grBack"); p.wait_for_selector("#grList .gr-row")
    p.click(row("ko-amuri-ado") + " .gr-open"); p.wait_for_selector("#grNote")
    assert "thêm 아무리" not in p.inner_text("#grammar"), "a frame around the word isn't an ending to add"
    assert not errs, errs

def L(b):
    """Vowel contraction: in the Notes card, spelled for that lesson's ending, also in a lesson with no other note."""
    p, errs = page_for(b)
    open_list(p)
    p.click(row("ko-past") + " .gr-open"); p.wait_for_selector("#grNote")
    t = p.inner_text("#grammar .gr-vowels")
    assert "Rút gọn nguyên âm" in t and "ㅗ + 아 → ㅘ" in t and "보다 → 봤어요" in t and "마시다 → 마셨어요" in t and "되다 → 됐어요" in t, t
    p.click("#grBack"); p.wait_for_selector("#grList .gr-row")
    p.click(row("ko-a-boda") + " .gr-open"); p.wait_for_selector("#grNote")
    assert "오다 → 와 보다" in p.inner_text("#grammar .gr-vowels") and "봐 보다" not in p.inner_text("#grammar .gr-vowels")
    p.click("#grBack"); p.wait_for_selector("#grList .gr-row")
    p.click(row("ko-do") + " .gr-open"); p.wait_for_selector("#grNote")
    assert p.locator("#grammar .gr-vowels").count() == 0
    assert not errs, errs

def F(b):
    """The phone's Back button goes detail → list → Speak, and tapping the Speak tab starts from its home."""
    p, errs = page_for(b)
    open_list(p)
    p.click(row("ko-do") + " .gr-open"); p.wait_for_selector("#grLearn")
    p.go_back(); p.wait_for_selector("#grList .gr-row")
    p.go_back(); p.wait_for_selector("#spHome .sp-pick")
    assert not p.is_visible("#grammar")
    p.click('#spHome .sp-pick[data-s="grammar"]'); p.wait_for_selector("#grList .gr-row")
    p.click(row("ko-do") + " .gr-open"); p.wait_for_selector("#grLearn")
    p.click('nav [data-v="read"]'); p.wait_for_selector("#spHome .sp-pick")
    p.click('#spHome .sp-pick[data-s="grammar"]'); p.wait_for_selector("#grList .gr-row")
    assert not errs, errs

def G(b):
    """A failed download shows Try again, and trying again works. Nothing is stuck for later visits."""
    p, errs = page_for(b)
    fail = { "on": True }
    p.route("**/grammar-ko.json", lambda r: r.abort() if fail["on"] else r.continue_())
    open_home(p)
    p.click('#spHome .sp-pick[data-s="grammar"]'); p.wait_for_selector("#grRetry")
    fail["on"] = False
    p.click("#grRetry"); p.wait_for_selector("#grList .gr-row")
    assert rows(p) == N
    assert not errs, errs

def H(b):
    """Level chips filter the list; they are built from the file, so a file with one level shows none."""
    p, errs = page_for(b)
    open_list(p)
    assert p.locator("#grLevels .chip").count() == 4
    p.click('#grLevels [data-l="s2"]')
    assert rows(p) == 32
    p.click('#grLevels [data-l="i1"]')
    assert rows(p) == 122
    p.click(row("ko-eojida") + " .gr-open"); p.wait_for_selector("#grLearn")
    assert "Trung cấp" in p.inner_text("#grammar .sub-head")
    p.click("#grBack"); p.wait_for_selector("#grList .gr-row")
    assert rows(p) == 122, "the filter stays"
    p.click('#grLevels [data-l=""]')
    assert rows(p) == N
    p2, errs2 = page_for(b)
    p2.route("**/grammar-ko.json", lambda r: r.fulfill(json=[g for g in DATA if g["level"] == "s1"]))
    open_list(p2)
    assert p2.locator("#grLevels").count() == 0
    assert not errs and not errs2, errs + errs2

def K(b):
    """My notes: saved while typing, kept after a reload and back in the box; a note alone doesn't mark the point; clearing it works."""
    p, errs = page_for(b)
    open_list(p)
    p.click(row("ko-do") + " .gr-open"); p.wait_for_selector("#grNote")
    p.fill("#grNote", "<b>ghi chú</b>")
    p.wait_for_function("(JSON.parse(localStorage.getItem('hangulCards.v1')).grammar[0] || {}).note === '<b>ghi chú</b>'")
    r = saved(p)["grammar"][0]
    assert r["id"] == "ko-do" and r["learned"] == 0 and r["mod"]
    p.click("#grLearn")
    assert p.input_value("#grNote") == "<b>ghi chú</b>", "marking keeps the note"
    p.reload(); p.wait_for_selector("#grList .gr-row")
    assert p.inner_text("#grCount") == f"1/{N}"
    p.click(row("ko-do") + " .gr-open"); p.wait_for_selector("#grNote")
    assert p.input_value("#grNote") == "<b>ghi chú</b>"
    p.fill("#grNote", ""); p.click("#grBack"); p.wait_for_selector("#grList .gr-row")
    assert saved(p)["grammar"][0]["note"] == ""
    assert not errs, errs

def I(b):
    """Layout on a phone, light and dark: nothing scrolls sideways, a lesson keeps to three font sizes, and screenshots for a look by eye."""
    for dark in (False, True):
        p, errs = page_for(b, dark=dark, grammar=[{ "id": "ko-i-ga", "lang": "ko", "learned": 1 }])
        open_list(p)
        n = "dark" if dark else "light"
        assert p.evaluate("document.documentElement.scrollWidth <= innerWidth")
        p.screenshot(path=f"{SP}/list-{n}.png")
        p.click(row("ko-ayo") + " .gr-open"); p.wait_for_selector("#grLearn")
        assert p.evaluate("document.documentElement.scrollWidth <= innerWidth")
        sizes = p.evaluate("""() => {
          const out = new Set(), w = document.createTreeWalker(document.querySelector('#grammar'), NodeFilter.SHOW_TEXT);
          for (let t; t = w.nextNode();) if (t.textContent.trim() && t.parentElement.closest('.card')) out.add(getComputedStyle(t.parentElement).fontSize);
          return [...out].sort();
        }""")
        assert sizes == ["13px", "15px", "22px"], sizes
        p.screenshot(path=f"{SP}/detail-{n}.png", full_page=True)
        assert not errs, errs

SCEN = { "A": A, "B": B, "C": C, "D": D, "E": E, "F": F, "G": G, "H": H, "I": I, "K": K, "L": L, "M": M }

if __name__ == "__main__":
    pick = [a.upper() for a in sys.argv[1:]] or list(SCEN)
    fails = 0
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for name in pick:
            try: SCEN[name](b); print(f"✓ {name} {SCEN[name].__doc__.strip().splitlines()[0]}")
            except Exception: fails += 1; print(f"✗ {name}"); traceback.print_exc()
        b.close()
    print(f"\n{len(pick) - fails}/{len(pick)} passed")
    sys.exit(1 if fails else 0)
