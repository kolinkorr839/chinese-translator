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
