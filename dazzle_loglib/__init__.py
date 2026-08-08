"""
dazzle-loglib — THAC0 verbosity system with consumer-defined channels.

A reusable output-management library providing:
- Single-axis THAC0 verbosity (level <= threshold) on a 10-rung signed scale
- Consumer-DECLARED named channels (ChannelDef) with per-channel overrides
- Env/CLI verbosity resolution with defined precedence
- The EmitterProtocol injection contract (+ Null/Callable shims)
- Hint registry with context filtering and dedup
- Function tracing decorator

Each program declares its OWN channels::

    from dazzle_loglib import init_output, ChannelDef

    init_output(verbosity=args.verbose - args.quiet, strict_channels=True,
                channel_defs=[
                    ChannelDef('liveness', 'Liveness ladder decisions'),
                    ChannelDef('git', 'Git operations'),
                    ChannelDef('vals', 'Value annotations', opt_in=True),
                ])

Public API:
    OutputManager    — central coordinator
    init_output      — singleton initialization
    get_output       — access singleton
    ChannelDef       — a consumer-declared channel
    ChannelSpec      — parse product of a CLI channel spec string
    parse_channel_spec — parse CLI channel spec
    resolve_verbosity / resolve_channel_specs — precedence-encoded resolution
    EmitterProtocol / NullEmitter / CallableEmitter — the injection contract
    Hint / register_hint(s) / get_hint / get_hints_by_category — hints
    trace            — function tracing decorator
    BUILTIN_CHANNELS — channels the manager's own surfaces emit on

Deprecated legacy surface (excluded from the API-stability guarantee, slated
for removal): KNOWN_CHANNELS, CHANNEL_DESCRIPTIONS, OPT_IN_CHANNELS,
format_channel_list (module form), channels.VERBOSITY_SPACE,
channels.ChannelConfig.
"""

from ._version import __version__, DISPLAY_VERSION
from .manager import OutputManager, init_output, get_output, BUILTIN_CHANNELS
from .hints import (
    Hint, register_hint, register_hints, get_hint, get_hints_by_category,
)
from .channels import (
    ChannelDef, ChannelSpec, parse_channel_spec, OPT_IN_START_RANK,
    KNOWN_CHANNELS, CHANNEL_DESCRIPTIONS, OPT_IN_CHANNELS, format_channel_list,
)
from .trace import trace
from .protocols import EmitterProtocol, NullEmitter, CallableEmitter
from .resolve import resolve_verbosity, resolve_channel_specs

__all__ = [
    '__version__', 'DISPLAY_VERSION',
    'OutputManager', 'init_output', 'get_output', 'BUILTIN_CHANNELS',
    'ChannelDef', 'ChannelSpec', 'parse_channel_spec', 'OPT_IN_START_RANK',
    'resolve_verbosity', 'resolve_channel_specs',
    'EmitterProtocol', 'NullEmitter', 'CallableEmitter',
    'Hint', 'register_hint', 'register_hints', 'get_hint', 'get_hints_by_category',
    'trace',
    # Deprecated legacy surface (cutover window only):
    'KNOWN_CHANNELS', 'CHANNEL_DESCRIPTIONS', 'OPT_IN_CHANNELS',
    'format_channel_list',
]
