"""ARMY → 🎵 BTS Songs — end-to-end test (see docs/translate-army.md).

Drives the real index.html in headless Chromium with Gemini faked (no key, no network). The lyrics are
made-up placeholder lines: checks the paste is cleaned up, [section: member] headers set the singer, AI fills
romanization/meaning/guessed singers without being sent anything to rewrite, the layer toggles, and the story tab.

    .venv/bin/python tests/songs_test.py
"""
import functools, http.server, json, os, sys, tempfile, threading
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SP = os.environ.get("SONGS_TEST_OUT") or os.path.join(tempfile.gettempdir(), "songs-test")
os.makedirs(SP, exist_ok=True)
_srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT))
_srv.RequestHandlerClass.log_message = lambda *a: None
threading.Thread(target=_srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{_srv.server_address[1]}/index.html"

# a pasted Genius-like page, with invented lines
PASTE = """12 Contributors
Translations
Español
Test Song Lyrics
Some blurb about the song… Read More
[Intro: RM]
우리는 테스트 노래
Hello test line

[Chorus: Jimin & Jung Kook]
노래를 불러요
[Jimin]
지민 줄
[Verse 2 - SUGA (슈가)]
슈가 줄
[Chorus: V (뷔), Jung Kook]
뷔 줄
[Bridge]
마지막 줄이에요
You might also like
Last english line5Embed"""

INIT = r"""
if (!sessionStorage.getItem("seeded")) {
  sessionStorage.setItem("seeded", "1");
  localStorage.setItem("hangulCards.v1", JSON.stringify({ cards: [], settings: { course: "ko", apiKey: "FAKE", uiLang: "vi", model: "gemini-2.5-flash-lite" } }));
  localStorage.setItem("hangulCards.welcomed", "1");
}
window.__prompts = [];
const realFetch = window.fetch;
window.fetch = async (url, opts) => {
  if (String(url).includes("generativelanguage")) {
    if (String(url).includes("/models?")) return new Response(JSON.stringify({ models: [{ name: "models/gemini-2.5-flash-lite", supportedGenerationMethods: ["generateContent"] }] }));
    const body = JSON.parse(opts.body), p = body.contents[0].parts[0].text;
    window.__prompts.push(p);
    if (p.includes("For EVERY line marked")) window.__singBody = body;
    await new Promise(r => setTimeout(r, 100));
    let out;
    if (p.includes("tell them about it")) { window.__storyBody = JSON.parse(opts.body); out = { album: "Album thử", released: "13/2/2017", about: "Giới thiệu thử", origin: "Nguồn gốc thử", meaning: "Ý nghĩa thử", theories: ["Theory thử"], facts: ["Fact 1", "Fact 2"] }; }
    else if (p.includes("For EVERY line marked")) out = { who: [{ n: 7, who: "V" }, { n: 8, who: "Jin" }] };
    else {
      // a chunk holding the 4th line is "blocked as recitation": no text, like the real API
      if (p.includes("마지막 줄이에요")) return new Response(JSON.stringify({ candidates: [{ finishReason: "RECITATION" }] }));
      const n = (p.match(/^\d+\. /gm) || []).length;
      out = { items: Array.from({ length: n }, (_, i) => ({ n: i + 1, mean: "nghĩa " + (i + 1) })) };
    }
    return new Response(JSON.stringify({ candidates: [{ content: { parts: [{ text: JSON.stringify(out) }] } }] }));
  }
  if (String(url).includes("translate.googleapis")) { window.__free = (window.__free || 0) + 1; return new Response(JSON.stringify([[["dịch google", "x"]]])); }
  return realFetch(url, opts);
};
window.__opened = [];
window.open = u => { window.__opened.push(u); return null; };
"""

results = []
def check(name, cond, info=""): results.append((name, bool(cond), info))

with sync_playwright() as pw:
    b = pw.chromium.launch()
    page = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.add_init_script(INIT)
    page.goto(URL); page.wait_for_timeout(800)
    page.click('nav button[data-v="army"]'); page.wait_for_timeout(200)
    page.click("#arSongsOpen"); page.wait_for_timeout(200)
    check("empty list", "Chưa có bài nào" in page.inner_text("#v-army"))
    page.click("#sgNew"); page.wait_for_timeout(200)
    check("title is free text, no suggestion list", page.get_attribute("#sgTitle", "list") is None and page.locator("#sgTitles").count() == 0)
    page.fill("#sgTitle", "Test Song")
    page.click("#sgFind")
    check("finds lyrics on Google", page.evaluate("__opened[0]").startswith("https://www.google.com/search?q=BTS%20Test%20Song%20lyrics"), page.evaluate("__opened"))
    page.fill("#sgRaw", PASTE)
    page.click("#sgGo"); page.wait_for_selector(".sg-ly", timeout=5000); page.wait_for_timeout(200)
    page.screenshot(path=os.path.join(SP, "lyrics.png"), full_page=True)

    song = page.evaluate("JSON.parse(localStorage.getItem('hangulCards.v1')).songs[0]")
    texts = [l["t"] for l in song["lines"]]
    check("paste cleaned", texts == ["우리는 테스트 노래", "Hello test line", "노래를 불러요", "지민 줄", "슈가 줄", "뷔 줄", "마지막 줄이에요", "Last english line"], texts)
    check("headers without colon / with dash / with brackets", [l["who"] for l in song["lines"][3:6]] == [["Jimin"], ["SUGA"], ["V", "Jung Kook"]], [l["who"] for l in song["lines"][3:6]])
    sb = page.evaluate("__singBody")
    check("singers looked up on Google with Flash", sb.get("tools") == [{"google_search": {}}] and sb["generationConfig"]["responseMimeType"] == "text/plain", sb.get("tools"))
    check("header singers", [l["who"] for l in song["lines"][:3]] == [["RM"], ["RM"], ["Jimin", "Jung Kook"]], [l["who"] for l in song["lines"]])
    check("AI picks a singer for every unknown line", [song["lines"][i]["who"] for i in (6, 7)] == [["V"], ["Jin"]] and all(song["lines"][i].get("gw") for i in (6, 7)), song["lines"])
    check("no line left without a singer", all(l["who"] for l in song["lines"]))
    rom = page.locator(".sg-r").all_inner_texts()
    check("romanization worked out on Korean lines", rom[:2] + rom[-1:] == ["urineun teseuteu norae", "noraereul bulleoyo", "majimak jurieyo"], rom)
    check("meanings filled", all(l["mean"] for l in song["lines"]), [l["mean"] for l in song["lines"]])
    check("blocked line falls back to Google Translate, others from AI", song["lines"][6]["mean"] == "dịch google" and song["lines"][0]["mean"].startswith("nghĩa") and page.evaluate("__free") == 1,
          [l["mean"] for l in song["lines"]])
    pw_ = page.evaluate("__prompts")
    sing = next(p for p in pw_ if "For EVERY line marked" in p)
    check("singer prompt marks unknown lines with ?", "[?] 마지막 줄이에요" in sing and "[RM] 우리는" in sing and "Never leave a line empty" in sing and "search the web" in sing)
    mean = next(p for p in pw_ if "translation of that line" in p)
    check("meaning prompt asks Vietnamese, no romanization", "Vietnamese translation" in mean and "rom" not in mean.split("Return")[0].lower().replace("from", ""))
    check("chips per singer run", page.locator(".sg-who").count() == 7, page.locator(".sg-who").all_inner_texts())
    check("speaker only on Korean lines", page.locator(".sg-say").count() == 6)
    page.evaluate("() => { window.__said = []; speechSynthesis.speak = u => __said.push(u.text); }")
    page.locator(".sg-say").first.click(); page.wait_for_timeout(100)
    said = page.evaluate("__said")
    check("speaker reads the Korean line (or says no voice)", said == ["우리는 테스트 노래"] or "giọng" in page.inner_text("#toast"), said)

    # hide meaning layer
    page.click('.sg-layers button[data-k="m"]'); page.wait_for_timeout(150)
    check("meaning hidden", not page.locator(".sg-m").first.is_visible())
    page.click('.sg-layers button[data-k="m"]'); page.wait_for_timeout(150)

    # fix the guessed singer
    page.locator(".sg-who").nth(5).click(); page.select_option(".sg-pick", "SUGA"); page.wait_for_timeout(150)
    l3 = page.evaluate("JSON.parse(localStorage.getItem('hangulCards.v1')).songs[0].lines[6]")
    check("singer edited", l3["who"] == ["SUGA"] and not l3["g"] and not l3.get("gw"), l3)

    # delete is an icon-only button
    check("delete button is icon only", page.inner_text("#sgDel").strip() == "" and page.locator("#sgDel svg").count() == 1 and "ico" in page.get_attribute("#sgDel", "class"))
    # analysing: the button says so, even after leaving the song and coming back
    page.click("#sgRedo"); page.wait_for_timeout(50)
    check("analyse button shows analysing", "Đang phân tích" in page.inner_text("#sgRedo") and page.is_disabled("#sgRedo"), page.inner_text("#sgRedo"))
    page.click("#sgBack"); page.wait_for_timeout(50); page.locator("#sgList li").first.click(); page.wait_for_timeout(50)
    check("still analysing after reopening", "Đang phân tích" in page.inner_text("#sgRedo") and page.is_disabled("#sgRedo"), page.inner_text("#sgRedo"))
    page.wait_for_function("!document.querySelector('#sgRedo').disabled", timeout=8000)
    check("button back to normal when done", "Phân tích lại" in page.inner_text("#sgRedo"), page.inner_text("#sgRedo"))

    # story tab
    page.click('#sgTabs button[data-t="st"]'); page.wait_for_timeout(100)
    page.click("#sgStory"); page.wait_for_selector(".sg-h", timeout=5000)
    page.screenshot(path=os.path.join(SP, "story.png"), full_page=True)
    st = page.inner_text("#sgBody")
    check("story shows album and release date", "Album thử" in st and "phát hành 13/2/2017" in st, st)
    check("story prompt asks for every field", "Fill EVERY field" in page.evaluate("JSON.stringify(__storyBody)"))
    check("story looked up on Google", page.evaluate("__storyBody.tools") == [{"google_search": {}}])
    check("story shown", "Nguồn gốc thử" in st and "Fact 2" in st and "Theory thử" in st, st)
    check("story prompt doesn't quote lyrics", "do not quote the lyrics" in page.evaluate("__prompts[__prompts.length-1]"))

    # survives a reload; list shows it
    page.reload(); page.wait_for_timeout(800)
    page.click('nav button[data-v="army"]'); page.click("#arSongsOpen"); page.wait_for_timeout(200)
    check("listed after reload", "Test Song" in page.inner_text("#sgList"))
    check("no page errors", not errs, errs)
    b.close()

ok = all(r[1] for r in results)
for n, c, info in results: print(("✅" if c else "❌"), n, "" if c else info)
print("screenshots:", SP)
sys.exit(0 if ok else 1)
