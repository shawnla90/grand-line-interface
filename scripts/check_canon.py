#!/usr/bin/env python3
"""check_canon.py — the guard suite for data/canon.json.

These are not unit tests of the code. They are assertions about the DATA, run on
the artifact the app actually ships. Every one of them exists because a specific
way of being wrong would reach 5.3 million One Piece readers.

Run: python3 scripts/check_canon.py
Exit 0 = the artifact is shippable. Exit 1 = it is not, and the test that fired says why.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANON_JSON = ROOT / "data" / "canon.json"
CANON_DIR = ROOT / "canon"
REPLACEMENT_CHAR = chr(0xFFFD)

STATUS_ENUM = {"alive", "dead", "unknown"}
CREW_STATUS_ENUM = {"active", "inactive", "disbanded", "unknown"}
CONFIDENCE_ENUM = {"canon", "derived", "guess"}

results: list[tuple[str, bool, str]] = []


def check(name: str):
    def deco(fn):
        def run(doc):
            try:
                detail = fn(doc) or "ok"
                results.append((name, True, detail))
            except AssertionError as exc:
                results.append((name, False, str(exc)))
        run.__name__ = name
        return run
    return deco


# ---------------------------------------------------------------------------
@check("jinbe_test")
def jinbe_test(doc):
    """THE test. Jinbe DEBUTS at episode 430 and JOINS at episode 977.

    Every upstream source has a Debut field. If anyone ever wires a scraper into
    crew_joins, Debut is what lands here, and Jinbe stands on the Thousand Sunny
    for 550 episodes he was not on it — in front of the most pedantic fandom on
    earth. This test is the tripwire on that exact mistake.
    """
    joins = {j["slug"]: j for j in doc["crew_joins"]}
    assert "jinbe" in joins, "jinbe is missing from crew_joins entirely"
    j = joins["jinbe"]
    ep, ch = j["join_episode"], j["join_chapter"]
    assert ep > 900, (
        f"jinbe.join_episode is {ep}, which is not > 900. His DEBUT is episode 430 and his "
        f"JOIN is episode 977. If this says ~430, someone scraped a Debut field into a join "
        f"field and the launch demo is now wrong by 547 episodes."
    )
    assert ch > 900, f"jinbe.join_chapter is {ch}, which is not > 900 (debut is chapter 528)"
    assert j["join_arc"] == "wano-country", f"jinbe joins in Wano, not {j['join_arc']!r}"
    return f"join_episode={ep} (debut is 430; gap {ep - 430}) — tripwire intact"


@check("crew_joins_are_human")
def crew_joins_are_human(doc):
    """Nothing in crew_joins may be silently marked verified by a machine."""
    assert doc["crew_joins"], "crew_joins is empty"
    unverified = 0
    for j in doc["crew_joins"]:
        src = j.get("source_ref") or ""
        assert src, f"{j['slug']}: source_ref is empty. Every authored row carries one. NOT NULL."
        assert j.get("canon_confidence") in CONFIDENCE_ENUM, f"{j['slug']}: bad canon_confidence"
        if j["verified"]:
            assert "hand-authored" in src.lower(), (
                f"{j['slug']} is marked verified:true but its source_ref is not hand-authored. "
                "A machine does not get to verify a crew join."
            )
        else:
            unverified += 1
    return (
        f"{len(doc['crew_joins'])} joins, {unverified} still verified:false "
        "(Shawn must confirm against the manga before any content ships)"
    )


@check("straw_hats_complete")
def straw_hats_complete(doc):
    expected = {
        "monkey-d-luffy", "roronoa-zoro", "nami", "usopp", "sanji",
        "tony-tony-chopper", "nico-robin", "franky", "brook", "jinbe",
    }
    got = {j["slug"] for j in doc["crew_joins"]}
    assert got == expected, f"crew roster mismatch. missing={expected - got} extra={got - expected}"
    orders = sorted(j["order"] for j in doc["crew_joins"])
    assert orders == list(range(1, 11)), f"join order is not 1..10: {orders}"
    # joins must be monotonic in chapter — you cannot join before the person before you
    by_order = sorted(doc["crew_joins"], key=lambda j: j["order"])
    for a, b in zip(by_order, by_order[1:]):
        assert b["join_chapter"] >= a["join_chapter"], (
            f"{b['slug']} joins at ch {b['join_chapter']} but is ordered after "
            f"{a['slug']} at ch {a['join_chapter']}"
        )
    return "10/10 Straw Hats, join chapters monotonic"


@check("islands_have_positions")
def islands_have_positions(doc):
    """position is NOT NULL from commit #1. A map of 15 pins on an empty ocean is a dead map."""
    assert doc["islands"], "islands is empty"
    for i in doc["islands"]:
        assert i["lng"] is not None and i["lat"] is not None, f"{i['slug']}: no position"
        assert -180 <= i["lng"] <= 180, f"{i['slug']}: lng {i['lng']} out of range"
        assert -90 <= i["lat"] <= 90, f"{i['slug']}: lat {i['lat']} out of range"
        assert i["canon_confidence"] in CONFIDENCE_ENUM, (
            f"{i['slug']}: canon_confidence {i['canon_confidence']!r} not in {CONFIDENCE_ENUM}"
        )
        assert i.get("source_ref"), f"{i['slug']}: source_ref is empty"
    conf: dict[str, int] = {}
    for i in doc["islands"]:
        conf[i["canon_confidence"]] = conf.get(i["canon_confidence"], 0) + 1
    return f"{len(doc['islands'])}/{len(doc['islands'])} positioned; confidence {conf}"


