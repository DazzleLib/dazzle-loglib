# dazzle-loglib API stability

This document states which surfaces are LOCKED (breaking them requires a deliberate, versioned, consumer-notified decision) and which are explicitly EXCLUDED from any stability promise. The canary suite `tests/test_import_stability.py` pins the locked surface — if it fails, a locked symbol moved.

Status: alpha. Locked here means "we will not break it casually and never silently" — not "frozen forever." Every intentional break lands in CHANGELOG.md with a version bump and, where a consumer is known, a heads-up on the consumer's tracker.

## Locked (the guarantee)

**Package-root imports** (`from dazzle_loglib import ...`): `OutputManager`, `init_output`, `get_output`, `BUILTIN_CHANNELS`, `ChannelDef`, `ChannelSpec`, `parse_channel_spec`, `OPT_IN_START_RANK`, `resolve_verbosity`, `resolve_channel_specs`, `EmitterProtocol`, `NullEmitter`, `CallableEmitter`, `Hint`, `register_hint`, `register_hints`, `get_hint`, `get_hints_by_category`, `trace`, `__version__`.

**The 10-rung verbosity scale** (rung names AND ranks — the scale is API):
`nothing:-4, error:-3, warning:-2, minimal:-1, default:0, extra:1, diagnostics:2, config:3, lite-debug:4, debug:5` — plus the THAC0 gate rule `shows(level, threshold) == (threshold > -4 and level <= threshold)`.

**Dataclass field sets** of `ChannelDef`, `ChannelSpec`, and `Hint` (fields may be APPENDED with defaults; existing fields don't move or rename).

**Call shapes**: `emit(level, message=None, *, channel=, file=, render=, **kwargs) -> bool`; `is_level_active(level, channel=) -> bool`; `init_output(verbosity=, quiet=, channels=, channel_fds=, renderer=, known_channels=, strict_channels=, channel_defs=)`; the `resolve_*` signatures and their precedence rules (explicit > CLI counts > env > default; nonzero counts beat env even at net zero; CLI channel specs override env specs per-channel).

**Behavioral contracts**: strict channel validation raises BEFORE the gate; gated-off emits perform no string formatting on kwargs; FD sentinels `'stdout'`/`'stderr'` resolve at emit time in all three FD positions; `init_output` REPLACES the singleton on reinit; when `channel_defs=` is passed, the legacy module sets and donor opt-in defaults contribute nothing.

**Homing promise (EmitterProtocol)**: the canonical home of `EmitterProtocol` may migrate to `dazzle_lib.protocols` in the release where a stack library first accepts an `emitter=` parameter. When that happens, `dazzle_loglib.protocols` re-exports it **permanently** — `from dazzle_loglib.protocols import EmitterProtocol` keeps working forever.

## Excluded (no promise — the cutover-window legacy surface)

These exist solely so the pre-extraction vendored copies' consumers keep working during the scheduled cutover (DazzleTools/dazzlecmd#118). They carry the DONOR project's channel vocabulary, warn on mutation, and are slated for removal in 0.4.0 (registered in the DazzleLib alias register):

- `KNOWN_CHANNELS`, `CHANNEL_DESCRIPTIONS`, `OPT_IN_CHANNELS` (module-level donor sets)
- `format_channel_list` (module-level form; use `OutputManager.format_channel_list()`)
- `channels.VERBOSITY_SPACE` (deprecated module attribute; use `OutputManager.verbosity_space()`)
- `channels.ChannelConfig` (renamed `ChannelSpec` in 0.2.0; deprecated alias)
- `init_output(known_channels=)` / `init_output(channel_fds=)` without `channel_defs=` (legacy path)
- `default_channel_overrides()` (donor-path helper)

## Not yet API (design space still open)

- Hierarchy semantics for dotted channel names (reserved; reference design: dazzlecmd SD-FQCN-2)
- Section/tier grouping of channels (deferred; reference: wtf-restarted sections-in-log_lib issue)
- `ChannelSpec.destination`/`format` routing (stored, not yet routed)
