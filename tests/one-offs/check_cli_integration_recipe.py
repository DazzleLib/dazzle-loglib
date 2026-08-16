"""Run the docs/cli-integration.md recipe verbatim, to prove it actually works.

A documented recipe that nobody executes rots silently -- and this one is the
adoption path for every future consumer, so a typo in it costs more than a typo
in the library. Run from the repo root:

    python tests/one-offs/check_cli_integration_recipe.py

Checks: the wiring parses; gating behaves; stdout stays byte-identical across
every verbosity (the property machine-readable output depends on); and a
malformed --show spec produces a clean argparse error rather than a traceback.
"""
import argparse
import contextlib
import io
import json
import pathlib
import sys

# Run against the working tree regardless of cwd (this is a throwaway check
# script, not library code -- the stack's ban on sys.path fallbacks is about
# shipped packages silently finding bundled copies, which is not this).
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from dazzle_loglib import (  # noqa: E402
    ChannelDef, init_output, get_output, parse_channel_spec,
    resolve_verbosity, resolve_channel_specs, verbosity_rungs,
)

MYAPP_CHANNELS = [
    ChannelDef("scan", "Discovery and scanning"),
    ChannelDef("git", "Git operations"),
    ChannelDef("vals", "Value annotations on results", opt_in=True),
]


def add_verbosity_flags(parser):
    parser.add_argument("-v", "--verbose", action="count", default=0)
    parser.add_argument("-q", "--quiet", action="count", default=0)
    parser.add_argument("--show", action="append", metavar="CHANNEL[:LEVEL]",
                        type=parse_channel_spec, default=[])


def run(argv):
    parser = argparse.ArgumentParser(prog="myapp")
    add_verbosity_flags(parser)
    args = parser.parse_args(argv)

    init_output(
        verbosity=resolve_verbosity(args.verbose, args.quiet,
                                    env_var="MYAPP_VERBOSITY"),
        # The name:level serialization here MUST match docs/cli-integration.md
        # verbatim -- this one-off exists to exercise the documented recipe, and
        # a divergence between the two once masked a broken doc (str(s) was the
        # dataclass repr, which does not round-trip; found by the berth
        # consultation's Round 1, 2026-08-14).
        channels=resolve_channel_specs(
            [f"{s.name}:{s.level}" for s in args.show], env_var="MYAPP_SHOW"),
        channel_defs=MYAPP_CHANNELS,
        strict_channels=True,
    )

    out = get_output()
    err, sout = io.StringIO(), io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(sout):
        out.emit(1, "scanned {n} items", channel="scan", n=7)
        out.emit(2, "deep detail", channel="scan")
        print(json.dumps({"ok": True}))        # the machine-readable payload
    return sout.getvalue(), err.getvalue()


def main():
    failures = []

    print("stderr by verbosity:")
    for argv, label in (([], "default"), (["-v"], "-v"), (["-vv"], "-vv"),
                        (["--show", "scan:debug"], "--show scan:debug")):
        print(f"  {label:<20} {run(argv)[1]!r}")

    if run([])[1] != "":
        failures.append("default verbosity should emit nothing on the scan channel")
    if "scanned 7 items" not in run(["-v"])[1]:
        failures.append("-v should surface the level-1 scan message")
    if "deep detail" not in run(["--show", "scan:debug"])[1]:
        failures.append("--show scan:debug should raise that channel alone")

    outs = {v: run(list(v))[0] for v in ((), ("-q",), ("-v",), ("-vv",), ("-vvv",))}
    identical = len(set(outs.values())) == 1
    print(f"\nstdout byte-identical across verbosities: {identical} "
          f"({next(iter(outs.values()))!r})")
    if not identical:
        failures.append("stdout drifted with verbosity -- --json output would break")

    parser = argparse.ArgumentParser(prog="myapp")
    add_verbosity_flags(parser)
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            parser.parse_args(["--show", "scan:loudly"])
        failures.append("a malformed spec should have exited")
    except SystemExit as exc:
        print(f"malformed --show spec -> clean argparse exit {exc.code} (no traceback)")
        if exc.code != 2:
            failures.append(f"expected argparse exit code 2, got {exc.code}")

    print(f"\nverbosity_rungs(): {len(verbosity_rungs())} rungs, "
          f"{verbosity_rungs()[0][0]} .. {verbosity_rungs()[-1][0]}")

    print("\nRESULT:", "PASS" if not failures else "FAIL")
    for f in failures:
        print("  -", f)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
