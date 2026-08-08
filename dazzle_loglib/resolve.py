"""Verbosity and channel-spec resolution with defined precedence (LH-6).

One place encodes the precedence rules so every consumer gets them right:

    explicit  >  CLI counts  >  environment  >  default

The middle rule carries the sharp edge (R1-F16): CLI counts are "expressed"
whenever EITHER count is nonzero — ``-v -q`` nets to zero but still means the
user said something on the command line, so it beats the environment. The
failure mode this module exists to prevent is the read-then-unconditionally-
overwrite bug observed in the wild, where an env-var verbosity default was
silently discarded whenever flags were absent (the from_environment/from_args
ordering trap) — pinned here by ``test_env_not_clobbered_when_no_flags_present``.

This module never reads the environment implicitly: consumers name their env
vars (``CSB_VERBOSITY``, ``DZ_SHOW``, ...) or pass ``env_var=None`` to opt out.
"""

import os
from typing import List, Optional

from .verbosity import rank_of

__all__ = ["resolve_verbosity", "resolve_channel_specs"]


def _parse_verbosity_value(raw: str, source: str) -> int:
    """An int (``"2"``, ``"-1"``) or a named verbosity rung (``"debug"``)."""
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return rank_of(raw.strip().lower())
    except Exception:
        raise ValueError(
            f"{source}: {raw!r} is neither an integer verbosity nor a "
            f"named rung (nothing/error/warning/minimal/default/timing/"
            f"config/debug)"
        )


def resolve_verbosity(verbose_count: int = 0, quiet_count: int = 0, *,
                      explicit: Optional[int] = None,
                      env_var: Optional[str] = None,
                      default: int = 0) -> int:
    """Resolve the effective verbosity from all sources, by precedence.

    Args:
        verbose_count: Number of ``-v`` occurrences (argparse ``action='count'``).
        quiet_count: Number of ``-q`` occurrences.
        explicit: A directly-stated level (e.g. ``--verbosity N``); wins outright.
        env_var: Name of an environment variable to consult when nothing was
            expressed on the CLI. Value may be an int or a named rung.
            ``None`` disables environment lookup.
        default: The level when no source speaks.

    Returns:
        The effective signed verbosity. When counts are expressed, the result
        is ``default + verbose_count - quiet_count`` (counts step from the
        consumer's default, which is 0 for every current consumer).

    Raises:
        ValueError: The environment variable is set to something that is
            neither an int nor a named rung. Loud by design — a typo'd env
            value silently ignored is how diagnosability dies.
    """
    if explicit is not None:
        return explicit
    if verbose_count != 0 or quiet_count != 0:
        # Expressed on the CLI — the environment is NOT consulted, even when
        # the counts cancel to net zero (R1-F16).
        return default + verbose_count - quiet_count
    if env_var:
        raw = os.environ.get(env_var)
        if raw is not None and raw.strip() != "":
            return _parse_verbosity_value(raw, f"environment variable {env_var}")
    return default


def resolve_channel_specs(cli_specs: Optional[List[str]] = None, *,
                          env_var: Optional[str] = None) -> List[str]:
    """Merge channel spec strings from CLI and environment, CLI winning per-channel.

    The environment value is a comma-joined list of spec strings
    (``"liveness:debug,timing:2"``). A CLI spec for a channel replaces any env
    spec for the SAME channel (the spec's channel is everything before the
    first ``:``); env specs for other channels survive. Result order:
    surviving env specs first (env order), then CLI specs (CLI order).

    Known limitation: the comma join means an env spec's file location cannot
    itself contain a comma — pass such specs on the CLI instead.
    """
    cli_specs = list(cli_specs or [])
    env_specs: List[str] = []
    if env_var:
        raw = os.environ.get(env_var)
        if raw and raw.strip():
            env_specs = [s.strip() for s in raw.split(",") if s.strip()]

    def channel_of(spec: str) -> str:
        return spec.split(":", 1)[0]

    cli_channels = {channel_of(s) for s in cli_specs}
    merged = [s for s in env_specs if channel_of(s) not in cli_channels]
    merged.extend(cli_specs)
    return merged
