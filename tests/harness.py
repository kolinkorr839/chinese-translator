"""
A very small check runner. Standard library only.

Each test module defines functions decorated with @check. The function's
docstring is its description. To fail a check, raise AssertionError (a bare
`assert` does this). To skip one, raise Skip. Returning a string attaches a
note to the result, which is handy for reporting measured values.
"""

import time
import traceback

# Populated at import time, in import order, so output order is predictable.
_CHECKS = []

PASS, FAIL, SKIP, ERROR = "PASS", "FAIL", "SKIP", "ERROR"

_COLOURS = {PASS: "\033[32m", FAIL: "\033[31m", SKIP: "\033[33m", ERROR: "\033[31m"}
_RESET = "\033[0m"


class Skip(Exception):
    """Raise to skip a check (missing credentials, not a git repo, ...)."""


def check(fn):
    """Register a function as a check."""
    _CHECKS.append(fn)
    return fn


class Result:
    __slots__ = ("module", "name", "status", "note")

    def __init__(self, module, name, status, note=""):
        self.module = module
        self.name = name
        self.status = status
        self.note = note


def _describe(fn):
    doc = (fn.__doc__ or fn.__name__).strip().splitlines()[0].strip()
    return doc


def run(modules, use_colour=True):
    """Run every check registered by the given modules. Returns a list of Results."""
    results = []
    for module in modules:
        registered = [fn for fn in _CHECKS if fn.__module__ == module.__name__]
        if not registered:
            continue

        label = module.__name__.replace("test_", "")
        print(f"\n\033[1m{label}\033[0m" if use_colour else f"\n{label}")
        print("─" * (len(label) + 2))

        for fn in registered:
            name = _describe(fn)
            try:
                note = fn() or ""
                status = PASS
            except Skip as e:
                status, note = SKIP, str(e)
            except AssertionError as e:
                status, note = FAIL, str(e) or "assertion failed"
            except Exception:
                status, note = ERROR, traceback.format_exc(limit=3).strip().splitlines()[-1]

            results.append(Result(module.__name__, name, status, note))
            _print_result(status, name, note, use_colour)

    return results


def _print_result(status, name, note, use_colour):
    tag = f"{_COLOURS[status]}{status:<5}{_RESET}" if use_colour else f"{status:<5}"
    print(f"  {tag}  {name}")
    if note:
        for line in str(note).splitlines():
            print(f"           {line}")


def summarise(results, elapsed, use_colour=True):
    """Print the tally. Returns a process exit code."""
    counts = {PASS: 0, FAIL: 0, SKIP: 0, ERROR: 0}
    for r in results:
        counts[r.status] += 1

    parts = [f"{counts[PASS]} passed"]
    if counts[FAIL]:
        parts.append(f"{counts[FAIL]} failed")
    if counts[ERROR]:
        parts.append(f"{counts[ERROR]} errored")
    if counts[SKIP]:
        parts.append(f"{counts[SKIP]} skipped")

    line = f"{', '.join(parts)}   ({elapsed:.1f}s)"
    bad = counts[FAIL] + counts[ERROR]
    if use_colour:
        # Not inlined into the f-string: backslash escapes inside f-string
        # expressions are a syntax error before Python 3.12.
        colour = _COLOURS[FAIL] if bad else _COLOURS[PASS]
        line = f"{colour}{line}{_RESET}"
    print(f"\n{line}")

    if bad:
        print("\nFailed:")
        for r in results:
            if r.status in (FAIL, ERROR):
                print(f"  - [{r.module.replace('test_', '')}] {r.name}")

    return 1 if bad else 0
