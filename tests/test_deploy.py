"""
Deploy — is what GitHub Pages serves actually what is in the repo?

LIVE tier: needs the network. This is the single best "did my deploy ship?"
signal. A push triggers an async Pages build, so run it a minute or two after
pushing, not immediately.

Scope is the site itself. Docs (README, TODO, CLAUDE.md) are served but are
not the site, and reference/ holds source PDFs no page links to — comparing
those would just make the check noisy about unpushed doc commits.
"""

from harness import check, Skip
import sitelib as s

DOCS = {"README.md", "TODO", "CLAUDE.md"}
SITE_SUFFIXES = {".html", ".js", ".json", ".png", ".ico", ".css", ".svg"}


def _site_files():
    """Tracked files that GitHub Pages actually serves as the site."""
    out = []
    for rel in s.tracked_files():
        if rel in DOCS or rel.startswith(("reference/", "tests/", ".")):
            continue
        if (s.ROOT / rel).suffix.lower() in SITE_SUFFIXES:
            out.append(rel)
    return sorted(out)


@check
def check_site_root_serves_the_hub():
    """the deployed root serves the Mandarin Hub"""
    r = s.http(s.LIVE_BASE + "/")
    assert not r.error, f"request failed: {r.error}"
    assert r.status == 200, f"expected 200, got {r.status}"
    assert "Mandarin Hub" in r.text, "the deployed root does not look like the hub"


@check
def check_deployed_files_match_local():
    """every deployed site file is byte-identical to the local copy"""
    files = _site_files()
    if not files:
        raise Skip("no tracked site files found (not a git checkout?)")

    missing, differing = [], []
    for rel in files:
        r = s.http(f"{s.LIVE_BASE}/{rel}")
        if r.error:
            raise Skip(f"network problem fetching {rel}: {r.error}")
        if r.status != 200:
            missing.append(f"{rel} (HTTP {r.status})")
            continue
        if s.sha256(r.body) != s.sha256((s.ROOT / rel).read_bytes()):
            differing.append(rel)

    problems = []
    if missing:
        problems.append("not served:\n  " + "\n  ".join(missing))
    if differing:
        problems.append(
            "differ from local:\n  " + "\n  ".join(differing) +
            "\nUsually one of: unpushed commits, a Pages build still running, "
            "or local edits you have not committed."
        )
    assert not problems, "\n".join(problems)
    return f"{len(files)} files identical"


@check
def check_service_worker_is_served():
    """sw.js is served and advertises the current CACHE_NAME"""
    r = s.http(f"{s.LIVE_BASE}/sw.js")
    assert not r.error, f"request failed: {r.error}"
    assert r.status == 200, f"expected 200, got {r.status}"

    deployed = s.sw_cache_name(r.text)
    local = s.sw_cache_name()
    assert deployed == local, (
        f"deployed CACHE_NAME is {deployed!r} but local is {local!r} — "
        "the new service worker has not shipped yet."
    )
    return deployed
