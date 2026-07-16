#!/usr/bin/env python3
"""
sync_wiki_characters.py — Phase 7B: the Char Box harvest. MACHINE-OWNED.

For every character in data/canon.json, pull the One Piece Fandom wiki's
{{Char Box}} and extract STRUCTURED FACTS ONLY (CC-BY-SA 3.0, attributed,
no prose): debut chapter/episode, epithet, origin, birthday, height, blood
type, and — the one nobody has digitized — the FULL BOUNTY PROGRESSION with
the chapter each amount was revealed. That table is what lets a wanted
poster show 30,000,000 at chapter 96 instead of leaking 3,000,000,000.

Batched (50 pages/request, ~16 requests for 786 characters), cached in
data/generated/_wiki_cache/ like every wiki call, fail-soft per page: a
missing page or unparseable box is a recorded miss, never a crash.

Output   data/generated/characters.wiki.json
Run      python3 scripts/sync_wiki_characters.py [--refresh]

NOT wired into normalize.py yet — next session threads it through the
schema (the Jinbe rule applies: debut here is DEBUT, never join).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sync_wiki import (  # noqa: E402 — shared wiki plumbing, same cache, same politeness
    API,
    BATCH_SIZE,
    GENERATED,
    REPO_ROOT,
    api_get,
    clean_text,
    extract_template,
    parse_debut,
    split_params,
    write_json,
)

CANON_JSON = REPO_ROOT / "data" / "canon.json"
OUT_PATH = GENERATED / "characters.wiki.json"

# Char Box params we extract. Everything else is counted (param_freq) but dropped.
WANTED = ("first", "bounty", "epithet", "origin", "birth", "height", "blood type",
          "affiliation", "occupation", "status")


def fetch_pages(titles: list[str], *, refresh: bool) -> tuple[dict[str, str], dict[str, str]]:
    """Batched revisions fetch that KEEPS the requested->resolved mapping.
    Returns (requested_title -> wikitext, requested_title -> resolved_title)."""
    text_by_requested: dict[str, str] = {}
    resolved_by_requested: dict[str, str] = {}
    uniq = sorted(set(titles))
    for i in range(0, len(uniq), BATCH_SIZE):
        chunk = uniq[i:i + BATCH_SIZE]
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
        q = data.get("query", {})
        norm = {m["from"]: m["to"] for m in q.get("normalized", [])}
        redir = {m["from"]: m["to"] for m in q.get("redirects", [])}
        content_by_final: dict[str, str] = {}
        for page in q.get("pages", []):
            if page.get("missing") or "revisions" not in page:
                continue
            content_by_final[page["title"]] = page["revisions"][0]["slots"]["main"].get("content", "")
        for req in chunk:
            final = redir.get(norm.get(req, req), norm.get(req, req))
            if final in content_by_final:
                text_by_requested[req] = content_by_final[final]
                resolved_by_requested[req] = final
    return text_by_requested, resolved_by_requested


# ---------------------------------------------------------------------------
# Bounty progression — "3,000,000,000<ref>Chapter 1053</ref><br>1,500,000,000..."
# ---------------------------------------------------------------------------

_AMOUNT = re.compile(r"(\d{1,3}(?:,\d{3})+|\d{4,})")
_CHAPTER_REF = re.compile(r"Chapter\s+(\d+)", re.IGNORECASE)
# {{Qref|name=c1053|chap=1053|page=4-5|ep=1080|...}} — the wiki's citation
# template; `chap=` is the chapter the fact was revealed.
_QREF_CHAP = re.compile(r"chap(?:ter)?\s*=\s*(\d+)", re.IGNORECASE)


def parse_bounty_history(raw: str) -> list[dict]:
    """Newest-first list of {amount, as_of_chapter|null}. Facts only: the
    amount digits and the chapter number cited in that segment ({{Qref|chap=N}}
    on modern pages, <ref>Chapter N</ref> on older ones). Struck-through
    amounts are superseded history — exactly what a progression wants."""
    if not raw:
        return []
    out: list[dict] = []
    for seg in re.split(r"<br\s*/?>", raw):
        m = _AMOUNT.search(seg)
        if not m:
            continue
        amount = int(m.group(1).replace(",", ""))
        chap = None
        qm = _QREF_CHAP.search(seg)
        if qm:
            chap = int(qm.group(1))
        else:
            for ref in re.findall(r"<ref[^>]*>(.*?)</ref>", seg, flags=re.DOTALL):
                cm = _CHAPTER_REF.search(ref)
                if cm:
                    chap = int(cm.group(1))
                    break
        out.append({"amount": amount, "as_of_chapter": chap})
    return out


_NIHONGO = re.compile(r"\{\{Nihongo\|([^|}]*)(?:\|[^}]*)?\}\}", re.IGNORECASE)


def unwrap_nihongo(raw: str) -> str:
    """{{Nihongo|Straw Hat Luffy|麦わらのルフィ|...}} -> Straw Hat Luffy."""
    return _NIHONGO.sub(r"\1", raw or "")


_HEIGHT_CM = re.compile(r"(\d{2,3}(?:\.\d+)?)\s*cm")


def parse_height_cm(raw: str) -> float | None:
    m = _HEIGHT_CM.search(raw or "")
    return float(m.group(1)) if m else None


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 7B Char Box harvest.")
    ap.add_argument("--refresh", action="store_true", help="ignore the wiki cache")
    args = ap.parse_args()

    canon = json.loads(CANON_JSON.read_text(encoding="utf-8"))
    chars = canon["characters"]
    print(f"Char Box harvest: {len(chars)} characters from canon.json")

    texts, resolved = fetch_pages([c["name"] for c in chars], refresh=args.refresh)

    # Major (tabbed) characters keep their Char Box inside their
    # {{<Name> Tabs Top}} TEMPLATE, not on the article. One extra batched
    # fetch resolves every one of them.
    tabs_re = re.compile(r"\{\{([^{}|\n]+ Tabs Top)\}\}")
    tabs_wanted: dict[str, str] = {}  # requested char name -> template title
    for c in chars:
        wikitext = texts.get(c["name"])
        if wikitext is None:
            continue
        if not extract_template(wikitext, "Char Box"):
            tm = tabs_re.search(wikitext)
            if tm:
                tabs_wanted[c["name"]] = f"Template:{tm.group(1)}"
    if tabs_wanted:
        print(f"  {len(tabs_wanted)} tabbed characters -> fetching their Tabs Top templates...")
        tab_texts, _ = fetch_pages(sorted(set(tabs_wanted.values())), refresh=args.refresh)

    rows, misses = [], []
    param_freq: dict[str, int] = {}
    for c in chars:
        name = c["name"]
        wikitext = texts.get(name)
        if wikitext is None:
            misses.append({"name": name, "slug": c["slug"], "why": "no wiki page under this title"})
            continue
        box = extract_template(wikitext, "Char Box")
        if not box and name in tabs_wanted:
            box = extract_template(tab_texts.get(tabs_wanted[name], ""), "Char Box")
        if not box:
            misses.append({"name": name, "slug": c["slug"], "why": "page has no {{Char Box}}"})
            continue
        params = split_params(box)
        for k in params:
            param_freq[k] = param_freq.get(k, 0) + 1

        debut = parse_debut(params.get("first", ""))
        bounties = parse_bounty_history(params.get("bounty", ""))
        page = resolved[name]
        rows.append({
            "slug": c["slug"],
            "name": name,
            "character_id": c["id"],
            "page_title": page,
            "debut_chapter": debut["chapter"],
            "debut_episode": debut["episode"],
            "canon_status": debut["status"],
            "epithet": clean_text(unwrap_nihongo(params.get("epithet", ""))) or None,
            "origin": clean_text(params.get("origin", "")) or None,
            "birthday": clean_text(params.get("birth", "")) or None,
            "height_cm": parse_height_cm(params.get("height", "")),
            "blood_type": clean_text(params.get("blood type", "")) or None,
            "bounty_history": bounties,
            "bounty_current": bounties[0]["amount"] if bounties else None,
            "source_ref": f"onepiece.fandom.com/wiki/{page.replace(' ', '_')}#Char_Box",
            "canon_confidence": "canon",
        })

    with_bounty = sum(1 for r in rows if r["bounty_history"])
    with_chapter_refs = sum(1 for r in rows
                            if any(b["as_of_chapter"] for b in r["bounty_history"]))
    with_debut = sum(1 for r in rows if r["debut_chapter"] is not None)

    payload = {
        "_meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generator": "scripts/sync_wiki_characters.py",
            "source": API,
            "license": "Facts extracted from One Piece Fandom under CC-BY-SA 3.0 — no prose reproduced.",
            "note": "debut is DEBUT, never join (the Jinbe rule). Not merged into canon.json yet.",
            "counts": {
                "characters_in_canon": len(chars),
                "char_boxes_parsed": len(rows),
                "misses": len(misses),
                "with_debut_chapter": with_debut,
                "with_bounty_history": with_bounty,
                "with_bounty_chapter_refs": with_chapter_refs,
                "bounty_rows_total": sum(len(r["bounty_history"]) for r in rows),
            },
            "wanted_params": list(WANTED),
            "param_freq_top": dict(sorted(param_freq.items(), key=lambda kv: -kv[1])[:25]),
        },
        "misses": misses,
        "characters": rows,
    }
    write_json(OUT_PATH, payload)

    m = payload["_meta"]["counts"]
    print(f"wrote {OUT_PATH.relative_to(REPO_ROOT)}")
    for k, v in m.items():
        print(f"  {k:28} {v}")
    if misses:
        print(f"\n  {len(misses)} misses (fail-soft, recorded in the file) — first 10:")
        for x in misses[:10]:
            print(f"    - {x['name']}: {x['why']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
