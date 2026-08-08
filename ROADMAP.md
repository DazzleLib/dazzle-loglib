# Roadmap

Living roadmap: **[Issue #1](https://github.com/DazzleLib/dazzle-loglib/issues/1)** (kept current there; this file summarizes).

dazzle-loglib is the diagnostic-output member of the DazzleLib **perpendicular tier** — orthogonal engines that any stack layer or tool may adopt, depending only on the `dazzle-lib` bedrock. See the [stack architecture contract](https://github.com/DazzleLib/.github/blob/main/docs/STACK-MAP.md) (ADDENDUM D12).

## Status

| Phase | What | Status |
|---|---|---|
| 0 | Extraction from the vendored `log_lib` lineage (PSS → ghtraf → wtf-restarted → wtf-windows → dazzlecmd, + the continuum redesign) | Done (0.1.0-alpha) |
| 1 | Consumer-defined channel registry (`ChannelDef`), 10-rung verbosity scale, env/CLI resolution, `EmitterProtocol` injection, API-stability canary | Done (0.2.0) |
| 1b | Repository setup: CI + release workflows, roadmap, platform support, repokit tooling — first PyPI publication | Done (0.3.0) |
| 2 | First consumer adoption: diagnostic verbosity in Claude-Session-Backup ([csb#87](https://github.com/DazzleML/Claude-Session-Backup/issues/87)) | In progress |
| 3 | De-vendoring wave: the bundled `log_lib` copies retire onto this dependency ([dazzlecmd#118](https://github.com/DazzleTools/dazzlecmd/issues/118)) | Planned |
| 4 | Sibling `dazzle-helplib` ships; the reserved `dazzle-clilib` composes both | Planned |

## Design space held open (not yet API)

These are deliberately deferred with recorded reopen triggers, not oversights:

- **Hierarchical channels** — dotted names (`liveness.verify`) are accepted and uninterpreted today; subtree suppression waits on the FQCN arc's derived-channel design.
- **Sections / tiers** — grouping channels into ordered, independently-gated output sections (verbosity answers *how much*; tiers would answer *which sections*).
- **stdlib `logging` bridge** — for consumers needing handler interop.
- **Multi-manager isolation** — the module singleton is documented; per-app managers await a real embedded two-app consumer.
- **Richer per-message context** — the Deja Insight north star (object/thread/context correlation) arrives only as consumers demand it.

## Non-goals

- Color and rich formatting in the core (they belong in a renderer callable — the hook already exists).
- Replacing durable structured logs; this library is on-demand interactive detail.
