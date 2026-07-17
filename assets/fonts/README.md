# assets/fonts — the OG cards' typefaces

These two `.ttf` files exist for exactly one reason: **`next/font` cannot feed
Satori.**

`next/font/google` self-hosts at build time, which is why the app makes no
request to Google and the browser makes no external font request. But it emits
content-hashed **`.woff2`** into `.next/static/media/` (e.g.
`bbc41e54d2fcbd21-s.1rgnod-3esatf.woff2`), and `ImageResponse` — the Satori
renderer behind `next/og` — supports **`ttf`/`otf`/`woff` only**, never woff2.
The filenames are unaddressable besides.

So the raw bytes are vendored and committed. The alternative — fetching Google
Fonts inside the OG route — would put a network call in the request path, and
this app has none anywhere: `data/canon.json` is a committed artifact and there
is no database, no ORM and no external API behind any page. A share card is not
where that record breaks.

**`assets/`, not `public/`.** These are server bytes, read by `node:fs` in the
OG route. The browser never asks for them — it gets `next/font`'s woff2. Putting
them in `public/` would ship 143KB to every visitor for nothing.

## The fonts

| File | Family | License |
|---|---|---|
| `PirataOne-Regular.ttf` | Pirata One | SIL Open Font License 1.1 |
| `IMFellEnglish-Regular.ttf` | IM Fell English | SIL Open Font License 1.1 |

Both are OFL, which permits redistribution *provided the licence travels with
them* — hence `PirataOne-OFL.txt` and `IMFellEnglish-OFL.txt` beside this file,
each carrying its real copyright holder (Rodrigo Fuenzalida & Nicolas Massi;
Igino Marini). Not the OFL template — the template ships with `<Copyright
Holder>` placeholders in it and satisfies nothing. Fetched once at authoring
time from
the Google Fonts API (the CSS endpoint serves TTF to a user-agent that predates
woff2), then committed. They are not re-fetched by any build or any request.

Same faces as `app/layout.tsx` uses on the site, on purpose: a share card that
does not look like the page it links to is a worse card.
