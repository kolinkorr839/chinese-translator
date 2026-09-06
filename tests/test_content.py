"""
Content — is the learning material itself well-formed?

The phrase data drives the flashcards today and will drive the course and the
new drills once TODO item 3 lands, so a malformed entry propagates everywhere.
The script-consistency check enforces TODO item 5.
"""

from harness import check
import sitelib as s


# Pages that legitimately show traditional AND simplified side by side: the
# S/T teaching material, and any deck carrying both fields or a script toggle.
BILINGUAL_BY_DESIGN = {
    "simplified_to_traditional_guide.html",
    "simplified_to_traditional_cheat_sheet.html",
    "simplified_traditional_flashcards.html",
    "phrase_reference.html",
    "flashcards.html",
    "grammar_flashcards.html",
    "mandarin_translation.html",
}

# Prose pages known to mix scripts today. This is TODO item 5.
# When you normalise a page to simplified, DELETE it from this set — the check
# then starts enforcing it and stops the mixing coming back.
KNOWN_MIXED = {
    "mandarin_in_14_days.html",
    "grammar_guide.html",
}

# A small sample of high-frequency characters that differ between scripts.
# Not exhaustive — enough to detect drift reliably.
SCRIPT_PAIRS = [
    ("這", "这"), ("們", "们"), ("學", "学"), ("說", "说"), ("會", "会"),
    ("個", "个"), ("來", "来"), ("時", "时"), ("對", "对"), ("開", "开"),
    ("樣", "样"), ("點", "点"), ("錢", "钱"), ("買", "买"), ("賣", "卖"),
]


@check
def check_phrase_data_parses():
    """the flashcard phrase data parses as JSON"""
    data = s.phrase_data()
    assert data, "phrase data is empty"
    total = sum(1 for _ in s.iter_phrases())
    return f"{len(data)} lessons, {total} phrases"


@check
def check_every_phrase_has_all_fields():
    """every phrase has non-empty trad, simp, pinyin and meaning"""
    bad = []
    for lesson, section, p in s.iter_phrases():
        for field in ("trad", "simp", "pinyin", "meaning"):
            if not str(p.get(field, "")).strip():
                bad.append(f"{lesson} / {section}: {p.get('simp') or p.get('trad') or '?'} missing {field!r}")
    assert not bad, "incomplete phrases:\n  " + "\n  ".join(bad[:20])


@check
def check_no_duplicate_phrases_within_a_lesson():
    """no phrase is repeated inside the same lesson"""
    dupes = []
    for lesson in s.phrase_data():
        seen = set()
        for section in lesson.get("sections", []):
            for p in section.get("phrases", []):
                key = p.get("simp", "")
                if key and key in seen:
                    dupes.append(f"{lesson.get('title')}: {key}")
                seen.add(key)
    assert not dupes, "duplicated phrases:\n  " + "\n  ".join(dupes)


@check
def check_pinyin_has_no_stray_whitespace():
    """pinyin fields are not padded or double-spaced"""
    bad = []
    for lesson, _section, p in s.iter_phrases():
        py = p.get("pinyin", "")
        if py != py.strip() or "  " in py:
            bad.append(f"{lesson}: {p.get('simp')} -> {py!r}")
    assert not bad, "pinyin needs tidying:\n  " + "\n  ".join(bad[:20])


@check
def check_script_consistency():
    """prose pages do not mix traditional and simplified characters"""
    # The student reads traditional but is learning simplified for mainland
    # China. A page that mixes both makes an already-fragile foothold worse.
    newly_mixed, still_mixed = [], []

    for name in s.html_files():
        if name in BILINGUAL_BY_DESIGN:
            continue
        src = s.read(name)
        mixed = [f"{t}x{src.count(t)}/{simp}x{src.count(simp)}"
                 for t, simp in SCRIPT_PAIRS
                 if src.count(t) and src.count(simp)]
        if not mixed:
            continue
        entry = f"{name}: {', '.join(mixed)}"
        (still_mixed if name in KNOWN_MIXED else newly_mixed).append(entry)

    assert not newly_mixed, (
        "these pages newly mix scripts:\n  " + "\n  ".join(newly_mixed) +
        "\nNormalise to simplified, or add to BILINGUAL_BY_DESIGN if intentional."
    )
    if still_mixed:
        return "known, tracked as TODO item 5:\n" + "\n".join("  " + m for m in still_mixed)


@check
def check_known_mixed_list_is_current():
    """the KNOWN_MIXED allowlist has no stale entries"""
    # If a page has been cleaned up, drop it from KNOWN_MIXED so the check
    # starts protecting it. This stops the allowlist rotting.
    stale = []
    for name in sorted(KNOWN_MIXED):
        if not (s.ROOT / name).is_file():
            stale.append(f"{name} (file no longer exists)")
            continue
        src = s.read(name)
        if not any(src.count(t) and src.count(simp) for t, simp in SCRIPT_PAIRS):
            stale.append(f"{name} (now consistent — remove it from KNOWN_MIXED)")
    assert not stale, "stale KNOWN_MIXED entries:\n  " + "\n  ".join(stale)
