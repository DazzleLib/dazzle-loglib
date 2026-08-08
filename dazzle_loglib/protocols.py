"""The emitter injection contract (LH-2 / R1-F9 / R1-F10).

``EmitterProtocol`` is the STRUCTURAL contract that lets any library accept an
optional diagnostic emitter without depending on dazzle-loglib: a function
parameter typed against this protocol is satisfied by :class:`OutputManager`,
by the shims below, or by any object of the caller's own making that implements
the two methods. Lower DazzleLib layers (filekit, unctools) are the intended
adopters — an optional ``emitter=`` argument defaulting to silent — so the
stack's down-only dependency rule holds: the CONTRACT travels down, the
IMPLEMENTATION stays perpendicular, the application wires the two together.

Why two methods, not one: ``emit()`` defers *formatting* until after the gate,
but the call site still pays to *collect* the kwargs. ``is_level_active()`` lets
a consumer skip expensive data collection entirely when the message would be
gated — the zero-cost-when-off guarantee the whole design is judged against.

Homing note (API stability): the canonical home of ``EmitterProtocol`` may
migrate to ``dazzle_lib.protocols`` in the release where a stack library first
accepts an ``emitter=`` parameter (the rule-of-two lift). When that happens,
THIS module re-exports it permanently — ``from dazzle_loglib.protocols import
EmitterProtocol`` keeps working forever.
"""

from typing import Any, Callable, Protocol, runtime_checkable

__all__ = ["EmitterProtocol", "NullEmitter", "CallableEmitter"]


@runtime_checkable
class EmitterProtocol(Protocol):
    """A destination for verbosity-gated diagnostic messages.

    Expectations:

    - ``emit()`` shows ``message`` (a ``str.format`` template completed with
      ``kwargs``) when ``level`` passes the receiver's threshold for
      ``channel``, and returns True iff the message was shown. Implementations
      must not format the message when it is gated.
    - ``is_level_active()`` answers "would a message at this level/channel be
      shown?" so callers can skip collecting expensive diagnostic data when
      the answer is no.
    """

    def emit(self, level: int, message: str = None, *,
             channel: str = 'general', **kwargs: Any) -> bool:
        """Show ``message`` if ``level`` passes ``channel``'s threshold."""
        ...

    def is_level_active(self, level: int, channel: str = 'general') -> bool:
        """True if a message at ``level`` on ``channel`` would be shown."""
        ...


class NullEmitter:
    """The silent default: emits nothing, reports every level inactive.

    ``is_level_active()`` returning False is the point — guarded call sites
    skip their data collection entirely, which is cheaper than emitting into
    a void.
    """

    def emit(self, level: int, message: str = None, *,
             channel: str = 'general', **kwargs: Any) -> bool:
        return False

    def is_level_active(self, level: int, channel: str = 'general') -> bool:
        return False


class CallableEmitter:
    """Adapt any print-like callable into an emitter (the std-swap shim).

    ``CallableEmitter(print)`` or ``CallableEmitter(logging.getLogger(...).info)``
    turns a plain callable into something satisfying :class:`EmitterProtocol`.
    Everything is considered active — gating is the wrapped side's problem, if
    it has one.
    """

    def __init__(self, fn: Callable[[str], Any]):
        self._fn = fn

    def emit(self, level: int, message: str = None, *,
             channel: str = 'general', **kwargs: Any) -> bool:
        if message is not None:
            self._fn(message.format(**kwargs) if kwargs else message)
        return True

    def is_level_active(self, level: int, channel: str = 'general') -> bool:
        return True
