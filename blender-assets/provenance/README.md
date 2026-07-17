# Sol production provenance

This directory records how the Blender asset-production phase was built. The
project's public Shipwright's Log identifies the model and harness; the JSON
snapshot here preserves the measured Codex token counters behind that summary.

Token counters come from the local Codex Desktop session's `token_count`
events. `total_tokens` includes cached input tokens. It is therefore a workload
and context-reuse measurement, not a direct invoice or a count of newly written
words. `uncached_input_tokens` is derived as `input_tokens -
cached_input_tokens`.

The snapshot is intentionally timestamped. Continuing the same Codex task
after that timestamp consumes additional tokens and does not rewrite history.

