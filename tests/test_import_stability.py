"""API-stability canary (STACK-MAP review F9: every new lib ships this at
first release). If any of these fail, a locked public symbol moved or changed
shape — that is a BREAKING change requiring a deliberate version decision,
docs/api-stability.md update, and consumer notice. See docs/api-stability.md
for what is and is NOT covered (the legacy donor surface is explicitly
excluded from the guarantee).
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
