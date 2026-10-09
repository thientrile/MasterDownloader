<!-- OPENWIKI:START -->

## OpenWiki

See [AGENTS.md](AGENTS.md) for OpenWiki agent instructions.

<!-- OPENWIKI:END -->

## Codeflow

- direct-to-main: ok — 13 files, no review surface to lose

- skip: Gate A `/simplify` — 13 files, no bloat to find
- skip: Gate D reality-checker — no auth, money, or migrations here
- Gate B `/code-review` at the default level, and only when the diff is
  non-trivial

Gate C still runs; this repo declares no test script, so expect it to report
that nothing was verified. That is accurate, not a failure — say so rather
than implying the code was checked.
