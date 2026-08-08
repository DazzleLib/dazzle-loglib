"""The verbosity axis as a `dazzle_lib.Continuum`, and the THAC0 emit gate
routed through `shows()`. These pin the MUST-PRESERVE gate behavior (the
redesigns must not change what shows at what threshold) — updated 0.2.0 for
the 10-rung SD-FQCN-4 re-rung (rung MAP changed; gate unchanged).
"""
import pytest

from dazzle_loglib.verbosity import (
    VERBOSITY_CONTINUUM, SILENCE_FLOOR, shows, rank_of)
from dazzle_loglib.levels import (
    NOTHING, ERROR, DEFAULT, DEBUG, LITE_DEBUG, CONFIG, DIAGNOSTICS, EXTRA,
    TIMING)
from dazzle_loglib.manager import OutputManager


class TestVerbosityContinuum:
    def test_ten_named_rungs_with_the_invariant_zero(self):
        c = VERBOSITY_CONTINUUM
        assert c.rank("default") == 0                      # the invariant
        assert c.rank("nothing") == -4 and c.rank("debug") == 5
        assert c.cold_pole() == "nothing" and c.warm_pole() == "debug"
        assert len(c.levels()) == 10

    def test_the_rerung_map(self):
        """SD-FQCN-4 (user-adopted 2026-08-08): the warm reach differentiates."""
        assert rank_of("extra") == EXTRA == 1
        assert rank_of("diagnostics") == DIAGNOSTICS == 2
        assert rank_of("config") == CONFIG == 3
        assert rank_of("lite-debug") == LITE_DEBUG == 4
        assert rank_of("debug") == DEBUG == 5

    def test_deprecated_timing_alias_points_at_extra(self):
        assert TIMING == EXTRA == 1

    def test_silence_floor_is_the_cold_pole(self):
        assert SILENCE_FLOOR == NOTHING == -4

    def test_rank_of_named_rung(self):
        assert rank_of("config") == 3 and rank_of("error") == -3


class TestShowsGate:
    """`shows(level, threshold)` == the THAC0 gate (must-preserve)."""

    @pytest.mark.parametrize("level,threshold,expected", [
        (DEFAULT, DEFAULT, True),     # default shows at default
        (1, DEFAULT, False),          # extra too loud for default
        (DEFAULT, 1, True),           # default shows when louder allowed
        (ERROR, ERROR, True),         # errors show at error threshold
        (ERROR, NOTHING, False),      # the HARD WALL: errors off at the floor
        (NOTHING, NOTHING, False),    # nothing shows at/under the floor
        (DEBUG, DEBUG, True),         # full debug shows at -vvvvv
        (DEBUG, DEFAULT, False),      # debug hidden at default
        (LITE_DEBUG, DEBUG, True),    # lite-debug shows under full debug
        (DEBUG, LITE_DEBUG, False),   # full debug hidden at lite-debug
    ])
    def test_thaco_gate_preserved(self, level, threshold, expected):
        assert shows(level, threshold) is expected


class TestOutputManagerGate:
    """The OutputManager routes its gate through `shows()` (one path)."""

    def test_is_level_active_uses_the_gate(self):
        om = OutputManager(verbosity=1)               # -v
        assert om.is_level_active(1, "general") is True     # extra shows
        assert om.is_level_active(2, "general") is False    # diagnostics hidden

    def test_hard_wall_suppresses_even_errors(self):
        om = OutputManager(verbosity=NOTHING)         # -qqqq
        assert om.is_level_active(ERROR, "error") is False

    def test_per_channel_override_beats_global(self):
        om = OutputManager(verbosity=0)
        om.channel_overrides["timing"] = 1            # raise just the timing channel
        assert om.is_level_active(1, "timing") is True      # timing now shows
        assert om.is_level_active(1, "general") is False    # but not elsewhere


class TestChannelSpecsAndSpace:
    """Named-rank channel specs + the channels x verbosity ContinuumSpace."""

    def test_named_rank_channel_spec(self):
        from dazzle_loglib.channels import parse_channel_spec
        assert parse_channel_spec("timing:config").level == 3   # named -> rank 3
        assert parse_channel_spec("parse:debug").level == 5     # the continuum surface
        assert parse_channel_spec("scan:diagnostics").level == 2

    def test_int_channel_spec_still_works(self):
        from dazzle_loglib.channels import parse_channel_spec
        assert parse_channel_spec("timing:2").level == 2        # int preserved
        assert parse_channel_spec("timing").level == 0          # default

    def test_unknown_named_rung_raises_value_error(self):
        """R1-F17: argparse-friendly ValueError at the parse boundary."""
        from dazzle_loglib.channels import parse_channel_spec
        with pytest.raises(ValueError, match="named verbosity rung"):
            parse_channel_spec("timing:loudly")

    def test_manager_verbosity_space_reflects_legacy_set_when_undeclared(self):
        from dazzle_loglib.channels import KNOWN_CHANNELS
        space = OutputManager().verbosity_space()
        assert set(space.axes) == set(KNOWN_CHANNELS)
        # each channel axis carries the verbosity continuum ('config' == 3)
        assert space.axes["timing"].rank("config") == 3

    def test_module_verbosity_space_attr_is_deprecated(self):
        import dazzle_loglib.channels as ch
        with pytest.warns(DeprecationWarning, match="verbosity_space"):
            space = ch.VERBOSITY_SPACE
        assert set(space.axes) == set(ch.KNOWN_CHANNELS)

    def test_opt_in_channels_declared_cold(self):
        from dazzle_loglib.channels import default_channel_overrides
        assert default_channel_overrides() == {"vals": -1, "trace": -1}


class TestHintRouting:
    """hint() routes through emit() (ONE gate path); dedup + context +
    level gating all preserved (the must-preserve hint behavior)."""

    def _om(self, verbosity, sink):
        om = OutputManager(verbosity=verbosity)
        om.default_renderer = sink.append      # capture emit()'s layer-3 output
        return om

    def test_hint_shows_when_level_and_context_pass(self):
        from dazzle_loglib.hints import register_hint, Hint
        register_hint(Hint(id="t.show", message="a tip", min_level=0,
                           context={"result"}))
        out = []
        self._om(0, out).hint("t.show", context="result")
        assert out == ["a tip"]

    def test_hint_gated_when_too_verbose_for_threshold(self):
        from dazzle_loglib.hints import register_hint, Hint
        register_hint(Hint(id="t.gated", message="deep", min_level=2,
                           context={"result"}))
        out = []
        self._om(0, out).hint("t.gated", context="result")    # 0 < 2 -> gated
        assert out == []

    def test_hint_dedup_shows_once(self):
        from dazzle_loglib.hints import register_hint, Hint
        register_hint(Hint(id="t.dedup", message="once", min_level=0,
                           context={"result"}))
        out = []
        om = self._om(0, out)
        om.hint("t.dedup", context="result")
        om.hint("t.dedup", context="result")
        assert out == ["once"]                                # dedup preserved

    def test_hint_context_mismatch_suppresses(self):
        from dazzle_loglib.hints import register_hint, Hint
        register_hint(Hint(id="t.ctx", message="err only", min_level=0,
                           context={"error"}))
        out = []
        self._om(0, out).hint("t.ctx", context="result")      # context mismatch
        assert out == []
