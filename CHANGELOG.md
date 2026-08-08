# Changelog

All notable changes to dazzle-loglib are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/), and the project adheres to [PEP 440](https://peps.python.org/pep-0440/) versioning.

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
