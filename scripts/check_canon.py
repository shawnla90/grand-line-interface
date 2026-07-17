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


@check("bounty_history_gated")
def bounty_history_gated(doc):
    """The Char Box overlay. Every bounty row must be chapter-gated and ordered,
    because a bounty is the single most spoiler-dense number in One Piece:
    'Luffy 3,000,000,000' on a chapter-96 map gives away twenty years of story.

    order is STORY time, as_of_chapter is READER time. They are different axes —
    a flashback reveals an old bounty late — so the invariant is per-axis:
    amounts descend with order (a bounty never falls in-world), and every row
    carries a real reveal chapter.
    """
    rows = 0
    for c in doc["characters"]:
        h = c["bounty_history"]
        if not h:
            continue
        rows += len(h)
        assert [r["order"] for r in h] == list(range(len(h))), (
            f"{c['slug']}: bounty_history order is not a dense 0..N chain"
        )
        for r in h:
            assert isinstance(r["as_of_chapter"], int) and r["as_of_chapter"] >= 1, (
                f"{c['slug']}: bounty row {r['amount']} has no reveal chapter — it could never "
                f"be fogged. normalize.py should have dropped it."
            )
            assert r["canon_confidence"] in CONFIDENCE_ENUM, f"{c['slug']}: bad canon_confidence"
        amounts = [r["amount"] for r in h]
        assert all(amounts[i] >= amounts[i + 1] for i in range(len(amounts) - 1)), (
            f"{c['slug']}: bounty amounts do not descend with order ({amounts}). Bounties only "
            f"ever rise in-world, so this is a parse error, not a fact."
        )

    # The tripwire. If the gate ever silently inverts, these two lines fail.
    luffy = next(c for c in doc["characters"] if c["slug"] == "monkey-d-luffy")
    hist = luffy["bounty_history"]
    assert any(r["amount"] == 30_000_000 and r["as_of_chapter"] <= 100 for r in hist), (
        "Luffy's first bounty (30,000,000 at ch. 96) is missing — the overlay is not merging"
    )
    assert not any(r["amount"] == 3_000_000_000 and r["as_of_chapter"] < 1053 for r in hist), (
        "Luffy's 3,000,000,000 is claimed before ch. 1053 — that is the spoiler this check exists for"
    )

    with_hist = sum(1 for c in doc["characters"] if c["bounty_history"])
    return f"{rows} bounty rows across {with_hist} characters, every row chapter-gated"


@check("wiki_debut_is_not_join")
def wiki_debut_is_not_join(doc):
    """The Jinbe rule, now that the Char Box overlay ships a debut_chapter next
    to the crew_joins table. Both facts must coexist and stay distinct: Jinbe is
    on the page from ch. 528 and in the crew from ch. 976. A merge that let debut
    overwrite join would sail him with the Straw Hats for 448 chapters he spent
    as a Warlord, an enemy, and a prisoner."""
    jinbe = next(c for c in doc["characters"] if c["slug"] == "jinbe")
    join = next(j for j in doc["crew_joins"] if j["slug"] == "jinbe")
    assert jinbe["debut_chapter"] is not None, "Jinbe has no debut_chapter — the overlay missed him"
    assert jinbe["debut_chapter"] < 600, (
        f"Jinbe's debut_chapter is {jinbe['debut_chapter']}; he debuts at ch. 528. "
        f"This looks like his JOIN chapter leaked into the debut field."
    )
    assert join["join_chapter"] > 900, (
        f"Jinbe's join_chapter is {join['join_chapter']}; he joins at ch. 976. "
        f"This looks like his DEBUT chapter leaked into the join field."
    )
    assert join["join_chapter"] - jinbe["debut_chapter"] > 400, (
        "Jinbe's debut and join have collapsed toward each other — the two axes are being conflated"
    )
    # and the rule generalises: nobody joins before they debut
    joins = {j["slug"]: j["join_chapter"] for j in doc["crew_joins"]}
    for c in doc["characters"]:
        if c["slug"] in joins and c["debut_chapter"] is not None:
            assert c["debut_chapter"] <= joins[c["slug"]], (
                f"{c['slug']} joins (ch. {joins[c['slug']]}) before they debut "
                f"(ch. {c['debut_chapter']}) — impossible"
            )
    return (f"Jinbe: debut ch. {jinbe['debut_chapter']}, joins ch. {join['join_chapter']} "
            f"— {join['join_chapter'] - jinbe['debut_chapter']} chapters apart, both intact")


