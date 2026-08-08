"""
OutputManager — the THAC0 verbosity system core.

Central coordinator for verbosity-gated output with per-channel overrides.
The emit rule is: message shows when message.level <= threshold.
The threshold is either a per-channel override or the global verbosity.

THAC0 axis (10-rung scale, re-runged 0.2.0):
    ←── quieter ─────────────── default ─────────────────────── louder ──→
    -4    -3     -2       -1      0       1     2           3      4          5
    wall  errors warnings minimal default extra diagnostics config lite-debug debug

    -v increments, -q decrements. They compose: -vv -q = 1

Channels are consumer-DECLARED since 0.2.0 (LH-4): pass
``channel_defs=[ChannelDef(...)]`` and the manager owns its own registry —
names, descriptions, opt-in cold starts, per-channel FD defaults. When defs
are supplied, the legacy module sets contribute NOTHING (R1-F2).

Per-channel overrides:
    --show timing:2      pins the timing channel to threshold 2
    --show timing:config named rungs work anywhere ints do
    Specific > generic, except at -4 (hard wall, nothing at all)

Reinitialization contract (R1-F7): ``init_output()`` REPLACES the module
singleton; a second call with different defs is legal and total. Call sites
should obtain the manager via ``get_output()`` per use — holding a manager
across an ``init_output()`` means using the pre-reinit configuration.

Issue refs: donor arc #31 (multi-level verbosity), #57 (structured hints),
            #65 (named channels, THAC0 model); cutover: DazzleTools/dazzlecmd#118
"""

import sys
import warnings
from typing import Any, Dict, List, Optional, Set, TextIO, Union

from .hints import get_hint
from .channels import (
    ChannelDef, parse_channel_spec, default_channel_overrides,
    KNOWN_CHANNELS, CHANNEL_DESCRIPTIONS)
from .verbosity import VERBOSITY_CONTINUUM, shows

# Channels the manager's OWN service surfaces emit on — always valid under
# strict validation so error()/hint()/progress()/@trace never explode merely
# because an app declared its own defs. Declaring one of these as a ChannelDef
# refines it (description, opt-in, fd).
BUILTIN_CHANNELS = frozenset({'general', 'error', 'hint', 'progress', 'trace'})


