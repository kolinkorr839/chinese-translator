"""
Browser — does the JS runtime behave correctly?

These tests load pages in headless Chromium via Playwright, intercept
network calls with canned responses, and assert on the resulting DOM.
Requires: pip install playwright && playwright install chromium

    python3 tests/run.py --browser
"""

from harness import check, Skip
import sitelib as s

_pw_module = None
try:
    from playwright.sync_api import sync_playwright
    _pw_module = sync_playwright
except ImportError:
    pass

_browser = None
_playwright = None


def _get_browser():
    global _browser, _playwright
    if _pw_module is None:
        raise Skip("playwright not installed (pip install playwright)")
    if _browser is None:
        _playwright = _pw_module().start()
        try:
            _browser = _playwright.chromium.launch()
        except Exception as e:
            _playwright.stop()
            _playwright = None
            raise Skip(f"chromium not available: {e}")
    return _browser


def _file_url(name):
    return (s.ROOT / name).as_uri()


# Canned Google Translate responses. The real API returns a nested array:
#   [[["translated","original",null,null,10]],null,"en",...]
# We only need data[0][i][0] to be correct.
_TRANSLATE = {
    ("en", "zh-TW", "bus"):    "公車",
    ("en", "zh-CN", "bus"):    "公共汽车",      # purposely differs in length
    ("zh-TW", "zh-CN", "公車"): "公共汽车",
    ("zh-CN", "zh-TW", "公共汽车"): "公車",
    ("auto", "en", "公共汽车"): "bus",
    ("zh-CN", "en", "公"):     "public",
    ("zh-CN", "en", "共"):     "common",
    ("zh-CN", "en", "汽"):     "steam",
    ("zh-CN", "en", "车"):     "vehicle",
    ("en", "zh-TW", "cat"):    "貓",
    ("en", "zh-CN", "cat"):    "猫",            # same length, different chars
    ("zh-TW", "zh-CN", "貓"):  "猫",
    ("zh-CN", "zh-TW", "猫"):  "貓",
    ("auto", "en", "猫"):      "cat",
    ("zh-CN", "en", "猫"):     "cat",
}


def _translate_response(sl, tl, q):
    """Build a fake Google Translate JSON response."""
    import json
    key = (sl, tl, q)
    text = _TRANSLATE.get(key, q)
    return json.dumps([[[text, q, None, None, 10]], None, sl])


def _setup_route(page):
    """Intercept Google Translate and pinyin-pro CDN requests."""
    import json
    from urllib.parse import urlparse, parse_qs

    def handle_translate(route):
        url = route.request.url
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        sl = params.get("sl", ["auto"])[0]
        tl = params.get("tl", ["en"])[0]
        q = params.get("q", [""])[0]
        body = _translate_response(sl, tl, q)
        route.fulfill(
            status=200,
            content_type="application/json",
            body=body,
        )

    def handle_pinyin_cdn(route):
        # Serve a minimal pinyin-pro stub that returns numbered pinyin.
        # The real library is complex; this stub covers getPinyin() usage.
        stub = """
        (function() {
            var table = {
                '公': 'gong1', '共': 'gong4', '汽': 'qi4', '车': 'che1',
                '公共汽车': 'gong1 gong4 qi4 che1',
                '公車': 'gong1 che1',
                '猫': 'mao1', '貓': 'mao1',
                '機': 'ji1', '机': 'ji1', '場': 'chang3', '场': 'chang3',
            };
            window.pinyinPro = {
                pinyin: function(text, opts) {
                    if (table[text]) return table[text].split(' ');
                    var result = [];
                    for (var i = 0; i < text.length; i++) {
                        result.push(table[text[i]] || text[i]);
                    }
                    return result;
                }
            };
        })();
        """
        route.fulfill(status=200, content_type="application/javascript", body=stub)

    def handle_tts(route):
        route.fulfill(status=200, content_type="audio/mpeg", body=b"")

    def handle_youdao_tts(route):
        route.fulfill(status=200, content_type="audio/mpeg", body=b"")

    page.route("**/translate.googleapis.com/**", handle_translate)
    page.route("**/cdn.jsdelivr.net/npm/pinyin-pro*", handle_pinyin_cdn)
    page.route("**/translate.google.com/translate_tts**", handle_tts)
    page.route("**/dict.youdao.com/**", handle_youdao_tts)


