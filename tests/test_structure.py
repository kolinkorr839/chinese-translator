"""
Structure — does everything the site references actually exist?

These catch the classic static-site break: a page gets renamed or deleted and
the sidebar link, or the service worker's precache list, still points at the
old name. Offline and fast.
"""

from harness import check
import sitelib as s


@check
def check_nav_targets_exist():
    """every sidebar nav target resolves to a real file"""
    missing = [p for p in s.nav_pages() if not (s.ROOT / p).is_file()]
    assert not missing, f"index.html links to files that do not exist: {missing}"
    return f"{len(s.nav_pages())} nav entries"


@check
def check_home_page_exists():
    """the hub's HOME fallback page exists"""
    home = s.hub_home_page()
    assert home, "could not find `const HOME = ...` in index.html"
    assert (s.ROOT / home).is_file(), f"HOME points at a missing file: {home}"
    return home


@check
def check_sw_precached_assets_exist():
    """every local file in the service worker's precache list exists"""
    local = [a for a in s.sw_static_assets() if not a.startswith("http")]
    missing = [a for a in local if not (s.ROOT / a.lstrip("./")).is_file()]
    assert not missing, (
        f"sw.js STATIC_ASSETS references missing files: {missing}\n"
        "Either restore them or remove the entries, then bump CACHE_NAME."
    )
    return f"{len(local)} local assets"


@check
def check_sw_precaches_every_nav_page():
    """every page reachable from the sidebar is precached for offline use"""
    precached = {a.lstrip("./") for a in s.sw_static_assets()}
    absent = [p for p in s.nav_pages() if p not in precached]
    assert not absent, (
        f"pages reachable from the hub but missing from sw.js STATIC_ASSETS: {absent}\n"
        "They will not work offline or in the installed PWA. Add them and bump CACHE_NAME."
    )


@check
def check_manifest_icons_exist():
    """PWA manifest icons exist on disk"""
    import json
    manifest = json.loads(s.read("manifest.json"))
    missing = [i["src"] for i in manifest.get("icons", [])
               if not (s.ROOT / i["src"]).is_file()]
    assert not missing, f"manifest.json references missing icons: {missing}"


@check
def check_manifest_start_url_exists():
    """PWA manifest start_url points at a real page"""
    import json
    start = json.loads(s.read("manifest.json")).get("start_url", "")
    target = start.lstrip("./") or "index.html"
    assert (s.ROOT / target).is_file(), f"manifest start_url points at a missing file: {start}"
    return start
