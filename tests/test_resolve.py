"""LH-6 / R1-F16: resolution precedence — explicit > CLI counts > env > default.

The named regressions here are the point: the dazzlesum lineage showed how
bolted-on env support silently dies (read, then unconditionally overwritten by
the flags path), and the -v/-q cancellation case is the cousin of that bug.
"""
import pytest

from dazzle_loglib.resolve import resolve_verbosity, resolve_channel_specs


class TestResolveVerbosityPrecedence:
    def test_default_when_nothing_speaks(self):
        assert resolve_verbosity() == 0
        assert resolve_verbosity(default=1) == 1

    def test_counts_compose(self):
        assert resolve_verbosity(verbose_count=2) == 2
        assert resolve_verbosity(quiet_count=3) == -3
        assert resolve_verbosity(verbose_count=2, quiet_count=1) == 1

    def test_explicit_beats_everything(self, monkeypatch):
        monkeypatch.setenv("X_VERBOSITY", "3")
        assert resolve_verbosity(verbose_count=2, explicit=-1,
                                 env_var="X_VERBOSITY") == -1

    def test_env_not_clobbered_when_no_flags_present(self, monkeypatch):
        """THE dazzlesum regression: env must win when the CLI said nothing."""
        monkeypatch.setenv("X_VERBOSITY", "2")
        assert resolve_verbosity(env_var="X_VERBOSITY") == 2

    def test_v_and_Q_cancel_still_overrides_env(self, monkeypatch):
        """R1-F16: -v -q nets to 0 but IS expressed — env must NOT win."""
        monkeypatch.setenv("X_VERBOSITY", "3")
        assert resolve_verbosity(verbose_count=1, quiet_count=1,
                                 env_var="X_VERBOSITY") == 0

    def test_env_named_rung(self, monkeypatch):
        monkeypatch.setenv("X_VERBOSITY", "debug")
        assert resolve_verbosity(env_var="X_VERBOSITY") == 5   # 10-rung scale
        monkeypatch.setenv("X_VERBOSITY", "diagnostics")
        assert resolve_verbosity(env_var="X_VERBOSITY") == 2
        monkeypatch.setenv("X_VERBOSITY", "error")
        assert resolve_verbosity(env_var="X_VERBOSITY") == -3

    def test_env_invalid_value_raises_loudly(self, monkeypatch):
        monkeypatch.setenv("X_VERBOSITY", "loudly")
        with pytest.raises(ValueError, match="X_VERBOSITY"):
            resolve_verbosity(env_var="X_VERBOSITY")

    def test_env_empty_value_falls_through_to_default(self, monkeypatch):
        monkeypatch.setenv("X_VERBOSITY", "  ")
        assert resolve_verbosity(env_var="X_VERBOSITY", default=1) == 1

    def test_env_disabled_when_no_var_named(self, monkeypatch):
        monkeypatch.setenv("X_VERBOSITY", "3")
        assert resolve_verbosity() == 0

    def test_counts_step_from_nonzero_default(self):
        assert resolve_verbosity(quiet_count=1, default=1) == 0


class TestResolveChannelSpecs:
    def test_cli_only(self):
        assert resolve_channel_specs(["timing:2"]) == ["timing:2"]

    def test_env_only(self, monkeypatch):
        monkeypatch.setenv("X_SHOW", "liveness:debug, timing:2")
        assert resolve_channel_specs(env_var="X_SHOW") == \
            ["liveness:debug", "timing:2"]

    def test_cli_overrides_env_per_channel(self, monkeypatch):
        """R1-F16: same-channel CLI spec replaces env's; other env specs survive."""
        monkeypatch.setenv("X_SHOW", "liveness:debug,timing:2")
        assert resolve_channel_specs(["timing:config"], env_var="X_SHOW") == \
            ["liveness:debug", "timing:config"]

    def test_no_sources(self):
        assert resolve_channel_specs() == []
        assert resolve_channel_specs(None, env_var="X_UNSET_SHOW") == []
