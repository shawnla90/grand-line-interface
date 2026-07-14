#!/usr/bin/env python3
"""
sync_wiki.py — pull STRUCTURED FACTS from the One Piece Fandom MediaWiki API.

WHY THIS EXISTS
---------------
api-onepiece.com gives us an encyclopedia with no time axis. The wiki gives us
the time axis: exact chapter AND episode ranges per story arc, the prev/next
linked list that IS the voyage order, and island debut chapters (which is what
lets the map fog what the reader hasn't reached).

WHAT IT WRITES (machine-owned, safe to overwrite):
    data/generated/arcs.json
    data/generated/islands.json
    data/generated/chapter_episode_map.json
    data/generated/_wiki_manifest.json
    data/generated/_wiki_cache/*.json   (raw responses; re-runs are free)

WHAT IT MUST NEVER TOUCH:
    canon/  — human-owned. A sync script writing to canon/ is a BUG.
              Asserted at runtime (see assert_no_canon_writes).

LICENSE POSTURE
---------------
Source is CC-BY-SA 3.0. FACTS (numbers, names, ranges, categories) are not
copyrightable and are free to use. PROSE IS NOT. This script extracts ONLY
template parameters and infobox fields. It never reads, stores, or emits
article body text, descriptions, or summaries. If you extend it, keep it that
way: if your parser is grabbing sentences, you are doing it wrong.

POLITENESS
----------
1 request/second, descriptive User-Agent, maxlag=5, exponential backoff on
429/503, respects Retry-After, and batches up to 50 titles per query. Total
cost of a cold run is roughly 50 requests, not 450.

Usage:
    python3 scripts/sync_wiki.py            # cached where possible
    python3 scripts/sync_wiki.py --refresh  # ignore cache, refetch everything
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API = "https://onepiece.fandom.com/api.php"
WIKI_BASE = "https://onepiece.fandom.com/wiki/"
USER_AGENT = "dead-reckoning/0.1 (One Piece fan atlas; contact: shawn@leadalchemy.co)"

REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATED = REPO_ROOT / "data" / "generated"
CACHE_DIR = GENERATED / "_wiki_cache"
CANON_DIR = REPO_ROOT / "canon"

REQUEST_DELAY_S = 1.0  # hard floor between requests
MAX_RETRIES = 5
BATCH_SIZE = 50  # MediaWiki's own limit for anonymous title batching

SOURCE_LICENSE = "CC-BY-SA 3.0 (One Piece Fandom). Facts only; no prose copied. Attributed in UI footer."

# Counters
STATS = {"requests": 0, "cache_hits": 0, "retries": 0}


# ---------------------------------------------------------------------------
# Guardrail: this script may never write to canon/
# ---------------------------------------------------------------------------

def assert_no_canon_writes(path: Path) -> None:
    """canon/ is human-owned. A sync script that writes there is a bug. Fail loud."""
    resolved = path.resolve()
    if CANON_DIR.resolve() in resolved.parents or resolved == CANON_DIR.resolve():
        raise RuntimeError(
            f"ARCHITECTURE VIOLATION: sync_wiki.py attempted to write into canon/ "
            f"({resolved}). canon/ is hand-authored and machine-immutable. "
            f"Fix the script, not the guardrail."
        )


def write_json(path: Path, payload: Any) -> None:
    assert_no_canon_writes(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


# ---------------------------------------------------------------------------
# Polite HTTP with on-disk cache
# ---------------------------------------------------------------------------

_last_request_at = 0.0


def _throttle() -> None:
    global _last_request_at
    elapsed = time.time() - _last_request_at
    if elapsed < REQUEST_DELAY_S:
        time.sleep(REQUEST_DELAY_S - elapsed)
    _last_request_at = time.time()


def api_get(params: dict[str, str], *, refresh: bool = False) -> dict:
    """GET the MediaWiki API with caching, throttling, maxlag, and backoff."""
    params = {**params, "format": "json", "formatversion": "2", "maxlag": "5"}
    url = f"{API}?{urllib.parse.urlencode(params)}"

    cache_key = hashlib.sha1(url.encode("utf-8")).hexdigest()
    cache_file = CACHE_DIR / f"{cache_key}.json"

    if cache_file.exists() and not refresh:
        STATS["cache_hits"] += 1
        return json.loads(cache_file.read_text(encoding="utf-8"))

    backoff = 2.0
    for attempt in range(1, MAX_RETRIES + 1):
        _throttle()
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                body = resp.read().decode("utf-8")
            data = json.loads(body)

            # maxlag / API-level errors come back 200 with an "error" key
            if "error" in data:
                code = data["error"].get("code", "")
                if code in ("maxlag", "readonly"):
                    STATS["retries"] += 1
                    print(f"    maxlag/readonly, backing off {backoff:.0f}s", file=sys.stderr)
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise RuntimeError(f"MediaWiki API error: {data['error']}")

            STATS["requests"] += 1
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return data

        except urllib.error.HTTPError as exc:
            if exc.code in (429, 503, 502, 504) and attempt < MAX_RETRIES:
                retry_after = exc.headers.get("Retry-After")
                wait = float(retry_after) if retry_after and retry_after.isdigit() else backoff
                STATS["retries"] += 1
                print(f"    HTTP {exc.code}, retrying in {wait:.0f}s", file=sys.stderr)
                time.sleep(wait)
                backoff *= 2
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt < MAX_RETRIES:
                STATS["retries"] += 1
                print(f"    network error ({exc}), retrying in {backoff:.0f}s", file=sys.stderr)
                time.sleep(backoff)
                backoff *= 2
                continue
            raise

    raise RuntimeError(f"Gave up after {MAX_RETRIES} attempts: {url}")


# ---------------------------------------------------------------------------
# Wikitext helpers — template params only, never body prose
# ---------------------------------------------------------------------------

def extract_template(wikitext: str, template_name: str) -> str | None:
    """Return the raw source of the first {{template_name ...}} call, brace-balanced."""
    pattern = re.compile(r"\{\{\s*" + re.escape(template_name) + r"\s*[\|\}]", re.IGNORECASE)
    match = pattern.search(wikitext)
    if not match:
        return None

    start = match.start()
    depth = 0
    i = start
    while i < len(wikitext) - 1:
        pair = wikitext[i:i + 2]
        if pair == "{{":
            depth += 1
            i += 2
            continue
        if pair == "}}":
            depth -= 1
            i += 2
            if depth == 0:
                return wikitext[start:i]
            continue
        i += 1
    return None


def split_params(template_src: str) -> dict[str, str]:
    """
    Split a template body into {param: value}, respecting nested {{ }}, [[ ]],
    <gallery>/<ref> blocks and HTML tags. Only top-level pipes split params.
    """
    inner = template_src[2:-2]  # strip {{ }}
    # drop the template name (everything before the first top-level pipe)
    parts: list[str] = []
    buf: list[str] = []
    depth_curly = 0
    depth_square = 0
    depth_angle = 0

    i = 0
    while i < len(inner):
        two = inner[i:i + 2]
        ch = inner[i]

        if two == "{{":
            depth_curly += 1
            buf.append(two); i += 2; continue
        if two == "}}":
            depth_curly -= 1
            buf.append(two); i += 2; continue
        if two == "[[":
            depth_square += 1
            buf.append(two); i += 2; continue
        if two == "]]":
            depth_square -= 1
            buf.append(two); i += 2; continue
        if ch == "<":
            depth_angle += 1
            buf.append(ch); i += 1; continue
        if ch == ">":
            depth_angle = max(0, depth_angle - 1)
            buf.append(ch); i += 1; continue

        if ch == "|" and depth_curly == 0 and depth_square == 0 and depth_angle == 0:
            parts.append("".join(buf))
            buf = []
            i += 1
            continue

        buf.append(ch)
        i += 1
    parts.append("".join(buf))

    params: dict[str, str] = {}
    for part in parts[1:]:  # parts[0] is the template name
        if "=" not in part:
            continue
        key, _, value = part.partition("=")
        params[key.strip().lower()] = value.strip()
    return params


def strip_refs(value: str) -> str:
    """Remove {{Qref|...}}, <ref>...</ref>, and citation noise. Brace-balanced."""
    out: list[str] = []
    i = 0
    while i < len(value):
        if value[i:i + 2] == "{{":
            depth = 0
            j = i
            while j < len(value) - 1:
                if value[j:j + 2] == "{{":
                    depth += 1; j += 2; continue
                if value[j:j + 2] == "}}":
                    depth -= 1; j += 2
                    if depth == 0:
                        break
                    continue
                j += 1
            i = j
            continue
        out.append(value[i])
        i += 1
    cleaned = "".join(out)
    cleaned = re.sub(r"<ref[^>]*/>", "", cleaned)
    cleaned = re.sub(r"<ref[^>]*>.*?</ref>", "", cleaned, flags=re.S | re.I)
    return cleaned


def clean_text(value: str) -> str:
    """Reduce a template param to a plain fact string: no links, no tags, no refs."""
    v = strip_refs(value)
    v = re.sub(r"<gallery>.*?</gallery>", "", v, flags=re.S | re.I)
    v = re.sub(r"<br\s*/?>", " ", v, flags=re.I)
    v = re.sub(r"<small>.*?</small>", "", v, flags=re.S | re.I)
    v = re.sub(r"<[^>]+>", "", v)
    # [[Target|Label]] -> Label ; [[Target]] -> Target
    v = re.sub(r"\[\[(?:[^\]\|]+\|)?([^\]\|]+)\]\]", r"\1", v)
    v = v.replace("'''", "").replace("''", "")
    v = re.sub(r"\s+", " ", v).strip()
    return v.strip(" ;,-")


def first_link_target(value: str, suffix: str) -> str | None:
    """Return the first [[X <suffix>]] link TARGET (a fact, not prose)."""
    m = re.search(r"\[\[([^\]\|#]+?\s" + re.escape(suffix) + r")(?:\||\]\])", value)
    return m.group(1).strip() if m else None


def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"\s+arc$", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


# ---------------------------------------------------------------------------
# A) STORY ARCS
# ---------------------------------------------------------------------------

def fetch_arc_titles(refresh: bool) -> list[str]:
    data = api_get(
        {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": "Category:Story Arcs",
            "cmlimit": "500",
            "cmnamespace": "0",
        },
        refresh=refresh,
    )
    members = data["query"]["categorymembers"]
    # The category contains its own index page "Story Arcs"; that's not an arc.
    return [m["title"] for m in members if m["title"].endswith(" Arc")]


def fetch_wikitext_batch(titles: list[str], refresh: bool) -> dict[str, str]:
    """Batched revisions fetch (<=50 titles/request). Returns {resolved_title: wikitext}."""
    out: dict[str, str] = {}
    for i in range(0, len(titles), BATCH_SIZE):
        chunk = titles[i:i + BATCH_SIZE]
        data = api_get(
            {
                "action": "query",
                "titles": "|".join(chunk),
                "prop": "revisions",
                "rvslots": "main",
                "rvprop": "content",
                "redirects": "1",
            },
            refresh=refresh,
        )
        query = data.get("query", {})
        for page in query.get("pages", []):
            if page.get("missing") or "revisions" not in page:
                continue
            content = page["revisions"][0]["slots"]["main"].get("content", "")
            out[page["title"]] = content
    return out


def parse_range_field(raw: str | None) -> dict[str, Any]:
    """
    Parse an Arc Box range string into segments + span + an integrity check.

    THE SHAPES THAT ACTUALLY OCCUR (all observed live, do not simplify this):
      "155-217, 63 chapters"                                   single segment
      "422-425\xa0and 430-452, 27 episodes"                    TWO segments — eps
                                                               426-429 are FILLER
      "890-894, 897-906, 908-1028 and 1031-1085, 191 episodes" FOUR segments
      "45\xa0and 48-53, 7 episodes"                            BARE SINGLE + range
      "1126-"                                                  OPEN-ENDED (ongoing arc)

    Anime episode ranges are MULTI-SEGMENT because filler arcs interrupt them.
    Taking only the first segment is how you tell a reader at episode 1000 that
    they haven't reached Wano (real bug, caught in review). Segments may also be
    a BARE single episode (Loguetown = "45 and 48-53"), so we tokenize on
    comma/"and" rather than pattern-matching N-M pairs.

    We keep every segment AND the outer span, then cross-check our parse against
    the count the wiki itself declares ("191 episodes"). A mismatch means the
    format drifted -> surface it loudly rather than silently ship a wrong range.
    That check is what caught both bugs above; do not remove it.
    """
    result: dict[str, Any] = {
        "start": None, "end": None, "segments": [], "ongoing": False,
        "declared_count": None, "parsed_count": None, "count_matches": None,
    }
    if not raw:
        return result

    text = unescape(raw).replace("\xa0", " ")  # "&#160;" -> nbsp -> space

    # The total the wiki computes for itself, e.g. "191 episodes". Strip it off
    # so it can never be misread as a range bound — then use it to verify us.
    dc = re.search(r"(\d+)\s+(?:chapters?|episodes?|volumes?)\b", text, re.I)
    if dc:
        result["declared_count"] = int(dc.group(1))
        text = text[:dc.start()]

    for token in re.split(r",|\band\b", text):
        token = token.strip()
        if not token:
            continue
        m = re.fullmatch(r"(\d+)\s*[-–—]\s*(\d+)", token)
        if m:
            result["segments"].append([int(m.group(1)), int(m.group(2))])
            continue
        m = re.fullmatch(r"(\d+)\s*[-–—]", token)  # open-ended: "1126-"
        if m:
            result["segments"].append([int(m.group(1)), None])
            result["ongoing"] = True
            continue
        m = re.fullmatch(r"(\d+)", token)  # bare single: "45"
        if m:
            n = int(m.group(1))
            result["segments"].append([n, n])

    if result["segments"]:
        result["start"] = result["segments"][0][0]
        result["end"] = result["segments"][-1][1]  # None when ongoing
        if not result["ongoing"]:
            result["parsed_count"] = sum(e - s + 1 for s, e in result["segments"])
            if result["declared_count"] is not None:
                result["count_matches"] = result["parsed_count"] == result["declared_count"]

    return result


def parse_arc_ranges(title: str, refresh: bool) -> dict[str, Any]:
    """
    The Arc Box has `chapter = auto` / `episode = auto` — the real ranges are
    computed by a Lua module and only exist in the RENDERED output. So we must
    action=parse and read the portable-infobox data-source fields.
    """
    data = api_get({"action": "parse", "page": title, "prop": "text"}, refresh=refresh)
    html = data["parse"]["text"]
    aside_end = html.find("</aside>")
    aside = html[:aside_end] if aside_end > 0 else html[:20000]

    fields: dict[str, str] = {}
    for m in re.finditer(r'data-source="([^"]+)"', aside):
        key = m.group(1)
        seg = aside[m.end():m.end() + 900]
        vm = re.search(r'pi-data-value[^>]*>(.*?)</div>', seg, re.S)
        if vm:
            txt = re.sub(r"<[^>]+>", "", vm.group(1))
            fields[key] = re.sub(r"[ \t]+", " ", txt).strip()

    ch = parse_range_field(fields.get("chapter"))
    ep = parse_range_field(fields.get("episode"))

    return {
        "chapter_start": ch["start"],
        "chapter_end": ch["end"],
        "chapter_segments": ch["segments"],
        "episode_start": ep["start"],
        "episode_end": ep["end"],
        # Filler gaps live between these segments. The app must use segments —
        # not [start, end] — to decide whether an episode is inside this arc.
        "episode_segments": ep["segments"],
        "ongoing": ch["ongoing"] or ep["ongoing"],
        "_checks": {
            "chapter": ch,
            "episode": ep,
            "raw_chapter": fields.get("chapter"),
            "raw_episode": fields.get("episode"),
        },
    }


def resolve_order(arcs: list[dict]) -> tuple[list[dict], list[str]]:
    """
    Walk the prev/next linked list into an integer `order`. This chain IS the
    voyage sequence. Verify it forms ONE unbroken chain: no cycles, no orphans.
    """
    problems: list[str] = []
    by_name = {a["name"]: a for a in arcs}

    heads = [a for a in arcs if not a["prev_arc"]]
    tails = [a for a in arcs if not a["next_arc"]]
    if len(heads) != 1:
        problems.append(f"expected exactly 1 head (no prev), found {len(heads)}: {[h['name'] for h in heads]}")
    if len(tails) != 1:
        problems.append(f"expected exactly 1 tail (no next), found {len(tails)}: {[t['name'] for t in tails]}")

    # Dangling pointers
    for a in arcs:
        for field in ("prev_arc", "next_arc"):
            target = a[field]
            if target and target not in by_name:
                problems.append(f"{a['name']}.{field} -> '{target}' is not a known story arc")

    if not heads:
        problems.append("no head found; cannot resolve order (cycle?)")
        return arcs, problems

    # Walk the chain
    seen: set[str] = set()
    node = heads[0]
    order = 0
    while node is not None:
        if node["name"] in seen:
            problems.append(f"CYCLE detected at '{node['name']}'")
            break
        seen.add(node["name"])
        node["order"] = order
        order += 1
        nxt = node["next_arc"]
        node = by_name.get(nxt) if nxt else None

    orphans = [a["name"] for a in arcs if a["name"] not in seen]
    if orphans:
        problems.append(f"{len(orphans)} arc(s) not reachable from head (orphans): {orphans}")
        for a in arcs:
            if a["name"] not in seen:
                a["order"] = None

    # Sanity: order should march forward with chapter_start
    ordered = sorted([a for a in arcs if a.get("order") is not None], key=lambda x: x["order"])
    for prev, cur in zip(ordered, ordered[1:]):
        if prev["chapter_start"] and cur["chapter_start"] and prev["chapter_start"] > cur["chapter_start"]:
            problems.append(
                f"order/chapter mismatch: '{prev['name']}' (ch {prev['chapter_start']}) "
                f"precedes '{cur['name']}' (ch {cur['chapter_start']})"
            )
    return arcs, problems


def build_arcs(refresh: bool) -> tuple[list[dict], list[str]]:
    print("\n[A] STORY ARCS")
    titles = fetch_arc_titles(refresh)
    print(f"    Category:Story Arcs -> {len(titles)} arc pages")

    wikitexts = fetch_wikitext_batch(titles, refresh)
    print(f"    fetched wikitext for {len(wikitexts)} arcs (prev/next + saga)")

    arcs: list[dict] = []
    for title in titles:
        wt = wikitexts.get(title, "")
        box_src = extract_template(wt, "Arc Box")
        params = split_params(box_src) if box_src else {}

        prev_arc = first_link_target(params.get("prev", ""), "Arc")
        next_arc = first_link_target(params.get("next", ""), "Arc")

        # Saga membership: pull the [[X Saga]] LINK TARGET, not the sentence.
        saga = None
        m = re.search(r"(?:story )?arc of the \[\[([^\]\|]+?\sSaga)\]\]", wt)
        if m:
            saga = m.group(1).strip()
        else:
            m = re.search(r"\[\[([^\]\|#]+?\sSaga)\]\]", wt)
            if m:
                saga = m.group(1).strip()

        arcs.append({
            "id": slugify(title),
            "name": title,
            "slug": slugify(title),
            "saga": saga,
            "prev_arc": prev_arc,
            "next_arc": next_arc,
            "order": None,
            "wiki_url": WIKI_BASE + urllib.parse.quote(title.replace(" ", "_")),
            "source_ref": f"onepiece.fandom.com/wiki/{title.replace(' ', '_')}#Arc_Box",
            "canon_confidence": "canon",
        })

    print(f"    fetching rendered infoboxes for chapter/episode ranges ({len(arcs)} requests)...")
    range_problems: list[str] = []
    for idx, arc in enumerate(arcs, 1):
        ranges = parse_arc_ranges(arc["name"], refresh)
        checks = ranges.pop("_checks")
        arc.update(ranges)

        # FAIL LOUD: our parsed segment total must agree with the count the wiki
        # itself declares. If it doesn't, the format drifted and the range is
        # suspect — say so rather than shipping a wrong number.
        for kind in ("chapter", "episode"):
            c = checks[kind]
            if c["count_matches"] is False:
                range_problems.append(
                    f"{arc['name']}: {kind} count mismatch — wiki declares "
                    f"{c['declared_count']}, segments {c['segments']} sum to {c['parsed_count']} "
                    f"(raw: {checks['raw_' + kind]!r})"
                )
        if idx % 10 == 0 or idx == len(arcs):
            print(f"      {idx}/{len(arcs)}")

    multi = [a["name"] for a in arcs if len(a.get("episode_segments") or []) > 1]
    if multi:
        print(f"    {len(multi)} arc(s) have filler-split episode ranges: {', '.join(multi)}")

    arcs, problems = resolve_order(arcs)
    problems = range_problems + problems
    arcs.sort(key=lambda a: (a["order"] is None, a["order"] if a["order"] is not None else 0))

    # Reorder keys for output readability
    shaped = [{
        "id": a["id"],
        "name": a["name"],
        "slug": a["slug"],
        "saga": a["saga"],
        "chapter_start": a["chapter_start"],
        "chapter_end": a["chapter_end"],
        "chapter_segments": a["chapter_segments"],
        "episode_start": a["episode_start"],
        "episode_end": a["episode_end"],
        "episode_segments": a["episode_segments"],
        "ongoing": a["ongoing"],
        "prev_arc": a["prev_arc"],
        "next_arc": a["next_arc"],
        "order": a["order"],
        "wiki_url": a["wiki_url"],
        "source_ref": a["source_ref"],
        "canon_confidence": a["canon_confidence"],
    } for a in arcs]

    return shaped, problems


# ---------------------------------------------------------------------------
# B) ISLANDS
# ---------------------------------------------------------------------------

def fetch_island_titles(refresh: bool) -> list[str]:
    titles: list[str] = []
    cont: dict[str, str] = {}
    while True:
        params = {
            "action": "query",
            "list": "embeddedin",
            "eititle": "Template:Island Box",
            "eilimit": "500",
            "einamespace": "0",
        }
        params.update(cont)
        data = api_get(params, refresh=refresh)
        titles.extend(x["title"] for x in data.get("query", {}).get("embeddedin", []))
        if "continue" not in data:
            break
        cont = {k: str(v) for k, v in data["continue"].items()}
    return titles


def parse_debut(raw_first: str) -> dict[str, Any]:
    """
    Parse Island Box `first` into a debut + a CANON CLASSIFICATION.

        first = [[Chapter 323]]; [[Episode 229]]{{Qref|...}}   -> manga canon
        first = [[Episode 895]]                                -> anime only
        first = [[One Piece Film: Z]]                          -> NON-CANON
        first = [[One Piece: World Seeker]]                    -> NON-CANON (game)

    This classification is load-bearing, not cosmetic. 106 of 413 "islands" debut
    only in movies, games, ONAs, magazines or stage shows. They have no chapter
    AND no episode because they are not in the manga or the anime series at all.
    A spoiler-safe canon atlas must not treat them as missing data and must not
    plot them as canon. `canon_status` is what lets the map filter them out.

    Refs are stripped first so a {{Qref|chap=...}} can never be misread as the debut.
    """
    cleaned = strip_refs(raw_first).strip()
    if not cleaned:
        return {"chapter": None, "episode": None, "status": "unknown", "source": None}

    # MATCH THE LINK TARGET, NEVER THE LABEL. A piped link can put canon-looking
    # display text in front of a non-canon target:
    #   [[MiraBato Strongest Strategy#Chapter 0|MiraBato Chapter 0]]  <- NOT canon ch 0
    #   [[One Piece Film Strong World: Episode 0|Episode 0]]          <- a FILM, not ep 0
    # Matching loosely on "Chapter \d+" anywhere classified both of those as manga
    # canon (real bug, caught in review). The target must itself BE "Chapter N".
    def target_number(kind: str) -> int | None:
        m = re.search(r"\[\[" + kind + r"\s+(\d+)\s*(?:\||\]\])", cleaned, re.I)
        if m:
            return int(m.group(1))
        # Fallback for unlinked plain text ("Chapter 1") — only safe when the
        # field contains no wikilinks at all, so no label can be mistaken for one.
        if "[[" not in cleaned:
            m = re.fullmatch(r"\s*" + kind + r"\s+(\d+)\s*", cleaned, re.I)
            if m:
                return int(m.group(1))
        return None

    chapter = target_number("Chapter")
    episode = target_number("Episode")

    if chapter is not None:
        status = "manga"          # true canon; has a place on the chapter axis
    elif episode is not None:
        status = "anime"          # anime-only / filler; no manga chapter exists
    else:
        status = "non_canon"      # movie, game, ONA, magazine, stage show

    # For non-canon debuts, record WHICH medium (the wikilink target = a fact).
    source = None
    if status == "non_canon":
        m = re.search(r"\[\[([^\]\|]+)(?:\|[^\]]+)?\]\]", cleaned)
        source = m.group(1).split("#")[0].strip() if m else clean_text(cleaned)[:80] or None

    return {"chapter": chapter, "episode": episode, "status": status, "source": source}


def build_islands(refresh: bool) -> tuple[list[dict], dict]:
    print("\n[B] ISLANDS / LOCATIONS")
    titles = fetch_island_titles(refresh)
    print(f"    Template:Island Box transclusions (ns0) -> {len(titles)} pages")

    n_batches = (len(titles) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"    fetching wikitext in {n_batches} batched requests ({BATCH_SIZE} titles each)...")
    wikitexts = fetch_wikitext_batch(titles, refresh)
    print(f"    got wikitext for {len(wikitexts)} pages")

    islands: list[dict] = []
    param_freq: dict[str, int] = {}
    no_box = 0

    for title, wt in sorted(wikitexts.items()):
        box_src = extract_template(wt, "Island Box")
        if not box_src:
            no_box += 1
            continue
        params = split_params(box_src)
        for k in params:
            param_freq[k] = param_freq.get(k, 0) + 1

        debut = parse_debut(params.get("first", ""))

        # `ename` is NOT a name — it's a pile of dub/translation variants, e.g.
        #   "Coco Village <small>(VIZ manga, 4Kids dub...)</small><br/>Cocoyasi Village"
        # Using it raw drags a sentence of localization trivia into the map label.
        # The page title IS the wiki's canonical name and is always clean, so that
        # is `name`. We keep the first ename variant separately, when it differs.
        first_variant = re.split(r"<br\s*/?>", params.get("ename", ""), maxsplit=1)[0]
        first_variant = re.sub(r"\([^)]*\)", "", clean_text(first_variant)).strip()
        english_name = first_variant if first_variant and first_variant != title else None

        islands.append({
            "name": title,
            "english_name": english_name,
            "slug": slugify(title),
            "page_title": title,
            "romaji": clean_text(params.get("rname", "")) or None,
            "japanese": clean_text(params.get("jname", "")) or None,
            "sea": clean_text(params.get("sea", "")) or None,
            "region": clean_text(params.get("region", "")) or None,
            "debut_chapter": debut["chapter"],
            "debut_episode": debut["episode"],
            # manga = on the chapter axis (fog-able) | anime = anime-only |
            # non_canon = movie/game/ONA/magazine/stage | unknown = no data
            "canon_status": debut["status"],
            "debut_source": debut["source"],
            "affiliation": clean_text(params.get("affiliation", "")) or None,
            "log_pose": clean_text(params.get("log", "")) or None,
            "wiki_url": WIKI_BASE + urllib.parse.quote(title.replace(" ", "_")),
            "source_ref": f"onepiece.fandom.com/wiki/{title.replace(' ', '_')}#Island_Box",
            # Direct infobox reads are "canon"; a status we inferred from the
            # debut medium rather than read outright is "derived".
            "canon_confidence": "canon" if debut["status"] in ("manga", "anime") else "derived",
        })

    by_status = collections.Counter(i["canon_status"] for i in islands)
    with_ch = sum(1 for i in islands if i["debut_chapter"] is not None)
    with_ep = sum(1 for i in islands if i["debut_episode"] is not None)
    with_region = sum(1 for i in islands if i["region"])

    stats = {
        "pages_transcluding_template": len(titles),
        "islands_with_parsed_box": len(islands),
        "pages_missing_box": no_box,
        "with_debut_chapter": with_ch,
        "with_debut_episode": with_ep,
        "with_region": with_region,
        "by_canon_status": dict(by_status),
        "mappable_manga_canon": by_status["manga"],
        "note_on_missing_chapters": (
            f"{by_status['non_canon']} 'islands' debut only in non-canon media (movies, games, "
            f"ONAs, magazines, stage shows) and {by_status['anime']} are anime-only. They have no "
            f"chapter because they are not in the manga — this is correct, not missing data. "
            f"Filter on canon_status == 'manga' for the fog-able set."
        ),
        "top_params": dict(sorted(param_freq.items(), key=lambda kv: -kv[1])[:15]),
    }
    print(f"    parsed {len(islands)} islands")
    print(f"      manga canon (fog-able): {by_status['manga']}  | anime-only: {by_status['anime']}"
          f"  | non-canon: {by_status['non_canon']}  | unknown: {by_status['unknown']}")
    return islands, stats


# ---------------------------------------------------------------------------
# C) CHAPTER -> EPISODE MAP (derived from arc ranges; see note)
# ---------------------------------------------------------------------------

def build_chapter_episode_map(arcs: list[dict]) -> dict:
    """
    PROBE RESULT: a per-chapter map is NOT cheaply available from this wiki.
      - Chapter Box carries title/jname/rname/ename only. No episode field.
      - Episode Box carries titles/airdates/staff. No chapter field, and the
        episode pages do not reference chapters anywhere.
    Getting a true per-chapter map would mean scraping 1185 pages for data the
    infoboxes don't hold. So we DERIVE an arc-granular piecewise map instead,
    and label it honestly. Chapter->episode is not linear inside an arc (anime
    pacing, filler), so we do NOT interpolate a fake per-chapter number.
    """
    segments = []
    for a in sorted([x for x in arcs if x["order"] is not None], key=lambda x: x["order"]):
        if a["chapter_start"] is None:
            continue
        segments.append({
            "arc": a["name"],
            "slug": a["slug"],
            "saga": a["saga"],
            "order": a["order"],
            "chapter_start": a["chapter_start"],
            "chapter_end": a["chapter_end"],
            "chapter_segments": a["chapter_segments"],
            "episode_start": a["episode_start"],
            "episode_end": a["episode_end"],
            "episode_segments": a["episode_segments"],
            "ongoing": a["ongoing"],
        })
    return {
        "granularity": "arc",
        "canon_confidence": "derived",
        "note": (
            "Arc-granular piecewise map. A per-chapter->episode map is NOT available from the "
            "Fandom wiki: Chapter Box has no episode field and Episode Box has no chapter field, "
            "and episode pages never reference chapters. Given a chapter, locate its arc segment "
            "to get the corresponding episode range."
        ),
        "warnings": [
            "Do NOT linearly interpolate inside a segment: anime pacing makes the chapter->episode "
            "relationship non-linear within an arc.",
            "episode_segments is authoritative, NOT [episode_start, episode_end]. The gaps between "
            "segments are FILLER episodes that belong to no canon arc (e.g. Impel Down runs "
            "422-425 and 430-452 — episodes 426-429 are filler). Use segments for membership tests.",
        ],
        "segments": segments,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Sync structured facts from the One Piece Fandom wiki.")
    ap.add_argument("--refresh", action="store_true", help="ignore cache, refetch everything")
    args = ap.parse_args()

    started = time.time()
    GENERATED.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 68)
    print("dead-reckoning :: sync_wiki.py")
    print(f"source: {API}  (CC-BY-SA 3.0, facts only)")
    print(f"policy: {REQUEST_DELAY_S}s/request, maxlag=5, batch={BATCH_SIZE}, cache={'BYPASSED' if args.refresh else 'ON'}")
    print("=" * 68)

    arcs, arc_problems = build_arcs(args.refresh)
    islands, island_stats = build_islands(args.refresh)
    ch_ep = build_chapter_episode_map(arcs)

    write_json(GENERATED / "arcs.json", arcs)
    write_json(GENERATED / "islands.json", islands)
    write_json(GENERATED / "chapter_episode_map.json", ch_ep)

    arcs_with_ch = sum(1 for a in arcs if a["chapter_start"] is not None)
    arcs_with_ep = sum(1 for a in arcs if a["episode_start"] is not None)
    arcs_ordered = sum(1 for a in arcs if a["order"] is not None)

    manifest = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "api": API,
            "license": SOURCE_LICENSE,
            "usage": "Structured facts only (numbers, names, ranges, link targets). No prose, descriptions, or summaries are extracted or stored.",
            "attribution_required_in_ui": True,
        },
        "politeness": {
            "user_agent": USER_AGENT,
            "delay_seconds": REQUEST_DELAY_S,
            "maxlag": 5,
            "batch_size": BATCH_SIZE,
        },
        "requests": {
            "network_requests": STATS["requests"],
            "cache_hits": STATS["cache_hits"],
            "retries": STATS["retries"],
        },
        "duration_seconds": round(time.time() - started, 1),
        "files": {
            "arcs.json": {
                "records": len(arcs),
                "with_chapter_range": arcs_with_ch,
                "with_episode_range": arcs_with_ep,
                "with_resolved_order": arcs_ordered,
                "chain_problems": arc_problems,
            },
            "islands.json": {"records": len(islands), **island_stats},
            "chapter_episode_map.json": {
                "records": len(ch_ep["segments"]),
                "granularity": "arc",
                "canon_confidence": "derived",
            },
        },
        "notes": [
            "MACHINE-OWNED output. Safe to overwrite. Never hand-edit.",
            "This script never writes to canon/ (asserted at runtime).",
            "No crew join data is produced here. Crew joins are hand-authored: the wiki's "
            "'Debut' field is NOT the join chapter (Jinbe debuts ~ep430, joins ~ep977).",
        ],
    }
    write_json(GENERATED / "_wiki_manifest.json", manifest)

    print("\n" + "=" * 68)
    print("RESULTS")
    print("=" * 68)
    print(f"  arcs.json                 {len(arcs):>4} arcs")
    print(f"    with chapter range      {arcs_with_ch:>4}")
    print(f"    with episode range      {arcs_with_ep:>4}")
    print(f"    with resolved order     {arcs_ordered:>4}")
    print(f"  islands.json              {len(islands):>4} islands")
    print(f"    manga canon (fog-able)  {island_stats['by_canon_status'].get('manga', 0):>4}  <- have debut_chapter")
    print(f"    anime-only              {island_stats['by_canon_status'].get('anime', 0):>4}")
    print(f"    non-canon (film/game)   {island_stats['by_canon_status'].get('non_canon', 0):>4}")
    print(f"    unknown                 {island_stats['by_canon_status'].get('unknown', 0):>4}")
    print(f"  chapter_episode_map.json  {len(ch_ep['segments']):>4} arc segments (derived)")
    print()
    print(f"  network requests {STATS['requests']} | cache hits {STATS['cache_hits']} | retries {STATS['retries']}")
    print(f"  elapsed {time.time() - started:.0f}s")

    if arc_problems:
        print("\n  !! VOYAGE CHAIN PROBLEMS:")
        for p in arc_problems:
            print(f"     - {p}")
    else:
        print("\n  voyage chain: OK — one unbroken sequence, no cycles, no orphans.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
