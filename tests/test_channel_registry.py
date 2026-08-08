"""LH-4 + R1 fixes: the consumer-declared channel registry.

Covers: defs-suppress-donor-defaults (R1-F2), opt-in via declaration (R1-F3),
validate-before-gate (R1-F4), FD sentinels in all three positions (R1-F5),
manager verbosity_space (R1-F6), reinit contract (R1-F7), warning shims
(R1-F8/AC-9), drive-letter specs (R1-F15), zero-cost gating (AC-2).
"""
import sys
import warnings

import pytest

from dazzle_loglib.channels import (
    ChannelDef, ChannelSpec, parse_channel_spec, OPT_IN_START_RANK)
from dazzle_loglib.manager import (
    OutputManager, init_output, get_output, BUILTIN_CHANNELS)


class TestChannelDef:
    def test_basic_declaration(self):
        d = ChannelDef("liveness", "Liveness ladder decisions")
        assert d.starting_level() is None          # follows global

    def test_opt_in_is_sugar_for_cold_start(self):
        d = ChannelDef("vals", opt_in=True)
        assert d.starting_level() == OPT_IN_START_RANK == -1

    def test_opt_in_conflicting_default_level_raises(self):
        with pytest.raises(ValueError, match="contradictory"):
            ChannelDef("vals", opt_in=True, default_level=2)

    def test_opt_in_with_matching_default_level_allowed(self):
        d = ChannelDef("vals", opt_in=True, default_level=OPT_IN_START_RANK)
        assert d.starting_level() == -1

    def test_default_level_zero_pins_not_follows(self):
        """R1-F3: 0 pins the channel at `default`; None means follow global."""
        assert ChannelDef("x", default_level=0).starting_level() == 0
        assert ChannelDef("x").starting_level() is None

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            ChannelDef("")

    def test_dotted_names_allowed_uninterpreted(self):
        assert ChannelDef("liveness.verify").name == "liveness.verify"


class TestRegistryConstruction:
    def test_defs_define_known_channels_plus_builtins(self):
        om = OutputManager(channel_defs=[ChannelDef("liveness"),
                                         ChannelDef("git")])
        assert om.known_channels == {"liveness", "git"} | set(BUILTIN_CHANNELS)

    def test_defs_suppress_donor_defaults(self):
        """R1-F2: with defs present, donor opt-in overrides contribute NOTHING."""
        om = init_output(channel_defs=[ChannelDef("trace")])   # a HOT trace
        assert "vals" not in om.channel_overrides
        assert om.channel_overrides.get("trace") is None       # follows global
        assert om.channel_active("trace") is True              # not donor-cold

    def test_legacy_path_still_applies_donor_defaults(self):
        om = init_output()
        assert om.channel_overrides == {"vals": -1, "trace": -1}

    def test_def_starting_levels_become_overrides(self):
        om = OutputManager(channel_defs=[
            ChannelDef("vals", opt_in=True),
            ChannelDef("epoch", default_level=2),
        ])
        assert om.channel_overrides["vals"] == -1
        assert om.channel_overrides["epoch"] == 2

    def test_cli_spec_beats_declared_starting_level(self):
        om = init_output(channel_defs=[ChannelDef("vals", opt_in=True)],
                         channels=["vals:1"])
        assert om.channel_overrides["vals"] == 1               # user spec wins

    def test_duplicate_defs_raise(self):
        with pytest.raises(ValueError, match="duplicate"):
            OutputManager(channel_defs=[ChannelDef("x"), ChannelDef("x")])

    def test_non_channeldef_item_raises(self):
        with pytest.raises(TypeError, match="ChannelDef"):
            OutputManager(channel_defs=["liveness"])

    def test_spec_string_in_channel_defs_position_raises(self):
        with pytest.raises(TypeError, match="spec strings"):
            init_output(channels=[ChannelDef("x")])

    def test_known_channels_conflicting_with_defs_raises(self):
        with pytest.raises(ValueError, match="conflicts with channel_defs"):
            OutputManager(channel_defs=[ChannelDef("a")],
                          known_channels={"a", "rogue"})

    def test_known_channels_subset_of_defs_accepted(self):
        om = OutputManager(channel_defs=[ChannelDef("a")],
                           known_channels={"a", "general"})
        assert "a" in om.known_channels

    def test_known_channels_without_defs_warns_deprecated(self):
        with pytest.warns(DeprecationWarning, match="channel_defs"):
            OutputManager(known_channels={"a"})


class TestStrictValidation:
    def test_unknown_channel_raises_at_default_verbosity(self):
        """R1-F4: validation runs BEFORE the gate — typos fail even gated."""
        om = OutputManager(verbosity=0, strict_channels=True,
                           channel_defs=[ChannelDef("liveness")])
        with pytest.raises(ValueError, match="tpyo"):
            om.emit(5, "never shown anyway", channel="tpyo")

    def test_builtin_channels_always_valid_under_strict(self):
        om = OutputManager(verbosity=0, strict_channels=True,
                           channel_defs=[ChannelDef("liveness")])
        om.error("boom")                       # 'error' channel — no raise
        assert om.emit(0, "hi") is True        # 'general' — no raise

    def test_declared_channel_passes_strict(self):
        om = OutputManager(verbosity=0, strict_channels=True,
                           channel_defs=[ChannelDef("liveness")])
        assert om.emit(0, "ok", channel="liveness") is True


