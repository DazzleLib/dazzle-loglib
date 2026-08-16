# dazzle-loglib API stability

This document separates the **tracked** surface — what this library considers its real public API, pinned by the canary suite `tests/test_import_stability.py` — from the surfaces explicitly **excluded** from any promise, and from the design space still **open**.

## What "tracked" does and does not mean

**Status: 0.3.x, alpha.** Tracked is a claim about *process*, not permanence:

- **It does mean** no silent drift. Every symbol and behavior listed below is asserted by a test, so a change is loud, deliberate, versioned in `CHANGELOG.md`, and — where a consumer is known — raised on that consumer's tracker.
- **It does not mean** frozen. This library has not yet been adopted by a real consumer, and adoption is exactly what tends to reshape an API. Saying otherwise would be a promise the project cannot currently keep.

An honest example, from this library's own history: 0.3.2 listed "FD sentinels resolve at emit time in all three positions" among its behavioral contracts. Building the CLI recipe in 0.3.3 revealed the *default* destination did not honor that, and the behavior changed one release later. That was the right call — nobody depended on it yet — and it is the reason this page describes a tracked surface rather than a locked one.

### Where movement is expected

These are known, named, and not hypothetical. If you build on this library today, these are the areas to hold loosely:

| Area | Why it may move |
|---|---|
| Anything adoption stresses | The first real consumer ([csb#87](https://github.com/DazzleML/Claude-Session-Backup/issues/87)) has not landed; the roadmap explicitly plans to fold friction it surfaces back in |
| Channel identity | The FQCN arc may make channels derived tree nodes rather than declared strings; `ChannelDef` is the intended stable façade, but the surface behind it will change |
| Anything a CLI library wants | `dazzle-clilib` does not exist yet; when it does, it may want additions here (additions are non-breaking, but the shape of the seam could shift) |
| The legacy donor surface | Slated for removal in 0.4.0 — see Excluded, below |

Stability firms up as consumers land, not as time passes. When it does, this page will say so and the version will reflect it.

## Tracked (pinned by the canary)

**Package-root imports** (`from dazzle_loglib import ...`): `OutputManager`, `init_output`, `get_output`, `BUILTIN_CHANNELS`, `ChannelDef`, `ChannelSpec`, `parse_channel_spec`, `OPT_IN_START_RANK`, `resolve_verbosity`, `resolve_channel_specs`, `EmitterProtocol`, `NullEmitter`, `CallableEmitter`, `Hint`, `register_hint`, `register_hints`, `get_hint`, `get_hints_by_category`, `trace`, `__version__` — plus the scale symbols below.

**The 10-rung verbosity scale** (rung names AND ranks — the scale is API):
`nothing:-4, error:-3, warning:-2, minimal:-1, default:0, extra:1, diagnostics:2, config:3, lite-debug:4, debug:5` — plus the THAC0 gate rule `shows(level, threshold) == (threshold > -4 and level <= threshold)`.

The scale is reachable from the package root, not only from submodules: `VERBOSITY_CONTINUUM`, `SILENCE_FLOOR`, `shows`, `rank_of`, `verbosity_rungs`, and the ten level constants (`NOTHING`, `ERROR`, `WARNING`, `MINIMAL`, `DEFAULT`, `EXTRA`, `DIAGNOSTICS`, `CONFIG`, `LITE_DEBUG`, `DEBUG`).

**`verbosity_rungs()`** returns the scale as data — `(name, rank, gloss)` per rung, ordered cold to warm — for any surface that explains the verbosity model to a user. The rung names and ranks are tracked above; the one-line glosses are library-owned and tracked with them, so consumers render them rather than re-authoring ten strings each. Glosses are guaranteed ASCII (they are printed to terminals, including Windows codepage 437/1252). Presentation — banding, width, color, whether the flag reads `-vv` or `--verbosity 2` — is explicitly *not* decided here.

**Dataclass field sets** of `ChannelDef`, `ChannelSpec`, and `Hint` (fields may be APPENDED with defaults; existing fields don't move or rename).

**Call shapes**: `emit(level, message=None, *, channel=, file=, render=, **kwargs) -> bool`; `is_level_active(level, channel=) -> bool`; `init_output(verbosity=, quiet=, channels=, channel_fds=, renderer=, known_channels=, strict_channels=, channel_defs=)`; the `resolve_*` signatures and their precedence rules (explicit > CLI counts > env > default; nonzero counts beat env even at net zero; CLI channel specs override env specs per-channel).

**Charter**: this library imports no `argparse` and constructs no parsers — CLI structure belongs to the consuming application or a CLI library. Enforced by `tests/test_import_stability.py::TestCharterWalls`.

**Behavioral contracts**: strict channel validation raises BEFORE the gate; gated-off emits perform no string formatting on kwargs; FD sentinels `'stdout'`/`'stderr'` resolve at emit time in all three FD positions, and the manager's DEFAULT destination is the `'stderr'` sentinel rather than a stream captured at construction (so rebinding hosts and output-capturing test harnesses both work regardless of initialization order); `init_output` REPLACES the singleton on reinit; when `channel_defs=` is passed, the legacy module sets and donor opt-in defaults contribute nothing.

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
