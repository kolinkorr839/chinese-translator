"""
Endpoints — are the third-party services the site depends on still working?

LIVE tier: needs the network. Do NOT wire these into a pre-commit hook. They
depend on services you do not control, so they will eventually go red for
reasons that have nothing to do with your code — and a suite that cries wolf
is a suite that gets bypassed. Run them on a schedule, or before a release.
"""

import json
import time
import urllib.parse

from harness import check, Skip
import sitelib as s

TTS_URL = (
    "https://translate.google.com/translate_tts"
    "?ie=UTF-8&client=tw-ob&tl=zh-CN&q=" + urllib.parse.quote("水")
)

# Statuses that mean "the service is fine, you are just being throttled".
# These become SKIP rather than FAIL: a red suite you learn to ignore is worse
# than no suite, and rate limiting says nothing about whether the site works.
THROTTLED = {429, 503}


def _require_ok(response, what, retry=None):
    """
    Skip on throttling, fail on anything else that is not a 200.

    Google's public endpoints throttle per-IP and recover within seconds, so a
    single backoff-and-retry clears almost every 429 in practice. If it is still
    throttled after that, SKIP rather than FAIL — being rate limited says
    nothing about whether the site works, and a red suite you learn to ignore
    is worse than no suite.
    """
    if response.status in THROTTLED and retry is not None:
        time.sleep(3)
        response = retry()

    assert not response.error, f"{what} request failed: {response.error}"
    if response.status in THROTTLED:
        raise Skip(f"{what} returned HTTP {response.status} (rate limited) — retry later")
    assert response.status == 200, f"{what} expected 200, got {response.status}"
    return response


@check
def check_google_tts_serves_audio():
    """Google TTS returns audio when no Referer is sent"""
    r = _require_ok(s.http(TTS_URL), "TTS", retry=lambda: s.http(TTS_URL))
    assert "audio" in r.content_type, f"expected audio, got {r.content_type!r}"
    return f"{len(r.body)} bytes of {r.content_type}"


@check
def check_google_tts_still_blocks_on_referer():
    """Google TTS still 404s when a Referer IS sent"""
    # This is the canary for the no-referrer meta tag. If this check ever goes
    # green-on-200, Google has relaxed the restriction and the meta tag is no
    # longer load-bearing. If it starts 404ing *without* a Referer too, the
    # endpoint is gone and every TTS feature needs a new audio source.
    r = s.http(TTS_URL, headers={"Referer": s.LIVE_BASE + "/"})
    assert not r.error, f"request failed: {r.error}"
    assert r.status != 200, (
        "TTS now succeeds even with a Referer. The no-referrer meta may no "
        "longer be needed — re-verify before relying on that."
    )
    return f"blocked with HTTP {r.status}, as expected"


@check
def check_google_translate_api():
    """Google Translate returns 水 for 'water'"""
    url = ("https://translate.googleapis.com/translate_a/single"
           "?client=gtx&sl=en&tl=zh-CN&dt=t&q=water")
    r = _require_ok(s.http(url), "Translate", retry=lambda: s.http(url))
    assert "水" in r.text, f"expected 水 in the response, got: {r.text[:120]}"


@check
def check_handwriting_input_api():
    """Google inputtools accepts handwriting strokes"""
    payload = json.dumps({
        "options": "enable_pre_space",
        "requests": [{
            "writing_guide": {"writing_area_width": 250, "writing_area_height": 250},
            "ink": [[[50, 150, 250], [60, 120, 60]]],
            "pre_context": "",
            "max_num_results": 8,
            "max_completions": 0,
        }],
    }).encode()

    call = lambda: s.http(
        "https://inputtools.google.com/request?itc=zh-t-i0-handwrit&app=translate",
        method="POST", headers={"Content-Type": "application/json"}, data=payload,
    )
    r = _require_ok(call(), "inputtools", retry=call)
    assert "SUCCESS" in r.text, f"unexpected response: {r.text[:120]}"


@check
def check_pinyin_pro_cdn():
    """the pinyin-pro library is reachable on jsDelivr"""
    # Pinned in sw.js STATIC_ASSETS; read the URL from there so this check
    # follows any version bump automatically.
    urls = [a for a in s.sw_static_assets() if "pinyin-pro" in a]
    assert urls, "no pinyin-pro URL found in sw.js STATIC_ASSETS"
    r = s.http(urls[0])
    _require_ok(r, "jsDelivr")
    return f"{urls[0].split('/')[-3]} — {len(r.body)} bytes"


@check
def check_pinyin_chart_audio_sources():
    """both pinyin chart audio hosts are serving clips"""
    sources = {
        "yoyochinese": "https://cdn.yoyochinese.com/audio/pychart/a1.mp3",
        "zhongchinese": "https://zhongchinese.com/audio/zhuyin/tones/M_a.mp3",
    }
    problems, ok = [], []
    for label, url in sources.items():
        r = s.http(url)
        if r.error or r.status != 200 or "audio" not in r.content_type:
            problems.append(f"{label}: {r.error or f'HTTP {r.status} {r.content_type!r}'}")
        else:
            ok.append(f"{label} {len(r.body)}B")
    assert not problems, "audio sources failing:\n  " + "\n  ".join(problems)
    return ", ".join(ok)
