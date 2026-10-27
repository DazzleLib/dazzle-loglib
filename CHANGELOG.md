# Changelog

All notable changes to dazzle-loglib are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/), and the project adheres to [PEP 440](https://peps.python.org/pep-0440/) versioning.

## [0.3.4] - 2026-10-26

Documentation only; no change to the package.

### Added
- `docs/cli-integration.md` gains a "Sub-commands" section: the flags are declared on the main parser and on every sub-parser, so `myapp -v run`, `myapp run -v` and `myapp -v run -v` (meaning `-vv`) all feed one verbosity. It names the pitfall that recipe avoids: with the same `dest` on both parsers, argparse lets the sub-parser's default (0) overwrite the main parser's count, so a `-v` typed before the sub-command is silently lost. The fix is to give the main parser's copies their own dests and add the counts. The section also notes the other legitimate pattern, a sub-command with its own separate verbosity. Found while adopting the library in ck3-save-migrator, which uses this recipe.
- `tests/test_cli_integration_doc.py` runs that section's code blocks straight from the page: the pitfall block must lose the flag as the page says, and the recipe must give one verbosity, and join `--show` specs, on both sides of the sub-command.

## [0.3.3] - 2026-08-08

Closes the gap between what `docs/api-stability.md` promises and what the package root actually exposes, before the first PyPI publication makes the surface permanent.

### Added
- The verbosity scale is now importable from the package root, not only from submodules: `VERBOSITY_CONTINUUM`, `SILENCE_FLOOR`, `shows`, `rank_of`, and the ten level constants. The stability document already described the scale as part of the tracked surface; the root did not export it, so the document pointed at symbols the documented surface did not provide.
- `verbosity_rungs()` — the scale as data: `(name, rank, gloss)` per rung, cold to warm. The rung names and ranks are library-owned, so the one-line glosses are too; any surface that explains the verbosity model to a user (a `--help` table, a `verbosity` sub-command) renders these instead of re-authoring ten strings. Glosses are ASCII, since they are printed to terminals including Windows codepage 437/1252.
- `tests/test_import_stability.py::TestCharterWalls` asserts the package never *imports* `argparse` (checked via the AST, so prose about argparse remains fine). Parser construction belongs to the consuming application or a CLI library; this makes that boundary executable rather than merely documented.
- `docs/cli-integration.md` — the canonical CLI wiring recipe: flag declarations (counts for `-v`/`-q`, `type=parse_channel_spec` on `--show` so argparse renders a clean error), resolution with the env-var path for hook and scheduler contexts, a `--help` rung table built from `verbosity_rungs()`, keeping `--json` stdout pure, and the single `add_verbosity_flags()` helper each consumer should own so the flags are declared once rather than per-parser. Exercised end-to-end by `tests/one-offs/check_cli_integration_recipe.py`.

### Changed
- `docs/api-stability.md` reframed from "locked" to **tracked**: the honest claim for a 0.3.x library shipping mid-development of its stack is *no silent drift*, not *no change*. The page now names where movement is still expected (first-consumer adoption, the FQCN channel arc, a future CLI library) instead of implying a stability the project cannot yet promise. This release's own behavior fix — below — is the worked example.

### Fixed
- The manager's default output destination is now the `'stderr'` sentinel rather than `sys.stderr` captured during `__init__`. Binding the stream at construction defeated the emit-time resolution guarantee in the most common case: a `pythonw` host that rebound its streams after import, or a test harness wrapping output with `contextlib.redirect_stderr`/`capsys`, would silently keep writing to the original stream. Found by executing the documented CLI recipe, which captured nothing; pinned by a regression test.
- The CLI recipe's `--show` serialization: the doc used `str(s)`, which is the dataclass repr and does not round-trip — the override landed under a garbage channel name that nothing ever emits on, so every `--show` flag was silently inert (spec names are not validated at init, even under `strict_channels=True`, whose check runs at emit time against the emitted name). The recipe now serializes as `name:level` (matching what the one-off verifier had always exercised — that divergence is what masked the bug), the reserved spec slots (`DEST:LOCATION:FORMAT`) are documented as inert until routing lands, and two regression tests pin the round-trip and doc/verifier agreement.

## [0.3.2] - 2026-08-08

### Changed
- README rewritten on the house library pattern (badge row, tagline placing the library in the stack, "what this owns and what it doesn't", model, status, usage, installation, documentation, contributing, license, related projects) so it presents like its `dazzle-linklib` / `dazzle-filekit` siblings.
- README license section carries the copyright attribution in the house form (`dazzle-loglib, Copyright (C) 2026 Dustin Darcy`).
- Contributing section brought to the house shape: dev-environment setup, the two standing rules this library lives by (dependencies point down only; the public surface is locked by the canary), and the project support link.
- `ROADMAP.md` records phase 1c: the remaining structural gap to `dazzle-filekit` (Read the Docs, `BREAKING_CHANGES.md`, ghtraf traffic tracking).

## [0.3.1] - 2026-08-08

### Added
- repokit-common tooling as a subtree at **`scripts/repokit-common/`**, with the standard git hooks installed. The nested path keeps `scripts/` free for project-specific scripts instead of interleaving them with vendored tooling; repokit's own hooks already prefer this layout and fall back to a flat `scripts/` only for legacy repos.
- `[tool.repokit-common]` configuration so the shared version tooling resolves this project's version source.

### Changed
- `_version.py` adopts the full repokit shape (`MAJOR`/`MINOR`/`PATCH`/`PHASE`/`PROJECT_PHASE` plus derived constants). The git hooks stamp build metadata into `__version__`, which is deliberately **not** PEP 440 valid — packaging now reads `PIP_VERSION` instead, so a stamped working copy still builds a valid wheel.

## [0.3.0] - 2026-08-08

First published release (PyPI). Repository infrastructure — the library API is unchanged from 0.2.0.

### Added
- GitHub project setup: CI workflow (Python 3.10–3.13), PyPI release workflow keyed off the *release published* event (never tag push, so publishing follows the release notes and a re-pushed tag cannot double-fire), issue/PR templates, CODEOWNERS, dependabot, stale-bot, and funding metadata.
- `ROADMAP.md` and `docs/platform-support.md`.
- `[dev]` optional-dependency extra (pytest) so CI's editable install resolves.

## [0.2.0] - 2026-08-08

The API generalization: turns the extracted library from its donor-project shape into a consumer-defined system. Committed but never published to PyPI — 0.3.0 is the first release on the index.

### Added
- `ChannelDef` and the consumer-declared channel registry: `init_output(channel_defs=[...])` gives each application its own channel set (names, descriptions, opt-in cold start, per-channel FD defaults) without touching module state. When `channel_defs` is passed, the legacy module-level sets contribute nothing.
- `resolve` module: `resolve_verbosity()` (explicit > CLI counts > environment > default precedence; nonzero counts always beat the environment, even when `-v -q` nets to zero) and `resolve_channel_specs()` (CLI specs override environment specs per-channel).
- `protocols` module: `EmitterProtocol` (structural: `emit()` + `is_level_active()`), `NullEmitter`, and `CallableEmitter` — the injection contract that lets lower-level libraries accept an optional emitter without depending on this package.
- `OutputManager.verbosity_space()`: the channels x verbosity `ContinuumSpace` built from the manager's own registry (the module-level `VERBOSITY_SPACE` constant reflected only the donor channel set).
- Output FD sentinels (`'stdout'`/`'stderr'`) accepted in all three FD positions (manager default, per-channel, per-message) and resolved at emit time — required for hosts that rebind streams after import (e.g. pythonw).
- `docs/api-stability.md` and the import-stability canary test suite.

### Changed
- `ChannelConfig` renamed to `ChannelSpec` (it is the parse product of a CLI channel spec string). `ChannelSpec.fd` now actually participates in FD resolution.
- Strict channel validation runs before the verbosity gate: an unknown channel name raises at any verbosity, not only when the message would emit.
- `parse_channel_spec` raises `ValueError` (argparse-friendly) instead of leaking `dazzle_lib.continuum.ContinuumError` for unknown named rungs.
- `init_output` reinitialization contract documented: a second call replaces the singleton; call sites obtain the manager via `get_output()` per use.

### Deprecated
- The module-level `KNOWN_CHANNELS` / `CHANNEL_DESCRIPTIONS` / `OPT_IN_CHANNELS` donor sets and the module-level `VERBOSITY_SPACE` constant. Contents are frozen (they carry the donor project's channel names), excluded from the API-stability guarantee, and mutation warns via `DeprecationWarning` naming `channel_defs=` as the replacement. Slated for removal in a future release per the DazzleLib shim policy.

## [0.1.0-alpha] - 2026-07-04

- Extracted standalone from dazzlecmd `_vendor/log_lib` (commit `4e8487d`; lineage: Prime-Square-Sum -> github-traffic-tracker -> wtf-restarted -> wtf-windows -> dazzlecmd, plus the continuum redesign: `VERBOSITY_CONTINUUM` on `dazzle_lib.Continuum`, the `shows()` gate, named-rank channel specs, the channels x verbosity space, opt-in cold start declared via the Continuum). Not published to PyPI.
