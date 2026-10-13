"""Google Drive sync — merge rules and "Delete all data" — end-to-end tests (see docs/settings.md, "Google Drive sync", "Backup").

Drives the real index.html in headless Chromium. Google sign-in and the Drive API are faked (a valid token is
already stored, Drive calls are answered in the page), so it needs no account and no network.

Run from the repo root (add scenario letters to run only those, e.g. `... sync_test.py B`):
    .venv/bin/python tests/sync_test.py

Exit code 1 when anything fails.
"""
import functools, http.server, json, os, sys, threading, time, traceback
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT))
_srv.RequestHandlerClass.log_message = lambda *a: None
threading.Thread(target=_srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{_srv.server_address[1]}/index.html"

NOW = int(time.time() * 1000)
H, DAY = 3600_000, 86400_000

def card(id, ko, lang="en", meaning="nghĩa", reps=0, last=0, mod=None):
    c = { "id": id, "lang": lang, "ko": ko, "meaning": meaning, "ex": "", "exMean": "", "ease": 2.5, "interval": reps, "reps": reps,
          "lapses": 0, "due": 0, "last": last, "created": NOW - 30 * DAY }
    if mod: c["mod"] = mod
    return c

def init(local, remote, drive_fail=False):
    st = { "cards": [], "settings": { "course": "en", "uiLang": "vi", "apiKey": "MYKEY", "keyMod": NOW - 10 * DAY, "voice": "my-voice", "newPerDay": 10, "_mod": NOW - 5 * DAY } }
    st.update(local)
    st["settings"] = dict({ "course": "en", "uiLang": "vi", "apiKey": "MYKEY", "keyMod": NOW - 10 * DAY, "voice": "my-voice", "newPerDay": 10, "_mod": NOW - 5 * DAY }, **local.get("settings", {}))
    return r"""
if (!sessionStorage.getItem("seeded")) {
  sessionStorage.setItem("seeded", "1");
  localStorage.setItem("hangulCards.v1", %s);
  localStorage.setItem("hangulCards.welcomed", "1");
  localStorage.setItem("hangulCards.sync", JSON.stringify({ clientId: "test.apps.googleusercontent.com", on: true, last: 1, fileId: "F1" }));
  localStorage.setItem("hangulCards.gtoken", JSON.stringify({ t: "TOKEN", exp: Date.now() + 3600e3 }));
}
window.__remote = %s; window.__uploads = []; window.__deleted = []; window.__driveFail = %s;
const realFetch = window.fetch;
window.fetch = async (url, opts = {}) => {
  url = String(url);
  if (!url.includes("googleapis.com")) return realFetch(url, opts);
  const m = (opts.method || "GET").toUpperCase(), json = o => new Response(JSON.stringify(o), { status: 200, headers: { "Content-Type": "application/json" } });
  if (window.__driveFail) return new Response("{}", { status: 500 });
  if (url.includes("/upload/")) { window.__uploads.push(JSON.parse(opts.body)); return json({ id: "F1" }); }
  if (m === "DELETE") { window.__deleted.push(url.split("/files/")[1]); return new Response(null, { status: 204 }); }
  if (url.includes("alt=media")) return json(window.__remote);
  if (url.includes("/files?")) return json({ files: [{ id: "F1" }] });
  return json({});
};
""" % (json.dumps(json.dumps(st)), json.dumps(remote), "true" if drive_fail else "false")

def page_for(b, local, remote, **kw):
    ctx = b.new_context(viewport={ "width": 390, "height": 844 }, service_workers="block")
    ctx.add_init_script(init(local, remote, **kw))
    p = ctx.new_page()
    errs = []
    p.on("pageerror", lambda e: errs.append(str(e)))
    p.goto(URL); p.wait_for_selector("#goCal")
    p.click('nav [data-v="set"]'); p.wait_for_selector("#resetBtn")
    return p, errs

def sync(p):
    n = p.evaluate("window.__uploads.length")
    p.click("#gdStatus")
    p.wait_for_function(f"window.__uploads.length > {n} && document.querySelector('#gdStatus').dataset.st === 'ok'", timeout=5000)
    return p.evaluate("window.__uploads[window.__uploads.length - 1]")

def saved(p): return p.evaluate("() => JSON.parse(localStorage.getItem('hangulCards.v1'))")
def by_id(s): return { c["id"]: c for c in s["cards"] }

def A(b):
    """Words: the newer version of each wins (both ways), new ones from either side kept; the same word added on two devices keeps the one with more progress."""
    local = { "cards": [card("c1", "one", meaning="old", mod=NOW - 3 * H), card("c2", "two", meaning="mine, newer", mod=NOW - 1 * H),
                        card("c4", "four"), card("w1", "apple", reps=1), card("k1", "apple", lang="ko")] }
    remote = { "cards": [card("c1", "one", meaning="theirs, newer", mod=NOW - 2 * H), card("c2", "two", meaning="theirs", mod=NOW - 2 * H),
                         card("c3", "three"), card("w2", "apple", reps=4)], "settings": {} }
    p, errs = page_for(b, local, remote)
    up = sync(p)
    for s in (saved(p), up):
        c = by_id(s)
        assert c["c1"]["meaning"] == "theirs, newer" and c["c2"]["meaning"] == "mine, newer", (c["c1"], c["c2"])
        assert "c3" in c and "c4" in c, sorted(c)
        assert "w2" in c and "w1" not in c, "same word on two devices: more reps kept"
        assert "k1" in c, "same word in another course isn't a duplicate"
    assert "w1" in up["deleted"], "the dropped duplicate is spread as a deletion"
    assert "apiKey" in up["settings"]
    assert not errs, errs

def B(b):
    """Deletions: a tombstone removes older copies but not one edited after it; local deletions reach Drive; tombstones older than 180 days are dropped."""
    local = { "cards": [card("c5", "five", mod=NOW - 3 * H), card("c6", "six", meaning="edited after", mod=NOW - 1 * H)],
              "deleted": { "c7": NOW - 2 * H, "old": NOW - 200 * DAY } }
    remote = { "cards": [card("c5", "five", mod=NOW - 3 * H), card("c6", "six", mod=NOW - 4 * H), card("c7", "seven", mod=NOW - 5 * H)],
               "deleted": { "c5": NOW - 2 * H, "c6": NOW - 2 * H } }
    p, errs = page_for(b, local, remote)
    up = sync(p)
    for s in (saved(p), up):
        c = by_id(s)
        assert "c5" not in c, "deleted on the other device after its last edit"
        assert c.get("c6", {}).get("meaning") == "edited after", "edited here after the deletion → kept"
        assert "c7" not in c, "deleted here → not brought back"
        assert "c7" in s["deleted"] and "c5" in s["deleted"] and "old" not in s["deleted"], s["deleted"]
    assert not errs, errs

def C(b):
    """Settings: the newer side wins but voice + course stay per device; the key follows its own stamp; studied days from both devices are joined."""
    local = { "settings": { "newPerDay": 10, "_mod": NOW - 5 * DAY, "apiKey": "MYKEY", "keyMod": NOW - 10 * DAY },
              "streak": { "last": "2026-1-5", "count": 2, "days": ["2026-1-4", "2026-1-5"] } }
    remote = { "cards": [], "settings": { "course": "ko", "uiLang": "vi", "voice": "their-voice", "newPerDay": 30, "_mod": NOW - 1 * DAY,
                                          "apiKey": "", "keyMod": NOW - 2 * DAY },
               "streak": { "last": "2026-1-3", "count": 5, "days": ["2026-1-1", "2026-1-2", "2026-1-3"] } }
    p, errs = page_for(b, local, remote)
    p.evaluate("window.__remote.settings._mod = Date.now() + 1000")   # opening the page fills in defaults, which stamps the settings here
    sync(p)
    st = saved(p)["settings"]
    assert st["newPerDay"] == 30, st
    assert st["voice"] == "my-voice" and st["course"] == "en", st
    assert st["apiKey"] == "", "the key was removed later on the other device"
    days = saved(p)["streak"]["days"]
    assert sorted(days) == ["2026-1-1", "2026-1-2", "2026-1-3", "2026-1-4", "2026-1-5"], days
    assert saved(p)["streak"]["last"] == "2026-1-5", "the run that reached the latest day is kept"
    assert not errs, errs

def C2(b):
    """An older Drive copy doesn't overwrite newer settings here, and a newer key here stays."""
    local = { "settings": { "newPerDay": 15, "_mod": NOW - 1 * DAY, "apiKey": "MYKEY", "keyMod": NOW - 1 * DAY } }
    remote = { "cards": [], "settings": { "course": "en", "uiLang": "vi", "newPerDay": 30, "_mod": NOW - 5 * DAY, "apiKey": "OLDKEY", "keyMod": NOW - 6 * DAY } }
    p, errs = page_for(b, local, remote)
    up = sync(p)
    assert saved(p)["settings"]["newPerDay"] == 15 and up["settings"]["newPerDay"] == 15
    assert saved(p)["settings"]["apiKey"] == "MYKEY"
    assert not errs, errs

def D(b):
    """Delete all data with sync on: the Drive file is deleted, then everything here, key and sync too; language + course stay; no tombstones left behind."""
    p, errs = page_for(b, { "cards": [card("c1", "one"), card("c2", "two")], "settings": { "uiLang": "vi", "course": "en" } }, { "cards": [] })
    p.click("#resetBtn"); p.click("#resetBtn")
    p.wait_for_function("JSON.parse(localStorage.getItem('hangulCards.v1')).cards.length === 0", timeout=5000)
    assert p.evaluate("window.__deleted") == ["F1"], p.evaluate("window.__deleted")
    s = saved(p)
    assert s["settings"].get("apiKey", "") == "" and s["settings"]["course"] == "en" and s["settings"]["uiLang"] == "vi", s["settings"]
    assert not s.get("deleted"), s.get("deleted")
    assert p.evaluate("localStorage.getItem('hangulCards.sync')") is None and p.evaluate("localStorage.getItem('hangulCards.gtoken')") is None
    assert not errs, errs

def E(b):
    """Delete all data when deleting the Drive copy fails: nothing is deleted at all."""
    p, errs = page_for(b, { "cards": [card("c1", "one")] }, { "cards": [] }, drive_fail=True)
    p.click("#resetBtn"); p.click("#resetBtn")
    p.wait_for_function("document.querySelector('#toast').textContent.includes('⚠️')", timeout=5000)
    s = saved(p)
    assert [c["id"] for c in s["cards"]] == ["c1"] and s["settings"]["apiKey"] == "MYKEY", s
    assert json.loads(p.evaluate("localStorage.getItem('hangulCards.sync')"))["on"] is True
    assert not errs, errs

def F(b):
    """A single tap doesn't delete; the confirm runs out after 4 s."""
    p, errs = page_for(b, { "cards": [card("c1", "one")] }, { "cards": [] })
    p.click("#resetBtn"); p.wait_for_timeout(4300); p.click("#resetBtn"); p.wait_for_timeout(500)
    assert len(saved(p)["cards"]) == 1 and p.evaluate("window.__deleted") == []
    assert not errs, errs

SCEN = { "A": A, "B": B, "C": C, "C2": C2, "D": D, "E": E, "F": F }

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