@check("statuses_gated")
def statuses_gated(doc):
    """Warlord/Emperor/Supernova windows: gated, disjoint, and pointed at things
    that can render. Statuses are the map's most time-sensitive claim — 'Emperor'
    on Luffy's flag is a 1053-chapter spoiler, and 'Warlord' on Crocodile at 1000
    is simply false — so both ENDS matter, not just the start."""
    kinds = {"warlord", "yonko", "supernova"}
    statuses = doc["statuses"]
    assert statuses, "no statuses reached the artifact — the chips would be empty"

    # every slug must be something the chart can actually draw
    render = {c["slug"] for c in doc["presence"]["crews"]}
    render |= {m["slug"] for c in doc["presence"]["crews"] for m in c.get("members", [])}
    render |= {c["slug"] for c in doc["presence"]["characters"]}
    render |= {j["slug"] for j in doc["crew_joins"]}
    render.add(doc["voyage"]["crew_slug"])

    windows = 0
    for s in statuses:
        assert s["status"] in kinds, f"{s['slug']}: bad status {s['status']!r}"
        assert s["slug"] in render, (
            f"status {s['status']!r} names {s['slug']!r}, which nothing on the chart can render"
        )
        assert s["windows"], f"{s['slug']}: no windows"
        prev_end = None
        for w in s["windows"]:
            windows += 1
            assert w["from_chapter"] >= 1, f"{s['slug']}: from_chapter < 1"
            if w["to_chapter"] is not None:
                assert w["to_chapter"] >= w["from_chapter"], f"{s['slug']}: window ends before it starts"
            if prev_end is not None:
                assert w["from_chapter"] > prev_end, f"{s['slug']}: overlapping windows"
            prev_end = w["to_chapter"]
            assert w["canon_confidence"] in CONFIDENCE_ENUM, f"{s['slug']}: bad canon_confidence"

    # Tripwire 1: the Warlord system is abolished on the page at ch. 956. No
    # reader past it may ever see a Warlord chip, so no window may outlive it.
    survivors = [s["slug"] for s in statuses if s["status"] == "warlord"
                 and any(w["to_chapter"] is None or w["to_chapter"] > 956 for w in s["windows"])]
    assert not survivors, (
        f"Warlord windows survive the abolition of the system at ch. 956: {survivors}"
    )

    # Tripwire 2: Whitebeard's seat ENDS. An open-ended window here would mean
    # the gate has lost its second half, and a chapter-1000 reader would be shown
    # a dead man holding an Emperor's seat.
    wb = next((s for s in statuses if s["slug"] == "whitebeard-pirates"
               and s["status"] == "yonko"), None)
    assert wb is not None, "Whitebeard has no Emperor window — the tripwire cannot fire"
    assert all(w["to_chapter"] is not None for w in wb["windows"]), (
        "Whitebeard's Emperor window is open-ended; he dies at Marineford and the seat ends"
    )

    # Tripwire 3: THERE ARE FOUR EMPERORS. Not five. The seats are a fixed number
    # in the story, so sweeping every chapter and counting holders is a cheap,
    # total test of both window ends at once — and it is the one that caught the
    # off-by-one where Big Mom's and Kaido's seats ended at 1053 (inclusive) on
    # the same chapter Luffy's and Buggy's began: six Emperors for one chapter.
    # Fewer than four is legal and honest: between Whitebeard's death and the
    # reader being told who replaced him, the chart should show three.
    def holders_at(kind, ch):
        return [s["slug"] for s in statuses if s["status"] == kind and any(
            w["from_chapter"] <= ch and (w["to_chapter"] is None or ch <= w["to_chapter"])
            for w in s["windows"])]

    ch_max = max(a["chapter_start"] for a in doc["arcs"])
    for ch in range(1, ch_max + 1):
        held = holders_at("yonko", ch)
        assert len(held) <= 4, (
            f"ch {ch}: {len(held)} Emperors on the chart ({', '.join(sorted(held))}). "
            f"There are four seats. Check where a window ends against where the next begins — "
            f"to_chapter is INCLUSIVE."
        )
        wl = holders_at("warlord", ch)
        assert len(wl) <= 7, (
            f"ch {ch}: {len(wl)} Warlords on the chart ({', '.join(sorted(wl))}). There are seven."
        )

    by_kind = {k: sum(1 for s in statuses if s["status"] == k) for k in sorted(kinds)}
    unverified = sum(1 for s in statuses for w in s["windows"] if not w["verified"])
    peak_y = max(len(holders_at("yonko", ch)) for ch in range(1, ch_max + 1))
    peak_w = max(len(holders_at("warlord", ch)) for ch in range(1, ch_max + 1))
    return (f"{len(statuses)} statuses / {windows} windows {by_kind}, all gated, "
            f"never more than {peak_y} Emperors or {peak_w} Warlords at once, "
            f"{unverified} still verified:false")


