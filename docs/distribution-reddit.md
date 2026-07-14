# Dead Reckoning — Reddit Distribution (Phase 4 recon)

Working doc. Phase 4 does not block Phase 1. Nothing here touches app code.

All subscriber counts and rule text below were pulled **live from Reddit's own
`about.json` / `about/rules.json` endpoints on 2026-07-14**, through the authed Playwright
session in `~/clearbox-reddit` (plain HTTP clients get a hard 403 — see "How this was
researched" at the bottom). Rule text is quoted verbatim. Where a sub exposes no rules via
API, the sidebar text is quoted instead and labelled as such.

---

## 0. The one thing that matters

Shawn's Reddit account is the bottleneck, not the build.

`u/Shawntenam` over the **last 90 days**: 287 tracked items, **10 of them in r/OnePiece**.
The other ~96% is B2B/GTM/SaaS marketing content (r/gtmengineering 65, r/GTMbuilders 62,
r/SaaS 39, r/ClaudeGTM 20…). Last r/OnePiece activity: **2026-05-17** — two months cold.

Every fandom mod clicks the profile. What they currently see is a growth marketer who
showed up with a link. Two subs on the list encode this as an actual rule:

- **r/OnePiece rule 6**: the 9:1 ratio — nine quality discussion threads per promotional one.
- **r/InternetIsBeautiful**: *"If almost all your recent activity on Reddit is advertising
  something you made, you will not be allowed to post here. 90% of your recent participation
  on Reddit should have nothing to do with a site you own or operate."*

On today's account mix, **he fails the r/InternetIsBeautiful bar as written** and is thin on
r/OnePiece's. The fix is cheap but it is *time*, not code: ~2-3 weeks of genuine r/OnePiece
commenting before the atlas link ever gets posted. That warm-up is rung 0 of the ladder and
it is the only unskippable step in this document.

**The good news, and it's real:** he already has fandom proof-of-fit. His r/OnePiece post
[*"Which Devil Fruit would you choose, but there's a catch"*](https://www.reddit.com/r/OnePiece/comments/1t7uk0c/which_devil_fruit_would_you_choose_but_theres_a/)
(2026-05-09, `Discussion` flair) did **59 upvotes, 84 comments, 71,000 views**. He can land in
that sub. He has done it. He just has to not walk in cold with a URL.

---

## 1. The subreddit map

### Verdict column legend
- **YES** — link to his own site is permitted under stated conditions
- **THREAD** — only inside a designated weekly/recurring thread
- **DAY** — only on a specific day of the week
- **MODMAIL** — requires asking mods first
- **NO** — self-promo links effectively banned

### Fandom

| Sub | Subs | Own link? | Conditions | What gets removed |
|---|---|---|---|---|
| **r/OnePiece** | **5,305,775** | **YES** | 9:1 ratio; **flair mandatory**; text post > bare link; no spoilers in title | Unflaired posts (auto), low-effort, spoiler titles |
| r/MemePiece | 830,852 | **NO** | Memes only | Any promo — *"will result in a ban"* |
| r/Piratefolk | 252,494 | **MODMAIL** | Ask first, always | Unsolicited promo; **AI-written text posts** |
| r/manga | 4,792,265 | Weak YES | Must be a genuine community participant | Profiteering/soliciting links |
| r/anime | 14,346,006 | Weak NO | A web tool isn't really on-topic | Restricted/low-effort content |
| r/OnePieceLiveAction | 88,712 | marginal | LA-show scoped | — |
| r/OnePieceTC | 86,653 | skip | Treasure Cruise game sub | — |

**r/OnePiece — rule 6, "Self promotion" (verbatim):**
> *"Self-promotion should be thoughtful, limited, and consistently well received by the
> community. The [9:1 ratio](https://www.reddit.com/wiki/selfpromotion) (ie. every one
> promotional video should be followed by approximately nine quality discussion threads)
> should be followed. In addition, Youtube reviews and theorist videos must: 1. Be in a text
> post format. 2. Summarise your video for the community or create new points to further the
> discussion of the videos."*

Two things fall out of that. First, there is **no outright link ban** — self-promo is allowed,
gated on ratio and reception. Second, the sub's stated preference for promotional content is
**text post + summary + new discussion points**. That's the format to copy even though the
letter of it addresses YouTube: a text post that explains the thing and asks a real question,
with the link in the body.

**r/OnePiece — rule 12, "Flair your posts" (verbatim):**
> *"Unflaired posts will be automatically removed until one is selected."*

Live flair list (14): `Theory`, `Discussion`, `Powerscaling`, `Analysis`, `Fanart`, `Cosplay`,
`Media`, `Merchandise`, `Help`, `Meta`, `Misc`, `Big News`, `One Piece RED`, `Live Action`.
→ **Use `Analysis`.** Second choice `Discussion`. It is *not* `Fanart` (that rule demands a
source link to the original artist and caps you at one per 24h) and *not* `Media`.

**r/OnePiece — rule 1, "Be mindful of Spoilers" (verbatim, abridged):**
> *"No spoilers in titles. Use spoiler tags for anything that hasn't been revealed in the
> anime yet… If the author hasn't seen beyond X chapter/episode, please be respectful and tag
> appropriately."*

This rule is the product. Say that out loud in the post — the sub has a *hand-enforced* social
norm for exactly the problem Dead Reckoning solves in software. That is the hook (§2).

**r/Piratefolk — "Fan Art / Cosplay / Self promotion" (verbatim):**
> *"No unsolicited self promotion is allowed. This includes promoting other subreddits or
> discords. Posting your friends youtube video or twitch stream counts. Please ask in modmail
> before making a post."*

And, critically, from their "Banned Content" rule:
> *"AI Fan art, Videos, Memes, and Text posts are banned"*

Piratefolk is the *anti*-hype One Piece sub (their rules literally say *"Do not Whiteknight for
Oda"*). Modmail first or don't bother. And an AI-drafted post there is a ban, not a removal.

**r/manga — "Excessive or Aggregate Site Self-Promotion" (verbatim):**
> *"Posts to your own blog or YouTube video are only okay under strict requirements. For every
> post you do linking to your blog, you should have done numerous other posts in various
> discussions. If someone can tell from a glance that the majority of your posts are only in
> relation to your own blog or YouTube account, you aren't properly participating in the
> community. Also… doing re-posts when your original doesn't do well is not allowed."*

Note that last clause — **deleting a flop and reposting is explicitly a violation.** It is also
Shawn's instinct as a growth operator. Don't.

**r/MemePiece — "No Promotion, Self-Advertisement or Spam" (verbatim):**
> *"No spam, self-advertisement, or reposts for the reasons below (aka Karma Farming, Clout
> Chasing) and redirecting to other social media accounts will result in a ban from this
> subreddit."*

Zero link value. Only reachable later as an organic meme (a "Jinbe standing on the Sunny for
550 episodes" meme would genuinely play there) — with **no link, no attribution to the site.**
That is a brand play, not a distribution play. Low priority.

### Data-viz

| Sub | Subs | Own link? | Conditions | What gets removed |
|---|---|---|---|---|
| **r/dataisbeautiful** | **21,783,217** | **YES** | `[OC]` tag + **sources & tools in first top-level comment** + plain title | Clickbait titles, missing OC comment, false OC claims |
| r/MapPorn | 6,336,477 | **NO** | Rule: *"No Advertising"* | Ads; real-world-map scoped anyway |
| r/imaginarymaps | 551,545 | risky | Must be *fictional* + *OC* | See below — likely disqualified |
| r/visualization | 139,757 | Weak YES | Must drive discussion about **design/construction** | Sales, memes |
| r/worldbuilding | 1,903,837 | **YES** | *"non-disruptive advertising"* explicitly allowed | Disruptive/irrelevant ads |
| r/datavisualization | 28,939 | YES | No formal rules (0 via API) | — (tiny sub) |

**r/dataisbeautiful — rules 2, 3, 4, 7 (verbatim):**
> *"[2] Directly link to the original source article of the visualization… If you made the
> visualization yourself, tag it as [OC]."*
> *"[3] [OC] posts must state the data source(s) and tool(s) used in the first top-level
> comment on their submission."*
> *"[4] DO NOT claim '[OC]' for visualizations that are not yours."*
> *"[7] Post titles must describe the data plainly without using sensationalized headlines.
> Clickbait posts will be removed."*

This is the sub with a hard, mechanical format. It is also **21.8M subscribers — by far the
biggest ceiling on the list.** The format:

- Title: `[OC] ...` — plain, descriptive, **no hook.** DiB punishes the exact copywriting
  instinct Shawn is good at. "Every One Piece island, plotted by the chapter it debuts in
  (1,185 chapters)" is a DiB title. "I built the map Oda never gave you" is a removal.
- The submission should be **the visual** (a PNG of the map, or better a short screen-capture
  of the fog receding as the chapter slider drags) — DiB is chart-first, not link-first. The
  site URL goes in the body/comment.
- **First top-level comment, immediately, by him** — this is rule 3 and it is enforced:
  > Data: api-onepiece.com v2 (1,185 chapters / 50 arcs / 128 locations); One Piece Fandom
  > wiki (chapter+episode arc ranges, island debut chapters). Tools: Python (normalize),
  > MapLibre GL JS, Next.js, TypeScript. Island coordinates hand-authored (no upstream source
  > has them). Live: <url>

That comment is not a chore — it is the single best advertisement the project has, because
*"island coordinates hand-authored, no upstream source has them"* is the whole moat stated as
a footnote. DiB people respect that sentence.

**r/imaginarymaps — the disqualifier (verbatim):**
> *"Post must be a map, be fictional and be OC or commissioned. No plagiarism."*
> *"No map generating tools or websites (excluding GIS tools)"*

The One Piece world is fictional, but it is **Oda's**, not Shawn's OC. The plagiarism clause
plus the "no map websites" clause makes this a likely removal and a possible bad-faith read.
**Skip**, or modmail first. Not worth the risk for 551k.

**r/worldbuilding — "We allow non-disruptive advertising" (verbatim):**
> *"In general, we're tolerant of ads that respect our community and meet our worldbuilding
> context requirements. Ads should be able to demonstrate some relevance and usefulness to the
> community… It's always okay to monetize your own worldbuilding."*

Underrated, 1.9M subs, and the *most permissive promo rule on the entire list*. But the angle
has to be the **technique**, not the fandom: "how I built a spoiler-gated map where the world
state is a function of reader position in the timeline" is a genuinely novel worldbuilding tool
idea. Worldbuilders would want this for their own worlds.

### Dev / build-in-public

| Sub | Subs | Own link? | Conditions | What gets removed |
|---|---|---|---|---|
| **r/SideProject** | **776,867** | **YES** | Title format `[Name] - [Short description]` | (no formal rules via API) |
| **r/webdev** | **3,280,862** | **DAY** | **Showoff Saturday only** + correct flair | Any showcase Sun–Fri; all commercial promo |
| r/InternetIsBeautiful | 16,628,819 | **YES**\* | Interactive site only; **90/10 recent activity** | Business tools; articles/videos/images |
| r/programming | 6,899,899 | **NO**\*\* | Technical write-up only | *"I Made This"* project demos |
| r/nextjs | 171,034 | **THREAD** | Weekly show-and-tell only | Standalone project/portfolio posts |
| r/reactjs | 508,557 | Weak | Be a contributor first | Value-extractors |
| r/buildinpublic | 105,821 | **YES** | Progress + lessons, not a bare launch | Promo without context |
| r/opensource | 368,109 | YES | **Needs an OSI LICENSE file**; `Promotional` flair | <10% self-promo; **AI-generated content** |
| r/coolgithubprojects | 108,294 | YES | **Needs a public GitHub repo** | Non-GitHub |
| r/SomebodyMakeThis | 94,807 | **NO** | *"No Promotions"* | — |

**r/webdev — rules 4 and 6 (verbatim):**
> *"[No commercial promotions/solicitations] We do not allow any commercial promotion or
> solicitation. Violations can result in a ban."*
> *"[No soliciting feedback not on Saturday] Sharing your project, portfolio, or any other
> content that you want to either show off or request feedback on is limited to Showoff
> Saturday. If you post such content on any other day, it will be removed. Posts must be tagged
> with the correct flair… Think project, not product. Focus on the technical details of your
> project and how it's relevant to the audience of the subreddit."*

**Saturday. Correct flair. "Think project, not product."** Dead Reckoning is a free fan atlas
with no pricing page — it clears the commercial bar cleanly, *as long as nothing in the post or
on the site sells anything.*

**r/InternetIsBeautiful — the three rules that decide it (verbatim):**
> *"[No accounts designed for self-promotion] This sub follows the 90/10 rule for
> self-promotion. If almost all your recent activity on Reddit is advertising something you
> made, you will not be allowed to post here. 90% of your recent participation on Reddit
> should have nothing to do with a site you own or operate."*
> *"[No Business Tools] Posts featuring tools designed for launching products, job boards, SEO
> optimization, or any other tool aimed at businesses are not allowed."*
> *"[No Articles, Videos or Images] Articles, videos and static or animated images are not
> allowed, this includes collections… Blog posts, LinkedIn posts or similar are also not
> allowed."*

\* Read those together. Dead Reckoning is **the perfect content type** for IIB — an interactive,
free, non-commercial website, which is precisely what that sub exists for and what its "no
articles/videos/images" rule is protecting. It is a 16.6M-subscriber sub whose format Dead
Reckoning fits better than anything else on this list.

**And Shawn is currently the wrong person to post it.** The 90/10 rule is about *the account*,
not the site. His recent activity is ~96% self-promotional B2B content. If a mod applies that
rule as written today, it's a rejection — and possibly a flagged account. This is the single
highest-value / highest-risk cell in the entire map. Treat IIB as a **rung-4 reward for a
genuinely rehabilitated posting mix**, not a launch-week target.

\*\* **r/programming — "No Product Promotion/'I Made This' Project Demo Posts" (verbatim):**
> *"r/programming is not the place to post a project to get feedback, ask for help, or
> otherwise promote it. Technical write-ups on what makes a project technically challenging,
> interesting, or educational are allowed and encouraged, but just a link to a GitHub page or a
> list of features is not. The technical write-up must be the focus of the post… **We don't
> care what you built, we care how you build it.**"*

So r/programming is reachable, but only with a real essay and **the essay must be the link.**
Dead Reckoning happens to have one (see §2 — the Jinbe bug).

**r/nextjs — rule (verbatim):**
> *"[No posts shilling your product, project, portfolio, etc] Post your projects in the weekly
> show and tell"* / *"[No rate my website or ask for feedback posts] …If you wish to share your
> project in this community you may do so in the weekly show and tell."*

Weekly thread only. Low ceiling. Cheap to do, don't spend design effort on it.

**r/opensource — two rules that gate it (verbatim):**
> *"Code or repositories linked to MUST have a LICENSE file that MUST be an OSI listed Open
> Source license"*
> *"All AI-generated content is low-effort and ban worthy."*

If Shawn wants r/opensource + r/coolgithubprojects, **the repo must be public with an OSI
license** — that's a Phase-1/2 decision (does the hand-authored `canon/` go public?) with a
distribution consequence. Flagging it now so it isn't discovered at launch.

---

## 2. The angle per sub

The build has three separable stories. Each sub wants exactly one of them, and mixing them is
what gets posts removed.

| Story | What it is | Where it plays |
|---|---|---|
| **A. The fan story** | "I got spoiled. So I built a map that only knows what I've read." | r/OnePiece, r/manga, r/anime |
| **B. The data story** | 1,185 chapters × 128 locations, plotted on a time axis nobody had | r/dataisbeautiful, r/visualization, r/worldbuilding |
| **C. The engineering story** | The Jinbe bug; spoiler-gating as a data-model problem | r/programming, r/webdev, r/SideProject, r/buildinpublic |

### r/OnePiece — flair `Analysis`, text post
**Format that survives:** text post. Body explains the thing, embeds the link mid-body, ends
with a real question. Never a bare link submission.

**Hook — the sub's own rule 1 is the pitch:**
> This sub has a *rule* about not spoiling people who aren't caught up. Every wiki, every map,
> every character page breaks it by default — you look up one island and eat a reveal from 400
> chapters ahead. So I built the opposite: you tell it what chapter you're on, and it renders
> the world *as you know it*. Everything after is fog.

**Then the thing that makes it land, and it is not the map — it's the confession:**
> Ask them what he got wrong.

The most pedantic fandom on earth is a QA department that works for free *if you frame the post
as an audit request rather than a launch.* Surface `canon_confidence` (canon / derived / guess)
in the UI and say so in the post: *"every island coordinate is hand-placed and marked with how
confident I am. The `guess` ones are marked `guess`. Tell me which ones are wrong."*

That single move converts the sub's hostility into its engagement. It also pre-empts the Jinbe
class of error — **and per the project brief, crew-join data is the known landmine.** Ship with
crew joins explicitly marked unverified, and *say* that in the post. If a redditor finds Jinbe
on the Sunny at chapter 700 and Shawn hasn't flagged it, the thread is over.

**Title constraints:** no spoilers, no chapter numbers that reveal anything (rule 1). Something
like *"I built a One Piece map that only shows you what you've actually read"* — states the
product, spoils nothing.

### r/dataisbeautiful — `[OC]`
**Format that survives:** the visual (screen-capture of fog receding on slider-drag > static
PNG), plain title, **mandatory first top-level comment with sources + tools** (rule 3).
**Hook:** the fact, not the story. *"Nobody had ever put the chapter axis on this map"* is the
finding. The GIF of 1,185 chapters of fog burning away in three seconds **is** the
visualization — it's a time-series, and DiB loves a time-series.

### r/webdev — Showoff Saturday, correct flair
**Format that survives:** *"Think project, not product. Focus on the technical details."*
**Hook:** the architecture rules from the brief are the post. Zero request-time fetches. No
database — 4MB of committed JSON is the store. A normalizer that *throws* on an unknown enum
rather than coercing. The hard machine-owned/human-owned directory boundary where a script
writing to `canon/` is a **bug you assert against in code.** That last one is a genuinely good
engineering idea and webdev will argue about it, which is the goal.

### r/programming — the essay, and the essay is the link
**Hook — the Jinbe bug, and it's a great one:**
> Every wiki has a "Debut" field. Ten out of ten Straw Hats have one. It is *wrong* for all ten
> — because "debut" is not "joined." Jinbe debuts at episode 430 and joins at ~977. If you
> scrape the obvious field, he stands on the Thousand Sunny for 547 episodes.

That is a post about **the gap between the data you can get and the data you actually meant**,
which is the most universal problem in the entire discipline. It generalizes instantly to every
engineer who has ever trusted a plausible-looking field. It is also completely honest — it's the
real bug the project was designed around. This is the strongest single piece of writing
available in the whole launch, and r/programming is the only sub that will reward it properly.

### r/SideProject — `[Dead Reckoning] - A spoiler-safe One Piece atlas`
Sidebar-mandated title format. Friendliest sub, lowest stakes. **Its real job is the load test
and the bug hunt** (see ladder).

### r/buildinpublic — progress + lessons
*"No Self-Promotion Without Context… focus on sharing progress, lessons learned."* The lesson
is the Jinbe bug, told short.

### r/worldbuilding — the technique
Not "look at my One Piece map." Instead: *"spoiler-gated worldbuilding — making world state a
function of reader position."* Useful to them for their own worlds. Their ad rule is permissive;
the relevance bar is the real gate.

---

## 3. The cross-post ladder

Design principle: **the fandom is the hardest audience and the only one-shot audience.** Every
rung before r/OnePiece exists to make the r/OnePiece post survive contact. Every rung after it
harvests proof the fandom generated.

Reddit's spam heuristics and human mods both punish same-day multi-sub blasting. Nothing below
posts the same content twice, and no two rungs share a day.

### Rung 0 — Warm the account (weeks −3 to 0). **Unskippable.**
- **r/OnePiece: 9+ genuine comments**, spread over 2-3 weeks. No links. Not "engagement" —
  actual opinions in chapter threads. He's already good at this (his comments there scored 51,
  16, 9). Target rule 6's 9:1 before it's ever tested. ~10 min/day.
- Build the **screen-capture asset** (fog receding on slider drag, 15-30s). This one asset
  carries r/dataisbeautiful, X and LinkedIn. It is the highest-leverage thing in the launch and
  it should exist before rung 1.
- Decide **public repo + OSI license**, yes or no. Gates r/opensource + r/coolgithubprojects.
- **Nothing commercial anywhere on the site.** No Clearbox, no pricing, no email capture, no
  "built by" that leads to a B2B funnel. r/webdev bans commercial promo outright and IIB bans
  business tools. One footer link is enough to kill three subs.

### Rung 1 — Soft launch / bug hunt (week 1, Tue-Wed)
- **r/SideProject** (`[Dead Reckoning] - A spoiler-safe One Piece atlas`)
- **r/buildinpublic** (next day, progress framing)

Its purpose is **not reach.** It is to find the Jinbe-class error in front of 776k
generalists instead of 5.3M pedants, and to confirm the site survives traffic. Fix everything
they find before rung 2. If a fandom-fact bug survives to rung 2, the launch is dead.

### Rung 2 — Technical proof (week 1, **Saturday**)
- **r/webdev, Showoff Saturday.** Forced onto Saturday by rule 6 — which is convenient, because
  it lands after the rung-1 bugs are fixed.

### Rung 3 — **The fandom (week 2-3). The main event.**
- **r/OnePiece**, flair `Analysis`, text post, audit-request framing.

Do this **only** when rung 0's comment history is real and rung 1's bugs are fixed. This is the
post that matters — it's the audience that actually wants the product, and it's the one that
cannot be retried (r/manga's rule names delete-and-repost as a violation; the norm holds
everywhere). Then **sit in the thread for 24-48h and answer everything**, especially the
corrections. The corrections are the content.

### Rung 4 — Harvest the proof (weeks 3-4, one sub every 2-3 days)
Now, and only now, there is something to cite: real fan reception, real corrections
incorporated, real traffic survived.

- **r/dataisbeautiful** `[OC]` — the biggest ceiling (21.8M). Independent of fandom proof on the
  merits, but the post is better after real users have hardened the data.
- **r/programming** — the Jinbe essay. Needs the finished artifact to be credible.
- **r/worldbuilding** — the technique post.
- **r/visualization** — design/construction discussion.
- **r/nextjs** weekly show-and-tell — cheap, low ceiling.
- **r/opensource** / **r/coolgithubprojects** — only if the repo went public with an OSI license.

### Rung 5 — r/InternetIsBeautiful (week 5+, conditional)
16.6M subs. Perfect content fit. **Gated entirely on the 90/10 account rule.** If his posting
mix in the preceding weeks is still ~96% B2B self-promo, this is a rejection. If Phase 4's
fandom warm-up has genuinely shifted the recent mix, it's the biggest single day the project
will have. Do not spend it early.

**Timeline: ~5-6 weeks end to end, and ~3 of those are just earning the right to post in
r/OnePiece.** That is the honest cost.

---

## 4. The Clearbox hook — what actually exists on disk

I grepped `~/clearbox-intel`, `~/clearbox`, `~/clearbox-os`, `~/clearbox-reddit`. Findings,
including two corrections to the brief.

### Correction 1 — the DB path in the brief is an empty file

| Path | Size | Reality |
|---|---|---|
| `~/clearbox-reddit.db` | **0 bytes** | empty decoy (created 2026-07-01) |
| `~/clearbox-intel/data/clearbox-reddit.db` | **0 bytes** | empty decoy (created 2026-07-03) |
| **`~/clearbox-reddit/data/clearbox-reddit.db`** | **2.8 MB** | **the real one** |

Two zero-byte files are shadowing the real DB. Worth deleting them before something opens the
wrong one and silently reports zeros.

### Correction 2 — the tracked view count is 1.49M, not 1.37M

From `account_snapshots`, latest row (2026-07-13):
`link_karma 1,555 · comment_karma 884 · total_posts 172 · total_comments 559 · total_score 3,155 · **total_views 1,489,137**`

Tracked corpus: 731 items, 680 replies, 731 ai_scores, 19 leads (all `new`), 13,473
item_snapshots, 19 runs. (Note: the 2M+ cumulative figure in Shawn's own notes is a broader
number than what this DB tracks — don't conflate them in public copy. **1.49M is the defensible
tracked figure.**)

### What the machinery actually is

**`~/clearbox-reddit/` — a journey tracker, and it is _account-scoped, not subreddit-scoped_.**

This is the important architectural fact, and it's good news. There is **no subreddit allowlist
in `config.py`.** The daily run pulls `u/Shawntenam`'s own overview listing and ingests whatever
it finds. That's why **r/OnePiece is already in the DB with 15 items** — nobody configured it,
it just showed up.

**Minimum change to track the Dead Reckoning launch: one line.**

`clearbox_reddit/config.py` → `ERAS` is documented as *"the one thing meant to be hand-edited as
the story evolves."* Add a third era:

```python
ERAS = [
    {"name": "karma-building", "start": "2026-03-01", "end": "2026-04-06"},
    {"name": "clearbox",       "start": "2026-04-07", "end": "2026-07-XX"},
    {"name": "dead-reckoning", "start": "2026-07-XX", "end": None},
]
```
then `python -m clearbox_reddit.db --retag-eras`. That's it. Views, karma, replies, screenshots,
lead detection, Discord digest and the Google Sheet mirror all follow automatically. **Every
post in the ladder above is tracked with zero new code.**

Modules (all read-only against Reddit): `browser.py` (Playwright + persisted `storage_state.json`
— the only thing that beats Reddit's 403 on plain HTTP clients), `json_api.py`, `fetcher.py`,
`brain.py` (AI scoring), `leads.py`, `views.py`, `snapshots.py`, `stats.py`, `screenshot.py`,
`sync_sheet.py`, `notify.py` (Discord). Tables: `items`, `replies`, `ai_scores`, `leads`,
`account_snapshots`, `item_snapshots`, `runs`, + view `wins`. Runs daily 08:15 on the Mac Mini
via `com.clearbox.reddit-daily.plist`.

**Two cosmetic mismatches, neither a blocker:**
1. `ai_scores.clearbox_relevance` is *"0-10 proximity to Clearbox ICP."* Fan posts score ~0.
   Harmless — the `wins` view keys on `value_score >= 8` OR a live lead, so wins still fire. But
   the column is meaningless for this era and shouldn't be read as a signal.
2. `config/sub_baselines.json` (p90 score / median comments per sub, used for context) **has no
   `OnePiece` row** — 13 B2B subs only. Add one if the stats block should contextualize fandom
   performance. Optional.

### Subreddit *discovery* — exists, but it is not what the brief implies

`~/clearbox-intel/scripts/expand_subreddits.py` + `evaluate_subreddits.py`, against
`~/clearbox-intel/data/content-intel.db` (tables `nl_subreddit_cache` — 156 rows —
`nl_subreddit_eval`, `nl_outreach_deep`, `nl_signals`). API: RapidAPI
`reddit34.p.rapidapi.com/getSimilarSubreddits` + `getSubredditInfo`, key at `~/.env.rapidapi`.

**It is not a general-purpose subreddit finder.** It iterates **B2B leads** in
`nl_outreach_deep`, takes each lead's `specific_subreddit`, and ranks similar subs by
`0.5 × subscribers_log_norm + 0.5 × pain_keyword_overlap` against `BUCKET_PAINS` — hardcoded B2B
pain phrases (*"pipeline coverage", "forecast accuracy", "attribution", "mql quality"*). The
`DENY_LIST` and `NAME_REJECT_PATTERNS` are hand-tuned to *reject* fandom/hobby subs — they
explicitly filter out `spongebob`, `crochet`, `baseball`, `vinyl`. It is a machine built to
**avoid** the exact subs Dead Reckoning needs.

**Honest verdict:** the only reusable piece is the raw `getSimilarSubreddits` call. Everything
above it (lead-binding, the B2B pain vocab, the anti-hobby deny list, the eval loop) would be a
rewrite, not a config change. Pointing it at One Piece is roughly a 60-line new script — seed
`OnePiece` instead of a lead, drop the pain-keyword term, invert the deny list.

And for **this** launch the ROI is ≈ zero: §1 of this document already *is* that output, done by
hand with live rule text the API wouldn't have given anyway. The real value of building the
fandom variant is as a **future Clearbox capability** ("point it at any fandom"), not as a
dependency of the Dead Reckoning launch. **Do not block Phase 4 on it.**

### Not relevant, despite the names
- `~/clearbox/scripts/enterprise-discovery/processors/subreddit_mapper.py` — maps **companies**
  → subreddits (vertical/keyword/mention/competitor). There is no company here. Irrelevant.
- `~/clearbox/reddit_stories/{reddit_client,old_reddit}.py` — the httpx ancestor of
  `json_api.py`, superseded by the Playwright path.
- `~/clearbox/gtm/content/reddit/subreddit-strategy.md` — the existing B2B posting playbook
  (9 subs, 5:1 ratio, per-day schedule). Every sub in it is B2B. Useful only as a **template**
  for the shape of this doc — the content doesn't transfer.
- `~/clearbox-os` — no Reddit machinery.

### The guardrail that is already in the code, and must stay

`~/clearbox-reddit/scripts/draft_posts.py`, line 1:

> *"""Save Reddit post DRAFTS into the logged-in account. **Never posts.** Shawn opens
> reddit.com/drafts afterwards, picks the community per draft, and hits Post himself (**the
> no-auto-post rule stands**)."""*

Good. Keep it. That rule is the difference between this working and this ending in a sitewide
ban (see §5). The whole Clearbox Reddit stack is read-only against Reddit today — fetch, score,
snapshot, notify. **Nothing in Phase 4 should change that.**

---

## 5. The honest risk — what gets him banned

Ranked by likelihood × damage, against how this specific account actually behaves.

**1. Automating any Reddit write.** The stack is read-only and `draft_posts.py` says *"Never
posts."* Automated posting, commenting, or voting is a sitewide TOS violation, not a subreddit
rule — it takes the account, the 1.49M views, and the karma with it. There is no version of this
launch worth that. **Every post and every comment in the ladder is typed by a human.**

**2. Pointing `leads.py` at the fandom.** The lead detector flags "buying interest" in replies
and there are 19 open leads in the table. If that machinery is ever aimed at r/OnePiece — DMing
users who engaged with the atlas, harvesting fan replies into a CRM — that is *precisely* the
growth-hacker behavior fandom mods hunt for, and it's the one that gets a permanent ban plus a
public callout thread. **Hard-exclude `subreddit='OnePiece'` from lead detection before rung 3.**
The fandom is an audience, not a pipeline. If Dead Reckoning ever converts to Clearbox, it does
it because someone read the footer and chose to click — not because they got a DM.

**3. Posting the r/OnePiece link cold.** Disk-verified: 96% of his last-90-day activity is B2B
marketing, and he's been silent in r/OnePiece since 2026-05-17. Rule 6's 9:1 exists to catch
exactly this. Mods click profiles. Rung 0 is not optional.

**4. Any commercial surface on the site at launch.** One Clearbox link, one email capture, one
pricing page in the footer and r/webdev's *"no commercial promotion or solicitation — violations
can result in a ban"* and IIB's *"no business tools"* both trigger. The site must be, and must
*look like*, a free fan project. Because it is one.

**5. AI-written posts.** r/Piratefolk bans AI text posts outright. r/opensource: *"All
AI-generated content is low-effort and ban worthy."* Fandom readers detect the register
instantly. **These posts get written by Shawn, in his voice, by hand.** This is a genuine
constraint on his normal workflow and it is worth naming plainly.

**6. Same-day multi-sub blasting.** The ladder deliberately spaces every rung. Reddit's own spam
filter catches identical/near-identical submissions across subs, and it's the fastest way to look
like a bot.

**7. Delete-and-repost when something flops.** r/manga names it explicitly: *"doing re-posts when
your original doesn't do well is not allowed."* This is a growth-operator reflex. Suppress it.

**8. Getting the canon wrong.** Not a ban — worse. Jinbe on the Thousand Sunny 550 episodes
early, in front of 5.3M people who will find it in ninety seconds. The credibility is
unrecoverable and the thread becomes the story. This is why crew joins ship hand-typed, marked
unverified, and *declared as such in the post*. **Turn the pedantry into the feature: ask them to
audit it.** A fandom that corrects you is a fandom that engaged with you.

---

## How this was researched

Reddit 403s plain HTTP clients (`curl` with a descriptive UA → `403` on all five subs tested),
which is the same wall `~/clearbox-reddit/README.md` documents. Rules and subscriber counts were
pulled through the **existing authed Playwright session** in `~/clearbox-reddit`
(`browser.session()` → `page.request.get`), read-only, ≥1.2s between requests, against
`/r/<sub>/about.json` and `/r/<sub>/about/rules.json` for 27 subreddits on **2026-07-14**.
No Clearbox DB was written to. No repo file outside `docs/` was touched.

Raw capture (ephemeral, scratchpad):
`/private/tmp/claude-501/-Users-shawnos-ai/3b24e18b-a577-4aad-8738-a96aadec70d8/scratchpad/rules_raw.json`

Rules change. Re-pull before launch week — especially r/OnePiece rule 6 and r/webdev's Saturday
rule, which are the two load-bearing constraints in the ladder.
