# Changelog

All notable changes to dazzle-loglib are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/), and the project adheres to [PEP 440](https://peps.python.org/pep-0440/) versioning.

## [0.2.0] - 2026-08-08

First published release (PyPI). Generalizes the extracted library from its donor-project shape into a consumer-defined system.

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
