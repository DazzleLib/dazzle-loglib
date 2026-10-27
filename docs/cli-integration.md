# CLI integration

dazzle-loglib deliberately contains no `argparse` code — parser construction belongs to your application (and eventually to a shared CLI library), not to the output layer. A test enforces that boundary: `tests/test_import_stability.py::TestCharterWalls` fails if the package ever imports `argparse`.

Because that code does not exist in the package, this page is the only place the wiring is specified — there is no module to read instead, so whatever an adopter copies from here becomes their convention permanently. When it was missing, each project invented its own: one declares the same three flags in *three* separate places, two chose incompatible spellings, and a fourth shipped no verbosity surface at all. Four adopters, four conventions, none shareable. Following this page means a future CLI library packages one convention rather than reconciling four.

## The canonical wiring

```python
import argparse
from dazzle_loglib import (
    ChannelDef, init_output, parse_channel_spec,
    resolve_verbosity, resolve_channel_specs, verbosity_rungs,
)

MYAPP_CHANNELS = [
    ChannelDef("scan",   "Discovery and scanning"),
    ChannelDef("git",    "Git operations"),
    ChannelDef("config", "Configuration resolution"),
    ChannelDef("vals",   "Value annotations on results", opt_in=True),
]


def add_verbosity_flags(parser: argparse.ArgumentParser) -> None:
    """The ONE place these flags are declared.

    Call it from every parser that needs them -- the main parser, and any
    pre-parse or sugar parser. Declaring them per-parser instead is how a
    project ends up with three copies that drift. (With sub-commands, the
    main parser's copies need their own dests: see "Sub-commands" below.)
    """
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="Increase detail (repeatable: -v .. -vvvvv)")
    parser.add_argument("-q", "--quiet", action="count", default=0,
                        help="Decrease detail (repeatable: -q .. -qqqq)")
    parser.add_argument("--show", action="append", metavar="CHANNEL[:LEVEL]",
                        type=parse_channel_spec, default=[],
                        help="Raise one channel independently, e.g. --show scan:debug")
```

Two details worth not skipping:

**`action="count"` on both**, not `store_true`. Verbosity is one signed axis, not two booleans — `-v` and `-q` are the warm and cold directions of the same continuum, and the counts subtract. Making `--quiet` a boolean is the mistake that later forces special-case code to reconcile "quiet AND verbose".

**`type=parse_channel_spec` on `--show`.** It returns a `ChannelSpec` and raises `ValueError` on a malformed spec, and argparse converts that automatically into a clean `usage:` error with exit code 2. Omit it and a typo surfaces as an uncaught traceback from deep inside `init_output()`.

## Resolving and initializing

```python
def main(argv=None):
    parser = argparse.ArgumentParser(prog="myapp")
    add_verbosity_flags(parser)
    args = parser.parse_args(argv)

    init_output(
        verbosity=resolve_verbosity(args.verbose, args.quiet,
                                    env_var="MYAPP_VERBOSITY"),
        channels=resolve_channel_specs(
            [f"{s.name}:{s.level}" for s in args.show],
            env_var="MYAPP_SHOW"),
        channel_defs=MYAPP_CHANNELS,
        strict_channels=True,
    )
```

**Serialize `--show` specs back to `name:level` exactly as written** — not `str(s)`, which is the dataclass repr and does not round-trip through `resolve_channel_specs`. A spec string's remaining slots (`CHANNEL:LEVEL:DEST:LOCATION:FORMAT`) are reserved: the parser accepts them, but nothing routes on them yet, so `name:level` is the complete round-trip today. When a future release wires the reserved slots, this recipe will change alongside a serializer that carries them.

`resolve_verbosity` encodes the precedence so you don't: **explicit > CLI counts > environment > default**, where the counts are "expressed" whenever either is nonzero — so `-v -q` nets to zero but still beats the environment. (A sibling project bolted env support on by reading the variable and then unconditionally overwriting it from the flags, silently discarding it whenever no flag was passed. That failure is a named regression test here.)

`strict_channels=True` is worth turning on: an unknown channel name then raises at *any* verbosity, rather than lying dormant until someone runs `-vvvvv`.

### Non-interactive contexts

Hooks, schedulers, and CI have no command line to add flags to. The environment variables above are the whole mechanism — `MYAPP_VERBOSITY=diagnostics` or `MYAPP_SHOW=scan:debug,git:2` turns detail up without editing a script. The library never reads the environment implicitly; you name the variables, so they can match your project's existing conventions.

## Sub-commands: one chain, on both sides of the command

In a CLI with sub-commands, users type the flags on either side of the command: `myapp -v run`, `myapp run -v`, and `myapp -v run -v` (meaning `-vv`). All three should work and feed the same verbosity, so the flags are declared on the main parser **and** on every sub-parser.

**The pitfall: the same `dest` on both parsers.** argparse applies a sub-parser's defaults after the main parser has stored its values, so the sub-parser's `verbose=0` silently overwrites the main parser's count. `myapp -v run` resolves to verbosity 0, with no error:

```python
parser = argparse.ArgumentParser(prog="myapp")
add_verbosity_flags(parser)                 # dest "verbose"
sub = parser.add_subparsers(dest="cmd", required=True)
add_verbosity_flags(sub.add_parser("run"))  # dest "verbose" again
parser.parse_args(["-v", "run"]).verbose    # 0, not 1: the -v is lost
```

**The recipe: give the main parser's copies their own dests, and add the counts.**

