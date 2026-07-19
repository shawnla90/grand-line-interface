# Overlay intake — putting the page itself on an event

How a colored panel, restored spread, or fan animation becomes visible on an
`/event/[slug]` page. Data-only, like pack intake (`docs/PACK_INTAKE.md`): a
drop is a media file plus one registry row. No TypeScript, no Python edits, no
flags — the registry starts empty and the first valid row lights up on its own.

## Who does what

- **Asset track (Codex) or a human sourcing run** produces the media: a colored
  panel still (`.png`/`.webp`/`.jpg`) or a motion piece (`.webm`/`.mp4`).
  Motion pieces render muted + looping — author them silent.
- **The app track** (this checkout) lands the file and the row, runs the guard,
  and ships. One integration owner per drop, per the workspace-ownership rule.

## The drop, step by step

1. **Land the media** under `public/art/overlays/<event-slug>/<name>.<ext>`.
   Nothing outside `/art/overlays/` — that directory is the license boundary
   (art is © its rights holders, MIT-excluded, same as the rest of `public/art`).
2. **Add one row** to `canon/overlays.json` `overlays[]`:

   ```json
   {
     "slug": "marineford-576-colored",
     "kind": "panel",
     "event_slug": "the-death-of-whitebeard",
     "from_chapter": 576,
     "media_path": "/art/overlays/the-death-of-whitebeard/576-colored.webp",
     "title": "The One Piece is real — the colored spread",
     "credit": {
       "source_ref": "Hand-authored. Digital colored edition, vol. 59. NEEDS HUMAN VERIFICATION against the source.",
       "license_note": "(c) Shueisha/Eiichiro Oda — carried as fan archive, zero-profit"
     },
     "canon_confidence": "canon",
     "verified": false
   }
   ```

   Rules the guard enforces (`scripts/check_overlays.py`):
   - `event_slug` resolves in `canon/events.json` — no event, no overlay. If the
     beat isn't charted yet, author the event FIRST (that file's own rules).
   - `from_chapter >= ` the event's `occurred_chapter`. An overlay can never
     show before its beat. (It may gate LATER — e.g. a panel whose content
     spoils a follow-up reveal.)
   - the file exists, the extension matches the kind, and both credit fields
     are present. Unattributed art does not ship.
3. **Run the guard**: `python3 scripts/check_overlays.py` → must exit 0.
4. **Eyeball it**: open `/event/<event-slug>?ch=<from_chapter>` — the "The page
   itself" section appears between "Where/Weight" and "Who was there". Check
   one chapter EARLIER too: the section must be gone.
5. Every row lands `verified:false` until Shawn confirms the event match, the
   gate, and the credit. Same lifecycle as every canon file.

## Why events, not scenes

Story-simulation scenes are the OTHER system (registry + runtime, Codex-owned
packs) and already carry their own art pipeline. Events are the atlas's own
hand-authored beat layer with stable slugs and reader-facing pages — the right
anchor for "show me the real page." If a fight deserves both, it gets a sim
scene from the asset track AND an overlay row here; they do not share plumbing.

## Renderer contract (for reference, already built)

`lib/overlays.ts` (schema + `overlaysForEvent`), `lib/overlays-load.ts`
(server-only loader), viewer inside `components/entry/EventEntry.tsx`. The
event page pre-gates; the component never re-gates. Adding fields to a row
means editing the zod schema + this doc + the guard, in one change.
