# Chinese Translator

A side-by-side Traditional and Simplified Chinese translator with pinyin, pronunciation, and character breakdown.

## Install

### Computer

Visit the app at your GitHub Pages URL:

```
https://kolinkorr839.github.io/chinese-translator/
```

Bookmark it or, in Chrome, click the install icon in the address bar to install it as a desktop app.

### iPhone

1. Open the URL above in **Safari**
2. Tap the **Share** button (square with arrow)
3. Tap **Add to Home Screen**
4. The app appears on your home screen and opens full-screen like a native app

## How to use

### Translate from English

Type an English word (e.g. "rice", "tofu", "dragon") and press **Enter**. Three columns appear:

- **English** - your input
- **Traditional Chinese** - the Traditional Chinese translation with large characters
- **Simplified Chinese** - the Simplified Chinese translation

### Translate from Chinese

Type a Chinese character or word in either Traditional or Simplified (e.g. 說, 龙, 環境) and press **Enter**. The app auto-detects the input, fills in the other script, and shows the English meaning.

### Pinyin

Below each Chinese card, the pinyin appears in green using tone number format (e.g. shuo1, huan2 jing4). **Click the pinyin to hear the pronunciation.**

### Character Breakdown

Below the translation cards, a breakdown section shows:

- **Per-character meanings** - each character's individual English meaning (e.g. 豆腐: 豆 = bean, 腐 = rotten)
- **Traditional to Simplified mapping** - when a character differs between scripts, an arrow shows the mapping (e.g. 頭 -> 头)
- **Component decomposition** - for single-character lookups, the app shows the structural components and their meanings (e.g. 說 = 言 speech + 兌 exchange), including how radicals simplify (e.g. 言 -> 讠)

## Development

No build step, no package manager. The site is static HTML served by GitHub Pages from `main`.

### Testing

Tests use a custom harness (not unittest/pytest). A virtualenv at `.venv/` has Playwright installed for browser tests.

```bash
# Local tests only - offline, deterministic, ~0.1s
.venv/bin/python3 tests/run.py

# Local + browser tests via headless Chromium (~7s)
.venv/bin/python3 tests/run.py --browser

# All tests including live endpoint and deploy checks
.venv/bin/python3 tests/run.py --browser --live
```

The local tier runs automatically on every commit via a pre-commit hook. The `--live` tier hits external services (Google, jsDelivr, GitHub Pages) so run it after pushing, not before.

### Virtualenv setup

If `.venv/` doesn't exist (fresh clone):

```bash
python3 -m venv .venv
.venv/bin/pip install playwright
.venv/bin/python3 -m playwright install chromium
```

### Deploying

Push to `main`. GitHub Pages serves the repo directly - no CI, no build step.
