# Grand Line Interface — Reddit launch drafts

These are text-post drafts, not a cross-post blast. Verify the active Reddit
account, its participation history, each community's current rules, and the
available flair before saving or publishing. Do not publish all four at once.

Project disclosure used throughout: built by the poster, free, non-commercial,
open source, no affiliate links.

## r/OnePiece

**Suggested title**

I built a spoiler-safe One Piece map that changes with your chapter — looking for fans to help verify it

**Suggested body**

I kept wanting a world map I could send to someone watching or reading for the first time without accidentally showing them every island, crew, and reveal in the series.

So I built Grand Line Interface. You give it your chapter or episode, and the atlas redraws to that point in the story: the route advances, locations become visible, crews change, and everything after your bookmark stays fogged. There is also a guided Journey mode if you want to watch the voyage unfold instead of moving the timeline manually.

The project is free, non-commercial, and open source. I built it because I love One Piece, not as a product or an ad.

Spoiler-safe starting point: https://grandlineinterface.com/?ch=1

Source: https://github.com/shawnla90/grand-line-interface

What I need from people who know the geography better than I do: which island placement, reveal chapter, or crew appearance feels wrong? Even one correction with a chapter reference helps. I would also love to know whether the chapter/episode control makes sense without instructions.

**Posting note**

r/OnePiece requires thoughtful, limited self-promotion and recommends roughly a
9:1 participation ratio. Use a text post, select the correct flair, and do not
publish from an account that does not meet that community-participation bar.

## r/OnePieceSpoilers

**Suggested title**

I mapped the Grand Line by when locations become known, not only where they are

**Suggested body**

Most One Piece maps answer “where is everything?” I wanted to answer a different question: “what did the world look like to us at this exact chapter?”

Grand Line Interface is a chapter-driven atlas. At the latest point it includes the voyage through Wano and Onigashima, Egghead, Elbaph, moving geography, story scenes, and explorable 3D island systems. Scrub backward and the later state disappears again instead of leaking into earlier chapters.

Latest view: https://grandlineinterface.com/?ch=1185

The project is free, non-commercial, and open source: https://github.com/shawnla90/grand-line-interface

I am looking for brutal canon checks from current readers. Which transition or reveal is gated at the wrong chapter? Which endgame location is visually misleading? The goal is to make every state traceable to a chapter, and to label anything derived instead of pretending it is confirmed.

**Posting note**

This community limits promotion and does not welcome AI-generated content. Keep
the post focused on the fan atlas and canon discussion, use only original app
captures, credit sources, and ask moderators first if the rule interpretation is
unclear.

## r/ClaudeCode

**Suggested title**

I built a spoiler-safe One Piece atlas across Claude Code + Codex — here is the handoff system that kept it coherent

**Suggested body**

I have been building a free, open-source One Piece atlas that redraws itself for any chapter or episode. The interesting part for this sub is not the fandom layer; it is how the project survived being passed between Claude Code and Codex across data, React/MapLibre, Blender, audio, and deployment work.

The division that held up:

- Claude Code owned the original data spine, chapter-axis runtime, map, and most product phases.
- Codex planned later phases and built the canon-aware Blender asset factory, manifests, verification scripts, and runtime handoffs.
- The repository—not either agent's memory—became the contract: generated data stays machine-owned, canon files stay human-owned, and every runtime asset carries placement, chapter gates, bounds, projection support, and source receipts.
- Static “it exists” checks were not enough. We added runtime audits for camera movement, scene mounting, audio continuity, model requests, and chapter progression after several changes looked correct in code but failed in the actual experience.

The failure that taught me the most: a directory said 20/20 islands were available, but that did not prove a user could see one. The real contract had to include zoom, projection, proximity, GPU mounting, and discoverability.

Live result: https://grandlineinterface.com

Repo and build log: https://github.com/shawnla90/grand-line-interface

I built this project; it is free, non-commercial, MIT-licensed where the assets allow it, and has no affiliate links. I would love feedback from anyone running long multi-agent builds: what do you make the durable handoff—the issue tracker, manifests, tests, or something else?

**Suggested flair:** Showcase, Workflow, or Project (use the closest available).

## r/buildinpublic

**Suggested title**

I spent months building a free One Piece atlas. The hardest part was making AI work verifiable.

**Suggested body**

I am building Grand Line Interface, a free One Piece atlas that changes based on where you are in the story. Enter a chapter or episode and it shows the world, route, crews, scenes, and islands known at that point while fogging everything later.

This started as a map and turned into a lesson in building a visual product with multiple AI coding agents.

Three things I learned:

1. The repository has to be the memory. Claude Code and Codex can hand work back and forth only when the manifests, chapter gates, source receipts, and audits are more trustworthy than a chat summary.
2. “The build passed” is not a user test. I repeatedly had code that was technically present but invisible, glitchy, or badly timed in the actual journey.
3. Discoverability beats cleverness. A cryptic 3D asset counter made finished islands look missing. One plain “Explore 3D islands” button fixed more than another animation would have.

It is live at https://grandlineinterface.com and open source at https://github.com/shawnla90/grand-line-interface. I built it as a non-commercial fan project: no ads, no paid plan, no affiliate link.

The next goal is collaboration, not more blind scope: verify island coordinates and chapter gates, improve mobile/performance, and let fans contribute canon events and spoiler-safe theory layers.

Specific feedback I need: can you understand the chapter control, Journey mode, and 3D islands within your first 30 seconds? Where do you hesitate?