@check("islands_fog_key")
def islands_fog_key(doc):
    """Every manga-canon island must have a debut_chapter — that IS the fog key."""
    manga = [i for i in doc["islands"] if i["canon_status"] == "manga"]
    missing = [i["slug"] for i in manga if i["debut_chapter"] is None]
    assert not missing, f"manga-canon islands with no debut_chapter (unfoggable): {missing[:10]}"
    return f"{len(manga)} manga-canon islands, all with a debut_chapter"


@check("no_mojibake")
def no_mojibake(doc):
    """U+FFFD anywhere means French bytes died in transit and reached the artifact."""
    hits = []

    def walk(o, p="$"):
        if isinstance(o, str):
            if REPLACEMENT_CHAR in o:
                hits.append(f"{p} = {o[:60]!r}")
        elif isinstance(o, dict):
            for k, v in o.items():
                walk(v, f"{p}.{k}")
        elif isinstance(o, list):
            for n, v in enumerate(o):
                walk(v, f"{p}[{n}]")

    walk(doc)
    assert not hits, f"{len(hits)} U+FFFD replacement chars in the artifact: {hits[:5]}"
    return "0 U+FFFD in data/canon.json"


@check("arc_chain_unbroken")
def arc_chain_unbroken(doc):
    """The voyage is a linked list. A gap in it fogs the wrong half of the map."""
    arcs = sorted(doc["arcs"], key=lambda a: a["order"])
    assert arcs, "arcs is empty"
    orders = [a["order"] for a in arcs]
    assert orders == list(range(len(arcs))), f"arc order is not a dense 0..N chain: {orders}"
    by_name = {a["name"]: a for a in arcs}
    for a, nxt in zip(arcs, arcs[1:]):
        assert a["next_arc"] == nxt["name"], (
            f"{a['slug']}.next_arc = {a['next_arc']!r} but the next arc by order is {nxt['name']!r}"
        )
        assert nxt["prev_arc"] == a["name"], (
            f"{nxt['slug']}.prev_arc = {nxt['prev_arc']!r} but the previous arc is {a['name']!r}"
        )
        assert nxt["chapter_start"] >= a["chapter_start"], (
            f"{nxt['slug']} starts at ch {nxt['chapter_start']}, before {a['slug']} "
            f"at ch {a['chapter_start']} — the voyage runs backwards"
        )
    assert arcs[0]["prev_arc"] is None, "the first arc has a previous arc"
    assert arcs[-1]["next_arc"] is None, "the last arc has a next arc"
    assert len(by_name) == len(arcs), "duplicate arc names"
    ongoing = [a["slug"] for a in arcs if a["ongoing"]]
    return f"{len(arcs)} arcs, chain unbroken, ongoing={ongoing}"


@check("status_enum")
def status_enum(doc):
    bad = {c["status"] for c in doc["characters"]} - STATUS_ENUM
    assert not bad, (
        f"character status values outside the canonical enum: {bad}. The raw feed has SIX "
        "(living/alive/vivant/deceased/dead/unknown) across two languages — map them in "
        "canon/overrides.json, never coerce them."
    )
    bad_crew = {c["status"] for c in doc["crews"]} - CREW_STATUS_ENUM
    assert not bad_crew, f"crew status values outside the canonical enum: {bad_crew}"
    return f"characters in {sorted(STATUS_ENUM)}, crews in {sorted(CREW_STATUS_ENUM)}"


