#!/usr/bin/env python3
"""
sync_art.py — Phase 6 official-art pipeline. MACHINE-OWNED.

WHAT IT DOES
------------
Phases 1-5 drew every crew, Warlord and ship as ORIGINAL SVG marks. Phase 6
replaces those (where art exists) with the real thing: actual Jolly Rogers,
character portraits, recognizable ships, official Devil-Fruit renders, and
island images.

WHAT IT WRITES (machine-owned, safe to overwrite):
    public/art/{characters,flags,ships,fruits,islands}/<slug>.webp
    data/generated/art_manifest.json      (one row per image + license + receipts)
    data/generated/art_contact_sheet.html (eyeball-QA grid — auto-opened)
    data/generated/_art_cache/*.json      (raw pageimages responses; re-runs are free)

WHAT IT MUST NEVER TOUCH:
    canon/  — human-owned. Asserted at runtime (assert_no_canon_writes).
    The only canon/ file it READS is canon/art_sources.json (the override map).

LICENSE POSTURE (READ THIS)
---------------------------
Unlike sync_wiki.py, which pulls only non-copyrightable FACTS, this script pulls
ARTWORK. That artwork is © Eiichiro Oda / Shueisha / Toei Animation. It is used
here as attributed fan reference and is EXPLICITLY EXCLUDED from the repo's MIT
license (see public/art/README.md). Every file gets a manifest row carrying its
source URL, sha256, and a license string — the receipts are part of the product.
The original SVG marks remain in the code as fallbacks: if a takedown ever lands,
deleting public/art/ leaves a working atlas.

POLITENESS
----------
Same discipline as sync_wiki.py: 1 request/second, descriptive User-Agent,
maxlag=5, exponential backoff, batched pageimages (<=50 titles/request). Image
files already on disk are skipped unless --refresh, so iterating on the override
map is nearly free.

Usage:
    python3 scripts/sync_art.py            # skip files already downloaded
    python3 scripts/sync_art.py --refresh  # re-fetch everything
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API = "https://onepiece.fandom.com/api.php"
USER_AGENT = "grand-line-interface/0.6 (One Piece fan atlas; contact: shawn@leadalchemy.co)"

REPO_ROOT = Path(__file__).resolve().parent.parent
CANON_DIR = REPO_ROOT / "canon"
CANON_JSON = REPO_ROOT / "data" / "canon.json"
RAW_FRUITS = REPO_ROOT / "data" / "raw" / "fruits.json"
GENERATED = REPO_ROOT / "data" / "generated"
CACHE_DIR = GENERATED / "_art_cache"
ART_ROOT = REPO_ROOT / "public" / "art"
ART_SOURCES = CANON_DIR / "art_sources.json"
MANIFEST_PATH = GENERATED / "art_manifest.json"
CONTACT_SHEET = GENERATED / "art_contact_sheet.html"

REQUEST_DELAY_S = 1.0
MAX_RETRIES = 5
BATCH_SIZE = 50

LICENSE = "© Eiichiro Oda/Shueisha/Toei — official artwork, attributed fan reference, NOT MIT"

# per-kind post-processing: (mode, size). "square" = top-biased square crop;
# "long" = fit longest side; "width" = fit to width, keep aspect.
# Sizes are 2-3x the on-map display size so retina markers stay crisp (6E).
KIND_PROCESS = {
    "characters": ("square", 512),
    "flags": ("long", 384),
    "ships": ("width", 960),
    "fruits": ("long", 320),
    "islands": ("width", 960),
}

# 6E: kinds whose wiki art is usually an anime SCREENSHOT (subject + scenery).
# These get matted to an alpha cutout so the map renders a sprite, not a photo.
# Model choice is empirical (A/B'd on real wiki art): u2net keeps the whole
# ship/emblem where isnet-anime swallowed the Merry's aft into shadow.
# Characters are NOT matted: infobox shots are crowded scenes both models
# butcher, and the map crops portraits into circular rings regardless.
# Islands stay rectangular on purpose — they're scenery, shown in the panel.
# Sources that already carry real transparency skip the matte untouched.
MATTE_KINDS = {"flags": "u2net", "ships": "u2net"}
# If the matte eats the subject (alpha coverage below this), keep the original.
MATTE_MIN_COVERAGE = 0.02
# Required kinds fail the run if an entry can't be resolved; optional kinds only warn.
REQUIRED_KINDS = {"characters", "flags", "fruits"}

STATS = {"requests": 0, "cache_hits": 0, "retries": 0, "downloads": 0, "skipped": 0}


def slugify(name: str) -> str:
    import re
    s = re.sub(r"[^a-z0-9]+", "-", name.lower())
    return s.strip("-")


# ---------------------------------------------------------------------------
# Guardrail — never write to canon/
# ---------------------------------------------------------------------------

def assert_no_canon_writes(path: Path) -> None:
    resolved = path.resolve()
    if CANON_DIR.resolve() in resolved.parents or resolved == CANON_DIR.resolve():
        raise RuntimeError(
            f"ARCHITECTURE VIOLATION: sync_art.py attempted to write into canon/ "
            f"({resolved}). canon/ is hand-authored and machine-immutable."
        )


def write_bytes(path: Path, data: bytes) -> None:
    assert_no_canon_writes(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def write_text(path: Path, text: str) -> None:
    assert_no_canon_writes(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Polite HTTP
# ---------------------------------------------------------------------------

_last_request_at = 0.0


def _throttle() -> None:
    global _last_request_at
    elapsed = time.time() - _last_request_at
    if elapsed < REQUEST_DELAY_S:
        time.sleep(REQUEST_DELAY_S - elapsed)
    _last_request_at = time.time()


def _get(url: str, *, binary: bool) -> bytes | dict:
    backoff = 2.0
    for attempt in range(1, MAX_RETRIES + 1):
        _throttle()
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read()
            if binary:
                return body
            data = json.loads(body.decode("utf-8"))
            if "error" in data:
                code = data["error"].get("code", "")
                if code in ("maxlag", "readonly") and attempt < MAX_RETRIES:
                    STATS["retries"] += 1
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise RuntimeError(f"MediaWiki API error: {data['error']}")
            return data
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 502, 503, 504) and attempt < MAX_RETRIES:
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


def api_get(params: dict[str, str], *, refresh: bool) -> dict:
    params = {**params, "format": "json", "formatversion": "2", "maxlag": "5"}
    url = f"{API}?{urllib.parse.urlencode(params)}"
    cache_file = CACHE_DIR / f"{hashlib.sha1(url.encode()).hexdigest()}.json"
    if cache_file.exists() and not refresh:
        STATS["cache_hits"] += 1
        return json.loads(cache_file.read_text(encoding="utf-8"))
    data = _get(url, binary=False)
    STATS["requests"] += 1
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def download_binary(url: str, *, refresh: bool = False) -> bytes:
    """Fetch image bytes, cached under _art_cache/raw/ so a --reprocess run
    (and the contact sheet's before/after column) never re-hits the wiki."""
    cache_file = CACHE_DIR / "raw" / hashlib.sha1(url.encode()).hexdigest()
    if cache_file.exists() and not refresh:
        STATS["cache_hits"] += 1
        return cache_file.read_bytes()
    data = _get(url, binary=True)
    STATS["downloads"] += 1
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_bytes(data)
    return data


def raw_cache_path(url: str) -> Path:
    return CACHE_DIR / "raw" / hashlib.sha1(url.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Wiki title / image resolution
# ---------------------------------------------------------------------------

def resolve_pageimages(titles: list[str], *, refresh: bool) -> dict[str, str | None]:
    """title (as requested) -> original image URL (or None). Handles normalize+redirect."""
    out: dict[str, str | None] = {t: None for t in titles}
    uniq = sorted(set(titles))
    for i in range(0, len(uniq), BATCH_SIZE):
        chunk = uniq[i:i + BATCH_SIZE]
        data = api_get(
            {
                "action": "query",
                "titles": "|".join(chunk),
                "prop": "pageimages",
                "piprop": "original",
                "redirects": "1",
            },
            refresh=refresh,
        )
        q = data.get("query", {})
        # map requested title -> final resolved title through normalized + redirects
        norm = {m["from"]: m["to"] for m in q.get("normalized", [])}
        redir = {m["from"]: m["to"] for m in q.get("redirects", [])}
        by_final: dict[str, str | None] = {}
        for page in q.get("pages", []):
            if page.get("missing"):
                continue
            src = (page.get("original") or {}).get("source")
            by_final[page["title"]] = src
        for req in chunk:
            t = norm.get(req, req)
            t = redir.get(t, t)
            out[req] = by_final.get(t)
    return out


def resolve_file_url(image_name: str, *, refresh: bool) -> str | None:
    """Resolve an explicit File:<name> to its original URL via imageinfo."""
    title = image_name if image_name.lower().startswith("file:") else f"File:{image_name}"
    data = api_get(
        {"action": "query", "titles": title, "prop": "imageinfo", "iiprop": "url"},
        refresh=refresh,
    )
    for page in data.get("query", {}).get("pages", []):
        info = page.get("imageinfo")
        if info:
            return info[0].get("url")
    return None


# ---------------------------------------------------------------------------
# Pillow post-processing
# ---------------------------------------------------------------------------

_REMBG_SESSIONS: dict[str, Any] = {}


def _matte(im: Image.Image, model: str) -> Image.Image | None:
    """AI background removal (rembg). Returns the RGBA cutout, or None when
    the matte is unusable (subject almost entirely removed) — the caller
    keeps the original then."""
    from rembg import new_session, remove  # lazy: model loads once, on demand
    if model not in _REMBG_SESSIONS:
        _REMBG_SESSIONS[model] = new_session(model)
    out = remove(im.convert("RGBA"), session=_REMBG_SESSIONS[model])
    alpha = out.getchannel("A")
    coverage = sum(1 for a in alpha.getdata() if a > 24) / (out.width * out.height)
    if coverage < MATTE_MIN_COVERAGE:
        return None
    return out


def _trim_to_subject(im: Image.Image, pad_frac: float = 0.04) -> Image.Image:
    """Crop an RGBA image to its alpha bounding box plus a small margin."""
    bbox = im.getchannel("A").getbbox()
    if not bbox:
        return im
    pad = round(max(im.width, im.height) * pad_frac)
    left = max(0, bbox[0] - pad)
    top = max(0, bbox[1] - pad)
    right = min(im.width, bbox[2] + pad)
    bottom = min(im.height, bbox[3] + pad)
    return im.crop((left, top, right, bottom))


# nagadomi's LBP cascade trained ON anime faces — the generic Haar frontal
# cascade fires on kimono skulls and shoes (verified on this exact art set).
# Cached in the gitignored _art_cache like the wiki bytes; never committed.
ANIME_CASCADE_URL = (
    "https://raw.githubusercontent.com/nagadomi/lbpcascade_animeface/master/"
    "lbpcascade_animeface.xml"
)


def _anime_cascade_path() -> "Path | None":
    dest = CACHE_DIR / "lbpcascade_animeface.xml"
    if dest.exists():
        return dest
    try:
        req = urllib.request.Request(ANIME_CASCADE_URL, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return dest
    except Exception:  # noqa: BLE001 — offline runs fall through to other detectors
        return None


def _detect_face_focus(im: Image.Image) -> tuple[float, float, str] | None:
    """Best-effort face center for the square portrait crop.

    Returns (fx, fy, detector) with fx/fy normalized to [0,1], or None.
    Order: mediapipe (rarely fires on painted faces, but trustworthy when it
    does) → anime-face LBP cascade (the workhorse for this art) → generic Haar
    (guarded hard: a "face" in the lower half of portrait art is a false
    positive on clothing, verified on Sanji's shoes and Jinbe's kimono).
    All deterministic per input, so re-runs stay no-op diffs. The caller MUST
    keep a geometric fallback + the canon/art_sources.json "focus" override.
    """
    import numpy as np
    rgb = np.asarray(im.convert("RGB"))
    h_img, w_img = rgb.shape[0], rgb.shape[1]

    try:
        import mediapipe as mp
        with mp.solutions.face_detection.FaceDetection(
            model_selection=1, min_detection_confidence=0.5
        ) as det:
            res = det.process(rgb)
        if res.detections:
            best = max(
                res.detections,
                key=lambda d: d.location_data.relative_bounding_box.width
                * d.location_data.relative_bounding_box.height,
            )
            bb = best.location_data.relative_bounding_box
            # a face under ~6% of the frame is noise (background extras)
            if bb.width >= 0.06:
                fx = min(1.0, max(0.0, bb.xmin + bb.width / 2))
                fy = min(1.0, max(0.0, bb.ymin + bb.height / 2))
                return (fx, fy, "mediapipe")
    except Exception:  # noqa: BLE001 — detection is best-effort by contract
        pass

    try:
        import cv2
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        min_side = max(24, w_img // 12)

        anime_xml = _anime_cascade_path()
        if anime_xml:
            cascade = cv2.CascadeClassifier(str(anime_xml))
            faces = cascade.detectMultiScale(gray, 1.1, 5, minSize=(min_side, min_side))
            if len(faces):
                x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
                fy = (y + fh / 2) / h_img
                if fy <= 0.6:
                    return ((x + fw / 2) / w_img, fy, "animeface")

        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        faces = cascade.detectMultiScale(gray, 1.1, 5, minSize=(min_side, min_side))
        if len(faces):
            x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
            fy = (y + fh / 2) / h_img
            if fy <= 0.42:
                return ((x + fw / 2) / w_img, fy, "haar")
    except Exception:  # noqa: BLE001
        pass
    return None


def process_image(
    raw: bytes, mode: str, size: int, *,
    matte_model: str | None = None,
    focus: dict | None = None,
) -> tuple[bytes, int, int, bool, dict | None]:
    """Return (webp_bytes, w, h, matted, focus_used). Raises on non-image input.

    focus: optional {"x": 0..1, "y": 0..1} from canon/art_sources.json — a
    human-picked head position that beats face detection (square mode only).
    """
    im = Image.open(io.BytesIO(raw))
    im.load()
    has_alpha = im.mode in ("RGBA", "LA", "P") and (
        "transparency" in im.info or im.mode in ("RGBA", "LA")
    )
    im = im.convert("RGBA" if has_alpha else "RGB")

    # 6E: screenshots become sprites. A source that already ships transparency
    # is a clean render — matting it again could only do harm, so skip.
    matted = False
    real_alpha = has_alpha and im.getchannel("A").getextrema()[0] < 250
    if matte_model and not real_alpha:
        cut = _matte(im, matte_model)
        if cut is not None:
            im = _trim_to_subject(cut)
            matted = True
    elif matte_model and real_alpha:
        im = _trim_to_subject(im)

    focus_used: dict | None = None
    if mode == "square":
        w, h = im.size
        s = min(w, h)
        pt: tuple[float, float] | None = None
        if isinstance(focus, dict) and "x" in focus and "y" in focus:
            pt = (float(focus["x"]), float(focus["y"]))
            focus_used = {"x": pt[0], "y": pt[1], "source": "override"}
        else:
            hit = _detect_face_focus(im)
            if hit:
                pt = (hit[0], hit[1])
                focus_used = {"x": round(hit[0], 4), "y": round(hit[1], 4), "source": hit[2]}
        if pt:
            # head-and-shoulders framing: the face sits at ~38% of the crop's
            # height, never dead-center (chins at center = floating torso look)
            left = min(max(0, round(pt[0] * w - s / 2)), w - s)
            top = min(max(0, round(pt[1] * h - 0.38 * s)), h - s)
        else:
            left = (w - s) // 2
            # top-biased: for tall art (full body) crop from the upper region to keep the head
            top = 0 if h <= w else min((h - s) // 4, h - s)
        im = im.crop((left, top, left + s, top + s)).resize((size, size), Image.LANCZOS)
    elif mode == "long":
        im.thumbnail((size, size), Image.LANCZOS)
    elif mode == "width":
        w, h = im.size
        if w > size:
            im = im.resize((size, round(h * size / w)), Image.LANCZOS)
    else:
        raise ValueError(f"unknown process mode {mode!r}")

    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=85, method=6)
    return buf.getvalue(), im.size[0], im.size[1], matted, focus_used


# ---------------------------------------------------------------------------
# Want-list — derived from data/canon.json (+ raw fruits + override map)
# ---------------------------------------------------------------------------

def build_wantlist(canon: dict, overrides: dict) -> list[dict]:
    """Each item: {kind, slug, page|None, image|None, direct_url|None, name}."""
    items: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def add(kind: str, slug: str, name: str, *, page: str | None = None,
            image: str | None = None, direct_url: str | None = None,
            ref_id: int | None = None):
        key = (kind, slug)
        if key in seen:
            return
        seen.add(key)
        ov = (overrides.get(kind) or {}).get(slug) or {}
        items.append({
            "kind": kind,
            "slug": slug,
            "name": name,
            "page": ov.get("page", page if page is not None else name),
            "image": ov.get("image", image),
            "direct_url": direct_url,
            "ref_id": ref_id,
        })

    pres = canon["presence"]

    # flags — one per presence crew (page defaults to crew name)
    for c in pres["crews"]:
        add("flags", c["slug"], c["name"])

    # ships — presence-crew vessels + the two Straw Hat ships that have wiki renders
    for c in pres["crews"]:
        v = c.get("vessel")
        if v:
            add("ships", v["slug"], v["name"])
    add("ships", "going-merry", "Going Merry")
    add("ships", "thousand-sunny", "Thousand Sunny")

    # characters — Straw Hats + presence crew members + Warlords (all portraits)
    for j in canon["crew_joins"]:
        add("characters", j["slug"], j["name"])
    for c in pres["crews"]:
        for m in c.get("members", []):
            add("characters", m["slug"], m["name"])
    for ch in pres["characters"]:
        add("characters", ch["slug"], ch["name"])

    # islands — voyage waypoints that resolve to a real island (name IS the wiki title)
    islands_by_slug = {i["slug"]: i for i in canon["islands"]}
    for w in canon["voyage"]["waypoints"]:
        s = w.get("slug")
        if not s:
            continue
        isl = islands_by_slug.get(s)
        if isl:
            add("islands", s, isl["name"], page=isl["name"])

    # fruits — the 23 official API PNGs, keyed by canon fruit slug (direct download)
    fruits_by_id = {f["id"]: f for f in canon["fruits"]}
    raw = json.loads(RAW_FRUITS.read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else raw.get("data", [])
    for r in rows:
        if not r.get("filename"):
            continue
        cf = fruits_by_id.get(r["id"])
        name = cf["name"] if cf else r["name"]
        slug = slugify(name)
        add("fruits", slug, name, direct_url=r["filename"], ref_id=r["id"])

    return items


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 6 official-art pipeline.")
    ap.add_argument("--refresh", action="store_true", help="re-fetch everything, ignore caches")
    ap.add_argument("--reprocess", action="store_true",
                    help="re-run Pillow/matte processing from cached raw bytes (no re-scraping)")
    args = ap.parse_args()

    started = time.time()
    if not CANON_JSON.exists():
        print("data/canon.json missing — run scripts/normalize.py first", file=sys.stderr)
        return 1
    canon = json.loads(CANON_JSON.read_text(encoding="utf-8"))
    overrides = json.loads(ART_SOURCES.read_text(encoding="utf-8"))

    print("=" * 70)
    print("grand-line-interface :: sync_art.py  (Phase 6 — real art)")
    print(f"source: {API} + images.api-onepiece.com")
    print(f"license: {LICENSE}")
    print(f"policy: {REQUEST_DELAY_S}s/request, batch={BATCH_SIZE}, refresh={args.refresh}")
    print("=" * 70)

    wantlist = build_wantlist(canon, overrides)
    by_kind: dict[str, int] = {}
    for it in wantlist:
        by_kind[it["kind"]] = by_kind.get(it["kind"], 0) + 1
    print("want-list: " + ", ".join(f"{k}={v}" for k, v in sorted(by_kind.items())))
    print(f"           {len(wantlist)} images total\n")

    # 1) Resolve every wiki-sourced image URL (skip fruits — they carry direct URLs)
    pageimage_titles = [it["page"] for it in wantlist if it["direct_url"] is None and not it["image"]]
    print(f"[1] resolving {len(set(pageimage_titles))} wiki titles via pageimages...")
    resolved = resolve_pageimages(pageimage_titles, refresh=args.refresh)

    # explicit File: overrides
    for it in wantlist:
        if it["image"] and it["direct_url"] is None:
            it["_url"] = resolve_file_url(it["image"], refresh=args.refresh)
        elif it["direct_url"]:
            it["_url"] = it["direct_url"]
        else:
            it["_url"] = resolved.get(it["page"])

    # 2) Download + process
    print(f"[2] downloading + processing (existing files skipped unless --refresh)...")
    manifest_rows: list[dict] = []
    misses: list[dict] = []
    for it in wantlist:
        kind, slug = it["kind"], it["slug"]
        out_path = ART_ROOT / kind / f"{slug}.webp"
        url = it.get("_url")
        if not url:
            misses.append({"kind": kind, "slug": slug, "page": it["page"],
                           "why": "no image resolved (fix page/image in canon/art_sources.json)"})
            continue

        if out_path.exists() and not args.refresh and not args.reprocess:
            STATS["skipped"] += 1
            # rebuild the manifest row from disk so re-runs keep receipts intact
            existing = out_path.read_bytes()
            with Image.open(io.BytesIO(existing)) as im:
                w, h = im.size
                was_matted = im.mode == "RGBA" and im.getchannel("A").getextrema()[0] < 250
            manifest_rows.append({
                "kind": kind, "slug": slug, "ref_id": it.get("ref_id"), "page": it["page"],
                "source_url": url, "retrieved": "(cached on disk)",
                "sha256": hashlib.sha256(existing).hexdigest(),
                "w": w, "h": h, "matted": was_matted,
                "file": f"art/{kind}/{slug}.webp", "license": LICENSE,
            })
            continue

        try:
            raw = download_binary(url, refresh=args.refresh)
        except Exception as exc:  # noqa: BLE001 — any fetch failure is a miss, not a crash
            misses.append({"kind": kind, "slug": slug, "page": it["page"],
                           "why": f"download failed: {exc}"})
            continue
        if not raw:
            misses.append({"kind": kind, "slug": slug, "page": it["page"], "why": "0 bytes"})
            continue
        try:
            mode, size = KIND_PROCESS[kind]
            ov = overrides.get(kind, {}).get(slug, {})
            no_matte = isinstance(ov, dict) and ov.get("no_matte")
            want_matte = MATTE_KINDS.get(kind) if not no_matte else None
            ov_focus = ov.get("focus") if isinstance(ov, dict) else None
            webp, w, h, matted, focus_used = process_image(
                raw, mode, size, matte_model=want_matte, focus=ov_focus)
        except Exception as exc:  # noqa: BLE001 — non-image (HTML error page) lands here
            misses.append({"kind": kind, "slug": slug, "page": it["page"],
                           "why": f"not a decodable image ({exc}) — likely an HTML error page"})
            continue

        write_bytes(out_path, webp)
        row = {
            "kind": kind, "slug": slug, "ref_id": it.get("ref_id"), "page": it["page"],
            "source_url": url, "retrieved": datetime.now(timezone.utc).isoformat(),
            "sha256": hashlib.sha256(webp).hexdigest(),
            "w": w, "h": h, "matted": matted,
            "file": f"art/{kind}/{slug}.webp", "license": LICENSE,
        }
        if focus_used:
            row["focus"] = focus_used
        manifest_rows.append(row)
        flag = " [matted]" if matted else (" [no-matte]" if want_matte else "")
        if focus_used:
            flag += f" [face:{focus_used['source']}]"
        print(f"    {kind}/{slug}.webp  ({w}x{h}){flag}")

    # 3) Manifest
    counts = {k: sum(1 for r in manifest_rows if r["kind"] == k) for k in KIND_PROCESS}
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "scripts/sync_art.py",
        "license_note": (
            "Every file below is official artwork © Eiichiro Oda / Shueisha / Toei Animation, "
            "used as attributed fan reference and EXCLUDED from the repo's MIT license. "
            "Original SVG marks in the app remain as fallbacks."
        ),
        "source": {"wiki": API, "fruit_api": "https://images.api-onepiece.com",
                   "user_agent": USER_AGENT, "delay_seconds": REQUEST_DELAY_S},
        "counts": counts,
        "total": len(manifest_rows),
        "misses": misses,
        "images": sorted(manifest_rows, key=lambda r: (r["kind"], r["slug"])),
    }
    write_text(MANIFEST_PATH, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

    # 4) Contact sheet (eyeball QA)
    write_text(CONTACT_SHEET, render_contact_sheet(manifest))

    # 5) Report
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    for k in KIND_PROCESS:
        want = by_kind.get(k, 0)
        print(f"  {k:12} {counts[k]:>3}/{want:<3} images")
    print(f"  {'TOTAL':12} {len(manifest_rows):>3}/{len(wantlist):<3}")
    print(f"\n  network {STATS['requests']} | cache {STATS['cache_hits']} | "
          f"downloads {STATS['downloads']} | skipped {STATS['skipped']} | retries {STATS['retries']}")
    print(f"  manifest      {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    print(f"  contact sheet {CONTACT_SHEET.relative_to(REPO_ROOT)}")
    print(f"  elapsed {time.time() - started:.0f}s")

    required_misses = [m for m in misses if m["kind"] in REQUIRED_KINDS]
    optional_misses = [m for m in misses if m["kind"] not in REQUIRED_KINDS]
    if optional_misses:
        print(f"\n  optional misses ({len(optional_misses)}) — ok, no wiki art for these:")
        for m in optional_misses:
            print(f"     - {m['kind']}/{m['slug']}  ({m['page']!r}): {m['why']}")
    if required_misses:
        print(f"\n  !! REQUIRED MISSES ({len(required_misses)}) — add a page/image override "
              f"in canon/art_sources.json and re-run:")
        for m in required_misses:
            print(f"     - {m['kind']}/{m['slug']}  page={m['page']!r}: {m['why']}")
        print()
        return 1

    print("\n  all required art resolved. Eyeball the contact sheet; fix wrong images via")
    print("  canon/art_sources.json overrides, then re-run.\n")
    return 0


def render_contact_sheet(manifest: dict) -> str:
    cells = []
    for r in manifest["images"]:
        # 6E: before/after — the raw wiki original (if cached) next to our cutout,
        # so a bad matte is caught by eyeball before it ever reaches the map.
        before = ""
        cache = raw_cache_path(r["source_url"])
        if cache.exists():
            before = f'<img class="before" src="_art_cache/raw/{cache.name}" alt="" loading="lazy">'
        matte_badge = ' <span class="matted">✂ matted</span>' if r.get("matted") else ""
        focus = r.get("focus")
        if focus:
            label = "focus override" if focus["source"] == "override" else f'face:{focus["source"]}'
            matte_badge += f' <span class="focus">⊙ {label}</span>'
        # characters: preview the EXACT circular crop the map renders, so a
        # torso-framed chip is caught here, not on the globe.
        circ = (
            f'<img class="circ" src="../../public/{r["file"]}" alt="" loading="lazy">'
            if r["kind"] == "characters" else ""
        )
        cells.append(
            f'<figure><div class="pair">{before}'
            f'<img src="../../public/{r["file"]}" alt="{r["slug"]}" loading="lazy">{circ}</div>'
            f'<figcaption><b>{r["kind"]}/{r["slug"]}</b>{matte_badge}<br>'
            f'<span class="page">{r["page"]}</span><br>'
            f'<a href="{r["source_url"]}" target="_blank">source</a> · {r["w"]}×{r["h"]}</figcaption></figure>'
        )
    miss_html = ""
    if manifest["misses"]:
        rows = "".join(
            f'<li><b>{m["kind"]}/{m["slug"]}</b> — page <code>{m["page"]}</code>: {m["why"]}</li>'
            for m in manifest["misses"]
        )
        miss_html = f'<section class="misses"><h2>Misses ({len(manifest["misses"])})</h2><ul>{rows}</ul></section>'
    counts = " · ".join(f"{k}: {v}" for k, v in manifest["counts"].items())
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Grand Line Interface — art contact sheet</title>
<style>
  body{{background:#0b1120;color:#e2e8f0;font:14px/1.4 -apple-system,system-ui,sans-serif;margin:24px}}
  h1{{font-size:20px;margin:0 0 4px}} .sub{{color:#94a3b8;margin:0 0 20px}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:14px}}
  figure{{margin:0;background:#111c33;border:1px solid #1e293b;border-radius:10px;padding:8px;text-align:center}}
  .pair{{display:flex;gap:4px}} .pair img{{min-width:0;flex:1}}
  img{{width:100%;height:130px;object-fit:contain;background:
      repeating-conic-gradient(#1e293b 0% 25%,#0f172a 0% 50%) 50%/16px 16px;border-radius:6px}}
  img.before{{opacity:0.75}}
  img.circ{{flex:0 0 64px;width:64px;height:64px;object-fit:cover;border-radius:50%;
      align-self:center;border:2px solid #b08d3e;background:#0f172a}}
  .matted{{color:#86efac;font-size:10px}}
  .focus{{color:#fcd34d;font-size:10px}}
  figcaption{{font-size:11px;margin-top:6px;color:#cbd5e1;word-break:break-word}}
  .page{{color:#7dd3fc}} a{{color:#fca5a5}}
  .misses{{margin-top:28px;background:#2a0f14;border:1px solid #7f1d1d;border-radius:10px;padding:12px 18px}}
  .misses h2{{margin:0 0 8px;font-size:15px;color:#fca5a5}} .misses li{{margin:3px 0}}
  code{{background:#0b1120;padding:1px 5px;border-radius:4px}}
</style></head><body>
<h1>Grand Line Interface — art contact sheet</h1>
<p class="sub">{manifest['total']} images · {counts} · generated {manifest['generated_at'][:19]}Z<br>
{manifest['license_note']}</p>
<div class="grid">{''.join(cells)}</div>
{miss_html}
</body></html>"""


if __name__ == "__main__":
    sys.exit(main())
