# Mandarin Hub

Static site for learning Mandarin. No build step, no package manager, nothing to install.

## Layout

- `index.html` — the hub. Sidebar nav loads every other page into an iframe. Hash-based
  routing (`#grammar_guide.html`) so deep links survive a refresh on GitHub Pages.
- One self-contained HTML file per page. Styles and scripts are inline; there are no
  shared CSS or JS files.
- `sw.js` — service worker. HTML is network-first so deploys appear on next load;
  other static assets are cache-first.
- `reference/` — source PDFs and scratch scripts. Not served, not linked from any page.

## Deploying

GitHub Pages serves `main` directly. Push to `main` is the deploy. No CI, no build step.

## Hard constraints

- **Must work from both `file://` and `https://`.** Opened from disk, iframes are
  cross-origin, so the hub talks to pages via `postMessage` — never `contentDocument`.
  Service workers don't run on `file://`; registration is guarded and fails silently.
- **Do not remove `<meta name="referrer" content="no-referrer">` from pages that play
  audio.** Google's TTS endpoint returns 404 when a Referer is sent and 200 without one.
  That meta tag is the only reason TTS works on the hosted origin.
- **Bump `CACHE_NAME` in `sw.js`** whenever `STATIC_ASSETS` changes. HTML doesn't need a
  bump (it's network-first); other assets do.
- **This repo is public** — it serves GitHub Pages. Never commit API keys or anything
  private. The Gemini key lives in the user's `localStorage`, entered at runtime.

## External services

Google Translate, Gemini (etymology enrichment), Google inputtools (handwriting),
pinyin-pro via jsDelivr, Google TTS plus yoyochinese/zhongchinese audio. All called
directly from the browser. All verified working from both origins.

## State

`localStorage`, which is per-origin — so `file://` and `https://` keep separate stores.
Keys: `gemini_api_key`, `etymology_cache`, `translation_cache`, `mandarin-hub-last`,
`mandarin-hub-speed`.

## Testing

Run the suite before declaring work complete:

```bash
python3 tests/run.py            # local tier — offline, deterministic, ~0.1s
python3 tests/run.py --live     # adds third-party endpoint + deploy checks
```

**This is not unittest or pytest.** It is a small custom harness (`@check`
decorators, see `tests/harness.py`). `python -m unittest discover tests/`
reports `Ran 0 tests ... OK` and exits 0 — a false green. Always use
`tests/run.py`.

- The **local tier** (structure, constraints, content) needs no network and can
  only fail because of something you changed. It is wired to
  `.git/hooks/pre-commit`, so it already runs on every commit.
- The **live tier** (endpoints, deploy) talks to Google, jsDelivr and GitHub
  Pages. Deliberately kept out of the hook — it fails for reasons unrelated to
  your commit. Run it after pushing, once Pages has rebuilt.
- Tests must pass. If one fails, fix the underlying issue — do not delete the
  check or widen an allowlist to force green. The one sanctioned allowlist is
  `KNOWN_MIXED` in `tests/test_content.py` (TODO item 5); entries come **out**
  of it as pages get fixed, never in.
- **A SKIP is not a failure.** Third-party throttling (429/503) skips by
  design, after one retry. Only fail on things you can actually fix.
- Re-run after changing any **site** file — HTML, `sw.js`, `manifest.json`.
  The Python files *are* the tests; the site is what they test.

Note git hooks are not version controlled. `.git/hooks/pre-commit` is local to
this machine and will not survive a fresh clone.

## TDD for new features

"Feature" here means a new page or behaviour — this is a static site, not a
Python library. Most relevant to the drills in TODO priority 1.

1. **Red** — add the checks first: the page in the hub nav, in `sw.js`
   `STATIC_ASSETS`, its data shape in `test_content.py`. Run and confirm they
   fail for the right reason (file missing, not an import error). Show the red.
2. **Green** — build the page until they pass. Show the green.
3. **Refactor (optional)** — clean up while it stays green.

Does not apply to doc changes or pure refactors, but those still need the local
tier green before claiming done.

## Secrets

There is no `.env` and no backend. This is a static site served straight from
`main`, so there is nowhere to put a secret the browser could not read anyway.

- The Gemini API key is entered by the user at runtime and lives in their
  `localStorage` under `gemini_api_key`. Never in a file, never in the repo.
- The repo is **public**. `test_constraints.py` scans every tracked file for
  key-shaped strings on each commit.
- Local-only files are excluded via `.git/info/exclude`, not `.gitignore` —
  they are personal working files, not things to hide from a clone. Currently
  `NOTES.local`, `CLAUDE.local.md`, `.claude/*`.

## Write Clean, Self-Documenting Code

Code is read far more often than it is written. Prioritize readability
over "clever" one-liners.

- **Meaningful Naming**: Use descriptive names for variables and functions
  (e.g., `calculate_total_price` instead of `ctp`).
- **Single Responsibility**: Each function or class should do one thing
  and do it well.
- **Avoid Over-Commenting**: If your code requires extensive comments to
  explain *what* it is doing, it likely needs a refactor. Use comments
  to explain *why* a complex decision was made.

## Embrace "DRY" and "KISS" Principles

- **DRY (Don't Repeat Yourself)**: Abstract repetitive logic into reusable
  functions or modules to make maintenance easier.
- **KISS (Keep It Simple, Stupid)**: Avoid over-engineering. Choose the
  simplest solution that meets the requirement.

## Security

- **Pin the CDN dependency.** Three files reference
  `cdn.jsdelivr.net/npm/pinyin-pro@3` — `mandarin_translation.html`,
  `simplified_traditional_flashcards.html` and `sw.js`. `@3` is a *floating*
  major version, so jsDelivr serves whatever the latest 3.x happens to be, and
  it runs with full access to the page. Pinning an exact `@3.x.y` in all three
  (and bumping `CACHE_NAME`) is the highest-value hardening step here.
- **Least privilege**: the site asks for nothing — no login, no cookies, no
  storage beyond `localStorage`. Keep it that way.
- Dependency scanning is moot: no package manager, no lockfile, no build. The
  one CDN script above is the entire third-party attack surface.
