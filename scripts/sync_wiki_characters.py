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

# The amount is whatever follows the berry sign: '{{B}}1,111,000,000' or
# '{{B}}<s>50</s>'. Anchoring on {{B}} is what lets Chopper's famously insulting
# 50- and 100-berry bounties parse at all — a bare-number rule has to demand 4+
# digits or it eats page numbers out of the citations, and that rule silently
# dropped every bounty under 1,000.
_B_AMOUNT = re.compile(r"\{\{B(?:\|[^{}]*)?\}\}\s*(?:<s>\s*)?(\d{1,3}(?:,\d{3})*|\d+)")
_B_MARK = re.compile(r"\{\{B(?:\|[^{}]*)?\}\}")
_AMOUNT = re.compile(r"(\d{1,3}(?:,\d{3})+|\d{4,})")
_CHAPTER_REF = re.compile(r"Chapter\s+(\d+)", re.IGNORECASE)
# {{Qref|name=c1053|chap=1053|page=4-5|ep=1080|...}} — the wiki's citation
# template; `chap=` is the chapter the fact was revealed.
# (?<![a-z]) matters: the Qrefs also carry `nchap=` (a chapter of a light NOVEL)
# and an unanchored 'chap=' happily matched it — that is how Ace's 100,000,000
# and Law's 80,000,000 came back as revealed in manga CHAPTER 1.
_QREF_CHAP = re.compile(r"(?<![a-z])chap(?:ter)?\s*=\s*(\d+)", re.IGNORECASE)
# Rows the wiki itself marks as outside the manga (novel/movie-only bounties).
_NONCANON = re.compile(r"\{\{Status\|noncanon\}\}", re.IGNORECASE)
# A Qref *named* c1058 cites chapter 1058. This is a wiki-wide convention, and
# the pages prove it themselves: Jinbe carries {{Qref|name=c976|chap=976}} and
# Kid {{Qref|name=c1053|chap=1053}} — name and chap agree wherever both appear.
# Suffixes are page numbers (name=c677p3 -> chapter 677).
_QREF_NAME_CHAP = re.compile(r"^c(\d{1,4})(?:[pP]\d+.*)?$")


def _walk_templates(text: str):
    """Every {{template}} at any depth. The Qrefs we need are nested inside the
    Char Box, which is itself a template, so a top-level scan can't see them."""
    for _, _, inner in _templates(text):
        yield inner
        yield from _walk_templates(inner)


def _qref_params(inner: str) -> dict[str, str] | None:
    parts = _split_top(inner)
    if not parts or parts[0].strip().lower() != "qref":
        return None
    kv: dict[str, str] = {}
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            kv[k.strip().lower()] = v.strip()
    return kv


def qref_chapter_index(*wikitexts: str) -> dict[str, int]:
    """name -> chapter, harvested from every FULLY-SPECIFIED Qref on the page.

    MediaWiki named references are defined once and back-referenced after, so a
    bounty row often cites {{Qref|name=Enies Lobby Bounty}} with no chapter and
    the definition — {{Qref|name=Enies Lobby Bounty|chap=435|...}} — sits in the
    article body a few sections down. Indexing the whole page resolves them.
    """
    idx: dict[str, int] = {}
    for wikitext in wikitexts:
        for inner in _walk_templates(wikitext or ""):
            kv = _qref_params(inner)
            if not kv:
                continue
            name, chap = kv.get("name"), kv.get("chap") or kv.get("chapter")
            if name and chap and chap.isdigit():
                idx.setdefault(name, int(chap))
    return idx


def _segment_chapter(seg: str, qref_index: dict[str, int]) -> int | None:
    """The chapter a bounty segment was revealed, by descending reliability."""
    for inner in _walk_templates(seg):
        kv = _qref_params(inner)
        if not kv:
            continue
        chap = kv.get("chap") or kv.get("chapter")
        if chap and chap.isdigit():
            return int(chap)                       # cited outright
        name = kv.get("name")
        if name:
            m = _QREF_NAME_CHAP.match(name.strip())
            if m:
                return int(m.group(1))             # name=c1058 -> 1058
            if name in qref_index:
                return qref_index[name]            # back-ref to a definition
    qm = _QREF_CHAP.search(seg)                    # unbraced fallback
    if qm:
        return int(qm.group(1))
    for ref in re.findall(r"<ref[^>]*>(.*?)</ref>", seg, flags=re.DOTALL):
        cm = _CHAPTER_REF.search(ref)
        if cm:
            return int(cm.group(1))                # older pages
    return None