```python
def add_verbosity_flags(parser: argparse.ArgumentParser, top: bool = False) -> None:
    p = "top_" if top else ""
    parser.add_argument("-v", "--verbose", action="count", default=0, dest=p + "verbose",
                        help="Increase detail (repeatable: -v .. -vvvvv)")
    parser.add_argument("-q", "--quiet", action="count", default=0, dest=p + "quiet",
                        help="Decrease detail (repeatable: -q .. -qqqq)")
    parser.add_argument("--show", action="append", metavar="CHANNEL[:LEVEL]",
                        type=parse_channel_spec, default=[], dest=p + "show",
                        help="Raise one channel independently, e.g. --show scan:debug")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="myapp")
    add_verbosity_flags(parser, top=True)
    sub = parser.add_subparsers(dest="cmd", required=True)
    add_verbosity_flags(sub.add_parser("run"))
    args = parser.parse_args(argv)
    shows = args.top_show + args.show
    init_output(
        verbosity=resolve_verbosity(args.top_verbose + args.verbose,
                                    args.top_quiet + args.quiet,
                                    env_var="MYAPP_VERBOSITY"),
        channels=resolve_channel_specs([f"{s.name}:{s.level}" for s in shows],
                                       env_var="MYAPP_SHOW"),
        channel_defs=MYAPP_CHANNELS,
        strict_channels=True,
    )
```

It is still one function, so the flags are still declared in one place. `tests/test_cli_integration_doc.py` runs this recipe, taken from this page, on all the forms above.

**The other legitimate pattern: a sub-command with its own verbosity.** A sub-command that wants levels or channels separate from the main ones (a sub-tool with its own scale) keeps distinct dests and simply does not add them. Nothing in the library changes for this: `resolve_verbosity` takes counts and does not care where they came from.

## Explaining the scale to users

`verbosity_rungs()` returns `(name, rank, gloss)` cold-to-warm, so a help surface is a loop rather than ten hand-copied strings:

```python
def print_verbosity_help(prog="myapp"):
    print("Verbosity levels (-q lowers, -v raises):\n")
    for name, rank, gloss in verbosity_rungs():
        flag = "-" + "v" * rank if rank > 0 else ("-" + "q" * -rank if rank else "")
        print(f"  {rank:+d}  {flag:<6} {name:<12} {gloss}")
    print(f"\nRaise one channel independently:  {prog} --show scan:debug")
```

which renders:

```
Verbosity levels (-q lowers, -v raises):

  -4  -qqqq  nothing      Nothing at all -- exit code only (CI/headless)
  -3  -qqq   error        Errors only
  -2  -qq    warning      Errors and warnings
  -1  -q     minimal      Results only -- no hints
  +0         default      Default output, result-context hints
  +1  -v     extra        Progress, timing, summary info
  +2  -vv    diagnostics  Diagnostic detail (decision inputs, guard math)
  +3  -vvv   config       Configuration, algorithm selection
  +4  -vvvv  lite-debug   Light debug detail
  +5  -vvvvv debug        Full debug -- internal state, evaluation/call tracing
```

Glosses are ASCII by contract, so this renders correctly on Windows codepage 437/1252 consoles. Where you put it — an epilog, a `--help-verbosity` action, a `verbosity` sub-command — is your call; the library supplies the truth, not the layout.

For the channel half, `get_output().format_channel_list()` renders the running registry (your declared channels plus the built-ins) the same way.

## Keeping stdout pure

Diagnostics default to stderr, which matters most for machine-readable output: a `--json` mode must be byte-identical at every verbosity. That is worth an actual test rather than a convention — run your JSON command at `-q`, default, `-v`, `-vv`, `-vvv` and assert stdout does not change.

If a channel should annotate *content* on stdout rather than emit diagnostics to stderr, declare it that way — `ChannelDef("vals", "...", fd="stdout")`.

Destinations resolve at emit time, not at construction — including the default. That matters in two places: hosts that rebind the streams after import (notably `pythonw.exe`, where `sys.stdout`/`sys.stderr` start as `None`) get the streams that exist when the message is written, so initialization order is not a trap; and a test harness can wrap output with `contextlib.redirect_stderr` or pytest's `capsys` even though the manager was built earlier.

## Cheap when off

`emit()` never formats a message that will not show, so a gated call costs one integer comparison. But the *arguments* are still evaluated at the call site, so guard anything expensive:

```python
if out.is_level_active(2, "scan"):
    rows = enumerate_everything()          # skipped entirely at default verbosity
    out.emit(2, "rows={n}", channel="scan", n=len(rows))
```

That guard is why `EmitterProtocol` carries `is_level_active` alongside `emit` — a library accepting an injected emitter needs the same escape hatch.

## Where this is going

This recipe is what a future `dazzle-clilib` is expected to package: the flag declarations, the help rendering, and the section/topic structure, composed over this library and its sibling `dazzle-helplib`. Until that library exists, copy the recipe — and keep `add_verbosity_flags` as a single function in your project so the eventual migration is one call site, not three.

The boundary is deliberate and recorded: CLI *structure* (parsers, flags, help layout) belongs to the CLI layer; diagnostic *output* (gating, channels, destinations) belongs here; dispatch, registries, and configuration belong to whatever aggregator framework you use. See the [stack architecture contract](https://github.com/DazzleLib/.github/blob/main/docs/STACK-MAP.md), ADDENDUM D12.
