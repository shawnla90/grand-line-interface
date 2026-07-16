#!/usr/bin/env python3
"""normalize.py — build data/canon.json, the ONE file the app reads.

Reads:
  data/raw/*.json          machine-owned mirror of api-onepiece.com   (French, dirty)
  data/generated/*.json    machine-owned facts from the Fandom wiki   (clean)
  canon/*.json             HUMAN-owned: hand-typed values that exist in no upstream source

Writes:
  data/canon.json          the merged build artifact (committed)

THE BOUNDARY: this script may never write into canon/. That is asserted in code,
not just in prose — see assert_not_canon().

FAIL LOUD: an unknown status enum, an unparseable bounty, a U+FFFD anywhere, an
island with no position, or a crew_join sourced from a wiki all RAISE. Silent
coercion is how machine-translated French reaches the UI.

Usage: python3 scripts/normalize.py [--stats]
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
GEN = ROOT / "data" / "generated"
CANON_DIR = ROOT / "canon"
OUT = ROOT / "data" / "canon.json"

REPLACEMENT_CHAR = "�"


class DataError(Exception):
    """A row the normalizer refuses to guess at. Always prints the offending row."""


def die(msg: str, row=None) -> "DataError":
    body = msg
    if row is not None:
        body += "\n  offending row: " + json.dumps(row, ensure_ascii=False)[:600]
    return DataError(body)


# --------------------------------------------------------------------- boundary
def assert_not_canon(path: Path) -> None:
    """canon/ is HUMAN-OWNED. A sync/build script that writes into it is a bug."""
    try:
        path.resolve().relative_to(CANON_DIR.resolve())
    except ValueError:
        return  # not under canon/ — fine
    raise RuntimeError(
        f"ARCHITECTURE VIOLATION: normalize.py tried to write into canon/ ({path}). "
        "canon/ is hand-authored. A script that writes there is a bug, not a feature."
    )


def write_json(path: Path, payload) -> None:
    assert_not_canon(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load(path: Path):
    if not path.exists():
        raise die(f"missing input file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- French parsers
BOUNTY_RE = re.compile(r"^\d{1,3}(\.\d{3})*$")
BARE_INT_RE = re.compile(r"^\d+$")
AGE_RE = re.compile(r"^\s*([\d ]+?)\s*ans\s*$")
SIZE_RE = re.compile(r"^\s*([\d ]+?)\s*cm\s*$")
# '1 à 100' and '802 à ?' (an ongoing saga). Split on ' à ', never on '-'.
SAGA_RANGE_RE = re.compile(r"^\s*(\d+)\s*(?:à|a|-)\s*(\d+|\?)\s*$")

# episodes[].chapter is the free-text bridge from the anime to the manga, and it is the
# spine of this entire product. It is typed by hand upstream and it shows: EIGHT prefix
# spellings across 1162 rows — Chap / Ch. / Ch / Ch.N / Cap / Cha / Chao / Chapitre —
# plus a French range nested inside a list ('Chap 596-(597 à 598)-599') and two rows
# whose whole value is 'Ch. -'.
#
# Every one of those was found by ENUMERATING the distinct shapes in the mirror, not by
# guessing. The allowlist below is exhaustive as of data/raw/episodes.json. Anything
# outside it THROWS: a ninth spelling appearing silently would drop chapters out of the
# fog calculation, and a fog that is quietly wrong is worse than one that crashes.
EP_PREFIX_RE = re.compile(r"^(?:chapitre|chap|chao|cha|cap|ch)\.?\s*", re.IGNORECASE)
EP_FILLER_TAIL_RE = re.compile(r"\s*\+\s*filler$", re.IGNORECASE)
EP_FILLER_RE = re.compile(r"^\[?\s*filler\s*\]?$", re.IGNORECASE)
EP_NESTED_RANGE_RE = re.compile(r"\((\d+)\s*à\s*(\d+)\)")
EP_BODY_RE = re.compile(r"^\d+(?:\s*-\s*\d+)*$")


def parse_bounty(raw, ctx, overrides):
    name = ctx.get("name")
    if name in overrides:
        return overrides[name]
    if raw in (None, "", "-"):
        return None
    s = str(raw).strip()
    if BOUNTY_RE.match(s):
        return int(s.replace(".", ""))
    if BARE_INT_RE.match(s):
        return int(s)
    raise die(
        f"unparseable bounty {s!r} for {name!r}. French thousands-separated string expected "
        f"(e.g. '3.000.000.000'). Add a row to canon/overrides.json:bounty_overrides to repair it.",
        ctx,
    )


def parse_crew_bounty(crew, ov):
    """crews[].total_prime: a French number, or the French words 'inconnu'/'aucune'."""
    raw = crew.get("total_prime")
    if crew["name"] in ov["crew_bounty_overrides"]:
        return ov["crew_bounty_overrides"][crew["name"]]
    key = "" if raw is None else str(raw).strip()
    if key in ov["crew_bounty_tokens"]:
        return ov["crew_bounty_tokens"][key]
    return parse_bounty(raw, {"name": crew["name"]}, {})


def parse_age(raw, ctx, overrides):
    s = "" if raw is None else str(raw).strip()
    if s in overrides:
        return overrides[s]
    if s == "":
        return None
    m = AGE_RE.match(s)
    if m:
        return int(m.group(1).replace(" ", ""))
    if BARE_INT_RE.match(s):
        return int(s)
    raise die(
        f"unparseable age {s!r} for {ctx.get('name')!r}. Expected 'NN ans'. "
        "Add it to canon/overrides.json:age_overrides.",
        ctx,
    )


def parse_size_cm(raw, ctx, overrides):
    s = "" if raw is None else str(raw).strip()
    if s in overrides:
        return overrides[s]
    if s == "":
        return None
    m = SIZE_RE.match(s)
    if m:
        return int(m.group(1).replace(" ", ""))
    raise die(
        f"unparseable size {s!r} for {ctx.get('name')!r}. Expected 'NNNcm'. "
        "Add it to canon/overrides.json:size_overrides.",
        ctx,
    )


def parse_french_range(raw, field, ctx):
    """'1 à 100' -> {'start': 1, 'end': 100}. Split on ' à ', never on '-'."""
    # '-' is upstream's "not filled in yet" (the Final Saga has no declared range).
    if raw in (None, "", "-", "?"):
        return None
    m = SAGA_RANGE_RE.match(str(raw))
    if not m:
        raise die(f"unparseable French range {raw!r} in field {field!r}. Expected 'N à M'.", ctx)
    start = int(m.group(1))
    end = None if m.group(2) == "?" else int(m.group(2))  # '?' = the saga is still running
    if end is not None and end < start:
        raise die(f"inverted range {raw!r} in {field!r}", ctx)
    return {"start": start, "end": end}


def parse_episode_chapters(raw, ctx):
    """episodes[].chapter -> list[int]. The dirty bridge from anime to manga.

    'Chap 2' | 'Chap 3-4-5' | 'Ch. 1118-1119' | 'Ch 12' | 'Chap 30 + filler' | '[Filler]' | ''
    Anything outside that allowlist THROWS. Six prefix spellings is exactly the
    silent-coercion trap the fail-loud rule exists for.
    """
    if raw is None:
        return []
    s = str(raw).strip()
    if s == "" or EP_FILLER_RE.match(s):
        return []

    m = EP_PREFIX_RE.match(s)
    if not m:
        raise die(
            f"unrecognised episode->chapter prefix in {s!r}. The allowlist is "
            "Chapitre|Chap|Chao|Cha|Cap|Ch (optional '.'). Upstream added a NINTH spelling — "
            "widen the allowlist deliberately, do not coerce.",
            ctx,
        )
    body = EP_FILLER_TAIL_RE.sub("", s[m.end():]).strip()

    # 'Ch. -' — the field exists but carries no chapter. Not filler, just blank.
    if body in ("", "-"):
        return []

    # one row nests a French range inside the dash list: 'Chap 596-(597 à 598)-599'
    def expand(mm):
        lo, hi = int(mm.group(1)), int(mm.group(2))
        if hi < lo or hi - lo > 50:
            raise die(f"implausible nested range {mm.group(0)!r} in {s!r}", ctx)
        return "-".join(str(n) for n in range(lo, hi + 1))

    body = EP_NESTED_RANGE_RE.sub(expand, body)

    if not EP_BODY_RE.match(body):
        raise die(
            f"unrecognised episode->chapter body {body!r} (from {s!r}). Expected "
            "'N' or 'N-N-N'. Widen the allowlist deliberately, do not coerce.",
            ctx,
        )
    return [int(x.strip()) for x in body.split("-")]


def parse_number(raw, ctx):
    """'n°1' -> 1"""
    if raw in (None, ""):
        return None
    m = re.match(r"^\s*n[°º]?\s*(\d+)\s*$", str(raw), re.IGNORECASE)
    if not m:
        if BARE_INT_RE.match(str(raw).strip()):
            return int(str(raw).strip())
        raise die(f"unparseable number {raw!r}", ctx)
    return int(m.group(1))


def enum(raw, table, field, ctx):
    key = "" if raw is None else str(raw).strip()
    if key not in table:
        raise die(
            f"unknown {field} value {key!r}. The canonical enum lives in canon/overrides.json. "
            "Add the mapping there — do not coerce.",
            ctx,
        )
    return table[key]


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = s.replace("&", " and ")
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_]+", "-", s)
    return re.sub(r"-{2,}", "-", s).strip("-")


def scan_mojibake(obj, path="$"):
    """U+FFFD anywhere in the artifact is a hard failure."""
    hits = []
    if isinstance(obj, str):
        if REPLACEMENT_CHAR in obj:
            hits.append((path, obj[:120]))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            hits += scan_mojibake(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits += scan_mojibake(v, f"{path}[{i}]")
    return hits


# ------------------------------------------------------------------------ build
def main() -> int:
    ov = load(CANON_DIR / "overrides.json")
    joins_doc = load(CANON_DIR / "crew_joins.json")
    coords_doc = load(CANON_DIR / "islands.coords.json")
    voyage_doc = load(CANON_DIR / "voyage_legs.json")
    vessels_doc = load(CANON_DIR / "vessels.json")
    presence_doc = load(CANON_DIR / "crew_presence.json")
    fruit_reveals_doc = load(CANON_DIR / "fruit_reveals.json")
    haki_users_doc = load(CANON_DIR / "haki_users.json")

    status_map = ov["character_status"]
    crew_status_map = ov["crew_status"]
    fruit_type_map = ov["fruit_types"]
    crew_name_map = ov["crew_names"]
    char_name_map = ov["character_names"]
    bounty_ov = ov["bounty_overrides"]
    age_ov = ov["age_overrides"]
    size_ov = ov["size_overrides"]

    raw_chars = load(RAW / "characters.json")
    raw_crews = load(RAW / "crews.json")
    raw_fruits = load(RAW / "fruits.json")
    raw_sagas = load(RAW / "sagas.json")
    raw_eps = load(RAW / "episodes.json")
    # Phase 7A: the endpoints we mirrored for months and never merged.
    raw_boats = load(RAW / "boats.json")
    raw_locates = load(RAW / "locates.json")
    raw_swords = load(RAW / "swords.json")
    raw_dials = load(RAW / "dials.json")
    raw_gears = load(RAW / "luffy_gears.json")
    raw_techs = load(RAW / "luffy_techniques.json")
    manifest_bytes = (RAW / "_manifest.json").read_bytes()

    gen_arcs = load(GEN / "arcs.json")
    gen_islands = load(GEN / "islands.json")

    warnings: list[str] = []

    # ---------------------------------------------------------------- sagas
    sagas = []
    for s in raw_sagas:
        sagas.append({
            "id": s["id"],
            "title": s["title"],
            "number": int(s["saga_number"]),
            "chapters": parse_french_range(s.get("saga_chapitre"), "saga_chapitre", s),
            "volumes": parse_french_range(s.get("saga_volume"), "saga_volume", s),
            "episodes": parse_french_range(s.get("saga_episode"), "saga_episode", s),
            "source_ref": "api-onepiece.com/v2/sagas/en",
            "canon_confidence": "canon",
        })

    # ----------------------------------------------------------------- arcs
    arcs = []
    for a in sorted(gen_arcs, key=lambda x: x["order"]):
        arcs.append({
            "slug": a["slug"],
            "name": a["name"],
            "saga": a["saga"],
            "order": a["order"],
            "chapter_start": a["chapter_start"],
            "chapter_end": a["chapter_end"],
            "chapter_segments": a["chapter_segments"],
            "episode_start": a["episode_start"],
            "episode_end": a["episode_end"],
            "episode_segments": a["episode_segments"],
            "ongoing": a["ongoing"],
            "prev_arc": a["prev_arc"],
            "next_arc": a["next_arc"],
            "source_ref": a["source_ref"],
            "canon_confidence": a["canon_confidence"],
        })

    # the arc chain must be unbroken — a gap here fogs the wrong half of the map
    for i, a in enumerate(arcs):
        if a["order"] != i:
            raise die(f"arc order is not a dense 0..N chain: expected {i}, got {a['order']}", a)

    def arc_for_chapter(ch):
        if ch is None:
            return None
        for a in arcs:
            for lo, hi in a["chapter_segments"]:
                if ch >= lo and (hi is None or ch <= hi):
                    return a
        return None

    def arc_for_episode(ep):
        if ep is None:
            return None
        for a in arcs:
            for lo, hi in a["episode_segments"]:
                if ep >= lo and (hi is None or ep <= hi):
                    return a
        return None  # gaps between segments are FILLER — belonging to no canon arc

    # -------------------------------------------------------------- islands
    coords = {c["slug"]: c for c in coords_doc["islands"]}
    islands = []
    for isl in gen_islands:
        slug = isl["slug"]
        pos = coords.get(slug)
        if pos is None or pos.get("lng") is None or pos.get("lat") is None:
            raise die(
                f"island {slug!r} has no position. RULE: position is NOT NULL from commit #1. "
                "Every island gets a pin; hand-authoring only UPGRADES its confidence. "
                "Add it to canon/islands.coords.json.",
                isl,
            )
        arc = arc_for_chapter(isl.get("debut_chapter"))
        islands.append({
            "slug": slug,
            "name": isl["name"],
            "japanese": isl.get("japanese"),
            "romaji": isl.get("romaji"),
            "region": isl.get("region"),
            "sea": pos["sea"],
            "lng": pos["lng"],
            "lat": pos["lat"],
            "debut_chapter": isl.get("debut_chapter"),
            "debut_episode": isl.get("debut_episode"),
            "debut_arc": arc["slug"] if arc else None,
            "debut_saga": arc["saga"] if arc else None,
            "canon_status": isl["canon_status"],
            "debut_source": isl.get("debut_source"),
            "affiliation": isl.get("affiliation"),
            "wiki_url": isl.get("wiki_url"),
            # the pin's confidence is the POSITION's confidence — that is what the UI renders
            "canon_confidence": pos["canon_confidence"],
            "source_ref": f"{isl.get('source_ref')} | position: {pos['source_ref']}",
        })

    # ---------------------------------------------------------------- crews
    crews = []
    crew_by_id = {}
    for c in raw_crews:
        name = crew_name_map.get(c["name"], c["name"])
        row = {
            "id": c["id"],
            "name": name,
            "raw_name": c["name"],
            "romanized": c.get("roman_name"),
            "status": enum(c.get("status"), crew_status_map, "crew status", c),
            "total_bounty": parse_crew_bounty(c, ov),
            "member_count": int(c["number"]) if str(c.get("number") or "").isdigit() else None,
            "is_yonko": bool(c.get("is_yonko")),
            "source_ref": "api-onepiece.com/v2/crews/en"
                          + (" + canon/overrides.json:crew_names" if c["name"] in crew_name_map else ""),
            "canon_confidence": "canon" if c["name"] in crew_name_map else "derived",
        }
        crews.append(row)
        crew_by_id[c["id"]] = row

    # --------------------------------------------------------------- fruits
    fruits = []
    fruit_by_id = {}
    for f in raw_fruits:
        row = {
            "id": f["id"],
            "name": f["name"],
            "romanized": f.get("roman_name"),
            "type": enum(f.get("type"), fruit_type_map, "fruit type", f),
            # 7A: the one-line power description finally ships (212/213 filled).
            "description": (f.get("description") or None),
            # `filename` is deliberately dropped: only ~23/213 resolve, and those are
            # traced official Oda art on a hobbyist box. We do not hotlink it.
            "source_ref": "api-onepiece.com/v2/fruits/en + canon/overrides.json:fruit_types",
            "canon_confidence": "canon",
        }
        fruits.append(row)
        fruit_by_id[f["id"]] = row

    # ----------------------------------------------------------- characters
    characters = []
    for ch in raw_chars:
        name = char_name_map.get(ch["name"], ch["name"])
        crew = ch.get("crew") or {}
        fruit = ch.get("fruit") or {}
        crew_row = crew_by_id.get(crew.get("id"))
        fruit_row = fruit_by_id.get(fruit.get("id"))
        if crew.get("id") and not crew_row:
            raise die(f"character {name!r} references crew id {crew.get('id')} that is not in crews.json", ch)
        if fruit.get("id") and not fruit_row:
            raise die(f"character {name!r} references fruit id {fruit.get('id')} that is not in fruits.json", ch)
        characters.append({
            "id": ch["id"],
            "name": name,
            "slug": slugify(name),
            "status": enum(ch.get("status"), status_map, "character status", ch),
            "bounty": parse_bounty(ch.get("bounty"), ch, bounty_ov),
            "age": parse_age(ch.get("age"), ch, age_ov),
            "size_cm": parse_size_cm(ch.get("size"), ch, size_ov),
            "job": (ch.get("job") or None),
            "crew_id": crew_row["id"] if crew_row else None,
            "crew_name": crew_row["name"] if crew_row else None,
            "fruit_id": fruit_row["id"] if fruit_row else None,
            "fruit_name": fruit_row["name"] if fruit_row else None,
            "source_ref": "api-onepiece.com/v2/characters/en + canon/overrides.json",
            "canon_confidence": "derived",
        })

    # ------------------------------------------------------------- episodes
    episodes = []
    ep_missing_arc = []
    for e in raw_eps:
        num = parse_number(e.get("number"), e) or e["id"]
        arc = arc_for_episode(num)
        chapters = parse_episode_chapters(e.get("chapter"), e)
        if arc is None:
            ep_missing_arc.append(num)
        episodes.append({
            "id": e["id"],
            "number": num,
            "title": e["title"],
            # descriptions are DROPPED on purpose: 3.07 MB of the 3.7 MB corpus is
            # machine-translated French episode prose the app never renders.
            "chapters": chapters,
            "arc": arc["slug"] if arc else None,
            "saga": arc["saga"] if arc else None,
            "filler": not chapters,
            "release_date": e.get("release_date"),
            "source_ref": "api-onepiece.com/v2/episodes/en (episode->chapter) + "
                          "data/generated/arcs.json episode_segments (episode->arc)",
            "canon_confidence": "derived",
        })
    if ep_missing_arc:
        warnings.append(
            f"{len(ep_missing_arc)} episodes fall in no canon arc segment (filler between arcs, "
            f"plus the Uta/Film Red tie-ins 1029/1030). This is correct: the gaps between "
            f"episode_segments ARE filler."
        )

    # ------------------------------------------- the arsenal (Phase 7A)
    # Six tables mirrored since Phase 1 and never merged. Minimal normalization:
    # ids validated against their referenced tables, names slugged for joins,
    # free-text `type` fields kept verbatim (no enum guessing on French labels).
    char_by_id = {c["id"]: c for c in characters}

    boats = []
    for b in raw_boats:
        crew = b.get("crew") or {}
        captain = b.get("character_captain") or {}
        crew_row = crew_by_id.get(crew.get("id"))
        cap_row = char_by_id.get(captain.get("id"))
        boats.append({
            "id": b["id"],
            "name": b["name"],
            "slug": slugify(b["name"]),
            "romanized": b.get("roman_name"),
            "type": (b.get("type") or None),
            "crew_id": crew_row["id"] if crew_row else None,
            "crew_name": crew_row["name"] if crew_row else None,
            "captain_id": cap_row["id"] if cap_row else None,
            "captain_name": cap_row["name"] if cap_row else None,
            "source_ref": "api-onepiece.com/v2/boats/en",
            "canon_confidence": "derived",
        })

    locations = []
    for l in raw_locates:
        locations.append({
            "id": l["id"],
            "name": l["name"],
            "slug": slugify(l["name"]),
            "romanized": l.get("roman_name"),
            "sea": (l.get("sea_name") or None),
            "region": (l.get("region_name") or None),
            "affiliation": (l.get("affiliation_name") or None),
            "source_ref": "api-onepiece.com/v2/locates/en",
            "canon_confidence": "derived",
        })

    swords = []
    for s in raw_swords:
        swords.append({
            "name": s["name"],
            "slug": slugify(s["name"]),
            "romanized": s.get("roman_name"),
            "type": (s.get("type") or None),
            "category": (s.get("category") or None),
            "description": (s.get("description") or None),
            "destroyed": bool(s.get("isDestroy")),
            "source_ref": "api-onepiece.com/v2/swords/en",
            "canon_confidence": "derived",
        })

    dials = [{
        "name": d["name"],
        "slug": slugify(d["name"]),
        "type": (d.get("type") or None),
        "source_ref": "api-onepiece.com/v2/dials/en",
        "canon_confidence": "derived",
    } for d in raw_dials]

    luffy_gears = [{
        "id": g["id"],
        "name": g["name"],
        "description": (g.get("description") or None),
        "technique_count": g.get("count_technique"),
        "source_ref": "api-onepiece.com/v2/luffy-gears/en",
        "canon_confidence": "derived",
    } for g in raw_gears]

    luffy_techniques = [{
        "id": t["id"],
        "name": t["name"],
        "translation": (t.get("translation") or None),
        "type": (t.get("type") or None),
        "description": (t.get("description") or None),
        "post_timeskip": bool(t.get("after_ellipsis")),
        "source_ref": "api-onepiece.com/v2/luffy-techniques/en",
        "canon_confidence": "derived",
    } for t in raw_techs]

    # ----------------------------------------------------------- crew joins
    crew_joins = []
    for j in joins_doc["crew_joins"]:
        src = (j.get("source_ref") or "")
        if not src:
            raise die("crew_join has no source_ref. Every authored row carries one. NOT NULL.", j)
        # THE JINBE GUARD. A crew join may only come from a human. The source_ref must
        # DECLARE itself hand-authored, and it may not CLAIM a wiki/scrape as its origin.
        # (Mentioning the wiki to explain why it is wrong is fine — and necessary.)
        if not src.lower().lstrip().startswith("hand-authored"):
            raise die(
                "crew_join source_ref does not declare itself 'Hand-authored'. THE JINBE BUG: "
                "every upstream source has a Debut field, and Debut is not Join — it is wrong for "
                "10/10 Straw Hats (Jinbe debuts at ep 430, joins at ep 977). Crew joins are "
                "hand-typed or they are not shipped.",
                j,
            )
        if re.search(
            r"\b(sourced\s+from|scraped\s+from|imported\s+from|per\s+the)\b[^.]{0,30}"
            r"\b(wiki|fandom|api-onepiece|debut\s+field)\b",
            src, re.IGNORECASE,
        ):
            raise die(
                "crew_join source_ref claims a wiki/scrape as its origin. That field is Debut, "
                "not Join. Hand-type it or drop it.",
                j,
            )
        if j.get("verified") is not False and "hand-authored" not in src.lower():
            raise die("crew_join is marked verified but has no human source_ref.", j)
        arc = next((a for a in arcs if a["slug"] == j["join_arc"]), None)
        if arc is None:
            raise die(f"crew_join join_arc {j['join_arc']!r} is not a known arc slug", j)
        crew_joins.append({
            "name": j["name"],
            "slug": j["slug"],
            "crew": joins_doc["crew"],
            "crew_slug": joins_doc["crew_slug"],
            "join_chapter": j["join_chapter"],
            "join_episode": j["join_episode"],
            "join_arc": j["join_arc"],
            "join_saga": arc["saga"],
            "order": j["order"],
            "source_ref": src,
            "canon_confidence": j["canon_confidence"],
            "verified": bool(j["verified"]),
        })
    crew_joins.sort(key=lambda r: r["order"])
    if any(not r["verified"] for r in crew_joins):
        warnings.append(
            "crew_joins contains UNVERIFIED rows. Shawn has not confirmed them against the manga. "
            "The UI must render them as unverified and no content ships on them."
        )

    # ------------------------------------------------------------- voyage
    # The authored route. Each waypoint resolves to a position (an island slug, or
    # an explicit lng/lat for open-sea points). Chapters must only move forward — a
    # voyage that goes backward in the story is a data error, not a shortcut.
    voyage_waypoints = []
    last_ch = None
    for w in sorted(voyage_doc["waypoints"], key=lambda r: r["order"]):
        src = (w.get("source_ref") or "")
        if not src.lower().lstrip().startswith("hand-authored"):
            raise die(
                "voyage waypoint source_ref must declare itself 'Hand-authored'. The route is "
                "authored (no upstream source stamps a chapter onto a sea route), not scraped.",
                w,
            )
        slug = w.get("slug")
        if w.get("lng") is not None and w.get("lat") is not None:
            lng, lat = float(w["lng"]), float(w["lat"])
        elif slug is not None:
            pos = coords.get(slug)
            if pos is None or pos.get("lng") is None or pos.get("lat") is None:
                raise die(
                    f"voyage waypoint slug {slug!r} resolves to no coordinate in "
                    "canon/islands.coords.json. Every waypoint must have a position; fix the slug "
                    "or give the waypoint an explicit lng/lat.",
                    w,
                )
            lng, lat = pos["lng"], pos["lat"]
        else:
            raise die("voyage waypoint has neither a slug nor an explicit lng/lat.", w)
        ch = w["chapter"]
        if last_ch is not None and ch < last_ch:
            raise die(
                f"voyage waypoints must be non-decreasing in chapter (order {w['order']} "
                f"chapter {ch} < previous {last_ch}). The route only moves forward in the story.",
                w,
            )
        last_ch = ch
        voyage_waypoints.append({
            "order": w["order"],
            "slug": slug,
            "label": w["label"],
            "chapter": ch,
            "lng": lng,
            "lat": lat,
            "source_ref": src,
            "canon_confidence": w["canon_confidence"],
            "verified": bool(w["verified"]),
        })
    voyage = {
        "crew": voyage_doc["crew"],
        "crew_slug": voyage_doc["crew_slug"],
        "waypoints": voyage_waypoints,
    }
    if any(not w["verified"] for w in voyage_waypoints):
        warnings.append(
            "voyage_legs contains UNVERIFIED waypoints. Route chapter stamps are not manga-confirmed. "
            "The UI must render the route as unverified."
        )

    # ------------------------------------------------------------- vessels
    # The ship progression, chapter-gated. A reader at ch. 20 must see the small
    # boat, never the Thousand Sunny. from_chapter only moves forward.
    vessels = []
    last_from = None
    for v in sorted(vessels_doc["vessels"], key=lambda r: r["order"]):
        src = (v.get("source_ref") or "")
        if not src.lower().lstrip().startswith("hand-authored"):
            raise die("vessel source_ref must declare itself 'Hand-authored'.", v)
        fr = v["from_chapter"]
        if last_from is not None and fr < last_from:
            raise die(
                f"vessels must be non-decreasing in from_chapter (vessel {v['slug']!r} "
                f"{fr} < previous {last_from}).",
                v,
            )
        last_from = fr
        vessels.append({
            "order": v["order"],
            "name": v["name"],
            "slug": v["slug"],
            "from_chapter": fr,
            "source_ref": src,
            "canon_confidence": v["canon_confidence"],
            "verified": bool(v["verified"]),
        })
    if any(not v["verified"] for v in vessels):
        warnings.append(
            "vessels contains UNVERIFIED rows. Ship-acquisition chapters are not manga-confirmed. "
            "The UI must render them as unverified."
        )

    # ------------------------------------------------------------- presence
    # Who is WHERE as of a chapter. Authored windows: the active one at chapter
    # N is the last whose from_chapter <= N, unless its to_chapter has passed
    # (a death, an arrest, a departure). No upstream source has this axis at
    # all — the API stores one current-day value per entity — so every row is
    # hand-typed, and a from_chapter of 0 (the seed scaffold's sentinel) is
    # rejected here so a scaffold row can never reach the artifact.
    def build_windows(windows, owner_slug):
        out = []
        last_from = None
        for w in sorted(windows, key=lambda r: r["order"]):
            src = (w.get("source_ref") or "")
            if not src.lower().lstrip().startswith("hand-authored"):
                raise die(f"presence window for {owner_slug!r} source_ref must declare itself "
                          "'Hand-authored'. Presence is authored, not scraped.", w)
            fr = w["from_chapter"]
            if not isinstance(fr, int) or fr < 1:
                raise die(f"presence window for {owner_slug!r} has from_chapter {fr!r}. It must be "
                          ">= 1 — a 0 is the seed scaffold's sentinel and means a human never "
                          "typed the real chapter.", w)
            to = w.get("to_chapter")
            if to is not None and (not isinstance(to, int) or to < fr):
                raise die(f"presence window for {owner_slug!r} has to_chapter {to!r} < "
                          f"from_chapter {fr}. A window cannot end before it starts.", w)
            if last_from is not None and fr < last_from:
                raise die(f"presence windows for {owner_slug!r} must be non-decreasing in "
                          f"from_chapter (order {w['order']}: {fr} < previous {last_from}).", w)
            last_from = fr
            slug = w.get("island_slug")
            if w.get("lng") is not None and w.get("lat") is not None:
                lng, lat = float(w["lng"]), float(w["lat"])
            elif slug is not None:
                pos = coords.get(slug)
                if pos is None or pos.get("lng") is None or pos.get("lat") is None:
                    raise die(f"presence window for {owner_slug!r} island_slug {slug!r} resolves "
                              "to no coordinate in canon/islands.coords.json. Fix the slug or "
                              "give the window an explicit lng/lat.", w)
                lng, lat = pos["lng"], pos["lat"]
            else:
                raise die(f"presence window for {owner_slug!r} has neither an island_slug nor an "
                          "explicit lng/lat.", w)
            out.append({
                "order": w["order"],
                "island_slug": slug,
                "label": w["label"],
                "from_chapter": fr,
                "to_chapter": to,
                "lng": lng,
                "lat": lat,
                "source_ref": src,
                "canon_confidence": w["canon_confidence"],
                "verified": bool(w["verified"]),
            })
        if not out:
            raise die(f"presence entity {owner_slug!r} has no windows — it can never render.")
        return out

    def build_members(members, owner_slug):
        out = []
        for m in members:
            src = (m.get("source_ref") or "")
            if not src.lower().lstrip().startswith("hand-authored"):
                raise die(f"presence member for {owner_slug!r} source_ref must declare itself "
                          "'Hand-authored'.", m)
            fr = m["from_chapter"]
            if not isinstance(fr, int) or fr < 1:
                raise die(f"presence member {m.get('slug')!r} has from_chapter {fr!r} (< 1).", m)
            out.append({
                "slug": m["slug"],
                "name": m["name"],
                "from_chapter": fr,
                "source_ref": src,
                "canon_confidence": m["canon_confidence"],
                "verified": bool(m["verified"]),
            })
        return out

    presence_crews = []
    seen_presence_slugs: set[str] = set()
    for pc in presence_doc["crews"]:
        slug = pc["slug"]
        if "roger" in slug:
            raise die("the Roger Pirates disbanded before chapter 1 — a defunct crew has no "
                      "presence. Remove them.", pc)
        if slug in seen_presence_slugs:
            raise die(f"duplicate presence slug {slug!r}", pc)
        seen_presence_slugs.add(slug)
        presence_crews.append({
            "slug": slug,
            "name": pc["name"],
            "crew_id": pc.get("crew_id"),
            "vessel": pc.get("vessel"),
            "members": build_members(pc.get("members", []), slug),
            "windows": build_windows(pc["windows"], slug),
        })

    presence_characters = []
    for ch_p in presence_doc["characters"]:
        slug = ch_p["slug"]
        if slug in seen_presence_slugs:
            raise die(f"duplicate presence slug {slug!r}", ch_p)
        seen_presence_slugs.add(slug)
        crew_slug = ch_p.get("crew_slug")
        if crew_slug is not None and crew_slug not in {c["slug"] for c in presence_crews}:
            raise die(f"presence character {slug!r} references crew_slug {crew_slug!r} that is "
                      "not a presence crew.", ch_p)
        presence_characters.append({
            "slug": slug,
            "name": ch_p["name"],
            "affiliation": ch_p["affiliation"],
            "crew_slug": crew_slug,
            "windows": build_windows(ch_p["windows"], slug),
        })

    presence = {"crews": presence_crews, "characters": presence_characters}
    presence_windows = [w for e in presence_crews + presence_characters for w in e["windows"]]
    if any(not w["verified"] for w in presence_windows):
        warnings.append(
            "crew_presence contains UNVERIFIED windows. Who-is-where chapter stamps are not "
            "manga-confirmed. The UI must render presence as unverified."
        )

    # --------------------------------------------------------------- powers
    # Fruit reveals and haki facts are STORY REVEALS with their own chapter
    # gates — no upstream source records when the reader learns a power, so
    # every row is hand-typed (canon/fruit_reveals.json, canon/haki_users.json).
    # The facts are embedded onto the presence entities they belong to: the
    # client join is free and there is exactly one gate shape.
    HAKI_TYPES = {"observation", "armament", "conqueror"}
    fruit_display_types = set(fruit_type_map.values())

    presence_entities: dict[str, dict] = {}
    for pc in presence_crews:
        for m in pc["members"]:
            if m["slug"] in presence_entities:
                raise die(f"presence member slug {m['slug']!r} appears in more than one crew — "
                          "power facts key on the slug and cannot be ambiguous.", m)
            presence_entities[m["slug"]] = m
    for ch_p in presence_characters:
        presence_entities[ch_p["slug"]] = ch_p
    for e in presence_entities.values():
        e["fruit"] = None
        e["haki"] = []

    def check_power_row(row, kind):
        src = (row.get("source_ref") or "")
        if not src.lower().lstrip().startswith("hand-authored"):
            raise die(f"{kind} for {row.get('slug')!r} source_ref must declare itself "
                      "'Hand-authored'. Powers are authored, not scraped.", row)
        fr = row["from_chapter"]
        if not isinstance(fr, int) or fr < 1:
            raise die(f"{kind} for {row.get('slug')!r} has from_chapter {fr!r}. It must be "
                      ">= 1 — a 0 is the seed scaffold's sentinel and means a human never "
                      "typed the real chapter.", row)
        if row["canon_confidence"] not in {"canon", "derived", "guess"}:
            raise die(f"{kind} for {row.get('slug')!r} has canon_confidence "
                      f"{row['canon_confidence']!r}.", row)
        if row["slug"] not in presence_entities:
            raise die(f"{kind} for {row['slug']!r} matches no presence member or character — "
                      "a reveal for someone who can never render is dead data.", row)

    fruit_reveals = []
    for r in fruit_reveals_doc["reveals"]:
        check_power_row(r, "fruit reveal")
        if r["fruit_type"] not in fruit_display_types:
            raise die(f"fruit reveal for {r['slug']!r} has fruit_type {r['fruit_type']!r} — not "
                      f"one of the normalized types {sorted(fruit_display_types)}.", r)
        if r.get("fruit_id") is not None and r["fruit_id"] not in fruit_by_id:
            raise die(f"fruit reveal for {r['slug']!r} references fruit id {r['fruit_id']!r} "
                      "that is not in fruits.json.", r)
        ent = presence_entities[r["slug"]]
        if ent["fruit"] is not None:
            raise die(f"duplicate fruit reveal for {r['slug']!r} — one fruit per entity.", r)
        ent["fruit"] = {
            "fruit_id": r.get("fruit_id"),
            "fruit_name": r["fruit_name"],
            "fruit_type": r["fruit_type"],
            "from_chapter": r["from_chapter"],
            "source_ref": r["source_ref"],
            "canon_confidence": r["canon_confidence"],
            "verified": bool(r["verified"]),
        }
        fruit_reveals.append(ent["fruit"])

    haki_facts = []
    seen_haki: set[tuple[str, str]] = set()
    for r in haki_users_doc["users"]:
        check_power_row(r, "haki fact")
        if r["haki"] not in HAKI_TYPES:
            raise die(f"haki fact for {r['slug']!r} has haki {r['haki']!r} — not one of "
                      f"{sorted(HAKI_TYPES)}.", r)
        key = (r["slug"], r["haki"])
        if key in seen_haki:
            raise die(f"duplicate haki fact {key!r} — one row per (user, haki-type).", r)
        seen_haki.add(key)
        fact = {
            "haki": r["haki"],
            "from_chapter": r["from_chapter"],
            "source_ref": r["source_ref"],
            "canon_confidence": r["canon_confidence"],
            "verified": bool(r["verified"]),
        }
        presence_entities[r["slug"]]["haki"].append(fact)
        haki_facts.append(fact)

    for e in presence_entities.values():
        e["haki"].sort(key=lambda f: f["from_chapter"])

    if any(not r["verified"] for r in fruit_reveals):
        warnings.append(
            "fruit_reveals contains UNVERIFIED rows. Fruit reveal chapters are not "
            "manga-confirmed. The UI must render fruit facts as unverified."
        )
    if any(not f["verified"] for f in haki_facts):
        warnings.append(
            "haki_users contains UNVERIFIED rows. Haki reveal chapters are not "
            "manga-confirmed. The UI must render haki facts as unverified."
        )

    # ------------------------------------------------------------------ out
    payload = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generator": "scripts/normalize.py",
            "source_manifest_sha": hashlib.sha256(manifest_bytes).hexdigest(),
            "sources": {
                "api": "api-onepiece.com v2 (machine-translated French; mirrored to data/raw/)",
                "wiki": "One Piece Fandom, CC-BY-SA 3.0 — structured facts only, no prose",
                "canon": "canon/ — hand-authored, human-owned",
            },
            "attribution_required_in_ui": True,
            "canon_confidence_values": ["canon", "derived", "guess"],
            "warnings": warnings,
            "counts": {
                "sagas": len(sagas),
                "arcs": len(arcs),
                "islands": len(islands),
                "islands_manga_canon": sum(1 for i in islands if i["canon_status"] == "manga"),
                "islands_with_position": sum(1 for i in islands if i["lng"] is not None),
                "characters": len(characters),
                "crews": len(crews),
                "fruits": len(fruits),
                "episodes": len(episodes),
                "crew_joins": len(crew_joins),
                "crew_joins_verified": sum(1 for j in crew_joins if j["verified"]),
                "voyage_waypoints": len(voyage_waypoints),
                "voyage_waypoints_verified": sum(1 for w in voyage_waypoints if w["verified"]),
                "vessels": len(vessels),
                "vessels_verified": sum(1 for v in vessels if v["verified"]),
                "presence_crews": len(presence_crews),
                "presence_characters": len(presence_characters),
                "presence_windows": len(presence_windows),
                "presence_windows_verified": sum(1 for w in presence_windows if w["verified"]),
                "fruit_reveals": len(fruit_reveals),
                "fruit_reveals_verified": sum(1 for r in fruit_reveals if r["verified"]),
                "haki_facts": len(haki_facts),
                "haki_facts_verified": sum(1 for f in haki_facts if f["verified"]),
                "haki_users": len({k[0] for k in seen_haki}),
                "boats": len(boats),
                "locations": len(locations),
                "swords": len(swords),
                "dials": len(dials),
                "luffy_gears": len(luffy_gears),
                "luffy_techniques": len(luffy_techniques),
            },
        },
        "sagas": sagas,
        "arcs": arcs,
        "islands": islands,
        "characters": characters,
        "crews": crews,
        "fruits": fruits,
        "episodes": episodes,
        "crew_joins": crew_joins,
        "voyage": voyage,
        "vessels": vessels,
        "presence": presence,
        # Phase 7A — the arsenal. Small tables (~120KB total) that make entity
        # views possible: every crew's ship, canonical locations with sea/region
        # joins, the named blades, dials, and Luffy's whole move-list.
        "boats": boats,
        "locations": locations,
        "swords": swords,
        "dials": dials,
        "luffy_gears": luffy_gears,
        "luffy_techniques": luffy_techniques,
    }

    hits = scan_mojibake(payload)
    if hits:
        for p, v in hits[:20]:
            print(f"  U+FFFD at {p}: {v!r}", file=sys.stderr)
        raise die(f"{len(hits)} U+FFFD replacement characters in the build artifact. "
                  "Mojibake reached the output — refusing to write.")

    write_json(OUT, payload)

    c = payload["meta"]["counts"]
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size:,} bytes)")
    for k, v in c.items():
        print(f"  {k:24s} {v}")
    conf = {}
    for i in islands:
        conf[i["canon_confidence"]] = conf.get(i["canon_confidence"], 0) + 1
    print(f"  island position confidence  {conf}")
    for w in warnings:
        print(f"  WARNING: {w}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except DataError as exc:
        print("\nNORMALIZE FAILED (fail-loud, by design):\n", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        sys.exit(1)
