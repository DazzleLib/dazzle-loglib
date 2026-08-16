"""API canary (STACK-MAP review F9: every new lib ships this at first release).

These pin the TRACKED surface described in docs/api-stability.md. A failure
here does not mean "you did something forbidden" — the library is 0.3.x alpha
and shipped mid-development of the wider stack, so the surface is still
expected to move. It means the change must be DELIBERATE: update this file,
say so in CHANGELOG.md with a version bump, and tell any known consumer.
The point is that drift fails a test instead of reaching someone quietly.

("Locked" in the class names below is the older word for the same idea; see
docs/api-stability.md for what is tracked, what is excluded, and where
movement is still expected.)
"""
import dataclasses

import pytest


class TestLockedImports:
    def test_package_root_locked_symbols(self):
        from dazzle_loglib import (                              # noqa: F401
            __version__, OutputManager, init_output, get_output,
            BUILTIN_CHANNELS,
            ChannelDef, ChannelSpec, parse_channel_spec, OPT_IN_START_RANK,
            resolve_verbosity, resolve_channel_specs,
            EmitterProtocol, NullEmitter, CallableEmitter,
            Hint, register_hint, register_hints, get_hint,
            get_hints_by_category,
            trace,
        )

    def test_the_locked_scale_is_reachable_from_the_ROOT(self):
        """AC-CL-1: api-stability.md locks the scale, so the root must expose
        it -- a contract pointing at symbols only reachable via submodules is
        a contract that lies."""
        from dazzle_loglib import (                              # noqa: F401
            VERBOSITY_CONTINUUM, SILENCE_FLOOR, shows, rank_of,
            verbosity_rungs,
            NOTHING, ERROR, WARNING, MINIMAL, DEFAULT,
            EXTRA, DIAGNOSTICS, CONFIG, LITE_DEBUG, DEBUG,
        )

    def test_protocols_module_permanent_reexport_home(self):
        """R1-F9: even if the canonical home lifts to dazzle_lib.protocols,
        THIS import path keeps working forever."""
        from dazzle_loglib.protocols import (                    # noqa: F401
            EmitterProtocol, NullEmitter, CallableEmitter)

    def test_levels_constants(self):
        from dazzle_loglib.levels import (
            NOTHING, ERROR, WARNING, MINIMAL, DEFAULT, EXTRA, DIAGNOSTICS,
            CONFIG, LITE_DEBUG, DEBUG)
        assert (NOTHING, ERROR, WARNING, MINIMAL, DEFAULT) == (-4, -3, -2, -1, 0)
        assert (EXTRA, DIAGNOSTICS, CONFIG, LITE_DEBUG, DEBUG) == (1, 2, 3, 4, 5)


class TestLockedScale:
    """The 10-rung scale IS API: rung names and ranks are locked."""

    def test_verbosity_continuum_rungs(self):
        from dazzle_loglib.verbosity import VERBOSITY_CONTINUUM as c
        assert {name: c.rank(name) for name in c.levels()} == {
            "nothing": -4, "error": -3, "warning": -2, "minimal": -1,
            "default": 0, "extra": 1, "diagnostics": 2, "config": 3,
            "lite-debug": 4, "debug": 5,
        }

    def test_gate_semantics(self):
        from dazzle_loglib.verbosity import shows
        assert shows(0, 0) and not shows(1, 0)
        assert shows(-3, -3) and not shows(-3, -4)   # the hard wall

    def test_verbosity_rungs_shape(self):
        """AC-CL-2: the scale as data -- 10 rungs, cold->warm, every one glossed."""
        from dazzle_loglib import verbosity_rungs, VERBOSITY_CONTINUUM
        rungs = verbosity_rungs()
        assert len(rungs) == 10
        names = [n for n, _, _ in rungs]
        ranks = [r for _, r, _ in rungs]
        assert names[0] == "nothing" and names[-1] == "debug"
        assert ranks == sorted(ranks) == list(range(-4, 6))   # cold -> warm
        assert all(isinstance(g, str) and g.strip() for _, _, g in rungs)
        # names/ranks agree with the continuum they claim to describe
        assert all(VERBOSITY_CONTINUUM.rank(n) == r for n, r, _ in rungs)

    def test_rung_glosses_are_ascii(self):
        """Glosses are printed to terminals, including Windows cp437/1252."""
        from dazzle_loglib import verbosity_rungs
        for name, _, gloss in verbosity_rungs():
            gloss.encode("ascii")            # raises if a smart dash sneaks in


class TestCharterWalls:
    def test_the_package_never_IMPORTS_argparse(self):
        """AC-CL-3: argparse construction belongs to a CLI library, never here.
        The boundary is a design decision (DWP-A / STACK-MAP D12); this makes
        it executable so it cannot erode by accident.

        Checks real import statements via the AST -- prose *about* argparse is
        fine and expected (``parse_channel_spec`` documents that it raises
        ``ValueError`` precisely so argparse can render a clean error).
        """
        import ast
        import pathlib
        import dazzle_loglib
        pkg = pathlib.Path(dazzle_loglib.__file__).parent
        offenders = []
        for path in sorted(pkg.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    if any(a.name.split(".")[0] == "argparse" for a in node.names):
                        offenders.append(f"{path.name}:{node.lineno}")
                elif isinstance(node, ast.ImportFrom):
                    if (node.module or "").split(".")[0] == "argparse":
                        offenders.append(f"{path.name}:{node.lineno}")
        assert not offenders, (
            f"argparse imported at {offenders} -- parser construction is the "
            f"CLI layer's charter, not this library's")


class TestLockedShapes:
    def test_channeldef_fields(self):
        from dazzle_loglib import ChannelDef
        assert [f.name for f in dataclasses.fields(ChannelDef)] == [
            "name", "description", "opt_in", "default_level", "fd"]

    def test_channelspec_fields(self):
        from dazzle_loglib import ChannelSpec
        assert [f.name for f in dataclasses.fields(ChannelSpec)] == [
            "name", "level", "fd", "destination", "location", "format"]

    def test_hint_fields(self):
        from dazzle_loglib import Hint
        assert [f.name for f in dataclasses.fields(Hint)] == [
            "id", "message", "context", "min_level", "category"]

    def test_emit_signature_accepts_locked_call_shape(self):
        from dazzle_loglib import OutputManager
        om = OutputManager(verbosity=0)
        assert om.emit(0, "m {x}", channel="general", x=1) in (True, False)
        assert om.is_level_active(0, "general") in (True, False)

    def test_init_output_locked_call_shape(self):
        from dazzle_loglib import init_output, ChannelDef
        om = init_output(verbosity=0, quiet=False,
                         channels=["general:1"], strict_channels=True,
                         channel_defs=[ChannelDef("c", "desc")])
        assert om is not None

    def test_resolve_locked_call_shapes(self):
        from dazzle_loglib import resolve_verbosity, resolve_channel_specs
        assert resolve_verbosity(verbose_count=1, quiet_count=0,
                                 explicit=None, env_var=None, default=0) == 1
        assert resolve_channel_specs(["a:1"], env_var=None) == ["a:1"]