def parse_bounty_history(raw: str, qref_index: dict[str, int] | None = None) -> list[dict]:
    """Newest-first list of {order, amount, as_of_chapter|null}.

    ORDER IS LOAD-BEARING, and it is not the same axis as as_of_chapter. Order
    is STORY time (newest bounty first); as_of_chapter is when the READER was
    shown that row, and a flashback can reveal an old bounty late. Jinbe is the
    proof: 250,000,000 (his bounty at the time) is revealed ch. 528, and
    76,000,000 (his FIRST bounty, years earlier in-world) is revealed ch. 622 in
    a flashback. Sorting by chapter would hand a ch. 700 reader 76,000,000.

    So the resolution rule downstream is: among rows revealed by your chapter,
    take the one with the LOWEST order — the most recent bounty you know about.
    Both fields ship; neither is derivable from the other.

    Order is assigned by amount, descending, rather than by the wiki's list
    order. In One Piece a bounty only ever rises, so amount IS story order —
    it's the one monotonic fact in the field, and it doesn't depend on every
    walk-on's page being sorted correctly by hand.
    """
    if not raw:
        return []
    out: list[dict] = []
    for seg in re.split(r"<br\s*/?>", raw):
        if _NONCANON.search(seg):
            continue  # the wiki flags its own novel/movie-only rows; believe it
        m = _B_AMOUNT.search(seg)
        if not m:
            # A segment that HAS a berry sign but no number after it is an
            # explicit non-amount ('{{B}}Unknown' — Sabo). Falling through to the
            # loose number regex there scrapes a digit out of the citation
            # instead: it read Sabo's Vivre Card id (0659) as a 659-berry bounty.
            if _B_MARK.search(seg):
                continue
            m = _AMOUNT.search(seg)  # older pages predate the {{B}} template
            if not m:
                continue
        out.append({
            "amount": int(m.group(1).replace(",", "")),
            "as_of_chapter": _segment_chapter(seg, qref_index or {}),
        })
    out.sort(key=lambda r: -r["amount"])
    for i, row in enumerate(out):
        row["order"] = i
    return [{"order": r["order"], "amount": r["amount"], "as_of_chapter": r["as_of_chapter"]}
            for r in out]


# ---------------------------------------------------------------------------
# Epithet — the one string a wanted poster prints, so it has to be clean.
#
# The raw field is NESTED wikitext, which is why this is a brace walker and not
# a regex. Caesar Clown's is:
#   {{Nihongo|"Master"|{{ruby|M|マスター}}|Masutā}}{{Qref|name=c658}}
# and Franky's stacks two Nihongos, two Qrefs (whose bodies contain their own
# [[links]] and prose), and a trailing "(former)". Any regex that tries to reach
# the closing }} either stops at the inner ruby or swallows the next template.
# ---------------------------------------------------------------------------


def _templates(text: str) -> list[tuple[int, int, str]]:
    """(start, end, inner) for every top-level {{...}}, brace-balanced."""
    out, i, n = [], 0, len(text)
    while i < n - 1:
        if text[i:i + 2] != "{{":
            i += 1
            continue
        depth, j = 0, i
        while j < n - 1:
            if text[j:j + 2] == "{{":
                depth += 1
                j += 2
            elif text[j:j + 2] == "}}":
                depth -= 1
                j += 2
                if depth == 0:
                    break
            else:
                j += 1
        if depth != 0:
            break  # unbalanced wikitext: leave the rest alone
        out.append((i, j, text[i + 2:j - 2]))
        i = j
    return out


def _split_top(inner: str) -> list[str]:
    """Split template params on top-level | only (nested {{...}} keep theirs)."""
    parts, depth, cur, i = [], 0, [], 0
    while i < len(inner):
        if inner[i:i + 2] == "{{":
            depth += 1
            cur.append("{{")
            i += 2
        elif inner[i:i + 2] == "}}":
            depth -= 1
            cur.append("}}")
            i += 2
        elif inner[i] == "|" and depth == 0:
            parts.append("".join(cur))
            cur = []
            i += 1
        else:
            cur.append(inner[i])
            i += 1
    parts.append("".join(cur))
    return parts


def _resolve_templates(text: str, drop: tuple[str, ...] = ("qref", "ref")) -> str:
    """{{Nihongo|X|...}} -> X (param 1 is the English). {{Qref|...}} -> ''
    (a citation, not a name). Anything else keeps its first param."""
    out, last = [], 0
    for start, end, inner in _templates(text):
        parts = _split_top(inner)
        name = parts[0].strip().lower()
        if name in drop:
            repl = ""
        elif name == "nihongo":
            repl = _resolve_templates(parts[1]) if len(parts) > 1 else ""
        else:
            repl = _resolve_templates(parts[1]) if len(parts) > 1 else ""
        out.append(text[last:start])
        out.append(repl)
        last = end
    out.append(text[last:])
    return "".join(out)


def unwrap_nihongo(raw: str) -> str:
    """{{Nihongo|Straw Hat Luffy|麦わらのルフィ|...}} -> Straw Hat Luffy."""
    return _resolve_templates(raw or "")


_DUB_NOTE = re.compile(r"\s*\([^()]*\b(?:dub|former|non-canon)\b[^()]*\)", re.IGNORECASE)


def clean_epithet(raw: str) -> str | None:
    """Char Box epithets ship as '"Pirate Hunter Zoro"' (the wiki quotes the
    alias part), often several at once separated by <br>, sometimes with an
    aside ('("Black Beard" in the edited dub)', '(former)').

    Take the FIRST — the wiki lists the current/primary epithet first (Franky is
    "Iron Man" since ch. 801, "Cyborg" is the former) — drop the aside, and
    remove the quote marks, which are wiki punctuation rather than part of the
    name. Every step here deletes; no word is invented.
    """
    text = _resolve_templates(raw or "")
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.DOTALL)
    text = re.split(r"<br\s*/?>|;", text)[0]
    text = _DUB_NOTE.sub("", text)
    text = clean_text(text).replace('"', "").replace("“", "").replace("”", "")
    return text.strip() or None