@check("no_french_leakage")
def no_french_leakage(doc):
    """Spot-check that the translation-repair layer actually ran."""
    crews = {c["name"] for c in doc["crews"]}
    assert "Straw Hat Pirates" in crews, "the Straw Hat Pirates are not in crews under their real name"
    assert "The Chapeau de Paille crew" not in crews, "raw French crew name reached the artifact"
    tell_tales = re.compile(
        r"\b(Chapeau de Paille|Équipage|Royaume de|Île |Pays des|inconnu|aucune|actif)\b"
    )
    hits = [c["name"] for c in doc["crews"] if tell_tales.search(c["name"])]
    hits += [c["name"] for c in doc["characters"] if tell_tales.search(c["name"])]
    assert not hits, f"French leaked into user-facing names: {hits[:10]}"
    types = {f["type"] for f in doc["fruits"]}
    assert "Zoan Mythique" not in types, "'Zoan Mythique' reached the artifact untranslated"
    return f"crews/characters clean; fruit types {sorted(types)}"


@check("types_are_numbers")
def types_are_numbers(doc):
    """Bounties are ints, not French strings. This is the whole point of the normalizer."""
    for c in doc["characters"]:
        b = c["bounty"]
        assert b is None or isinstance(b, int), f"{c['name']}: bounty is {type(b).__name__} {b!r}"
        assert b is None or b >= 0, f"{c['name']}: negative bounty"
        assert c["age"] is None or isinstance(c["age"], int), f"{c['name']}: age is not an int"
    luffy = next(c for c in doc["characters"] if c["slug"] == "monkey-d-luffy")
    assert luffy["bounty"] == 3_000_000_000, f"Luffy's bounty parsed as {luffy['bounty']!r}"
    return f"Luffy = {luffy['bounty']:,} berries (from the string '3.000.000.000')"


@check("source_refs_not_null")
def source_refs_not_null(doc):
    """Rule 4: every authored row carries source_ref + canon_confidence. NOT NULL."""
    for key in ("arcs", "islands", "characters", "crews", "fruits", "crew_joins", "sagas"):
        for row in doc[key]:
            ident = row.get("slug") or row.get("name") or row.get("id")
            assert row.get("source_ref"), f"{key}: {ident} has no source_ref"
            assert row.get("canon_confidence") in CONFIDENCE_ENUM, (
                f"{key}: {ident} has canon_confidence {row.get('canon_confidence')!r}"
            )
    return "every row in all 7 collections carries source_ref + canon_confidence"


@check("art_manifest_attributed")
def art_manifest_attributed(doc):
    """Phase 6: every image under public/art/ is attributed AND the manifest matches disk 1:1.

    The art is official © Oda/Shueisha/Toei, kept only as attributed fan reference. That
    posture is a lie the moment a file exists with no receipt, or the manifest names a file
    that isn't there. This check makes the attribution structural, not a promise in a README:
    every row carries a source_url + license, every row's file is on disk, and every .webp on
    disk has a row (no orphan art that slipped in unattributed).
    """
    manifest_path = ROOT / "data" / "generated" / "art_manifest.json"
    art_root = ROOT / "public" / "art"
    has_art = art_root.exists() and any(art_root.rglob("*.webp"))
    if not manifest_path.exists() and not has_art:
        return "no art yet (Phase 6 not run) — skipped"
    assert manifest_path.exists(), "public/art has images but data/generated/art_manifest.json is missing"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = manifest.get("images", [])
    manifest_files: set = set()
    for r in rows:
        f = r.get("file")
        assert f, f"a manifest row ({r.get('slug')!r}) has no file path"
        assert r.get("source_url"), f"{f}: no source_url — official art must carry its receipt"
        assert r.get("license"), f"{f}: no license string"
        p = (ROOT / "public" / f).resolve()
        assert p.exists(), f"manifest lists {f} but it is not on disk"
        manifest_files.add(p)
    on_disk = {p.resolve() for p in art_root.rglob("*.webp")} if art_root.exists() else set()
    orphans = on_disk - manifest_files
    assert not orphans, (
        f"{len(orphans)} art file(s) on disk with NO manifest row (unattributed): "
        f"{[str(o.relative_to(ROOT)) for o in list(orphans)[:5]]}"
    )
    counts = manifest.get("counts", {})
    return f"{len(rows)} images attributed + on disk, no orphans; {counts}"