class OutputManager:
    """Central coordinator for THAC0 verbosity-gated output.

    All output is written to the configured file handle (default: stderr).
    The manager tracks which hints have been shown to avoid repetition
    within a single session.

    Usage::

        out = OutputManager(verbosity=1, channel_defs=[
            ChannelDef('liveness', 'Liveness ladder decisions'),
            ChannelDef('vals', 'Value annotations', opt_in=True),
        ])
        out.emit(1, "Loaded {count} items", channel='liveness', count=42)
        out.hint('module.some_hint', 'result', var="value")
        out.error("Something went wrong")
    """

    def __init__(
        self,
        verbosity: int = 0,
        channel_overrides: Dict[str, int] = None,
        file: Union[TextIO, str] = None,
        quiet: bool = False,
        renderer=None,
        channel_renderers: Dict[str, Any] = None,
        known_channels: Set[str] = None,
        strict_channels: bool = False,
        channel_defs: Optional[List[ChannelDef]] = None,
    ):
        # Backward compat: quiet=True forces verbosity negative
        if quiet and verbosity >= 0:
            verbosity = -1
        self.verbosity = verbosity
        # May hold a real TextIO or a 'stdout'/'stderr' sentinel string —
        # sentinels are resolved at emit time in ALL positions (R1-F5), so
        # hosts that rebind streams after construction (pythonw) still work.
        self.file = file if file is not None else sys.stderr
        self.channel_fds: Dict[str, Union[TextIO, str]] = {}
        self._shown_hints: Set[str] = set()

        # Renderer resolution layers
        self.default_renderer = renderer
        self.channel_renderers: Dict[str, Any] = dict(channel_renderers or {})
        self.strict_channels = strict_channels
        self._vspace = None

        # --- The channel registry (LH-4) ---------------------------------
        self.channel_defs: Dict[str, ChannelDef] = {}
        overrides = dict(channel_overrides or {})
        if channel_defs is not None:
            for d in channel_defs:
                if not isinstance(d, ChannelDef):
                    raise TypeError(
                        f"channel_defs items must be ChannelDef, got "
                        f"{type(d).__name__}: {d!r}")
                if d.name in self.channel_defs:
                    raise ValueError(f"duplicate ChannelDef {d.name!r}")
                self.channel_defs[d.name] = d
            self.known_channels: Set[str] = \
                set(self.channel_defs) | set(BUILTIN_CHANNELS)
            # Deprecated alias must not smuggle in extra names (R1-F2).
            if known_channels is not None:
                extra = set(known_channels) - self.known_channels
                if extra:
                    raise ValueError(
                        f"known_channels= conflicts with channel_defs: "
                        f"{sorted(extra)} not declared — declare them as "
                        f"ChannelDef entries instead")
            # Starting coordinates come from the DEFS ONLY — donor opt-in
            # defaults are never consulted on this path (R1-F2). Explicit
            # channel_overrides beat def starting levels.
            for name, d in self.channel_defs.items():
                lvl = d.starting_level()
                if lvl is not None and name not in overrides:
                    overrides[name] = lvl
            # Def FDs seed the channel FD layer (R1-F3 — the once-phantom
            # layer is now real).
            for name, d in self.channel_defs.items():
                if d.fd is not None:
                    self.channel_fds[name] = d.fd
        else:
            if known_channels is not None:
                warnings.warn(
                    "known_channels= without channel_defs= is a deprecated "
                    "legacy path; declare channels via "
                    "channel_defs=[ChannelDef(...)]",
                    DeprecationWarning, stacklevel=2)
            self.known_channels = set(known_channels) if known_channels else set()
        self.channel_overrides: Dict[str, int] = overrides

    # -- FD resolution ------------------------------------------------------

    @staticmethod
    def _materialize_fd(fd: Union[TextIO, str]) -> TextIO:
        """Resolve the 'stdout'/'stderr' sentinels to the CURRENT stream at
        call time (R1-F5) — valid in all three FD positions."""
        if fd == 'stdout':
            return sys.stdout
        if fd == 'stderr':
            return sys.stderr
        return fd

    def set_channel_fd(self, channel: str, fd: Union[TextIO, str]) -> None:
        """Set the output file handle for a channel at runtime.

        Commands can call this to redirect a channel's output for the
        duration of their execution. It overrides the channel's declared
        ``ChannelDef.fd`` but is itself overridden by the per-message
        ``file=`` parameter on emit().

        FD resolution order (highest priority first):
            1. file= on emit() call (per-message)
            2. set_channel_fd() / ChannelDef.fd (the channel_fds layer —
               declared fd seeds it, runtime call replaces it)
            3. self.file (manager default — stderr)

        Sentinel strings 'stdout'/'stderr' are legal in every position and
        resolve at emit time.
        """
        self.channel_fds[channel] = fd

    def _resolve_fd(self, channel: str, file: Union[TextIO, str] = None) -> TextIO:
        """Resolve the output file handle for a message (see set_channel_fd)."""
        if file is not None:
            return self._materialize_fd(file)
        fd = self.channel_fds.get(channel)
        if fd is not None:
            return self._materialize_fd(fd)
        return self._materialize_fd(self.file)

    # -- The emit gate ------------------------------------------------------

    def emit(self, level: int, message: str = None, *,
             channel: str = 'general', file: TextIO = None,
             render=None, **kwargs: Any) -> bool:
        """Emit a message if level <= threshold for that channel.

        The threshold is the per-channel override if set, otherwise
        the global verbosity. At threshold -4 (hard wall), nothing
        is emitted regardless of level.

        Renderer resolution (highest priority first):
            1. render= callable on this call
            2. Per-channel renderer (channel_renderers)
            3. Global default_renderer
            4. Built-in print() fallback

        Args:
            level: Message level (higher = more verbose)
            message: Format string (uses str.format with kwargs).
                Optional when render= is provided.
            channel: Output channel name
            file: Per-message output override (highest priority FD)
            render: Callable to invoke instead of print. Called with
                no arguments -- use a closure to pass data.
            **kwargs: Values for template placeholders

        Returns:
            True if the message was shown, False if gated.

        Raises:
            ValueError: strict_channels is on and ``channel`` is unknown.
                Validation runs BEFORE the gate (R1-F4), so a typo'd channel
                fails at any verbosity — not only when it would emit.
        """
        if self.strict_channels and self.known_channels \
                and channel not in self.known_channels:
            raise ValueError(
                f"Unknown channel {channel!r}; known: "
                f"{sorted(self.known_channels)}")

        threshold = self.channel_overrides.get(channel, self.verbosity)
        if not shows(level, threshold):   # the THAC0 gate (verbosity Continuum)
            return False

        # Layer 1: per-call render callable
        if render is not None:
            render()
            return True

        # Layer 2: per-channel renderer
        channel_renderer = self.channel_renderers.get(channel)
        if channel_renderer is not None:
            channel_renderer()
            return True

        # Layer 3: global default renderer
        if self.default_renderer is not None:
            if message is not None:
                text = message.format(**kwargs) if kwargs else message
                self.default_renderer(text)
            return True

        # Layer 4: built-in fallback
        if message is not None and not isinstance(message, str):
            raise TypeError(
                f"emit() message must be str, got {type(message).__name__}. "
                "Use render= for complex objects."
            )
        if message is None:
            return True
        text = message.format(**kwargs) if kwargs else message
        dest = self._resolve_fd(channel, file)
        print(text, file=dest)
        return True

    def hint(self, hint_id: str, context: str = 'result', **kwargs: Any) -> None:
        """Show a hint if appropriate for context, level, and not yet shown.

        Two filters apply:
        1. Context filter: Is this hint relevant now? ('error', 'result', 'verbose')
        2. Level filter: Delegated to emit() via THAC0 threshold check.

        Args:
            hint_id: Registry key for the hint
            context: Current context ('error', 'result', 'verbose')
            **kwargs: Values for template placeholders in hint message
        """
        if hint_id in self._shown_hints:
            return
        h = get_hint(hint_id)
        if h is None or context not in h.context:
            return

        # Route through emit() -- ONE gate + renderer path. The hint shows at
        # level `h.min_level` on the 'hint' channel, gated by `shows()` inside
        # emit(); dedup-track it only if it actually emitted.
        if self.emit(h.min_level, h.message, channel='hint', **kwargs):
            self._shown_hints.add(hint_id)

    def progress(self, count: int, elapsed: float) -> None:
        """Emit a progress update (level 1, progress channel)."""
        self.emit(1, "  ... {count} results ({elapsed:.1f}s)",
                  channel='progress', count=count, elapsed=elapsed)

    def error(self, message: str, *, file: TextIO = None) -> None:
        """Emit an error message (level -3, shown unless at hard wall).

        In the THAC0 model, errors are just emit(-3, ...). They show
        at any verbosity >= -3 (i.e., everything except -QQQQ).

        Args:
            message: Error message text
            file: Per-message output override
        """
        self.emit(-3, message, channel='error', file=file)

    def is_level_active(self, level: int, channel: str = 'general') -> bool:
        """Check if a message at the given level/channel would be shown.

        Allows callers to gate expensive data collection (not just rendering)
        before calling emit(). Generalizes channel_active() to any level.

        Args:
            level: Message level to check
            channel: Channel name

        Returns:
            True if the message would pass the threshold check
        """
        threshold = self.channel_overrides.get(channel, self.verbosity)
        return shows(level, threshold)

    def channel_active(self, channel: str) -> bool:
        """Check if a channel would display messages at its default level.

        Returns True if a level-0 message on this channel would be shown.
        Used by callers to gate expensive operations (e.g., vals capture).

        Args:
            channel: Channel name to check

        Returns:
            True if the channel is active
        """
        return self.is_level_active(0, channel)

    # -- Registry views ------------------------------------------------------

    def verbosity_space(self):
        """The channels x verbosity ``ContinuumSpace`` built from THIS
        manager's registry (declared defs + builtins; the legacy donor set
        only when nothing was declared). Axis order is sorted; cached — the
        registry is init-frozen (R1-F6)."""
        if self._vspace is None:
            from dazzle_lib.continuum import ContinuumSpace
            names = self.known_channels or set(KNOWN_CHANNELS)
            self._vspace = ContinuumSpace.compose(
                "verbosity_space",
                {ch: VERBOSITY_CONTINUUM for ch in sorted(names)},
                meaning="per-channel verbosity: each output channel's "
                        "loudness, independently",
            )
        return self._vspace

    def format_channel_list(self) -> str:
        """Format THIS manager's channel registry for display (declared defs
        with their descriptions; builtins; or the legacy donor set when
        nothing was declared)."""
        names = sorted(self.known_channels or set(KNOWN_CHANNELS))
        max_name = max(len(n) for n in names)
        lines = ["Available channels:"]
        for n in names:
            if n in self.channel_defs:
                desc = self.channel_defs[n].description
            else:
                desc = CHANNEL_DESCRIPTIONS.get(n, '')
            lines.append(f"  {n:<{max_name}}  {desc}")
        return "\n".join(lines)

    @property
    def quiet(self) -> bool:
        """Backward compat: True when verbosity is negative."""
        return self.verbosity < 0

    @property
    def shown_hints(self) -> Set[str]:
        """Set of hint IDs that have been displayed this session."""
        return self._shown_hints.copy()