@check
def check_breakdown_uses_simplified_chars():
    """character breakdown iterates over simplified characters, not traditional"""
    browser = _get_browser()
    page = browser.new_page()
    try:
        _setup_route(page)
        page.goto(_file_url("mandarin_translation.html"))
        page.fill("#english-input", "bus")
        page.press("#english-input", "Enter")
        page.wait_for_selector("#breakdown-content .breakdown-item", timeout=5000)
        items = page.query_selector_all("#breakdown-content .breakdown-item")
        count = len(items)
        assert count == 4, (
            f"expected 4 breakdown items (one per simplified char in 公共汽车), "
            f"got {count}"
        )
    finally:
        page.close()
    return "公共汽车: 4 chars in breakdown"


@check
def check_breakdown_shows_simplified_before_traditional():
    """character breakdown shows simplified -> traditional (not reversed)"""
    browser = _get_browser()
    page = browser.new_page()
    try:
        _setup_route(page)
        page.goto(_file_url("mandarin_translation.html"))
        page.fill("#english-input", "cat")
        page.press("#english-input", "Enter")
        page.wait_for_selector("#breakdown-content .breakdown-item", timeout=5000)
        item = page.query_selector("#breakdown-content .breakdown-item")
        text = item.inner_text()
        assert "猫" in text and "貓" in text, f"expected both 猫 and 貓, got: {text}"
        html = item.inner_html()
        simp_pos = html.index("猫")
        trad_pos = html.index("貓")
        assert simp_pos < trad_pos, (
            f"simplified 猫 should appear before traditional 貓 in breakdown"
        )
    finally:
        page.close()
    return "猫 → 貓 (simplified first)"


@check
def check_etymology_headings_use_simplified():
    """etymology headings show simplified characters, not traditional"""
    import json

    browser = _get_browser()
    page = browser.new_page()
    try:
        _setup_route(page)

        def handle_gemini(route):
            etym = {
                "components": [],
                "meaning_logic": "Test stub.",
            }
            body = {"candidates": [{"content": {"parts": [{"text": json.dumps(etym)}]}}]}
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(body),
            )

        page.route("**/generativelanguage.googleapis.com/**", handle_gemini)
        page.goto(_file_url("mandarin_translation.html"))
        page.evaluate("localStorage.setItem('gemini_api_key', 'test-key')")
        page.reload()
        page.fill("#english-input", "bus")
        page.press("#english-input", "Enter")
        page.wait_for_selector("#etymology-content .etymology-char-heading", timeout=10000)
        headings = page.query_selector_all("#etymology-content .etymology-char-heading")
        chars = [h.inner_text().strip() for h in headings]
        assert chars == ["公", "共", "汽", "车"], (
            f"etymology headings should show simplified 公共汽车, got: {chars}"
        )
    finally:
        page.close()
    return "headings show 公, 共, 汽, 车 (simplified)"


@check
def check_flashcard_card_cycle():
    """flashcard deck shows prompt, reveals answer, then advances"""
    browser = _get_browser()
    page = browser.new_page()
    try:
        page.goto(_file_url("flashcards.html"))
        page.wait_for_selector(".english")
        prompt = page.inner_text(".english")
        assert prompt, "expected a prompt in .english"
        assert "revealed" not in page.get_attribute("#answer-area", "class"), \
            "answer-area should not be revealed initially"
        page.evaluate("revealAnswer()")
        assert "revealed" in page.get_attribute("#answer-area", "class"), \
            "answer-area should be revealed after revealAnswer()"
        simp = page.inner_text("#simp-char")
        assert simp, "expected text in #simp-char after reveal"
        page.evaluate("goNext()")
        assert "revealed" not in page.get_attribute("#answer-area", "class"), \
            "answer-area should reset after goNext()"
        new_prompt = page.inner_text(".english")
        assert new_prompt, "expected a new prompt after advancing"
    finally:
        page.close()
    return f"cycle: prompt '{prompt}' -> reveal '{simp}' -> next '{new_prompt}'"