@check("canon_boundary")
def canon_boundary(doc):
    """canon/ is HUMAN-OWNED. No build script may write into it."""
    canon_files = sorted(p.name for p in CANON_DIR.glob("*.json"))
    assert canon_files, "canon/ is empty — the hand-authored layer is missing"
    for script in ("normalize.py", "check_canon.py", "sync_api.py", "sync_wiki.py", "sync_art.py"):
        p = ROOT / "scripts" / script
        if not p.exists():
            continue
        src = p.read_text(encoding="utf-8")
        for m in re.finditer(r"(write_text|open)\s*\(\s*[^)]*canon\s*/", src):
            raise AssertionError(f"{script} appears to write into canon/: {m.group(0)!r}")
    return f"canon/ holds {canon_files}; no script writes into it"


@check("fog_mechanic")
def fog_mechanic(doc):
    """The actual product: at chapter N, how much of the world do you know?"""
    manga = [i for i in doc["islands"] if i["canon_status"] == "manga"]
    total = len(manga)
    rows = []
    prev = -1
    for ch in (1, 100, 300, 600, 900, 1044, 1185):
        seen = sum(1 for i in manga if i["debut_chapter"] <= ch)
        assert seen >= prev, "island visibility went DOWN as the chapter went up"
        prev = seen
        arc = next(
            (a["name"] for a in doc["arcs"]
             if a["chapter_start"] <= ch and (a["chapter_end"] is None or ch <= a["chapter_end"])),
            "—",
        )
        rows.append(f"ch {ch:>4}: {seen:>3}/{total} islands · {arc}")
    assert sum(1 for i in manga if i["debut_chapter"] <= 1) < total, "everything visible at chapter 1"
    assert sum(1 for i in manga if i["debut_chapter"] <= 1185) == total, "not everything visible at the end"
    return "fog monotonic — " + " | ".join(rows[:2]) + " ... " + rows[-2]


@check("voyage_route_forward")
def voyage_route_forward(doc):
    """The authored route must exist, only move forward, and carry a real position.

    A route that goes backward in the story, or a waypoint the build could not
    resolve to a coordinate, would draw a broken line across the map. Each waypoint
    is hand-authored — no upstream source stamps a chapter onto a sea route.
    """
    wps = doc.get("voyage", {}).get("waypoints", [])
    assert wps, "voyage.waypoints is empty — there is no route to draw"
    unverified = 0
    last = None
    for w in wps:
        assert isinstance(w["lng"], (int, float)) and isinstance(w["lat"], (int, float)), (
            f"waypoint order {w['order']} ({w['label']!r}) has no numeric position"
        )
        assert w["chapter"] >= 1, f"waypoint order {w['order']} has a non-positive chapter"
        if last is not None:
            assert w["chapter"] >= last, (
                f"voyage goes backward: order {w['order']} chapter {w['chapter']} < previous {last}. "
                "The route only moves forward in the story."
            )
        last = w["chapter"]
        src = w.get("source_ref") or ""
        assert src.lower().lstrip().startswith("hand-authored"), (
            f"waypoint order {w['order']} source_ref is not hand-authored"
        )
        if not w["verified"]:
            unverified += 1
    return f"{len(wps)} waypoints, forward-only, {unverified} still verified:false"


@check("vessels_chapter_gated")
def vessels_chapter_gated(doc):
    """The ship progression must be chapter-gated and only move forward.

    A reader at chapter 20 must see the small boat, never the Thousand Sunny. The
    first vessel must start at chapter 1 (the crew always has *a* boat), and
    from_chapter must be non-decreasing so the swap only ever moves forward.
    """
    vs = doc.get("vessels", [])
    assert vs, "vessels is empty — the ship never appears"
    assert vs[0]["from_chapter"] == 1, (
        f"first vessel starts at chapter {vs[0]['from_chapter']}, not 1. The crew has a boat "
        "from the first chapter, so there must be no chapter with no ship."
    )
    unverified = 0
    last = None
    for v in vs:
        if last is not None:
            assert v["from_chapter"] >= last, (
                f"vessels go backward: {v['slug']!r} from_chapter {v['from_chapter']} < previous {last}"
            )
        last = v["from_chapter"]
        src = v.get("source_ref") or ""
        assert src.lower().lstrip().startswith("hand-authored"), (
            f"vessel {v['slug']!r} source_ref is not hand-authored"
        )
        if not v["verified"]:
            unverified += 1
    return f"{len(vs)} vessels, first at ch.1, forward-only, {unverified} still verified:false"


