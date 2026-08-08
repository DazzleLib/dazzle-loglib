# dazzle-loglib

Channel/verbosity-aware CLI output management, built on [`dazzle-lib`](https://pypi.org/project/dazzle-lib/) continua.

`dazzle-loglib` is the diagnostic-output member of the [DazzleLib](https://github.com/DazzleLib) perpendicular tier: a THAC0-style signed verbosity axis crossed with **consumer-defined named channels**, so every program can answer *"how loud is each channel of my self-narration, and where does each message go?"* — independently per subsystem, from one `-v`-stacking CLI surface.

```bash
pip install dazzle-loglib
```

## The model: verbosity × channel

One signed verbosity axis (a `dazzle_lib.Continuum` with an invariant zero):

```
←── quieter ─────────────── default ─────────────────────── louder ──→
-4    -3     -2       -1      0       1     2           3      4          5
wall  errors warnings minimal default extra diagnostics config lite-debug debug
```

The emit gate is one comparison: a message at `level` shows when `level <= threshold`, and at `-4` (the hard wall) nothing shows at all. `-v` steps warmer, `-q` steps colder, and they compose (`-vv -q` = 1).

Channels are the orthogonal dimension — **each program declares its own**:

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
    channels=args.show,   # e.g. ["liveness:diagnostics", "scan:2"]
)

out = get_output()
out.emit(1, "scanned {n} sessions", channel="scan", n=count)
out.emit(2, "entry={id} pid={pid} in_by_pid={hit} -> reject({rung})",
         channel="liveness", id=entry_id, pid=pid, hit=hit, rung=rung)
```

Each channel can be pinned independently of the global level (`--show liveness:debug` floods one subsystem without drowning the rest), named rungs work anywhere ints do, and opt-in channels start cold until explicitly raised. The channels × verbosity crossing is a real `ContinuumSpace` (`out.verbosity_space()`), so future axes compose rather than bolt on.

## Zero cost when gated

`emit()` never formats a message that doesn't show — kwargs are only interpolated after the gate passes. For expensive *collection* (not just formatting), ask first:

```python
if out.is_level_active(2, "liveness"):
    rows = expensive_enumeration()          # skipped entirely at default verbosity
    out.emit(2, "rows={n}", channel="liveness", n=len(rows))
```

## Resolution with defined precedence

```python
from dazzle_loglib import resolve_verbosity, resolve_channel_specs

verbosity = resolve_verbosity(args.verbose, args.quiet,
                              explicit=args.verbosity,      # --verbosity N wins outright
                              env_var="MYAPP_VERBOSITY")    # consulted only when CLI is silent
specs = resolve_channel_specs(args.show, env_var="MYAPP_SHOW")
```

Precedence is `explicit > CLI counts > environment > default`, and CLI counts are "expressed" whenever either count is nonzero — `-v -q` nets to zero but still beats the environment. Hooks, schedulers, and other non-interactive contexts turn detail up by setting the env vars; nothing edits scripts.

## The injection contract (std-swappable, stack-safe)

Libraries that should never *depend* on a logging package can still speak — accept an optional emitter:

```python
from dazzle_loglib.protocols import EmitterProtocol, NullEmitter

def verify_tree(root, emitter: EmitterProtocol = None):
    emitter = emitter or NullEmitter()      # silent by default
    if emitter.is_level_active(2, "verify"):
        emitter.emit(2, "checking {p}", channel="verify", p=root)
```

`EmitterProtocol` is structural: a real `OutputManager` satisfies it, and so does a four-line shim over `print` (or `CallableEmitter(logging.getLogger(...).info)`). The contract travels down; the implementation stays out of your dependency tree.

## Renderers (color lives here, not in the core)

`emit()` resolves a renderer in layers — per-call `render=`, per-channel renderer, global `default_renderer`, then plain `print()` to the resolved destination (stderr by default; `'stdout'`/`'stderr'` sentinels resolve at emit time, so rebound streams are honored). Color and rich formatting belong in a renderer callable (`init_output(renderer=console.print)`), never in the library core.

Also included: a `Hint` registry (context-filtered, session-deduplicated contextual tips routed through the same gate) and a `@trace` decorator (function entry/exit at full debug on the `trace` channel).

## North star

The design leans toward Deja Insight-style instrumented narration: per-message channels, hierarchical suppression (dotted channel names are reserved for this), zero-cost gating, and eventually richer per-message context. Today's library is the disciplined core of that idea; the rest arrives only as real consumers demand it.

## Migration note (pre-0.2.0 vendored copies)

Projects carrying the ancestral `log_lib` (wtf-windows, dazzlecmd `_vendor`, ghtraf, Prime-Square-Sum lineage): 0.2.0 re-runged the scale (`config` 2→3, `debug` 3→5, `timing` renamed `extra`) and replaced module-set channel registration with `channel_defs=`. The legacy module sets still import but warn on mutation and are excluded from the [API-stability guarantee](docs/api-stability.md). See DazzleTools/dazzlecmd#118 for the cutover playbook.

## Part of DazzleLib

`dazzle-loglib` sits in the DazzleLib stack's perpendicular tier — usable from any layer, depending only on the [`dazzle-lib`](https://pypi.org/project/dazzle-lib/) bedrock. Sibling: `dazzle-helplib` (help content + detail continuum + TIPs). See the [stack architecture](https://github.com/DazzleLib/.github/blob/main/docs/STACK-MAP.md).

## License

MIT — see [LICENSE](LICENSE).
