# Narrative scene safety contract

The eleven chapter-aware narrative systems are now runtime-exported and
`integration_ready`. Use `CLAUDE_CODE_RUNTIME_3D.md` for the integration order.

The hierarchy remains:

`place -> subregion -> landmark -> event scene -> temporal variant`

Every scene's GLB preserves component identifiers and known reveal chapters in
node extras. Unknown gates are `chapter_to_verify` plus `default_hidden=true`.
The app must enforce both the scene-level gate and node-level gate.

Moving entities use a moving anchor rather than a permanent atlas position.
Transit systems use a relationship graph; any temporary globe line remains
`derived_schematic`. Event actors and destruction/storm variants stay hidden
unless their exact gate is verified.

Do not weaken the semantic safety rules in the runtime handoff to make a scene
appear earlier. The complete fallback has its own `safe_full_scene_chapter`
because a raster cannot hide individual landmarks.