@check("presence_windows_forward")
def presence_windows_forward(doc):
    """Presence windows must exist, only move forward, and carry a real position.

    Who-is-where is authored (no upstream source has a location-by-chapter axis).
    A window that goes backward in the story, ends before it starts, or lost its
    resolved coordinate would put a crew flag in the wrong ocean — or nowhere.
    """
    pres = doc.get("presence", {})
    entities = pres.get("crews", []) + pres.get("characters", [])
    assert entities, "presence is empty — the map has no crews or characters to show"
    total = unverified = 0
    for e in entities:
        wins = e.get("windows", [])
        assert wins, f"presence entity {e['slug']!r} has no windows — it can never render"
        last = None
        for w in wins:
            total += 1
            assert isinstance(w["lng"], (int, float)) and isinstance(w["lat"], (int, float)), (
                f"{e['slug']} window order {w['order']} has no numeric position"
            )
            assert w["from_chapter"] >= 1, (
                f"{e['slug']} window order {w['order']} has from_chapter {w['from_chapter']} < 1 "
                "— the seed scaffold's sentinel reached the artifact"
            )
            if w["to_chapter"] is not None:
                assert w["to_chapter"] >= w["from_chapter"], (
                    f"{e['slug']} window order {w['order']} ends (ch {w['to_chapter']}) before "
                    f"it starts (ch {w['from_chapter']})"
                )
            if last is not None:
                assert w["from_chapter"] >= last, (
                    f"{e['slug']} presence goes backward: order {w['order']} from_chapter "
                    f"{w['from_chapter']} < previous {last}"
                )
            last = w["from_chapter"]
            src = w.get("source_ref") or ""
            assert src.lower().lstrip().startswith("hand-authored"), (
                f"{e['slug']} window order {w['order']} source_ref is not hand-authored"
            )
            assert w.get("canon_confidence") in CONFIDENCE_ENUM, (
                f"{e['slug']} window order {w['order']} has bad canon_confidence"
            )
            if not w["verified"]:
                unverified += 1
    return (f"{len(entities)} entities, {total} windows, forward-only, "
            f"{unverified} still verified:false")


@check("presence_spoiler_and_roster")
def presence_spoiler_and_roster(doc):
    """The roster rules: no defunct Roger Pirates, and nothing renders ungated.

    Every member must carry a from_chapter >= 1 (the gate the UI renders by), and
    every window chapter must fall inside the derived chapter range — a window
    starting at chapter 5000 would simply never appear, silently.
    """
    pres = doc.get("presence", {})
    crews, chars = pres.get("crews", []), pres.get("characters", [])
    ch_max = max(
        [i["debut_chapter"] for i in doc["islands"] if i["debut_chapter"]]
        + [a["chapter_start"] for a in doc["arcs"]]
    )
    for e in crews + chars:
        assert "roger" not in e["slug"], (
            f"presence contains {e['slug']!r} — the Roger Pirates disbanded before chapter 1; "
            "a defunct crew has no presence"
        )
        for w in e["windows"]:
            assert w["from_chapter"] <= ch_max, (
                f"{e['slug']} window order {w['order']} starts at ch {w['from_chapter']}, past "
                f"the derived chapter max {ch_max} — it would never render"
            )
    for c in crews:
        for m in c.get("members", []):
            assert m["from_chapter"] >= 1, f"{c['slug']} member {m['slug']!r} has no chapter gate"
            src = m.get("source_ref") or ""
            assert src.lower().lstrip().startswith("hand-authored"), (
                f"{c['slug']} member {m['slug']!r} source_ref is not hand-authored"
            )
    crew_join_slugs = {j["slug"] for j in doc["crew_joins"]}
    char_slugs = {e["slug"] for e in chars}
    overlap = crew_join_slugs & char_slugs
    assert not overlap, (
        f"presence characters collide with crew_joins slugs: {overlap}. A Straw Hat is on the "
        "ship — the roster carries them; presence must not double-place them."
    )
    members_total = sum(len(c.get("members", [])) for c in crews)
    return (f"{len(crews)} crews ({members_total} members) + {len(chars)} characters, "
            f"all chapter-gated, no Roger Pirates, no crew_joins collision")


