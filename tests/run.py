#!/usr/bin/env python3
"""
Regression tests for Mandarin Hub.

Standard library only — no pip install, no browser, nothing to set up.

    python3 tests/run.py            # local checks: fast, offline, deterministic
    python3 tests/run.py --live     # local + network (third-party APIs, deploy)
    python3 tests/run.py --only content
    python3 tests/run.py --no-colour

Exit code is 0 when everything passes, 1 otherwise — so it works as a
pre-commit hook or a CI step.
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import harness  # noqa: E402

# (name, module path, tier). Order here is the order results are printed.
MODULES = [
    ("structure",   "test_structure",   "local"),
    ("constraints", "test_constraints", "local"),
    ("content",     "test_content",     "local"),
    ("endpoints",   "test_endpoints",   "live"),
    ("deploy",      "test_deploy",      "live"),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--live", action="store_true",
                    help="also run the network-dependent checks")
    ap.add_argument("--only", metavar="NAME",
                    help="run a single module (e.g. content)")
    ap.add_argument("--no-colour", action="store_true", help="plain output")
    args = ap.parse_args()

    selected = []
    for name, path, tier in MODULES:
        if args.only and name != args.only:
            continue
        if tier == "live" and not (args.live or args.only == name):
            continue
        selected.append(path)

    if not selected:
        known = ", ".join(n for n, _, _ in MODULES)
        print(f"nothing to run. --only takes one of: {known}")
        return 2

    modules = [__import__(path) for path in selected]

    use_colour = not args.no_colour and sys.stdout.isatty()
    started = time.time()
    results = harness.run(modules, use_colour)
    return harness.summarise(results, time.time() - started, use_colour)


if __name__ == "__main__":
    sys.exit(main())
