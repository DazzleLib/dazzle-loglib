# dazzle-loglib

[![PyPI](https://img.shields.io/pypi/v/dazzle-loglib?color=green)](https://pypi.org/project/dazzle-loglib/)
[![Release Date](https://img.shields.io/github/release-date/DazzleLib/dazzle-loglib?color=green)](https://github.com/DazzleLib/dazzle-loglib/releases)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/dazzle-loglib?period=total&units=international_system&left_color=black&right_color=green&left_text=downloads)](https://pypistats.org/packages/dazzle-loglib)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub Discussions](https://img.shields.io/github/discussions/DazzleLib/dazzle-loglib)](https://github.com/DazzleLib/dazzle-loglib/discussions)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](docs/platform-support.md)

**Channel/verbosity-aware CLI output management** -- the **diagnostic-output** member of the perpendicular tier of the [DazzleLib stack](https://github.com/DazzleLib/.github/blob/main/docs/STACK-MAP.md).

One signed verbosity axis crossed with **consumer-defined named channels**, so a program can answer *how loud is each channel of my self-narration, and where does each message go?* — per subsystem, independently, from one `-v`-stacking CLI surface.

```bash
pip install dazzle-loglib
```

## What this owns (and what it doesn't)

| Owns | Does not own |
|---|---|
| The verbosity **gate** — one integer comparison, and no message is formatted unless it passes | Color and rich formatting (supply a renderer callable; the hook is built in) |
| The **channel registry** each program declares for itself | Your channel vocabulary — there is no built-in "correct" channel set |
| **Where** a message goes (per-manager, per-channel, or per-message destinations) | Durable structured logs; this is on-demand interactive detail, not the audit record |
| Env/CLI **resolution** with defined precedence | Reading the environment implicitly — you name your own variables |
| A **hint** registry (runtime, context-filtered, session-deduplicated) | Help-surface content — that's [dazzle-helplib](https://github.com/DazzleLib/dazzle-helplib)'s TIPs, a deliberately separate mechanism |

## The model: verbosity x channel

One signed verbosity axis (a `dazzle_lib.Continuum` with an invariant zero):

```
<-- quieter --------------- default ------------------------- louder -->
-4    -3     -2       -1      0       1     2           3      4          5
wall  errors warnings minimal default extra diagnostics config lite-debug debug
```

A message at `level` shows when `level <= threshold`; at `-4` (the hard wall) nothing shows at all. `-v` steps warmer, `-q` steps colder, and they compose (`-vv -q` = 1).

Channels are the orthogonal dimension, and **each program declares its own**:

```python
from dazzle_loglib import init_output, get_output, ChannelDef

init_output(
    verbosity=args.verbose - args.quiet,
    strict_channels=True,
    channel_defs=[
        ChannelDef("liveness", "Session liveness verification"),
        ChannelDef("git",      "Git operations"),
        ChannelDef("scan",     "Discovery and scanning"),
        ChannelDef("vals",     "Value annotations on results", opt_in=True),
    ],
    channels=args.show,          # e.g. ["liveness:diagnostics", "scan:2"]
)

out = get_output()
out.emit(1, "scanned {n} sessions", channel="scan", n=count)
out.emit(2, "entry={id} pid={pid} in_by_pid={hit} -> reject({rung})",
         channel="liveness", id=entry_id, pid=pid, hit=hit, rung=rung)
```

Each channel can be pinned independently of the global level, so `--show liveness:debug` floods one subsystem without drowning the rest. Named rungs work anywhere integers do, opt-in channels stay cold until raised, and the channels x verbosity crossing is a real `ContinuumSpace` (`out.verbosity_space()`) — so further axes compose rather than bolt on.

## Status

**0.3.x, alpha.** The API is settling alongside its first consumers; the surfaces that are locked (and the ones deliberately excluded) are enumerated in [docs/api-stability.md](docs/api-stability.md) and pinned by an import-stability canary. Breaking changes land in [CHANGELOG.md](CHANGELOG.md) with a version bump, never silently.

## Usage

### Zero cost when gated

`emit()` never formats a message that will not show — keyword arguments are interpolated only after the gate passes. For expensive *collection*, ask first:

```python
if out.is_level_active(2, "liveness"):
    rows = expensive_enumeration()        # skipped entirely at default verbosity
    out.emit(2, "rows={n}", channel="liveness", n=len(rows))
```

### Resolution with defined precedence

```python
from dazzle_loglib import resolve_verbosity, resolve_channel_specs

verbosity = resolve_verbosity(args.verbose, args.quiet,
                              explicit=args.verbosity,     # --verbosity N wins outright
                              env_var="MYAPP_VERBOSITY")   # consulted only when the CLI is silent
specs = resolve_channel_specs(args.show, env_var="MYAPP_SHOW")
```

Precedence is `explicit > CLI counts > environment > default`, and CLI counts count as *expressed* whenever either is nonzero — `-v -q` nets to zero but still beats the environment. Hooks, schedulers, and other non-interactive contexts turn detail up by setting the variables; nothing edits scripts.

### Injecting an emitter (the std-swappable seam)

Libraries that should never *depend* on a logging package can still speak:

```python
from dazzle_loglib.protocols import EmitterProtocol, NullEmitter

def verify_tree(root, emitter: EmitterProtocol = None):
    emitter = emitter or NullEmitter()     # silent by default
    if emitter.is_level_active(2, "verify"):
        emitter.emit(2, "checking {p}", channel="verify", p=root)
```

`EmitterProtocol` is structural: a real `OutputManager` satisfies it, and so does a four-line shim over `print` (or `CallableEmitter(logging.getLogger(__name__).info)`). The contract travels down the stack; the implementation stays out of your dependency tree.

### Renderers, hints, and tracing

`emit()` resolves a renderer in layers — per-call `render=`, per-channel renderer, global `default_renderer`, then plain `print()` to the resolved destination (stderr by default; `'stdout'`/`'stderr'` sentinels resolve at emit time, so rebound streams are honored). Color belongs in a renderer callable (`init_output(renderer=console.print)`), never in the core. Also included: a `Hint` registry (context-filtered, session-deduplicated, routed through the same gate) and a `@trace` decorator (function entry/exit at full debug on the `trace` channel).

## Installation

```bash
pip install dazzle-loglib
```

### From source

```bash
git clone https://github.com/DazzleLib/dazzle-loglib.git
cd dazzle-loglib
pip install -e ".[dev]"
```

## Documentation

- [docs/api-stability.md](docs/api-stability.md) — what is locked, what is excluded, and the protocol homing promise
- [CHANGELOG.md](CHANGELOG.md) — release history
- [ROADMAP.md](ROADMAP.md) — where this is going (tracked live in [#1](https://github.com/DazzleLib/dazzle-loglib/issues/1))
- [docs/platform-support.md](docs/platform-support.md) — platform and Python support

### Migrating from a vendored `log_lib`

Projects carrying the ancestral copy: 0.2.0 re-runged the verbosity scale (`config` 2→3, `debug` 3→5, `timing` renamed `extra`) and replaced module-set channel registration with `channel_defs=`. The legacy module sets still import but warn on mutation and are excluded from the API-stability guarantee. See [DazzleTools/dazzlecmd#118](https://github.com/DazzleTools/dazzlecmd/issues/118) for the cutover playbook.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# Install git hooks
bash scripts/repokit-common/install-hooks.sh
```

Two house rules this library lives by:

- **Dependencies point down only.** The perpendicular tier consumes the bedrock and nothing else — never a consumer, never a sibling. `dazzle-loglib` and `dazzle-helplib` do not import each other.
- **The public surface is locked.** The symbols and behaviors listed in [docs/api-stability.md](docs/api-stability.md) are pinned by `tests/test_import_stability.py`; changes follow the documented version discipline rather than landing silently.

Like the project?

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/djdarcy)

## Part of DazzleLib

`dazzle-loglib` sits in the perpendicular tier: usable from any layer, depending only on the [`dazzle-lib`](https://github.com/DazzleLib/dazzle-lib) bedrock.

### Related Projects

- [dazzle-lib](https://github.com/DazzleLib/dazzle-lib) — the bedrock: protocols, payload schemas, and the `Continuum` primitive this builds on
- [dazzle-helplib](https://github.com/DazzleLib/dazzle-helplib) — the sibling: help content, detail continuum, and TIPs
- [dazzle-filekit](https://github.com/DazzleLib/dazzle-filekit) — cross-platform file operations
- [dazzle-linklib](https://github.com/DazzleLib/dazzle-linklib) — content-addressable link records
- [The stack map](https://github.com/DazzleLib/.github/blob/main/docs/STACK-MAP.md) — how the pieces fit

## License

dazzle-loglib, Copyright (C) 2026 Dustin Darcy

Licensed under the MIT License -- see [LICENSE](LICENSE). The whole DazzleLib stack is MIT-licensed.
