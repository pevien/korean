"""Settings → Backup (export / import) — end-to-end tests (see docs/settings.md, "Backup").

Drives the real index.html in headless Chromium; no key or network needed.

Run from the repo root (add scenario letters to run only those, e.g. `... backup_test.py C`):
    .venv/bin/python tests/backup_test.py

Exit code 1 when anything fails.
"""
import functools, http.server, json, os, sys, tempfile, threading, traceback
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SP = os.environ.get("BACKUP_TEST_OUT") or os.path.join(tempfile.gettempdir(), "backup-test")
os.makedirs(SP, exist_ok=True)
_srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT))
_srv.RequestHandlerClass.log_message = lambda *a: None
threading.Thread(target=_srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{_srv.server_address[1]}/index.html"

MODES = { m: True for m in ["ko2m", "listen2m", "listen2kc", "m2ko", "listen2ko", "ko2say", "m2say"] }

def card(id, ko, lang="en", meaning="nghĩa", reps=0):
    c = { "id": id, "ko": ko, "meaning": meaning, "ex": "", "exMean": "", "ease": 2.5, "interval": reps, "reps": reps,
          "lapses": 0, "due": 0, "last": 0, "created": 1 }
    if lang: c["lang"] = lang
    return c

def seed(state):
    st = { "cards": [], "settings": { "course": "en", "uiLang": "vi", "apiKey": "MYKEY", "voice": "my-voice", "newPerDay": 10 } }
    st.update(state)
    return r"""
if (!sessionStorage.getItem("seeded")) {
  sessionStorage.setItem("seeded", "1");
  localStorage.setItem("hangulCards.v1", %s);
  localStorage.setItem("hangulCards.welcomed", "1");
}""" % json.dumps(json.dumps(st))

def page_for(b, state):
    ctx = b.new_context(viewport={ "width": 390, "height": 844 }, service_workers="block", accept_downloads=True)
    ctx.add_init_script(seed(state))
    p = ctx.new_page()
    errs = []
    p.on("pageerror", lambda e: errs.append(str(e)))
    p.goto(URL); p.wait_for_selector("#goCal")
    p.click('nav [data-v="set"]'); p.wait_for_selector("#impBtn")
    return p, errs

def saved(p): return p.evaluate("() => JSON.parse(localStorage.getItem('hangulCards.v1'))")

def import_file(p, data, name="backup.json"):
    f = os.path.join(SP, name)
    with open(f, "w", encoding="utf-8") as fh: fh.write(data if isinstance(data, str) else json.dumps(data))
    p.set_input_files("#impFile", f); p.wait_for_timeout(500)
    return p.inner_text("#toast")

def force_save(p):   # any later save() writes what is in memory: a failed import must have left nothing there
    p.evaluate("() => { const e = document.querySelector('#setNew'); e.value = '12'; e.dispatchEvent(new Event('change')); }")
    p.wait_for_timeout(200)

BACKUP = {
    "cards": [card("b1", "apple"), card("b2", "pear"), card("b3", "사과", lang=None)],   # no lang = from before courses = Korean
    "settings": { "course": "ko", "uiLang": "vi", "apiKey": "", "voice": "old-voice", "newPerDay": 25,
                  "modes": { "ko2m": False, "listen2m": True } },                       # an old backup without the newer question types
    "streak": { "last": "2026-1-1", "count": 7, "days": ["2026-1-1"] },
    "passages": [{ "id": "p1", "title": "P", "sentences": [] }, { "id": "bad" }],          # no sentences → skipped
    "talks": [{ "id": "t1", "turns": [] }],
    "ielts": [{ "id": "i1", "qs": [], "result": { "band": 6 } }, { "id": "i2", "qs": [] }],  # no result → skipped
    "lives": [{ "id": "l1", "lines": [] }],
    "songs": [{ "id": "s1", "lines": [] }],
}

def A(b):
    """Into an empty device: everything added; settings + streak restored, but this device's key, course and voice kept; missing question types stay on."""
    p, errs = page_for(b, {})
    t = import_file(p, BACKUP)
    assert "3" in t and "1" in t, t
    s = saved(p)
    assert sorted((c["lang"], c["ko"]) for c in s["cards"]) == [("en", "apple"), ("en", "pear"), ("ko", "사과")], s["cards"]
    assert [x["id"] for x in s["passages"]] == ["p1"] and s["passages"][0]["vocab"] == []
    assert [x["id"] for x in s["talks"]] == ["t1"] and [x["id"] for x in s["ielts"]] == ["i1"]
    assert [x["id"] for x in s["lives"]] == ["l1"] and [x["id"] for x in s["songs"]] == ["s1"]
    st = s["settings"]
    assert st["newPerDay"] == 25, st
    assert st["apiKey"] == "MYKEY" and st["course"] == "en" and st["voice"] == "my-voice", st
    assert st["modes"]["ko2m"] is False and st["modes"]["m2say"] is True and st["modes"]["ko2say"] is True, st["modes"]
    assert s["streak"]["count"] == 7
    assert not errs, errs

def B(b):
    """Into a device with words: same course+word or same id skipped, same word in another course added; settings + streak untouched; importing twice adds nothing."""
    p, errs = page_for(b, { "cards": [card("x1", "apple", reps=3), card("b2", "edited pear")],
                            "streak": { "last": "2026-2-2", "count": 2, "days": ["2026-2-2"] } })
    data = dict(BACKUP, cards=BACKUP["cards"] + [card("b4", "apple", lang="ko")])
    import_file(p, data)
    s = saved(p)
    pairs = sorted((c["id"], c["lang"], c["ko"]) for c in s["cards"])
    assert pairs == [("b2", "en", "edited pear"), ("b3", "ko", "사과"), ("b4", "ko", "apple"), ("x1", "en", "apple")], pairs
    assert [c for c in s["cards"] if c["id"] == "x1"][0]["reps"] == 3, "progress on the word already here kept"
    assert s["settings"]["newPerDay"] == 10 and s["streak"]["count"] == 2, (s["settings"], s["streak"])
    import_file(p, data, "again.json")
    assert len(saved(p)["cards"]) == 4 and len(saved(p)["passages"]) == 1
    assert not errs, errs

def C(b):
    """A broken file adds nothing at all — not even after a later save — and says 'invalid'."""
    p, errs = page_for(b, { "cards": [card("x1", "apple")] })
    before = saved(p)
    for i, bad in enumerate([
        "not json {",
        { "cards": "nope" },
        dict(BACKUP, passages={}),        # cards fine, a later list broken
        dict(BACKUP, talks="x"),
        dict(BACKUP, ielts=5),
        dict(BACKUP, cards=BACKUP["cards"] + [{ "id": "n", "ko": 5 }]),   # a word that isn't text
    ]):
        t = import_file(p, bad, f"bad{i}.json")
        assert "không hợp lệ" in t or "Invalid" in t, (i, t)
        force_save(p)
        s = saved(p)
        assert [c["id"] for c in s["cards"]] == ["x1"], (i, s["cards"])
        assert s.get("passages", []) == before.get("passages", []) and s.get("talks", []) == before.get("talks", []), i
    assert not errs, errs

def C2(b):
    """A broken file into an empty device doesn't restore its settings or streak either."""
    p, errs = page_for(b, {})
    import_file(p, dict(BACKUP, songs={}))
    force_save(p)
    s = saved(p)
    assert s["cards"] == [] and s["settings"]["voice"] == "my-voice" and s["settings"].get("modes", {}).get("ko2m") is not False, s["settings"]
    assert not s.get("streak") or s["streak"].get("count") != 7, s.get("streak")
    assert not errs, errs

def D(b):
    """Export: dated file name, all data, but no API key; it imports back cleanly."""
    p, errs = page_for(b, { "cards": [card("x1", "apple")], "passages": [{ "id": "p9", "title": "P", "sentences": [] }] })
    with p.expect_download() as dl: p.click("#expBtn")
    d = dl.value
    assert d.suggested_filename.startswith("grow-with-pv-backup-") and d.suggested_filename.endswith(".json"), d.suggested_filename
    data = json.load(open(d.path(), encoding="utf-8"))
    assert data["settings"]["apiKey"] == "" and "MYKEY" not in json.dumps(data)
    assert [c["id"] for c in data["cards"]] == ["x1"] and data["passages"][0]["id"] == "p9"
    assert saved(p)["settings"]["apiKey"] == "MYKEY", "exporting doesn't touch the key here"
    p2, errs2 = page_for(b, {})
    import_file(p2, data)
    assert [c["ko"] for c in saved(p2)["cards"]] == ["apple"] and saved(p2)["settings"]["apiKey"] == "MYKEY"
    assert not errs and not errs2, errs + errs2

SCEN = { "A": A, "B": B, "C": C, "C2": C2, "D": D }

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