@check
def check_flashcard_lesson_filtering():
    """applyRange filters flashcards to the selected lessons"""
    browser = _get_browser()
    page = browser.new_page()
    try:
        page.goto(_file_url("flashcards.html"))
        page.wait_for_selector("#progress")
        page.evaluate("""
            document.getElementById('range-input').value = '1';
            applyRange();
        """)
        progress1 = page.inner_text("#progress")
        assert "/ 14" in progress1, f"lesson 1 should have 14 phrases, got: {progress1}"
        page.evaluate("""
            document.getElementById('range-input').value = '3';
            applyRange();
        """)
        progress3 = page.inner_text("#progress")
        assert "/ 17" in progress3, f"lesson 3 should have 17 phrases, got: {progress3}"
    finally:
        page.close()
    return f"lesson 1: {progress1}, lesson 3: {progress3}"


@check
def check_flashcard_trouble_words():
    """starring a flashcard persists it and trouble-words mode filters to starred"""
    browser = _get_browser()
    page = browser.new_page()
    try:
        page.goto(_file_url("flashcards.html"))
        page.wait_for_selector(".english")
        page.evaluate("localStorage.removeItem('trouble-words')")
        page.evaluate("revealAnswer()")
        page.click("#star-btn")
        stored = page.evaluate("JSON.parse(localStorage.getItem('trouble-words') || '[]').length")
        assert stored == 1, f"expected 1 trouble word in localStorage, got {stored}"
        page.evaluate("selectTroubleWords()")
        progress = page.inner_text("#progress")
        assert "1 / 1" in progress, f"trouble-words mode should show 1/1, got: {progress}"
    finally:
        page.close()
    return "star persists, trouble-words mode shows 1 / 1"


@check
def check_hub_loads_default_page():
    """the hub creates an iframe for the default HOME page"""
    browser = _get_browser()
    page = browser.new_page()
    try:
        _setup_route(page)
        page.goto(_file_url("index.html"))
        page.wait_for_selector("#content iframe", timeout=5000)
        src = page.evaluate("""
            document.querySelector('#content iframe').getAttribute('src')
        """)
        assert "mandarin_translation.html" in src, \
            f"default iframe should load mandarin_translation.html, got: {src}"
    finally:
        page.close()
    return f"default iframe src: {src}"


@check
def check_hub_hash_routing():
    """navigating to index.html#flashcards.html loads the flashcards page"""
    browser = _get_browser()
    page = browser.new_page()
    try:
        page.goto(_file_url("index.html") + "#flashcards.html")
        page.wait_for_selector("#content iframe", timeout=5000)
        src = page.evaluate("""
            (() => {
                const frames = document.querySelectorAll('#content iframe');
                for (const f of frames) {
                    if (f.style.display !== 'none' && f.src.includes('flashcards.html'))
                        return f.src;
                }
                return '';
            })()
        """)
        assert "flashcards.html" in src, \
            f"hash routing should load flashcards.html, got: {src}"
    finally:
        page.close()
    return "hash route loaded flashcards.html"


@check
def check_translation_fallback_shows_via_label():
    """when primary translation fails, the via-label shows the fallback service"""
    browser = _get_browser()
    page = browser.new_page()
    try:
        _setup_route(page)
        page.route("**/api.laratranslate.com/**",
                    lambda route: route.fulfill(status=500, body="server error"))
        page.goto(_file_url("mandarin_translation.html"))
        page.fill("#english-input", "bus")
        page.press("#english-input", "Enter")
        page.wait_for_function(
            "document.getElementById('simplified-text').textContent.trim().length > 0"
            " && !document.getElementById('simplified-text').textContent.includes('...')",
            timeout=10000,
        )
        via = page.inner_text("#translation-via")
        assert "Google" in via, f"via-label should mention Google Translate, got: {via!r}"
        display = page.evaluate(
            "getComputedStyle(document.getElementById('translation-via')).display"
        )
        assert display != "none", "via-label should be visible"
    finally:
        page.close()
    return f"via-label: {via}"


@check
def check_postmessage_pauses_flashcard_deck():
    """posting mandarin-hub:hidden pauses a running flashcard deck"""
    browser = _get_browser()
    page = browser.new_page()
    try:
        page.goto(_file_url("flashcards.html"))
        page.wait_for_selector(".english")
        page.evaluate("togglePause()")
        running = page.evaluate("!paused")
        assert running, "deck should be running after togglePause()"
        page.evaluate("window.postMessage({ type: 'mandarin-hub:hidden' }, '*')")
        page.wait_for_function("paused === true", timeout=3000)
        paused = page.evaluate("paused")
        assert paused, "deck should be paused after mandarin-hub:hidden message"
    finally:
        page.close()
    return "postMessage paused the deck"
