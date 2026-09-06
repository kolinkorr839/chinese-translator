"""
Shared helpers for the site tests.

Standard library only — no pip install, matching the project's "nothing to
install" rule in CLAUDE.md.
"""

import hashlib
import json
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE_BASE = "https://kolinkorr839.github.io/chinese-translator"

# Some endpoints behave differently for non-browser clients, so present a
# normal browser UA everywhere.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------- local files

def read(name):
    """Contents of a file in the repo root."""
    return (ROOT / name).read_text(encoding="utf-8")


def html_files():
    """Every .html file in the repo root, sorted."""
    return sorted(p.name for p in ROOT.glob("*.html"))


def nav_pages():
    """The pages the hub sidebar can load, in sidebar order."""
    return re.findall(r'data-page="([^"]+)"', read("index.html"))


def hub_home_page():
    """The page the hub falls back to (the HOME const in index.html)."""
    m = re.search(r"const HOME\s*=\s*['\"]([^'\"]+)['\"]", read("index.html"))
    return m.group(1) if m else None


def sw_cache_name(source=None):
    """The CACHE_NAME string in sw.js."""
    src = source if source is not None else read("sw.js")
    m = re.search(r"const CACHE_NAME\s*=\s*['\"]([^'\"]+)['\"]", src)
    return m.group(1) if m else None


def sw_static_assets(source=None):
    """The STATIC_ASSETS list in sw.js, as written (may include CDN URLs)."""
    src = source if source is not None else read("sw.js")
    m = re.search(r"const STATIC_ASSETS\s*=\s*\[(.*?)\];", src, re.S)
    if not m:
        return []
    return re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))


def phrase_data():
    """
    The lesson/phrase data powering the flashcards.

    Lives as `const DATA = [...]` inside mandarin_flashcards.html. It is valid
    JSON today; if that ever stops being true this raises and the content tests
    fail loudly, which is the point.

    NOTE: once TODO item 3 lands (single source of truth in data/phrases.js),
    point this at that file instead — it is the only place that needs changing.
    """
    src = read("mandarin_flashcards.html")
    m = re.search(r"const DATA = (\[.*?\]);\n", src, re.S)
    if not m:
        raise AssertionError("could not find `const DATA = [...]` in mandarin_flashcards.html")
    return json.loads(m.group(1))


def iter_phrases():
    """Yield (lesson_title, section_title, phrase_dict) for every phrase."""
    for lesson in phrase_data():
        for section in lesson.get("sections", []):
            for phrase in section.get("phrases", []):
                yield lesson.get("title", "?"), section.get("title", "?"), phrase


# ------------------------------------------------------------------------ git

def git(*args):
    """Run a git command in the repo. Returns stdout, or None if it failed."""
    try:
        out = subprocess.run(
            ["git", *args], cwd=ROOT,
            capture_output=True, text=True, timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


def tracked_files():
    """Files tracked by git, as repo-relative paths."""
    out = git("ls-files")
    return out.splitlines() if out else []


# ----------------------------------------------------------------------- http

class Response:
    __slots__ = ("status", "content_type", "body", "error")

    def __init__(self, status, content_type, body, error=None):
        self.status = status
        self.content_type = content_type
        self.body = body
        self.error = error

    @property
    def text(self):
        return self.body.decode("utf-8", "replace")


def http(url, method="GET", headers=None, data=None, timeout=25):
    """
    Fetch a URL. Never raises for HTTP status — a 404 comes back as a Response
    with status 404, because several checks assert on non-200 statuses.
    """
    hdrs = {"User-Agent": USER_AGENT}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, method=method, headers=hdrs, data=data)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return Response(resp.status, resp.headers.get("Content-Type", ""), resp.read())
    except urllib.error.HTTPError as e:
        return Response(e.code, e.headers.get("Content-Type", "") if e.headers else "", e.read())
    except Exception as e:                       # DNS, TLS, timeout, offline
        return Response(0, "", b"", error=f"{type(e).__name__}: {e}")


def sha256(data):
    return hashlib.sha256(data).hexdigest()
