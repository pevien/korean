"""Streak calendar — end-to-end tests (see docs/study.md, "Streaks and celebrations").

Drives the real index.html in headless Chromium; no key or network needed.

Run from the repo root (add scenario letters to run only those, e.g. `... streak_test.py B`):
    .venv/bin/python tests/streak_test.py

Screenshots land in $STREAK_TEST_OUT (default: a temp folder). Exit code 1 when anything fails.
"""
import functools, http.server, json, os, sys, tempfile, threading, traceback
from datetime import date, datetime, timedelta
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SP = os.environ.get("STREAK_TEST_OUT") or os.path.join(tempfile.gettempdir(), "streak-test")
os.makedirs(SP, exist_ok=True)
_srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT))
_srv.RequestHandlerClass.log_message = lambda *a: None
threading.Thread(target=_srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{_srv.server_address[1]}/index.html"

def k(d): return f"{d.year}-{d.month}-{d.day}"   # the app's "Y-M-D" day key, no padding
TODAY = date.today()
def ago(n): return TODAY - timedelta(days=n)
def ms(d): return int(datetime(d.year, d.month, d.day, 12).timestamp() * 1000)

def card(i, last=0, due=0):
    return { "id": f"c{i}", "lang": "en", "ko": f"word{i}", "meaning": f"nghĩa {i}", "ex": "", "exMean": "",
             "ease": 2.5, "interval": 1 if last else 0, "reps": 1 if last else 0, "lapses": 0, "due": due, "last": last, "created": 1 }

def seed(state, ui="vi"):
    st = { "cards": [], "settings": { "course": "en", "uiLang": ui } }
    st.update(state)
    return r"""
if (!sessionStorage.getItem("seeded")) {
  sessionStorage.setItem("seeded", "1");
  localStorage.setItem("hangulCards.v1", %s);
  localStorage.setItem("hangulCards.welcomed", "1");
}""" % json.dumps(json.dumps(st))

def page_for(b, state, ui="vi", dark=False):
    ctx = b.new_context(viewport={ "width": 390, "height": 844 }, color_scheme="dark" if dark else "light", service_workers="block")
    ctx.add_init_script(seed(state, ui))
    p = ctx.new_page()
    errs = []
    p.on("pageerror", lambda e: errs.append(str(e)))
    p.goto(URL); p.wait_for_selector("#goCal")
    return p, errs

def stats(p): return p.eval_on_selector_all("#v-cal .stat b", "els => els.map(e => e.textContent.trim())")

def A(b):
    """Old data ({ last, count } only) is rebuilt from the current run + each word's last review; tile opens the calendar."""
    p, errs = page_for(b, { "streak": { "last": k(ago(1)), "count": 3 },
                            "cards": [card(1, ms(ago(1))), card(2, ms(ago(10))), card(3, ms(ago(11))), card(4, ms(ago(12))), card(5, ms(ago(13))), card(6)] })
    p.click("#goCal"); p.wait_for_selector("#v-cal:not(.hidden) .cal-g")
    # days: run 1..3 ago + 10..13 ago → best 4, total 7, current 3 (yesterday still counts)
    assert stats(p) == ["3", "4", "7"], stats(p)
    assert p.is_visible("#v-cal .cal-g .cd.td"), "today is marked"
    assert p.eval_on_selector("nav button.on", "b => b.dataset.v") == "study"
    p.screenshot(path=f"{SP}/A-calendar.png", full_page=True)
    p.click("#calBack"); p.wait_for_selector("#v-study:not(.hidden)")
    assert not errs, errs

def B(b):
    """Month navigation: back stops at the first studied month, forward stops at this month; studied days in a week join."""
    first = (TODAY.replace(day=1) - timedelta(days=1)).replace(day=1)   # the 1st of last month
    days = [k(first + timedelta(days=i)) for i in (2, 3, 4)]
    p, errs = page_for(b, { "streak": { "last": days[-1], "count": 3, "days": days } })
    p.click("#goCal"); p.wait_for_selector("#v-cal .cal-g")
    assert p.is_disabled("#calNext"), "can't go past this month"
    assert not p.is_disabled("#calPrev")
    p.click("#calPrev")
    assert p.is_disabled("#calPrev"), "can't go before the first studied month"
    assert p.locator("#v-cal .cd.on").count() == 3
    assert "3 ngày học trong tháng" in p.inner_text("#v-cal .cal-sum")
    # the middle day joins on both sides unless it sits on a week edge
    mid = first + timedelta(days=3)
    if mid.weekday() not in (0, 6):
        assert "jl" in p.locator("#v-cal .cd.on").nth(1).get_attribute("class")
    assert stats(p) == ["0", "3", "3"], stats(p)
    p.screenshot(path=f"{SP}/B-last-month.png", full_page=True)
    assert not errs, errs

def C(b):
    """Answering a word adds today to the studied days (once) and the calendar shows it."""
    due = ms(ago(3))
    p, errs = page_for(b, { "streak": { "last": k(ago(1)), "count": 2, "days": [k(ago(1)), k(ago(2))] },
                            "settings": { "course": "en", "uiLang": "vi", "modes": { "ko2m": True, "listen2m": False, "listen2kc": False, "m2ko": False, "listen2ko": False, "ko2say": False, "m2say": False } },
                            "cards": [card(i, due, due) for i in range(1, 6)] })
    saved = lambda: p.evaluate("() => JSON.parse(localStorage.getItem('hangulCards.v1')).streak.days")
    for _ in range(2):   # the round starts by itself on the home page; two answers → today still added once
        p.wait_for_selector("#qBox .choice:not([disabled])")
        right = "nghĩa " + p.inner_text("#qBox .ko").strip().removeprefix("word")   # always pick a wrong one: the flow stays the same (✗ → Next)
        p.locator("#qBox .choice", has_not_text=right).first.click()
        p.wait_for_timeout(300)
        nxt = p.locator("#qBox button:has-text('Tiếp'), #qBox button:has-text('Next')")
        if nxt.count(): nxt.first.click()
    days = saved()
    assert days.count(k(TODAY)) == 1, days
    p.click("#endBtn"); p.wait_for_selector("#studyHome:not(.hidden)")
    p.click("#goCal"); p.wait_for_selector("#v-cal .cal-g")
    assert stats(p) == ["3", "3", "3"], stats(p)
    assert "on" in p.get_attribute("#v-cal .cd.td", "class")
    assert not errs, errs

def D(b):
    """English UI + dark theme render (screenshot only) and a reload stays on the calendar."""
    p, errs = page_for(b, { "streak": { "last": k(TODAY), "count": 5, "days": [k(ago(i)) for i in range(5)] + [k(ago(20))] } }, ui="en", dark=True)
    p.click("#goCal"); p.wait_for_selector("#v-cal .cal-g")
    assert stats(p) == ["5", "5", "6"], stats(p)
    assert "Days studied" in p.inner_text("#v-cal .stats")
    p.screenshot(path=f"{SP}/D-dark-en.png", full_page=True)
    p.reload(); p.wait_for_selector("#v-cal:not(.hidden) .cal-g")
    assert not errs, errs

SCEN = { "A": A, "B": B, "C": C, "D": D }

if __name__ == "__main__":
    pick = [a.upper() for a in sys.argv[1:]] or list(SCEN)
    fails = 0
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for name in pick:
            try: SCEN[name](b); print(f"✓ {name} {SCEN[name].__doc__.strip().splitlines()[0]}")
            except Exception: fails += 1; print(f"✗ {name}"); traceback.print_exc()
        b.close()
    print(f"\n{len(pick) - fails}/{len(pick)} passed · screenshots: {SP}")
    sys.exit(1 if fails else 0)