# =============================================================================
# Module-level singleton
# =============================================================================

_manager: Optional[OutputManager] = None


def init_output(verbosity: int = 0, quiet: bool = False,
                channels: list = None,
                channel_fds: Dict[str, TextIO] = None,
                renderer=None,
                known_channels: Set[str] = None,
                strict_channels: bool = False,
                channel_defs: Optional[List[ChannelDef]] = None) -> OutputManager:
    """Initialize the module-level OutputManager singleton.

    Call once at program startup after parsing CLI arguments. Calling again
    REPLACES the singleton (R1-F7): a second init with different defs is legal
    and total; obtain the manager via ``get_output()`` per use.

    Args:
        verbosity: THAC0 verbosity level (0=default, positive=verbose, negative=quiet)
        quiet: Legacy backward compat -- if True, sets verbosity to min(verbosity, -1)
        channels: List of CLI channel spec strings (e.g. ['timing:2', 'vals']).
            Applied LAST — a user's spec beats a declared starting level.
        channel_fds: Per-channel FD defaults (e.g. {'general': sys.stdout}).
            Prefer ``ChannelDef(fd=...)``; this parameter remains for the
            legacy path and beats def-declared FDs when both are given.
        renderer: Default renderer callable (e.g. console.print) — Layer 3
            in renderer resolution.
        known_channels: DEPRECATED legacy validation set — declare channels
            via ``channel_defs`` instead.
        strict_channels: If True, emit() raises ValueError on channels
            outside the registry (validated BEFORE the gate).
        channel_defs: The consumer's declared channel registry
            (list of :class:`ChannelDef`). When supplied, the legacy module
            sets and donor opt-in defaults contribute NOTHING (R1-F2).

    Returns:
        The initialized OutputManager instance
    """
    global _manager

    # Backward compat: quiet=True means at least -1
    if quiet and verbosity >= 0:
        verbosity = -1

    if channel_defs is not None:
        # Declared registry path: starting coordinates come from the defs
        # inside OutputManager.__init__; donor defaults are NOT consulted.
        channel_overrides: Dict[str, int] = {}
    else:
        # Legacy donor path: opt-in channels start cold per the module sets.
        channel_overrides = default_channel_overrides()

    # Parse explicit channel specs — collected here, applied AFTER the
    # manager computes def starting levels (user spec beats declaration).
    spec_overrides: Dict[str, int] = {}
    spec_fds: Dict[str, Any] = {}
    if channels:
        for spec in channels:
            if not isinstance(spec, str):
                raise TypeError(
                    f"channels= items must be spec strings, got "
                    f"{type(spec).__name__}: {spec!r} (declared channels "
                    f"go in channel_defs=)")
            cfg = parse_channel_spec(spec)
            spec_overrides[cfg.name] = cfg.level
            if cfg.fd is not None:
                spec_fds[cfg.name] = cfg.fd

    _manager = OutputManager(
        verbosity=verbosity,
        channel_overrides=channel_overrides,
        renderer=renderer,
        known_channels=known_channels,
        strict_channels=strict_channels,
        channel_defs=channel_defs,
    )

    # CLI specs are the LOUDEST declaration source (explicit user intent).
    _manager.channel_overrides.update(spec_overrides)
    for ch, fd in spec_fds.items():
        _manager.channel_fds[ch] = fd

    # Apply channel FD defaults (legacy parameter; beats def-declared FDs)
    if channel_fds:
        for ch, fd in channel_fds.items():
            _manager.channel_fds[ch] = fd

    return _manager


def get_output() -> OutputManager:
    """Get the module-level OutputManager, creating a default if needed."""
    global _manager
    if _manager is None:
        _manager = OutputManager()
    return _manager
