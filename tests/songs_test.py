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
    const p = JSON.parse(opts.body).contents[0].parts[0].text;
    window.__prompts.push(p);
    await new Promise(r => setTimeout(r, 100));
    let out;
    if (p.includes("tell them about it")) out = { known: true, about: "Giới thiệu thử", origin: "Nguồn gốc thử", meaning: "Ý nghĩa thử", theories: ["Theory thử"], facts: ["Fact 1", "Fact 2"] };
    else {
      const n = (p.match(/^\d+\. \[/gm) || []).length;
      out = { items: Array.from({ length: n }, (_, i) => ({ n: i + 1, rom: "rom " + (i + 1), mean: "nghĩa " + (i + 1), who: i === 3 ? "V" : "" })) };
    }
    return new Response(JSON.stringify({ candidates: [{ content: { parts: [{ text: JSON.stringify(out) }] } }] }));
  }
  return realFetch(url, opts);
};
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
    page.fill("#sgTitle", "Test Song"); page.fill("#sgRaw", PASTE)
    page.click("#sgGo"); page.wait_for_selector(".sg-ly", timeout=5000); page.wait_for_timeout(200)
    page.screenshot(path=os.path.join(SP, "lyrics.png"), full_page=True)

    song = page.evaluate("JSON.parse(localStorage.getItem('hangulCards.v1')).songs[0]")
    texts = [l["t"] for l in song["lines"]]
    check("paste cleaned", texts == ["우리는 테스트 노래", "Hello test line", "노래를 불러요", "마지막 줄이에요", "Last english line"], texts)
    check("header singers", [l["who"] for l in song["lines"][:3]] == [["RM"], ["RM"], ["Jimin", "Jung Kook"]], [l["who"] for l in song["lines"]])
    check("AI guesses singer of [Bridge] line", song["lines"][3]["who"] == ["V"] and song["lines"][3]["g"], song["lines"][3])
    check("romanization only on Korean lines", song["lines"][0]["rom"] == "rom 1" and song["lines"][1]["rom"] == "", song["lines"][1])
    check("meanings filled", all(l["mean"] for l in song["lines"]))
    pr = page.evaluate("__prompts[0]")
    check("prompt marks unknown singer with ?", "[?] 마지막 줄이에요" in pr and "[RM] 우리는" in pr, pr[-300:])
    check("prompt asks Vietnamese", "Vietnamese translation" in pr)
    check("chips per singer run", page.locator(".sg-who").count() == 4, page.locator(".sg-who").all_inner_texts())

    # hide meaning layer
    page.click('.sg-layers button[data-k="m"]'); page.wait_for_timeout(150)
    check("meaning hidden", not page.locator(".sg-m").first.is_visible())
    page.click('.sg-layers button[data-k="m"]'); page.wait_for_timeout(150)

    # fix the guessed singer
    page.locator(".sg-who").nth(2).click(); page.select_option(".sg-pick", "SUGA"); page.wait_for_timeout(150)
    l3 = page.evaluate("JSON.parse(localStorage.getItem('hangulCards.v1')).songs[0].lines[3]")
    check("singer edited", l3["who"] == ["SUGA"] and not l3["g"], l3)

    # story tab
    page.click('#sgTabs button[data-t="st"]'); page.wait_for_timeout(100)
    page.click("#sgStory"); page.wait_for_selector(".sg-h", timeout=5000)
    page.screenshot(path=os.path.join(SP, "story.png"), full_page=True)
    st = page.inner_text("#sgBody")
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
