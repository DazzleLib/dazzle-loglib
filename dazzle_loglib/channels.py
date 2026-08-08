"""
Channel declaration, configuration, and spec parsing for the THAC0 verbosity system.

Channels are named output categories. Each channel can have its own verbosity
threshold (overriding the global level) and routing properties. Since 0.2.0 the
channel set is CONSUMER-DEFINED (LH-4): applications declare their channels with
:class:`ChannelDef` and pass them to ``init_output(channel_defs=[...])``. The
module-level donor sets at the bottom of this file are a DEPRECATED legacy
surface kept for the vendored-copy cutover window (DazzleTools/dazzlecmd#118) —
they carry the original donor project's channel names, are excluded from the
API-stability guarantee, and warn on mutation.

Doctrine — content vs diagnostic channels (SL-5): most channels carry stderr
DIAGNOSTICS, but a channel may instead ANNOTATE stdout content (the donor
project's ``vals`` channel appended computed values to result lines). stderr is
a default destination, not a design principle — ``ChannelDef.fd`` or
``set_channel_fd()`` routes a channel wherever its kind demands.

Channel spec syntax (compact, positional):
    CHANNEL:LEVEL:DEST:LOCATION:FORMAT

    Examples:
        timing              # All defaults (level=0 — pins the channel at `default`)
        timing:2            # Level 2
        timing:config       # Named rung (resolved via the verbosity Continuum)
        timing::file:perf.log   # Default level, file dest
        timing::stdout::json    # Default level, stdout, json

Dotted channel names (``liveness.verify``) are ALLOWED and uninterpreted —
hierarchy semantics are deferred to the FQCN arc (reference design: SD-FQCN-2's
derive/cascade; see the loglib DWP's decision ledger).
"""

import warnings
from dataclasses import dataclass
from typing import Dict, Optional, TextIO, Union

from dazzle_lib.continuum import ContinuumSpace, ContinuumError

from .verbosity import VERBOSITY_CONTINUUM, rank_of

# The release in which the deprecated legacy surfaces are slated for removal
# (registered in the DazzleLib alias/violation register per shim policy Rule 6).
_REMOVAL_VERSION = "0.4.0"

# The opt-in channels' cold starting rung, DECLARED via the verbosity Continuum:
# an opt-in channel starts at `minimal` (-1) so a level-0 message is suppressed
# until a channel spec raises it.
OPT_IN_START_RANK = rank_of("minimal")  # -1


# =============================================================================
# ChannelDef — the consumer-declared channel (LH-4 / R1-F3)
# =============================================================================

@dataclass(frozen=True)
class ChannelDef:
    """A consumer-DECLARED output channel.

    Applications describe their channel set as a list of these and hand it to
    ``init_output(channel_defs=[...])`` (or ``OutputManager(channel_defs=...)``).
    When defs are supplied they are the WHOLE story: the legacy module sets and
    donor opt-in defaults contribute nothing (R1-F2).

    Attributes:
        name: Channel identifier. Dotted names are allowed and uninterpreted
            (reserved for future hierarchy semantics).
        description: Human-readable line for channel listings.
        opt_in: Start COLD (at the ``minimal`` rung) until a channel spec
            explicitly raises the channel. Sugar for
            ``default_level=OPT_IN_START_RANK``.
        default_level: Optional starting threshold override. ``None`` means
            "follow the global verbosity" (no override). NOTE ``0`` is NOT
            "no override" — it pins the channel at the ``default`` rung.
        fd: Default output destination for this channel: a ``TextIO``, or one
            of the sentinel strings ``'stdout'``/``'stderr'`` (resolved at
            emit time, surviving stream rebinds). Compat note (SL-2): a future
            ``Section`` grouping wrapper references channels by NAME — nothing
            here precludes it.
    """
    name: str
    description: str = ""
    opt_in: bool = False
    default_level: Optional[int] = None
    fd: Union[TextIO, str, None] = None

    def __post_init__(self):
        if not self.name or not isinstance(self.name, str):
            raise ValueError(
                f"ChannelDef.name must be a non-empty str, got {self.name!r}")
        if self.opt_in and self.default_level is not None \
                and self.default_level != OPT_IN_START_RANK:
            raise ValueError(
                f"ChannelDef({self.name!r}): opt_in=True is sugar for "
                f"default_level={OPT_IN_START_RANK}; also passing "
                f"default_level={self.default_level} is contradictory")

    def starting_level(self) -> Optional[int]:
        """The channel's starting threshold override, or None (follow global)."""
        if self.opt_in:
            return OPT_IN_START_RANK
        return self.default_level


