#!/usr/bin/env python3
"""check_buildlog.py — validate canon/build_log.json against the loader's contract.

THIS CHECK EXISTS BECAUSE ITS ABSENCE SHIPPED A 500. A build-log entry set its
usage token counts to null, but lib/buildlog.ts's zod schema only allowed null for
one field. The homepage loads the build log at request time and THROWS on a schema
violation — so every page view 500'd. It slipped through:

  - `npm run build` — the homepage is dynamic, so it validates on request, not at
    build. A clean build proved nothing.
  - `check_canon.py` — it asserts things about data/canon.json, and the build log
    deliberately does not flow through that pipeline.

Nobody was validating the build log until a human hit the broken page. This closes
that: the same shape the app enforces, enforced in the battery, so a bad log fails
here instead of in Shawn's browser.

It mirrors lib/buildlog.ts intentionally. If that schema changes, this changes with
it — the point is that the two agree, checked in CI-time rather than at 2am.

Run: python3 scripts/check_buildlog.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "canon" / "build_log.json"

results: list[tuple[bool, str]] = []


def check(ok: bool, label: str) -> None:
    results.append((ok, label))


def is_nonneg_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def main() -> int:
    try:
        doc = json.loads(LOG.read_text())
    except Exception as e:  # noqa: BLE001
        print(f"  FAIL  build_log.json does not parse: {e}")
        return 1

    check(isinstance(doc.get("entries"), list), "top level has an entries array")
    entries = doc.get("entries") or []
    check(len(entries) > 0, "at least one entry")

    for i, e in enumerate(entries):
        tag = f"entries[{i}] ({e.get('phase', '?')})"
        for f in ("phase", "title", "builder", "harness", "role", "commits", "verified"):
            check(f in e, f"{tag}: has {f}")
        check(isinstance(e.get("commits"), list), f"{tag}: commits is a list")
        check(isinstance(e.get("verified"), bool), f"{tag}: verified is a bool")

        # THE RULE THAT WAS MISSING. `usage` is optional, but if present it is a
        # COMPLETE measurement — every count a non-negative int, reasoning nullable,
        # note a string. An entry with no measurement omits `usage` and explains
        # itself in `usageNote`; it does NOT ship an object full of nulls (which is
        # exactly what 500'd the homepage). The renderer trusts this: it calls
        # toLocaleString on every number the moment `usage` exists.
        u = e.get("usage")
        if u is not None:
            for f in ("measuredAt", "inputTokens", "cachedInputTokens",
                      "uncachedInputTokens", "outputTokens", "totalTokens", "note"):
                check(f in u, f"{tag}: usage.{f} present")
            check(isinstance(u.get("measuredAt"), str), f"{tag}: usage.measuredAt is a string")
            check(isinstance(u.get("note"), str), f"{tag}: usage.note is a string")
            for f in ("inputTokens", "cachedInputTokens", "uncachedInputTokens",
                      "outputTokens", "totalTokens"):
                check(is_nonneg_int(u.get(f)),
                      f"{tag}: usage.{f} is a non-negative int (a MEASURED usage carries real numbers, not null)")
            r = u.get("reasoningOutputTokens")
            check(r is None or is_nonneg_int(r), f"{tag}: usage.reasoningOutputTokens is a non-neg int or null")
        # No `usage` is allowed — the loader makes it optional, and older entries
        # predate the measurement convention. This check MIRRORS the loader and no
        # more: requiring a usageNote here would be stricter than lib/buildlog.ts
        # and would retroactively fail seven valid historical entries. The bug this
        # file exists to catch is a PRESENT usage with null counts, above — not an
        # absent one. usageNote, if given, is just a string.
        if "usageNote" in e:
            check(isinstance(e["usageNote"], str), f"{tag}: usageNote is a string")

    passed = [r for r in results if r[0]]
    for ok, label in results:
        if not ok:
            print(f"  FAIL  {label}")
    print(f"\ncheck_buildlog: {len(passed)}/{len(results)} checks passed")
    return 0 if len(passed) == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
