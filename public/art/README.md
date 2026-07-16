# public/art/ — official artwork (NOT MIT-licensed)

Everything under this directory is **official One Piece artwork** — Jolly Rogers,
character portraits, ship renders, Devil Fruit art, and location images — scraped
from the [One Piece Fandom wiki](https://onepiece.fandom.com) and the
[api-onepiece.com](https://api-onepiece.com) image CDN.

**These images are © Eiichiro Oda / Shueisha / Toei Animation.** They are used here
as attributed fan reference on a non-commercial fan atlas. **They are explicitly
excluded from this repository's MIT license.** The MIT license covers the *code*
only, never the contents of this folder.

## Receipts

Every file here has a row in [`data/generated/art_manifest.json`](../../data/generated/art_manifest.json)
carrying its exact source URL, sha256, dimensions, and license string.
`scripts/check_canon.py` (`art_manifest_attributed`) fails the build if any file
here has no manifest row, or any manifest row points at a missing file — so nothing
lands here unattributed.

## Regenerating

```
python3 scripts/sync_art.py            # skips files already downloaded
python3 scripts/sync_art.py --refresh  # re-fetches everything
```

Wrong images (the wiki's `pageimages` returns a page's *first* image, which is
occasionally not the one we want) are corrected in
[`canon/art_sources.json`](../../canon/art_sources.json), never by hand-editing here.

## If a takedown ever lands

The app keeps its original hand-drawn SVG marks as fallbacks. Deleting this entire
folder leaves a fully working atlas — every crew, character, and island still renders
with its original cartographic mark. The art is an enhancement layer, not a dependency.
