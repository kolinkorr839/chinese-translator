"""
Constraints — the invisible rules from CLAUDE.md.

Every check here guards something that fails SILENTLY. Nothing looks broken;
audio just stops working, or the page stops updating, or the site breaks only
when opened from disk. Those are exactly the regressions worth automating,
because you will not notice them by looking at the site.
"""

import re

from harness import check, Skip
import sitelib as s


@check
def check_tts_pages_declare_no_referrer():
    """pages using Google TTS declare <meta name="referrer" content="no-referrer">"""
    # Verified behaviour: translate_tts returns 200 audio/mpeg with no Referer
    # and 404 when one is sent. The meta tag is the only reason audio works on
    # the hosted origin — delete it and TTS dies quietly.
    meta = '<meta name="referrer" content="no-referrer">'
    offenders = []
    for name in s.html_files():
        src = s.read(name)
        if "translate_tts" in src and meta not in src:
            offenders.append(name)
    assert not offenders, (
        f"these pages call Google TTS but do not suppress the Referer: {offenders}\n"
        f"Add {meta} to <head> or audio will 404 on the hosted origin."
    )


@check
def check_cache_name_bumped_when_precache_list_changes():
    """CACHE_NAME is bumped whenever STATIC_ASSETS changes"""
    committed = s.git("show", "HEAD:sw.js")
    if committed is None:
        raise Skip("no committed sw.js to compare against")

    if s.sw_static_assets(committed) == s.sw_static_assets():
        return "precache list unchanged"

    old, new = s.sw_cache_name(committed), s.sw_cache_name()
    assert old != new, (
        f"STATIC_ASSETS changed but CACHE_NAME is still {new!r}.\n"
        "Returning visitors keep the stale precache. Bump it (e.g. -v5)."
    )
    return f"precache changed, CACHE_NAME {old} -> {new}"


@check
def check_service_worker_registration_is_guarded():
    """service worker registration is feature-guarded and catches failure"""
    # Service workers do not exist on file://. An unguarded register() throws
    # there and takes the rest of the hub's startup script with it.
    src = s.read("index.html")
    assert "if ('serviceWorker' in navigator)" in src, \
        "index.html must guard registration with `if ('serviceWorker' in navigator)`"
    assert re.search(r"register\([^)]*\)\s*(\.then\([^)]*\)\s*)?\.catch\(", src), \
        "the register() call needs a .catch() — it rejects on file:// and unsupported browsers"


@check
def check_hub_does_not_reach_into_frames():
    """the hub talks to pages via postMessage, never contentDocument"""
    # Opened from file://, iframes get opaque origins and contentDocument is
    # null. Anything reaching into a frame directly works on https and breaks
    # silently on disk.
    src = s.read("index.html")
    # Dot-prefixed so the explanatory comment in index.html is not a false hit.
    hits = re.findall(r"\.contentDocument\b", src)
    assert not hits, (
        "index.html accesses .contentDocument, which is null when the site is "
        "opened from file://. Use postMessage instead."
    )
    assert "postMessage(" in src, "the hub should signal pages via postMessage"


@check
def check_no_api_keys_in_tracked_files():
    """no API keys committed to this public repo"""
    # The repo is public and serves GitHub Pages. The Gemini key belongs in
    # localStorage, entered at runtime — never in a file.
    patterns = {
        "Google/Gemini API key": r"AIza[0-9A-Za-z_\-]{35}",
        "OpenAI key": r"sk-[A-Za-z0-9]{20,}",
        "generic assignment": r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{24,}['\"]",
    }
    found = []
    for rel in s.tracked_files():
        path = s.ROOT / rel
        if not path.is_file() or path.suffix.lower() in {".png", ".pdf", ".jpg", ".ico"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for label, pat in patterns.items():
            if re.search(pat, text):
                found.append(f"{rel}: looks like a {label}")

    assert not found, "possible secrets in tracked files:\n  " + "\n  ".join(found)
    return f"scanned {len(s.tracked_files())} tracked files"