class TestFdSentinels:
    """R1-F5: 'stdout'/'stderr' sentinels legal in ALL THREE positions,
    resolved at emit time (post-rebind streams are honored)."""

    def _capture(self, monkeypatch, om, level=0, channel='general', file=None):
        import io
        fake_err, fake_out = io.StringIO(), io.StringIO()
        monkeypatch.setattr(sys, "stderr", fake_err)
        monkeypatch.setattr(sys, "stdout", fake_out)
        om.emit(level, "msg", channel=channel, file=file)
        return fake_out.getvalue(), fake_err.getvalue()

    def test_manager_default_sentinel(self, monkeypatch):
        om = OutputManager(file='stderr')
        out, err = self._capture(monkeypatch, om)
        assert err == "msg\n" and out == ""

    def test_channel_def_fd_sentinel(self, monkeypatch):
        om = OutputManager(channel_defs=[ChannelDef("vals", fd='stdout')])
        out, err = self._capture(monkeypatch, om, channel="vals")
        assert out == "msg\n" and err == ""

    def test_per_message_file_sentinel(self, monkeypatch):
        om = OutputManager()
        out, err = self._capture(monkeypatch, om, file='stdout')
        assert out == "msg\n" and err == ""


class TestReinit:
    def test_init_output_replaces_singleton(self):
        """R1-F7: a second init with different defs is legal and total."""
        first = init_output(channel_defs=[ChannelDef("a")])
        second = init_output(channel_defs=[ChannelDef("b")])
        assert get_output() is second and second is not first
        assert "b" in second.known_channels and "a" not in second.known_channels


class TestVerbositySpaceMethod:
    def test_space_reflects_declared_registry(self):
        om = OutputManager(channel_defs=[ChannelDef("liveness"),
                                         ChannelDef("git")])
        space = om.verbosity_space()
        assert set(space.axes) == {"liveness", "git"} | set(BUILTIN_CHANNELS)
        assert space.axes["liveness"].rank("debug") == 5

    def test_space_is_cached(self):
        om = OutputManager(channel_defs=[ChannelDef("a")])
        assert om.verbosity_space() is om.verbosity_space()

    def test_format_channel_list_uses_def_descriptions(self):
        om = OutputManager(channel_defs=[
            ChannelDef("liveness", "Liveness ladder decisions")])
        listing = om.format_channel_list()
        assert "liveness" in listing and "Liveness ladder decisions" in listing


class TestDeprecationShims:
    """R1-F8 / AC-9: legacy mutation warns loudly; declared usage is silent."""

    def test_known_channels_mutation_warns(self):
        from dazzle_loglib.channels import KNOWN_CHANNELS
        with pytest.warns(DeprecationWarning, match="channel_defs"):
            KNOWN_CHANNELS.add("__test_temp__")
        with pytest.warns(DeprecationWarning):
            KNOWN_CHANNELS.discard("__test_temp__")

    def test_descriptions_mutation_warns(self):
        from dazzle_loglib.channels import CHANNEL_DESCRIPTIONS
        with pytest.warns(DeprecationWarning, match="channel_defs"):
            CHANNEL_DESCRIPTIONS["__test_temp__"] = "x"
        with pytest.warns(DeprecationWarning):
            del CHANNEL_DESCRIPTIONS["__test_temp__"]

    def test_channelconfig_alias_warns_and_is_channelspec(self):
        import dazzle_loglib.channels as ch
        with pytest.warns(DeprecationWarning, match="ChannelSpec"):
            alias = ch.ChannelConfig
        assert alias is ChannelSpec

    def test_declared_registry_usage_emits_no_warnings(self):
        """AC-9: the recommended path is warning-clean."""
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            om = init_output(verbosity=1, strict_channels=True,
                             channel_defs=[ChannelDef("liveness")],
                             channels=["liveness:diagnostics"])
            om.emit(1, "clean", channel="liveness")


class TestZeroCostGating:
    """AC-2: gated-off emits perform NO string formatting on their kwargs."""

    class _Boom:
        def __format__(self, spec):
            raise AssertionError("kwargs were formatted despite the gate")
        def __str__(self):
            raise AssertionError("kwargs were stringified despite the gate")

    def test_gated_emit_never_formats(self):
        om = OutputManager(verbosity=0)
        assert om.emit(5, "value={v}", channel="general", v=self._Boom()) is False

    def test_shown_emit_does_format(self):
        om = OutputManager(verbosity=0)
        sink = []
        om.default_renderer = sink.append
        om.emit(0, "value={v}", v=42)
        assert sink == ["value=42"]


class TestDriveLetterSpec:
    def test_drive_letter_location_parses(self):
        """R1-F15: the Windows drive-letter rejoin, now covered IN THIS repo."""
        spec = parse_channel_spec(r"timing::file:C:\logs\out.log")
        assert spec.name == "timing"
        assert spec.destination == "file"
        assert spec.location == r"C:\logs\out.log"