@check("fruit_reveals_gated")
def fruit_reveals_gated(doc):
    """A fruit's identity is a STORY REVEAL, not a character-sheet fact.

    The tripwire is Blackbeard: the Yami Yami no Mi is a Banaro Island reveal
    (~ch. 440). Every upstream source stores the fruit as a current-day fact on
    the character — if anyone ever wires that join into the reveal field, this
    row reads ~ch. 1 and the fruit lens spoils Blackbeard from chapter one.
    """
    fruit_types = {"Paramecia", "Zoan", "Logia", "Mythical Zoan", "Ancient Zoan",
                   "SMILE", "Artificial"}
    pres = doc.get("presence", {})
    crews, chars = pres.get("crews", []), pres.get("characters", [])
    ch_max = max(
        [i["debut_chapter"] for i in doc["islands"] if i["debut_chapter"]]
        + [a["chapter_start"] for a in doc["arcs"]]
    )
    entities = [m for c in crews for m in c.get("members", [])] + chars
    reveals, unverified = 0, 0
    teach = None
    for e in entities:
        assert "fruit" in e, f"presence entity {e['slug']!r} is missing the fruit field"
        f = e["fruit"]
        if f is None:
            continue
        reveals += 1
        assert 1 <= f["from_chapter"] <= ch_max, (
            f"{e['slug']} fruit reveal at ch {f['from_chapter']} is outside [1, {ch_max}] — "
            "it would never render, or renders ungated"
        )
        assert f["fruit_type"] in fruit_types, (
            f"{e['slug']} fruit_type {f['fruit_type']!r} is not a normalized type"
        )
        src = (f.get("source_ref") or "")
        assert src.lower().lstrip().startswith("hand-authored"), (
            f"{e['slug']} fruit reveal source_ref is not hand-authored"
        )
        assert f.get("canon_confidence") in CONFIDENCE_ENUM, (
            f"{e['slug']} fruit reveal has bad canon_confidence"
        )
        if not f["verified"]:
            unverified += 1
        if e["slug"] == "marshall-d-teach":
            teach = f
    assert reveals >= 10, (
        f"only {reveals} fruit reveals reached the artifact — the fruit lens would be empty. "
        "Did normalize drop canon/fruit_reveals.json?"
    )
    assert teach is not None, "marshall-d-teach has no fruit reveal — the tripwire row is gone"
    assert teach["from_chapter"] >= 440, (
        f"marshall-d-teach's fruit reveal reads ch {teach['from_chapter']} (< 440). The Yami "
        "Yami no Mi is a Banaro Island reveal — someone wired a character-sheet fact into a "
        "reveal field and the fruit lens now spoils Blackbeard from chapter one."
    )
    return f"{reveals} fruit reveals, all gated, Blackbeard tripwire intact, {unverified} still verified:false"


@check("haki_users_gated")
def haki_users_gated(doc):
    """Haki facts are per-(user, type) reveals — no upstream source links haki to
    characters at all, so every fact must be hand-authored, enum-clean, unique,
    and chapter-gated inside the derivable range.
    """
    haki_types = {"observation", "armament", "conqueror"}
    pres = doc.get("presence", {})
    crews, chars = pres.get("crews", []), pres.get("characters", [])
    ch_max = max(
        [i["debut_chapter"] for i in doc["islands"] if i["debut_chapter"]]
        + [a["chapter_start"] for a in doc["arcs"]]
    )
    entities = [m for c in crews for m in c.get("members", [])] + chars
    facts, users, unverified = 0, set(), 0
    for e in entities:
        assert "haki" in e, f"presence entity {e['slug']!r} is missing the haki field"
        seen_types = set()
        for f in e["haki"]:
            facts += 1
            users.add(e["slug"])
            assert f["haki"] in haki_types, (
                f"{e['slug']} haki {f['haki']!r} is not one of {sorted(haki_types)}"
            )
            assert f["haki"] not in seen_types, (
                f"{e['slug']} has duplicate haki facts for {f['haki']!r}"
            )
            seen_types.add(f["haki"])
            assert 1 <= f["from_chapter"] <= ch_max, (
                f"{e['slug']} haki fact at ch {f['from_chapter']} is outside [1, {ch_max}]"
            )
            src = (f.get("source_ref") or "")
            assert src.lower().lstrip().startswith("hand-authored"), (
                f"{e['slug']} haki fact source_ref is not hand-authored"
            )
            assert f.get("canon_confidence") in CONFIDENCE_ENUM, (
                f"{e['slug']} haki fact has bad canon_confidence"
            )
            if not f["verified"]:
                unverified += 1
    assert facts >= 10, (
        f"only {facts} haki facts reached the artifact — the haki lens would be empty. "
        "Did normalize drop canon/haki_users.json?"
    )
    return f"{facts} haki facts across {len(users)} users, all gated, {unverified} still verified:false"


