"""The verbosity axis, materialized as a `dazzle_lib.Continuum` (DWP-B / B-1).

THAC0 ("to hit armor class 0") was always a signed Continuum with an invariant
zero -- and `dazzle_lib.continuum` was literally written around it (its docstring
names this logger as the canonical scalar axis; `Continuum.passes()` IS the THAC0
gate). This module connects that wire: `VERBOSITY_CONTINUUM` is the named-rung
axis, and `shows()` is the single emit gate every call routes through.

DEVELOPMENT NOTE: added for dazzlecmd (not in the original wtf-windows `log_lib`,
which used raw ints inline) -- the first step of the log_lib continuum redesign.
This makes the vendored copy depend on `dazzle_lib` (the bedrock; a valid
down-only dependency the future `dazzle_loglib` will declare). See `_VENDORED.md`.
"""
from dazzle_lib.continuum import Continuum

from .levels import (
    NOTHING, ERROR, WARNING, MINIMAL, DEFAULT, EXTRA, DIAGNOSTICS, CONFIG,
    LITE_DEBUG, DEBUG, RUNG_GLOSSES)

# The verbosity Continuum: 4 quiet rungs, the invariant 0 (DEFAULT), 5 verbose
# rungs — the 10-rung SD-FQCN-4 scale (re-runged 0.2.0). The int constants ARE
# the signed ranks -- `rank(level) <= rank(threshold)` (Continuum.passes) is the
# THAC0 gate, byte-for-byte the historical `level <= threshold`. The asymmetry
# (4 cold : 5 warm) is intentional: quiet compresses, verbose differentiates.
VERBOSITY_CONTINUUM = Continuum(
    name="verbosity",
    ranks={
        "nothing": NOTHING, "error": ERROR, "warning": WARNING, "minimal": MINIMAL,
        "default": DEFAULT, "extra": EXTRA, "diagnostics": DIAGNOSTICS,
        "config": CONFIG, "lite-debug": LITE_DEBUG, "debug": DEBUG,
    },
    invariant="default output",
)

# The silence floor = the cold pole, derived FROM the Continuum (not a magic -4).
SILENCE_FLOOR = VERBOSITY_CONTINUUM.ranks[VERBOSITY_CONTINUUM.cold_pole()]  # NOTHING


def shows(level: int, threshold: int) -> bool:
    """The THAC0 emit gate, materialized: a message at ``level`` shows when the
    channel's ``threshold`` admits it -- ``level <= threshold`` (the Continuum's
    ``passes``, since the levels ARE the ranks) AND the threshold is above the
    silence floor. Nothing is ever emitted AT the floor, so threshold==floor =
    "exit code only" (the hard wall falls out of the gate, no separate check)."""
    return threshold > SILENCE_FLOOR and level <= threshold


def rank_of(name: str) -> int:
    """The signed rank of a named rung (``rank_of('config') == 3``) -- the
    name->rank lookup channel specs use (`--show timing:config`)."""
    return VERBOSITY_CONTINUUM.rank(name)


def verbosity_rungs():
    """The full scale as DATA: ``(name, rank, gloss)`` per rung, cold -> warm.

    The rung names and ranks are locked API and the glosses are library-owned,
    so this is the canonical source for any surface that explains the verbosity
    model to a user -- a ``--help`` table, a ``verbosity`` sub-command, a docs
    page. Rendering (banding, width, color, whether the flag is spelled ``-vv``
    or ``--verbosity 2``) is deliberately NOT decided here: that belongs to the
    consumer, or to a future CLI library. This function only supplies the truth
    it would otherwise have to hand-copy.

    Example -- the smallest useful help table::

        for name, rank, gloss in verbosity_rungs():
            print(f"  {rank:+d}  {name:<12} {gloss}")

    Returns:
        A list of ``(name, rank, gloss)`` tuples ordered coldest to warmest
        (``nothing`` at -4 through ``debug`` at +5).
    """
    return [(name, VERBOSITY_CONTINUUM.rank(name), RUNG_GLOSSES[name])
            for name in VERBOSITY_CONTINUUM.levels()]   # levels() is cold->warm
