"""ARMY → 🎵 BTS Songs — end-to-end test (see docs/translate-army.md).

Drives the real index.html in headless Chromium with Gemini faked (no key, no network). The lyrics are
made-up placeholder lines: checks the paste is cleaned up, [section] headers only split sections (no singers),
AI fills meanings on the model picked in Settings, romanization is worked out locally, quota fallbacks, the layer toggles, and the story tab.

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
  localStorage.setItem("hangulCards.v1", JSON.stringify({ cards: [], settings: { course: "ko", apiKey: "FAKE", uiLang: "vi", model: "gemini-2.5-flash" } }));
  localStorage.setItem("hangulCards.welcomed", "1");
}
window.__prompts = [];
const realFetch = window.fetch;
window.fetch = async (url, opts) => {
  if (String(url).includes("generativelanguage")) {
    if (String(url).includes("/models?")) return new Response(JSON.stringify({ models: [{ name: "models/gemini-2.5-flash", supportedGenerationMethods: ["generateContent"] }, { name: "models/gemini-2.5-flash-lite", supportedGenerationMethods: ["generateContent"] }] }));
    const body = JSON.parse(opts.body), p = body.contents[0].parts[0].text;
    window.__prompts.push(p); (window.__models = window.__models || []).push(String(url).split("/models/")[1].split(":")[0]);
    await new Promise(r => setTimeout(r, 100));
    let out;
    if (window.__quota && !p.includes("tell them about it")) return new Response(JSON.stringify({ error: { message: "quota" } }), { status: 429 });
    if (window.__searchQuota && body.tools) { window.__searchFails = (window.__searchFails || 0) + 1; return new Response(JSON.stringify({ error: { message: "quota" } }), { status: 429 }); }
    if (body.tools) {
      window.__searchBody = body; window.__searches = (window.__searches || 0) + 1;
      const txt = window.__notFound ? "NOT FOUND" : "NOTES: album Album thử, released 13 Feb 2017, written by RM.";
      // __noGround: the model answered without actually searching (no groundingMetadata)
      return new Response(JSON.stringify({ candidates: [{ content: { parts: [{ text: txt }] }, ...(window.__noGround ? {} : { groundingMetadata: { webSearchQueries: ["BTS song"] } }) }] }));
    }
    if (window.__unknownSong && p.includes("tell them about it") && p.includes("never describe a different song")) { window.__stories = (window.__stories || 0) + 1; window.__storyBody = body;
      return new Response(JSON.stringify({ candidates: [{ content: { parts: [{ text: JSON.stringify({ known: false }) }] } }] })); }
    if (p.includes("tell them about it")) { window.__storyBody = JSON.parse(opts.body); (window.__storyBodies = window.__storyBodies || []).push(window.__storyBody); window.__storyModel = window.__models[window.__models.length - 1]; window.__stories = (window.__stories || 0) + 1; out = { album: "Album thử", released: "13/2/2017", about: "Giới thiệu thử", origin: "Nguồn gốc thử", meaning: "Ý nghĩa thử", theories: ["Theory thử"], facts: ["Fact 1", "Fact 2"] }; }
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
window.__songWaitMs = 50;
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
    check("no songs yet: the add form opens straight away", page.locator("#sgTitle").count() == 1 and page.locator("#sgList").count() == 0)
    page.click("#sgBack"); page.wait_for_timeout(200)
    check("back from the empty add form goes to ARMY", page.locator("#arSongsOpen").count() == 1)
    page.click("#arSongsOpen"); page.wait_for_timeout(200)
    check("title is free text, no suggestion list", page.get_attribute("#sgTitle", "list") is None and page.locator("#sgTitles").count() == 0)
    page.fill("#sgTitle", "Test Song")
    page.click("#sgFind")
    check("finds lyrics on Google", page.evaluate("__opened[0]").startswith("https://www.google.com/search?q=BTS%20Test%20Song%20lyrics"), page.evaluate("__opened"))
    page.fill("#sgRaw", PASTE)
    page.click("#sgGo"); page.wait_for_selector(".sg-ly", timeout=5000); page.wait_for_timeout(200)
    page.screenshot(path=os.path.join(SP, "lyrics.png"), full_page=True)

    song = page.evaluate("JSON.parse(localStorage.getItem('hangulCards.v1')).songs[0]")
    check("analysing also writes the story", song.get("story", {}).get("album") == "Album thử" and page.evaluate("__stories") == 1, song.get("story"))
    texts = [l["t"] for l in song["lines"]]
    check("paste cleaned", texts == ["우리는 테스트 노래", "Hello test line", "노래를 불러요", "지민 줄", "슈가 줄", "뷔 줄", "마지막 줄이에요", "Last english line"], texts)
    check("no singers kept or asked", not any("who" in l for l in song["lines"]) and not any("sings" in p for p in page.evaluate("__prompts")), song["lines"][0])
    check("no singer chips or member colours", page.locator(".sg-who").count() == 0 and "Jimin" not in page.inner_text(".sg-ly"))
    check("sections split by headers", [l["sec"] for l in song["lines"]] == [1, 1, 2, 3, 4, 5, 6, 6], [l["sec"] for l in song["lines"]])
    check("hint no longer talks about singers", "ai hát" not in page.content())
    check("meanings on the model picked in Settings", set(page.evaluate("__models")) == {"gemini-2.5-flash"}, page.evaluate("__models"))
    rom = page.locator(".sg-r").all_inner_texts()
    check("romanization worked out on Korean lines", rom[:2] + rom[-1:] == ["urineun teseuteu norae", "noraereul bulleoyo", "majimak jurieyo"], rom)
    check("meanings filled", all(l["mean"] for l in song["lines"]), [l["mean"] for l in song["lines"]])
    check("blocked line falls back to Google Translate, others from AI", song["lines"][6]["mean"] == "dịch google" and song["lines"][0]["mean"].startswith("nghĩa") and page.evaluate("__free") <= 2,
          [l["mean"] for l in song["lines"]])
    pw_ = page.evaluate("__prompts")
    mean = next(p for p in pw_ if "translation of that line" in p)
    check("meaning prompt asks Vietnamese, no romanization", "Vietnamese translation" in mean and "rom" not in mean.split("Return")[0].lower().replace("from", ""))
    check("speaker only on Korean lines", page.locator(".sg-say").count() == 6)
    page.evaluate("() => { window.__said = []; speechSynthesis.speak = u => __said.push(u.text); }")
    page.locator(".sg-say").first.click(); page.wait_for_timeout(100)
    said = page.evaluate("__said")
    check("speaker reads the Korean line (or says no voice)", said == ["우리는 테스트 노래"] or "giọng" in page.inner_text("#toast"), said)

    # hide meaning layer
    page.click('.sg-layers button[data-k="m"]'); page.wait_for_timeout(150)
    check("meaning hidden", not page.locator(".sg-m").first.is_visible())
    page.click('.sg-layers button[data-k="m"]'); page.wait_for_timeout(150)

    # delete is an icon-only button
    check("delete button is icon only", page.inner_text("#sgDel").strip() == "" and page.locator("#sgDel svg").count() == 1 and "ico" in page.get_attribute("#sgDel", "class"))
    # analysing: the button says so, even after leaving the song and coming back
    page.click("#sgRedo"); page.wait_for_timeout(50)
    check("analyse button shows analysing", "Đang phân tích" in page.inner_text("#sgRedo") and page.is_disabled("#sgRedo"), page.inner_text("#sgRedo"))
    page.click("#sgBack"); page.wait_for_timeout(50); page.locator("#sgList li").first.click(); page.wait_for_timeout(50)
    check("still analysing after reopening", "Đang phân tích" in page.inner_text("#sgRedo") and page.is_disabled("#sgRedo"), page.inner_text("#sgRedo"))
    page.wait_for_function("!document.querySelector('#sgRedo').disabled", timeout=8000)
    check("button back to normal when done", "Phân tích lại" in page.inner_text("#sgRedo"), page.inner_text("#sgRedo"))

    # out of Gemini quota: the analysis still finishes, meanings from Google Translate
    before = page.evaluate("JSON.parse(localStorage.getItem('hangulCards.v1')).songs[0]")
    page.evaluate("() => { window.__quota = true; window.__free = 0; }")
    page.click("#sgRedo"); page.wait_for_function("!document.querySelector('#sgRedo').disabled", timeout=15000)
    song = page.evaluate("JSON.parse(localStorage.getItem('hangulCards.v1')).songs[0]")
    check("quota on re-analyse: old meanings kept, no Google needed", [l["mean"] for l in song["lines"]] == [l["mean"] for l in before["lines"]] and page.evaluate("__free") == 0 and not any("old" in l for l in song["lines"]), song["lines"])
    check("quota on re-analyse: done", "Phân tích lại" in page.inner_text("#sgRedo"))
    # a new song while out of quota: meanings from Google Translate, and it's done
    page.click("#sgBack"); page.click("#sgNew"); page.fill("#sgTitle", "Quota Song"); page.fill("#sgRaw", "[Verse 1]\n첫 줄\n둘째 줄")
    page.click("#sgGo"); page.wait_for_selector(".sg-ly", timeout=15000); page.wait_for_timeout(200)
    q = page.evaluate("JSON.parse(localStorage.getItem('hangulCards.v1')).songs.find(s => s.title === 'Quota Song')")
    check("quota: every line still gets a meaning", all(l["mean"] == "dịch google" for l in q["lines"]), q["lines"])
    check("quota: song counts as analysed", "Phân tích lại" in page.inner_text("#sgRedo"))
    page.evaluate("() => { window.__quota = false; }")
    page.click("#sgBack"); page.locator("#sgList li", has_text="Test Song").click(); page.wait_for_timeout(100)

    # story tab
    page.click('#sgTabs button[data-t="st"]'); page.wait_for_timeout(100)
    check("story already there, no extra tap", page.locator(".sg-h").count() > 0)
    check("re-analysing doesn't rewrite the story", page.evaluate("__stories") == 2)   # once per song: Test Song + Quota Song
    page.screenshot(path=os.path.join(SP, "story.png"), full_page=True)
    st = page.inner_text("#sgBody")
    check("story shows album and release date", "Album thử" in st and "phát hành 13/2/2017" in st, st)
    check("story prompt asks for album and release date", "are always required" in page.evaluate("__storyBody.contents[0].parts[0].text"))
    check("story on the model picked in Settings", page.evaluate("__storyModel") == "gemini-2.5-flash")
    sb = page.evaluate("__searchBody")
    check("story: step 1 searches Google for free-text notes", sb.get("tools") == [{"google_search": {}}] and sb["generationConfig"]["responseMimeType"] == "text/plain" and "research" in sb["contents"][0]["parts"][0]["text"])
    first = page.evaluate("__storyBodies[0]")   # Test Song's story, written while search worked
    check("story: step 2 writes the fields from the notes, without search", "tools" not in first and "NOTES: album Album thử" in first["contents"][0]["parts"][0]["text"] and "<notes>" in first["contents"][0]["parts"][0]["text"])
    check("story: saved as searched", page.evaluate("JSON.parse(localStorage.getItem('hangulCards.v1')).songs.find(s => s.title === 'Test Song').story.searched") is True)
    check("story from Google: normal note", "AI tổng hợp từ Google" in st)
    check("story shown", "Nguồn gốc thử" in st and "Fact 2" in st and "Theory thử" in st, st)
    # Google Search quota used up (plain calls still fine): the story is still written, and search is skipped next time
    page.evaluate("() => { window.__searchQuota = true; window.__stories = 0; }")
    page.click("#sgStory"); page.wait_for_function("__stories >= 1 && !document.querySelector('#sgStory').disabled", timeout=5000); page.wait_for_timeout(100)
    check("search quota: story still written from memory", page.evaluate("__stories") == 1 and "<notes>" not in page.evaluate("JSON.stringify(__storyBody)") and "Album thử" in page.inner_text("#sgBody"))
    check("search quota: the story says it wasn't searched", "chưa tra được Google" in page.inner_text("#sgBody"), page.inner_text("#sgBody"))
    page.evaluate("() => { window.__searchQuota = false; }")
    page.click("#sgStory"); page.wait_for_function("__stories >= 2 && !document.querySelector('#sgStory').disabled", timeout=5000); page.wait_for_timeout(100)
    check("search back: rewrite searches again", "chưa tra được Google" not in page.inner_text("#sgBody") and "<notes>" in page.evaluate("JSON.stringify(__storyBody)"))
    # the search prompt gives today's date and a few lyric lines, so a new (2026) song isn't mixed up with an older one
    sp = page.evaluate("__searchBody.contents[0].parts[0].text")
    import datetime
    check("search prompt: today's date + lyric lines + no other song", datetime.date.today().isoformat() in sp and "우리는 테스트 노래" in sp and "never another song" in sp, sp[:300])
    # the model answers without really searching: treated as not searched, asked twice, then written from memory with a warning
    page.evaluate("() => { window.__noGround = true; window.__searches = 0; }")
    page.click("#sgStory"); page.wait_for_function("!document.querySelector('#sgStory').disabled", timeout=5000); page.wait_for_timeout(100)
    check("no grounding: search tried twice, notes not trusted", page.evaluate("__searches") == 2 and "<notes>" not in page.evaluate("__storyBody.contents[0].parts[0].text") and "chưa tra được Google" in page.inner_text("#sgBody"))
    check("memory prompt forbids describing another song", "never describe a different song" in page.evaluate("__storyBody.contents[0].parts[0].text"))
    # AI doesn't know the song (memory only) → says so instead of telling another song's story
    page.evaluate("() => { window.__unknownSong = true; }")
    page.click("#sgStory"); page.wait_for_function("!document.querySelector('#sgStory').disabled", timeout=5000); page.wait_for_timeout(100)
    check("unknown new song: says so, no wrong story", "AI chưa biết bài này" in page.inner_text("#sgBody") and "Album thử" not in page.inner_text("#sgBody"), page.inner_text("#sgBody"))
    # Google finds no BTS song with this title → ask to check the title
    page.evaluate("() => { window.__noGround = false; window.__notFound = true; }")
    page.click("#sgStory"); page.wait_for_function("!document.querySelector('#sgStory').disabled", timeout=5000); page.wait_for_timeout(100)
    check("not found: asks to check the title", "Google không tìm thấy bài BTS nào tên này" in page.inner_text("#sgBody"), page.inner_text("#sgBody"))
    page.evaluate("() => { window.__notFound = false; window.__unknownSong = false; }")
    check("story prompt doesn't quote lyrics", "do not quote the lyrics" in page.evaluate("__prompts[__prompts.length-1]"))

    # survives a reload; list shows it
    page.reload(); page.wait_for_timeout(800)
    page.click('nav button[data-v="army"]'); page.click("#arSongsOpen"); page.wait_for_timeout(200)
    check("listed after reload", "Test Song" in page.inner_text("#sgList") and "Quota Song" in page.inner_text("#sgList"))
    check("no page errors", not errs, errs)
    b.close()

ok = all(r[1] for r in results)
for n, c, info in results: print(("✅" if c else "❌"), n, "" if c else info)
print("screenshots:", SP)
sys.exit(0 if ok else 1)