@check("poneglyphs_gated")
def poneglyphs_gated(doc):
    """The stones. Two gates, and both have to hold: the reader must have been
    told a stone exists (revealed_chapter) and it must be somewhere they can see
    (an active custody window). A stone standing on a fogged island is the worst
    leak this map could produce — it draws a pin in what should be empty water
    AND names the island by implication."""
    kinds = {"road", "instructional", "historical", "rio"}
    pgs = doc["poneglyphs"]
    assert pgs, "no poneglyphs reached the artifact"
    debut = {i["slug"]: i["debut_chapter"] for i in doc["islands"]}

    for p in pgs:
        assert p["kind"] in kinds, f"{p['slug']}: bad kind {p['kind']!r}"
        assert p["custody"], f"{p['slug']}: no custody window — it can never render"
        first = min(w["from_chapter"] for w in p["custody"])
        assert p["revealed_chapter"] <= first, (
            f"{p['slug']}: revealed at ch. {p['revealed_chapter']} but its first custody window "
            f"opens at {first} — it would stand on the map before the reader knows it exists"
        )
        for w in p["custody"]:
            assert w["from_chapter"] >= 1, f"{p['slug']}: from_chapter < 1"
            isl = w["island_slug"]
            if isl is None:
                continue
            assert isl in debut, f"{p['slug']}: custody names unknown island {isl!r}"
            assert debut[isl] is not None and w["from_chapter"] >= debut[isl], (
                f"{p['slug']} stands on {isl!r} from ch. {w['from_chapter']}, but that island is "
                f"not charted until ch. {debut[isl]}"
            )

    # THERE ARE FOUR ROAD PONEGLYPHS, and the fourth's location is the plot.
    # Three is the honest count: inventing a pin for the fourth would be
    # inventing the answer to the story.
    roads = [p["slug"] for p in pgs if p["kind"] == "road"]
    assert len(roads) == 3, (
        f"{len(roads)} Road Poneglyphs are placed ({roads}). Three are findable in the story; "
        f"the fourth's location is the plot and must not be guessed at."
    )
    unverified = sum(1 for p in pgs for w in p["custody"] if not w["verified"])
    return (f"{len(pgs)} stones ({len(roads)} Road), every one revealed before it is placed "
            f"and standing on a charted island, {unverified} still verified:false")


@check("geo_artifacts_fresh")
def geo_artifacts_fresh(doc):
    """public/geo/*.json must be rebuilt from the inputs currently on disk.

    This exists because the dependency is not visible: an island's FOOTPRINT
    grows when a crew starts anchoring there, so editing canon/crew_presence.json
    silently invalidates every coastline — and the coastlines are a committed
    artifact nobody thinks to regenerate after typing a presence window. It
    happened exactly once, in the run that added 29 crews: Baltigo and Long Ring
    Long Land became anchors and kept their old pin-sized outlines, and nothing
    anywhere said so. Now this does.
    """
    sys.path.insert(0, str(ROOT / "scripts"))
    from gen_silhouettes import inputs_sha  # noqa: PLC0415 — shared with the generators

    want = inputs_sha()
    for rel in ("public/geo/islands.silhouettes.json", "public/geo/islands.terrain.json"):
        path = ROOT / rel
        assert path.exists(), f"{rel} is missing"
        meta = json.loads(path.read_text())["_meta"]
        got = meta.get("inputs_sha")
        assert got, f"{rel} carries no inputs_sha — regenerate it"
        assert got == want, (
            f"{rel} is STALE: it was built from different inputs than the ones on disk "
            f"({got[:12]} vs {want[:12]}). Re-run scripts/gen_silhouettes.py and "
            f"scripts/gen_terrain.py — an island's footprint depends on canon/crew_presence.json "
            f"and canon/voyage_legs.json, not just on its coordinates."
        )
    return f"silhouettes + terrain both built from inputs {want[:12]}"