_HEIGHT_CM = re.compile(r"(\d{2,3}(?:\.\d+)?)\s*cm")


def parse_height_cm(raw: str) -> float | None:
    """Char Box height lists every age a character has been drawn at, oldest
    first: Luffy is '91 cm (age 7)<br>172 cm (pre-timeskip)<br>174 cm'. The
    first match is therefore the CHILD. Take the last."""
    ms = _HEIGHT_CM.findall(raw or "")
    return float(ms[-1]) if ms else None


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 7B Char Box harvest.")
    ap.add_argument("--refresh", action="store_true", help="ignore the wiki cache")
    args = ap.parse_args()

    canon = json.loads(CANON_JSON.read_text(encoding="utf-8"))
    chars = canon["characters"]
    print(f"Char Box harvest: {len(chars)} characters from canon.json")

    # canon/overrides.json:wiki_title_overrides is the HUMAN door for the misses:
    # the upstream mirror is French (Léo), fuses aliases into names (Kuzan /
    # Aokiji), and our own name repairs add parentheses the wiki doesn't use.
    # A character with no override is asked for by their canon name, as before.
    overrides = json.loads((REPO_ROOT / "canon" / "overrides.json").read_text(encoding="utf-8"))
    title_ov = overrides.get("wiki_title_overrides", {})
    title_for = {c["name"]: title_ov.get(c["name"], c["name"]) for c in chars}
    print(f"  {sum(1 for n in title_for if n in title_ov)} hand-mapped wiki titles")

    texts, resolved = fetch_pages(list(title_for.values()), refresh=args.refresh)

    # Major (tabbed) characters keep their Char Box inside their
    # {{<Name> Tabs Top}} TEMPLATE, not on the article. One extra batched
    # fetch resolves every one of them.
    tabs_re = re.compile(r"\{\{([^{}|\n]+ Tabs Top)\}\}")
    tabs_wanted: dict[str, str] = {}  # requested wiki title -> template title
    for c in chars:
        title = title_for[c["name"]]
        wikitext = texts.get(title)
        if wikitext is None:
            continue
        if not extract_template(wikitext, "Char Box"):
            tm = tabs_re.search(wikitext)
            if tm:
                tabs_wanted[title] = f"Template:{tm.group(1)}"
    tab_texts: dict[str, str] = {}
    if tabs_wanted:
        print(f"  {len(tabs_wanted)} tabbed characters -> fetching their Tabs Top templates...")
        tab_texts, _ = fetch_pages(sorted(set(tabs_wanted.values())), refresh=args.refresh)

    rows, misses = [], []
    param_freq: dict[str, int] = {}
    for c in chars:
        name = c["name"]
        title = title_for[name]
        overridden = name in title_ov
        wikitext = texts.get(title)
        if wikitext is None:
            misses.append({"name": name, "slug": c["slug"], "asked_for": title,
                           "why": "no wiki page under this title"})
            continue
        box = extract_template(wikitext, "Char Box")
        if not box and title in tabs_wanted:
            box = extract_template(tab_texts.get(tabs_wanted[title], ""), "Char Box")
        if not box:
            misses.append({"name": name, "slug": c["slug"], "asked_for": title,
                           "why": "page has no {{Char Box}}"})
            continue
        params = split_params(box)
        for k in params:
            param_freq[k] = param_freq.get(k, 0) + 1

        debut = parse_debut(params.get("first", ""))
        # index the WHOLE page (article + tab template) so a bounty row citing a
        # bare {{Qref|name=Enies Lobby Bounty}} finds where that ref is defined
        qref_index = qref_chapter_index(wikitext, tab_texts.get(tabs_wanted.get(title, ""), ""))
        bounties = parse_bounty_history(params.get("bounty", ""), qref_index)
        page = resolved[title]
        rows.append({
            "slug": c["slug"],
            "name": name,
            "character_id": c["id"],
            "page_title": page,
            "debut_chapter": debut["chapter"],
            "debut_episode": debut["episode"],
            "canon_status": debut["status"],
            "epithet": clean_epithet(params.get("epithet", "")),
            "origin": clean_text(params.get("origin", "")) or None,
            "birthday": clean_text(params.get("birth", "")) or None,
            "height_cm": parse_height_cm(params.get("height", "")),
            "blood_type": clean_text(params.get("blood type", "")) or None,
            "bounty_history": bounties,
            "bounty_current": bounties[0]["amount"] if bounties else None,
            "source_ref": f"onepiece.fandom.com/wiki/{page.replace(' ', '_')}#Char_Box"
                          + (" (title from canon/overrides.json:wiki_title_overrides)"
                             if overridden else ""),
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
                "title_overrides_applied": sum(1 for c in chars if c["name"] in title_ov),
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