@check("biomes_valid")
def biomes_valid(doc):
    """canon/islands.biomes.json: every value is a known biome, every slug is a
    real island, and the silhouettes artifact carries a valid biome per feature.
    A typo'd biome would silently fall through match() to the default ink."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from biomes import BIOMES  # noqa: PLC0415 — shared with the generators

    biomes_path = CANON_DIR / "islands.biomes.json"
    assert biomes_path.exists(), "canon/islands.biomes.json is missing"
    overrides = json.loads(biomes_path.read_text())["biomes"]
    slugs = {i["slug"] for i in doc["islands"]}
    for slug, biome in overrides.items():
        assert biome in BIOMES, f"override {slug!r}: {biome!r} is not one of {sorted(BIOMES)}"
        assert slug in slugs, f"override slug {slug!r} is not an island in canon.json"
    for hero in ("punk-hazard", "arabasta-kingdom", "skypiea"):
        assert hero in overrides, f"hero island {hero!r} missing from biome overrides"

    sil_path = ROOT / "public" / "geo" / "islands.silhouettes.json"
    assert sil_path.exists(), "public/geo/islands.silhouettes.json is missing"
    sil = json.loads(sil_path.read_text())
    allowed_props = {"slug", "debut", "hand_drawn", "biome"}
    for f in sil["features"]:
        p = f["properties"]
        assert set(p) <= allowed_props, (
            f"silhouette {p.get('slug')!r} carries unexpected properties "
            f"{set(p) - allowed_props} — names must never ship in geometry"
        )
        assert p.get("biome") in BIOMES, f"silhouette {p.get('slug')!r} has bad biome {p.get('biome')!r}"
    return f"{len(overrides)} overrides valid, {len(sil['features'])} silhouettes biome-tagged"


CHECKS = [
    jinbe_test, crew_joins_are_human, straw_hats_complete,
    islands_have_positions, islands_fog_key, no_mojibake,
    arc_chain_unbroken, status_enum, no_french_leakage,
    types_are_numbers, source_refs_not_null, art_manifest_attributed, canon_boundary, fog_mechanic,
    voyage_route_forward, vessels_chapter_gated,
    presence_windows_forward, presence_spoiler_and_roster,
    fruit_reveals_gated, haki_users_gated, biomes_valid,
]


def main() -> int:
    if not CANON_JSON.exists():
        print(f"data/canon.json does not exist. Run: python3 scripts/normalize.py", file=sys.stderr)
        return 1
    doc = json.loads(CANON_JSON.read_text(encoding="utf-8"))

    for c in CHECKS:
        c(doc)

    width = max(len(n) for n, _, _ in results)
    failed = 0
    print(f"\ncheck_canon — {CANON_JSON.relative_to(ROOT)} "
          f"({CANON_JSON.stat().st_size:,} bytes)\n")
    for name, ok, detail in results:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"  [{mark}] {name:<{width}}  {detail}")

    # the fog table is the product; print it in full
    fog = next((d for n, ok, d in results if n == "fog_mechanic" and ok), None)
    if fog:
        manga = [i for i in doc["islands"] if i["canon_status"] == "manga"]
        print("\n  the fog, in full:")
        for ch in (1, 100, 300, 600, 900, 1044, 1185):
            seen = sum(1 for i in manga if i["debut_chapter"] <= ch)
            arc = next(
                (a["name"] for a in doc["arcs"]
                 if a["chapter_start"] <= ch and (a["chapter_end"] is None or ch <= a["chapter_end"])),
                "—",
            )
            bar = "#" * round(40 * seen / len(manga))
            print(f"    ch {ch:>4}  {seen:>3}/{len(manga)}  {bar:<40} {arc}")

    print()
    if failed:
        print(f"{failed}/{len(results)} CHECKS FAILED — data/canon.json is not shippable\n")
        return 1
    print(f"{len(results)}/{len(results)} checks passed\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