@check("entry_slugs_routable")
def entry_slugs_routable(doc):
    """The slugs the entry routes key on. A page is a URL, and a URL that moves
    or collides is worse than one that does not exist.

    fruit_slug is authored (canon/fruit_reveals.json) rather than slugified at
    runtime, because `slug` on those rows is the CHARACTER's — "buggy" — and a
    runtime slugify would silently put him at /fruit/buggy. Two rows MAY share a
    fruit_slug: the Mera Mera no Mi belongs to Ace and then to Sabo, because a
    devil fruit returns to the world when its user dies. That is one fruit with
    two users, which is what a fruit page is FOR — so the assertion is not
    uniqueness, it is that rows sharing a slug agree about the fruit.
    """
    reveals = []
    for e in doc["presence"]["crews"]:
        for m in e.get("members", []):
            if m.get("fruit"):
                reveals.append((m["slug"], m["fruit"]))
    for e in doc["presence"]["characters"]:
        if e.get("fruit"):
            reveals.append((e["slug"], e["fruit"]))

    by_slug: dict[str, list] = {}
    for who, f in reveals:
        assert f.get("fruit_slug"), f"{who}: fruit reveal carries no fruit_slug"
        assert re.fullmatch(r"[a-z0-9-]+", f["fruit_slug"]), (
            f"{who}: fruit_slug {f['fruit_slug']!r} is not URL-safe"
        )
        by_slug.setdefault(f["fruit_slug"], []).append((who, f))
    for fs, rows in by_slug.items():
        names = {f["fruit_name"] for _, f in rows}
        types = {f["fruit_type"] for _, f in rows}
        assert len(names) == 1 and len(types) == 1, (
            f"fruit_slug {fs!r} is shared by rows that disagree about the fruit: "
            f"{names} / {types}. Two users of ONE fruit is fine; two fruits under one "
            f"slug is a collision."
        )

    # crew slugs: the /crew/[slug] key
    crew_slugs = [c["slug"] for c in doc["presence"]["crews"]]
    assert len(crew_slugs) == len(set(crew_slugs)), "duplicate presence crew slug"
    for cs in crew_slugs:
        assert re.fullmatch(r"[a-z0-9-]+", cs), f"crew slug {cs!r} is not URL-safe"

    # duplicate character slugs resolve to the lowest id — harmless ONLY while the
    # pair agrees on the gate, because the gate is what the route gets wrong.
    by_char: dict[str, list] = {}
    for c in doc["characters"]:
        by_char.setdefault(c["slug"], []).append(c)
    dupes = {k: v for k, v in by_char.items() if len(v) > 1}
    for slug, rows in dupes.items():
        gates = {c["debut_chapter"] for c in rows}
        assert len(gates) == 1, (
            f"character slug {slug!r} is shared by {len(rows)} rows that disagree on "
            f"debut_chapter ({gates}). /character/{slug} resolves to the lowest id, so "
            f"the gate would depend on which row won. Disambiguate the slug."
        )
    return (f"{len(by_slug)} fruit slugs across {len(reveals)} reveals, {len(crew_slugs)} crew "
            f"slugs, {len(dupes)} duplicate character slugs (all agreeing on their gate)")


CHECKS = [
    jinbe_test, crew_joins_are_human, straw_hats_complete,
    islands_have_positions, islands_fog_key, no_mojibake,
    arc_chain_unbroken, status_enum, no_french_leakage,
    types_are_numbers, source_refs_not_null, art_manifest_attributed, canon_boundary, fog_mechanic,
    voyage_route_forward, vessels_chapter_gated,
    presence_windows_forward, presence_spoiler_and_roster,
    fruit_reveals_gated, haki_users_gated, biomes_valid,
    bounty_history_gated, wiki_debut_is_not_join, statuses_gated, poneglyphs_gated,
    geo_artifacts_fresh, entry_slugs_routable,
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