# =============================================================================
# ChannelSpec — the parse product of a CLI channel spec string
# =============================================================================
# Renamed from ChannelConfig in 0.2.0 (R1-F3): this dataclass IS the parse of
# a spec string, nothing more. `ChannelConfig` remains importable from this
# module as a warning alias (module __getattr__ below).

@dataclass
class ChannelSpec:
    """The parsed form of a CLI channel spec (``CHANNEL:LEVEL:DEST:LOCATION:FORMAT``).

    Attributes:
        name: Channel identifier
        level: Threshold override (0 = pin at `default`; specs cannot express
            "no override" — declare that with ``ChannelDef(default_level=None)``)
        fd: Output file handle for this channel (None = use manager default);
            participates in FD resolution when set
        destination: 'stderr', 'stdout', 'file', 'fdN' (routing hint)
        location: File path for file dest
        format: 'text', 'json', 'csv' (future)
    """
    name: str
    level: int = 0
    fd: Optional[TextIO] = None
    destination: Optional[str] = None
    location: Optional[str] = None
    format: Optional[str] = None


def _resolve_level(token: str) -> int:
    """A channel spec's level slot: a raw int (``'2'``) OR a NAMED verbosity
    rung (``'config'`` -> 3) resolved via the verbosity Continuum. Unknown
    names raise ``ValueError`` (argparse-friendly; R1-F17)."""
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return rank_of(token)
    except ContinuumError as e:
        raise ValueError(
            f"channel spec level {token!r} is neither an integer nor a named "
            f"verbosity rung ({', '.join(VERBOSITY_CONTINUUM.levels())})"
        ) from e


def parse_channel_spec(spec: str) -> ChannelSpec:
    """Parse a channel spec string into a ChannelSpec.

    Handles the compact positional syntax:
        CHANNEL:LEVEL:DEST:LOCATION:FORMAT

    Empty slots use :: (empty between colons).
    Windows drive letters (e.g., C:\\path) are detected and rejoined.

    Args:
        spec: Channel spec string like "timing:2" or "timing::file:C:\\logs\\out.log"

    Returns:
        ChannelSpec with parsed values

    Raises:
        ValueError: the LEVEL slot names an unknown verbosity rung.
    """
    parts = spec.split(':')

    # Handle Windows drive letters: rejoin 'C' + 'path' into 'C:path'
    # A single alpha character followed by another part is likely a drive letter
    rejoined = []
    i = 0
    while i < len(parts):
        if (len(parts[i]) == 1 and parts[i].isalpha()
                and i + 1 < len(parts)
                and i >= 3):  # Only in LOCATION slot (position 3+)
            rejoined.append(f"{parts[i]}:{parts[i+1]}")
            i += 2
        else:
            rejoined.append(parts[i])
            i += 1
    parts = rejoined

    name = parts[0] if len(parts) > 0 else ''
    level = 0
    dest = location = fmt = None

    if len(parts) > 1 and parts[1]:
        level = _resolve_level(parts[1])   # int OR named rung ('config')
    if len(parts) > 2 and parts[2]:
        dest = parts[2]
    if len(parts) > 3 and parts[3]:
        location = parts[3]
    if len(parts) > 4 and parts[4]:
        fmt = parts[4]

    return ChannelSpec(name=name, level=level, destination=dest,
                       location=location, format=fmt)


# =============================================================================
# DEPRECATED legacy surface — the donor project's module-level channel sets
# =============================================================================
# Kept byte-equivalent through the cutover window (#118) because the vendored
# copies' consumers still read them (e.g. dazzlecmd meta_audit). EXCLUDED from
# docs/api-stability.md. Mutation warns (R1-F8): the historical integration
# seam was `KNOWN_CHANNELS.clear(); KNOWN_CHANNELS.update(APP_CHANNELS)` —
# replaced by init_output(channel_defs=[...]).

def _mutation_warning():
    warnings.warn(
        "Mutating dazzle_loglib's module-level channel sets is deprecated; "
        "declare channels via init_output(channel_defs=[ChannelDef(...)]) "
        f"instead. This legacy surface is slated for removal in "
        f"{_REMOVAL_VERSION}.",
        DeprecationWarning, stacklevel=3)


class _WarningSet(set):
    """A set whose MUTATION warns; reads stay silent (R1-F8)."""

    def clear(self):
        _mutation_warning()
        return super().clear()

    def update(self, *args):
        _mutation_warning()
        return super().update(*args)

    def add(self, item):
        _mutation_warning()
        return super().add(item)

    def discard(self, item):
        _mutation_warning()
        return super().discard(item)

    def remove(self, item):
        _mutation_warning()
        return super().remove(item)

    def pop(self):
        _mutation_warning()
        return super().pop()


