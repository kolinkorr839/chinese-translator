# Tests

Regression tests for Mandarin Hub. **Standard library Python only** — no `pip install`,
no browser, nothing to set up. That's deliberate: the project's rule is "no build step,
no package manager, nothing to install", and the tests follow it.

## Running

```bash
python3 tests/run.py            # local checks — fast, offline, deterministic
python3 tests/run.py --live     # adds network checks (third-party APIs + deploy)
python3 tests/run.py --only content
```

Exit code is 0 when everything passes, 1 otherwise, so it drops straight into a
pre-commit hook or a CI step.

## The two tiers, and why they're separate

**Local** (`structure`, `constraints`, `content`) runs in about a tenth of a second,
needs no network, and can only fail because of something you changed. Safe to run on
every commit.

**Live** (`endpoints`, `deploy`) talks to Google, jsDelivr and GitHub Pages. These will
eventually go red for reasons that have nothing to do with your code — an API rate
limit, a CDN hiccup, a Pages build still in flight. Keep them **out of your pre-commit
hook.** A suite that cries wolf is a suite you learn to bypass, and then it protects
nothing. Run them before a release, or on a schedule.

Throttling responses (429, 503) are reported as SKIP rather than FAIL, for the same
reason: being rate-limited says nothing about whether the site works.

## What's in each file

| File | What it protects |
|---|---|
| `test_structure.py` | Every sidebar link, precache entry and manifest icon points at a file that exists. Catches renames and deletions. |
| `test_constraints.py` | The invisible rules from `CLAUDE.md` — see below. |
| `test_content.py` | The 227 phrases are well-formed; prose pages don't mix traditional and simplified. |
| `test_endpoints.py` | The third-party services the site depends on are still up and still behave as assumed. |
| `test_deploy.py` | What GitHub Pages serves is byte-identical to the repo. |
| `harness.py` | The tiny runner. `@check`, `Skip`, result printing. |
| `sitelib.py` | Shared helpers — file reading, parsing `sw.js` and the phrase data, HTTP, git. |

## Why `constraints` matters most

Every check in `test_constraints.py` guards something that **fails silently**. Nothing
looks broken; audio just stops working, or returning visitors stop getting updates, or
the site breaks only when opened from disk. You will not catch these by looking at the
page — which is exactly why they're worth automating.

- **`no-referrer` meta on TTS pages.** Google's TTS endpoint returns 200 with no
  `Referer` and 404 with one. That meta tag is the only reason audio works on the
  hosted origin. Tidy it away and audio dies quietly.
- **`CACHE_NAME` bumped when `STATIC_ASSETS` changes.** Miss this and returning
  visitors keep the stale precache indefinitely.
- **Guarded service worker registration.** Service workers don't exist on `file://`;
  an unguarded `register()` throws there and takes the hub's startup script with it.
- **No `.contentDocument` in the hub.** Opened from `file://`, iframes get opaque
  origins and `contentDocument` is `null`. Reaching into a frame works on https and
  breaks silently on disk.
- **No API keys committed.** The repo is public and serves Pages.

`test_endpoints.py` has a matching canary: it asserts TTS *still 404s when a Referer
is sent*. If that ever starts passing with a 200, Google has relaxed the restriction
and the meta tag is no longer load-bearing.

## Known-failing by design

`test_content.py` carries a `KNOWN_MIXED` allowlist for the two prose pages that mix
traditional and simplified today (`mandarin_in_14_days.html`, `grammar_guide.html`) —
that's TODO item 5. The check reports them as a note instead of failing, and a second
check makes sure the allowlist doesn't rot: **once you normalise a page, delete it
from `KNOWN_MIXED`** and the check starts protecting it.

## What isn't covered

No browser, so nothing here exercises: hash routing on click, iframes actually loading,
the translator end-to-end, or console-error-free. That's a deliberate trade. All of it
lives in ~100 lines of routing JS that changes rarely, and when it breaks **nothing
loads at all** — the loudest possible failure. The silent failures are the ones
automated here.

If you later want the browser layer covered, Playwright is the tool (it loads `file://`
URLs natively, which most automation can't). Worth revisiting once the listening,
production and transform drills exist, since those will have real card-sequencing state
machines. Not before.

## Adding a check

Write a function in the relevant module, decorate it with `@check`, and give it a
one-line docstring — that docstring is what gets printed. Raise `AssertionError` (a
bare `assert`) to fail, raise `Skip` to skip, return a string to attach a note.

```python
@check
def check_something_useful():
    """a one-line description, shown in the output"""
    assert condition, "what went wrong and what to do about it"
    return "optional note, e.g. a measured value"
```

Failure messages should say what to *do*, not just what's wrong. Compare
`"expected 200, got 404"` with `"add the meta tag or audio will 404 on the hosted
origin"` — the second one saves you the investigation.
