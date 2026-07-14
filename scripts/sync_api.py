#!/usr/bin/env python3
"""
sync_api.py — one-time (re-runnable) mirror of api-onepiece.com v2 into data/raw/.

Dead Reckoning architecture rules this script obeys:
  * It writes ONLY to data/raw/. It never touches canon/ (human-owned) or
    data/generated/. A sync script that writes to canon/ is a BUG — asserted below.
  * The app NEVER fetches at request time. This mirror is committed to git.
  * Raw responses are written byte-for-byte, unmodified. Normalization happens
    later, in scripts/normalize.py.

Politeness: sequential, ~1s between calls, 3 retries with backoff, 60s timeout,
explicit User-Agent. The upstream is a single un-CDN'd Apache box with a bus
factor of 1. Do not hammer it.

Usage:
    python3 scripts/sync_api.py            # resumable: skips endpoints already mirrored
    python3 scripts/sync_api.py --force    # re-fetch everything
    python3 scripts/sync_api.py --only characters,fruits
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# --- paths ------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
CANON_DIR = REPO_ROOT / "canon"
MANIFEST_PATH = RAW_DIR / "_manifest.json"

# --- config -----------------------------------------------------------------

BASE = "https://api.api-onepiece.com/v2"
LANG = "en"
USER_AGENT = "dead-reckoning/0.1 (One Piece fan atlas; contact: shawn@leadalchemy.co)"

TIMEOUT = 60
RETRIES = 3
SLEEP_BETWEEN = 1.0          # seconds between successful calls
BACKOFF_BASE = 2.0           # seconds; doubles per retry

# Logical endpoint name -> candidate URL paths (tried in order; first 200 wins).
# The multi-word resources are not documented consistently upstream, so we probe.
ENDPOINTS: dict[str, list[str]] = {
    "sagas": ["sagas"],
    "arcs": ["arcs"],
    "chapters": ["chapters"],
    "episodes": ["episodes"],
    "characters": ["characters"],
    "crews": ["crews"],
    "fruits": ["fruits"],
    "boats": ["boats"],
    "locates": ["locates"],
    "tomes": ["tomes"],
    "dials": ["dials"],
    "films": ["movies", "films"],  # upstream calls it /movies; /films is a 404
    "swords": ["swords"],
    "haki": ["haki", "hakis"],
    "luffy_gears": ["luffy/gears", "gears", "luffy-gears"],
    "luffy_techniques": ["luffy/techniques", "techniques", "luffy-techniques"],
}

# Known counts from the live probe. A mismatch means upstream changed and every
# downstream assumption (joins, ranges, enums) is suspect.
EXPECTED_COUNTS: dict[str, int] = {
    "sagas": 10,
    "arcs": 50,
    "chapters": 1185,
    "episodes": 1162,
    "characters": 786,
    "crews": 149,
    "fruits": 213,
    "boats": 99,
    "locates": 128,
}


def url_for(path: str) -> str:
    return f"{BASE}/{path}/{LANG}"


# --- fetch ------------------------------------------------------------------


class FetchResult:
    def __init__(self, url: str, status: int | None, body: bytes | None, error: str | None):
        self.url = url
        self.status = status
        self.body = body
        self.error = error

    @property
    def ok(self) -> bool:
        return self.status == 200 and self.body is not None


def fetch(url: str) -> FetchResult:
    """GET with retries + backoff. Never raises. A 404 is a result, not a crash."""
    last_error: str | None = None
    last_status: int | None = None

    for attempt in range(1, RETRIES + 1):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                body = resp.read()
                return FetchResult(url, resp.status, body, None)
        except urllib.error.HTTPError as e:
            last_status = e.code
            last_error = f"HTTP {e.code} {e.reason}"
            # 4xx is a real answer from the server — don't retry it.
            if 400 <= e.code < 500:
                return FetchResult(url, e.code, None, last_error)
        except urllib.error.URLError as e:
            last_error = f"URLError: {e.reason}"
        except TimeoutError:
            last_error = f"timeout after {TIMEOUT}s"
        except Exception as e:  # noqa: BLE001 — a partial mirror beats a crashed script
            last_error = f"{type(e).__name__}: {e}"

        if attempt < RETRIES:
            wait = BACKOFF_BASE ** attempt
            print(f"    retry {attempt}/{RETRIES - 1} in {wait:.0f}s ({last_error})", flush=True)
            time.sleep(wait)

    return FetchResult(url, last_status, None, last_error)


def record_count(body: bytes) -> tuple[int | None, str | None]:
    """(count, parse_error). Count = len for a list, else key count for an object."""
    try:
        parsed = json.loads(body.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"
    if isinstance(parsed, list):
        return len(parsed), None
    if isinstance(parsed, dict):
        # Some resources wrap the payload; count the biggest list inside if present.
        for value in parsed.values():
            if isinstance(value, list):
                return len(value), None
        return len(parsed), None
    return None, f"unexpected top-level JSON type: {type(parsed).__name__}"


# --- main -------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Mirror api-onepiece.com v2 into data/raw/")
    parser.add_argument("--force", action="store_true", help="re-fetch endpoints already on disk")
    parser.add_argument("--only", default="", help="comma-separated endpoint names to fetch")
    args = parser.parse_args()

    # ARCHITECTURE ASSERTION: this script is machine-owned and must never write
    # into the human-owned canon/ directory.
    assert RAW_DIR.resolve() != CANON_DIR.resolve(), "sync writes to canon/ — BUG"
    assert CANON_DIR.resolve() not in RAW_DIR.resolve().parents, "sync writes inside canon/ — BUG"

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    selected = [e.strip() for e in args.only.split(",") if e.strip()] or list(ENDPOINTS)
    unknown = [e for e in selected if e not in ENDPOINTS]
    if unknown:
        print(f"unknown endpoint(s): {', '.join(unknown)}", file=sys.stderr)
        return 2

    manifest: dict[str, dict] = {}
    if MANIFEST_PATH.exists():
        try:
            manifest = json.loads(MANIFEST_PATH.read_text())
            manifest.pop("_meta", None)
        except Exception:  # noqa: BLE001
            manifest = {}

    print(f"mirroring {len(selected)} endpoint(s) from {BASE} -> {RAW_DIR}\n", flush=True)

    for name in selected:
        out_path = RAW_DIR / f"{name}.json"

        if out_path.exists() and not args.force:
            print(f"[skip]   {name:<18} already mirrored ({out_path.stat().st_size:,} bytes)", flush=True)
            continue

        attempts: list[dict] = []
        winner: FetchResult | None = None

        for path in ENDPOINTS[name]:
            u = url_for(path)
            print(f"[fetch]  {name:<18} {u}", flush=True)
            res = fetch(u)
            attempts.append({"url": u, "status": res.status, "error": res.error})
            if res.ok:
                winner = res
                break
            print(f"         -> {res.status or 'ERR'} {res.error or ''}", flush=True)
            time.sleep(SLEEP_BETWEEN)

        fetched_at = datetime.now(timezone.utc).isoformat()

        if winner is None or winner.body is None:
            last = attempts[-1] if attempts else {"url": None, "status": None, "error": "no attempt"}
            manifest[name] = {
                "url": last["url"],
                "http_status": last["status"],
                "record_count": None,
                "bytes": 0,
                "fetched_at": fetched_at,
                "sha256": None,
                "file": None,
                "ok": False,
                "error": last["error"],
                "attempts": attempts,
            }
            print(f"[miss]   {name:<18} no candidate path responded 200 — recorded and moving on\n", flush=True)
            time.sleep(SLEEP_BETWEEN)
            continue

        body = winner.body
        count, parse_error = record_count(body)
        sha = hashlib.sha256(body).hexdigest()

        # Faithful mirror: bytes on the wire == bytes on disk. No re-serialization.
        out_path.write_bytes(body)

        manifest[name] = {
            "url": winner.url,
            "http_status": winner.status,
            "record_count": count,
            "bytes": len(body),
            "fetched_at": fetched_at,
            "sha256": sha,
            "file": f"data/raw/{name}.json",
            "ok": True,
            "error": parse_error,
            "attempts": attempts,
        }

        suffix = f" (parse warning: {parse_error})" if parse_error else ""
        print(f"[ok]     {name:<18} {count} records · {len(body):,} bytes · {sha[:12]}…{suffix}\n", flush=True)
        time.sleep(SLEEP_BETWEEN)

    ordered = {k: manifest[k] for k in ENDPOINTS if k in manifest}
    ordered["_meta"] = {
        "base": BASE,
        "lang": LANG,
        "user_agent": USER_AGENT,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": "Machine-owned mirror. Do not hand-edit data/raw/. Regenerate with scripts/sync_api.py --force.",
    }
    MANIFEST_PATH.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n")

    # --- verification -------------------------------------------------------

    print("=" * 72)
    print("MIRROR VERIFICATION")
    print("=" * 72)
    print(f"{'endpoint':<18} {'status':>6} {'records':>8} {'bytes':>10}  check")
    print("-" * 72)

    mismatches: list[str] = []
    missing: list[str] = []

    for name in ENDPOINTS:
        entry = ordered.get(name)
        if entry is None:
            print(f"{name:<18} {'-':>6} {'-':>8} {'-':>10}  not attempted")
            continue
        if not entry["ok"]:
            print(f"{name:<18} {str(entry['http_status'] or 'ERR'):>6} {'-':>8} {'-':>10}  DEAD ({entry['error']})")
            missing.append(name)
            continue

        expected = EXPECTED_COUNTS.get(name)
        actual = entry["record_count"]
        if expected is None:
            check = "ok (no baseline)"
        elif actual == expected:
            check = f"ok (== {expected})"
        else:
            check = f"*** MISMATCH: expected {expected}, got {actual} ***"
            mismatches.append(f"{name}: expected {expected}, got {actual}")

        print(f"{name:<18} {entry['http_status']:>6} {str(actual):>8} {entry['bytes']:>10,}  {check}")

    print("-" * 72)
    live = [n for n in ENDPOINTS if ordered.get(n, {}).get("ok")]
    total_bytes = sum(ordered[n]["bytes"] for n in live)
    total_records = sum(ordered[n]["record_count"] or 0 for n in live)
    print(f"{len(live)}/{len(ENDPOINTS)} endpoints mirrored · {total_records:,} records · {total_bytes:,} bytes")
    print(f"manifest: {MANIFEST_PATH}")

    if missing:
        print(f"\nDEAD ENDPOINTS (expected — recorded in manifest, not fatal): {', '.join(missing)}")

    if mismatches:
        print("\n" + "!" * 72)
        print("!! COUNT MISMATCH — UPSTREAM CHANGED. Downstream assumptions are stale.")
        for m in mismatches:
            print(f"!!   {m}")
        print("!" * 72)
        return 1

    print("\nAll baseline counts match. Mirror is consistent with the probe.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