class _WarningDict(dict):
    """A dict whose MUTATION warns; reads stay silent (R1-F8)."""

    def clear(self):
        _mutation_warning()
        return super().clear()

    def update(self, *args, **kwargs):
        _mutation_warning()
        return super().update(*args, **kwargs)

    def __setitem__(self, key, value):
        _mutation_warning()
        return super().__setitem__(key, value)

    def __delitem__(self, key):
        _mutation_warning()
        return super().__delitem__(key)

    def pop(self, *args):
        _mutation_warning()
        return super().pop(*args)

    def popitem(self):
        _mutation_warning()
        return super().popitem()

    def setdefault(self, *args):
        _mutation_warning()
        return super().setdefault(*args)


# Channels used by the DONOR codebase (legacy; consumer-defined sets replace this)
KNOWN_CHANNELS = _WarningSet({
    'config',       # Configuration loading and overrides
    'parse',        # Expression parsing
    'eval',         # Expression evaluation
    'iter',         # Iteration / search space
    'progress',     # Progress counters
    'timing',       # Timing information
    'algorithm',    # Algorithm selection
    'hint',         # Hint messages
    'error',        # Error messages
    'trace',        # Function tracing (@trace decorator)
    'vals',         # Computed LHS/RHS values on match output
    'general',      # Default channel
})

# Channel descriptions for --show listing (legacy; see OutputManager.format_channel_list)
CHANNEL_DESCRIPTIONS = _WarningDict({
    'config':    'Configuration loading and overrides',
    'parse':     'Expression parsing details',
    'eval':      'Expression evaluation trace',
    'iter':      'Iteration / search space info',
    'progress':  'Progress counters during search',
    'timing':    'Timing and match count summary',
    'algorithm': 'Algorithm selection details',
    'hint':      'Contextual tips and suggestions',
    'error':     'Error messages',
    'trace':     'Function call tracing',
    'vals':      'Computed LHS/RHS values on matches',
    'general':   'General output',
})

# Channels that are OFF by default in the DONOR set (legacy; declare with
# ChannelDef(opt_in=True) instead).
OPT_IN_CHANNELS = _WarningSet({
    'vals',     # Annotates stdout match lines — opt-in to avoid noise
    'trace',    # Function call tracing — opt-in (verbose debug output)
})


def default_channel_overrides() -> Dict[str, int]:
    """The DONOR set's per-channel starting coordinates: opt-in channels begin
    cold (`minimal`); every other channel defers to the global verbosity.
    Applied ONLY on the legacy path — when ``channel_defs`` are supplied this
    function is not consulted (R1-F2)."""
    return {ch: OPT_IN_START_RANK for ch in set(OPT_IN_CHANNELS)}


def format_channel_list() -> str:
    """Format the LEGACY module channel set for display.

    Prefer ``OutputManager.format_channel_list()``, which reads the manager's
    own registry (declared defs included).
    """
    lines = ["Available channels:"]
    max_name = max(len(name) for name in KNOWN_CHANNELS)
    for name in sorted(KNOWN_CHANNELS):
        desc = CHANNEL_DESCRIPTIONS.get(name, '')
        lines.append(f"  {name:<{max_name}}  {desc}")
    return "\n".join(lines)


# =============================================================================
# Deprecated module attributes (PEP 562)
# =============================================================================

def __getattr__(name):
    if name == "VERBOSITY_SPACE":
        warnings.warn(
            "dazzle_loglib.channels.VERBOSITY_SPACE reflects only the legacy "
            "donor channel set; use OutputManager.verbosity_space() for the "
            "running manager's real channels x verbosity space. Slated for "
            f"removal in {_REMOVAL_VERSION}.",
            DeprecationWarning, stacklevel=2)
        return ContinuumSpace.compose(
            "verbosity_space",
            {ch: VERBOSITY_CONTINUUM for ch in sorted(KNOWN_CHANNELS)},
            meaning="per-channel verbosity: each output channel's loudness, "
                    "independently",
        )
    if name == "ChannelConfig":
        warnings.warn(
            "ChannelConfig was renamed ChannelSpec in dazzle-loglib 0.2.0 "
            "(it is the parse product of a CLI channel spec). Slated for "
            f"removal in {_REMOVAL_VERSION}.",
            DeprecationWarning, stacklevel=2)
        return ChannelSpec
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
