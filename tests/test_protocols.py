"""LH-2 / R1-F9 / R1-F10: the emitter injection contract.

Pins the three claims the README and docs/cli-integration.md make on this
protocol's behalf, each of which would fail silently rather than loudly:

- ``OutputManager`` satisfies ``EmitterProtocol`` with no changes of its own.
  Structural typing means nothing declares the relationship, so if a signature
  drifted, every consumer passing a real manager into an ``emitter=`` parameter
  would keep type-checking and only misbehave at runtime.
- The shims satisfy it too, which is what lets a caller with no interest in
  this library hand in ``print`` and still work.
- ``NullEmitter.is_level_active`` answers False, which is what makes a guarded
  call site skip its data collection entirely instead of computing a message
  for a destination that discards it.
"""
from dazzle_loglib.manager import OutputManager
from dazzle_loglib.protocols import EmitterProtocol, NullEmitter, CallableEmitter


class TestProtocolSatisfaction:
    def test_output_manager_satisfies_protocol_unchanged(self):
        assert isinstance(OutputManager(), EmitterProtocol)

    def test_null_emitter_satisfies_protocol(self):
        assert isinstance(NullEmitter(), EmitterProtocol)

    def test_callable_emitter_satisfies_protocol(self):
        assert isinstance(CallableEmitter(print), EmitterProtocol)

    def test_four_line_print_shim_satisfies_protocol(self):
        """The user-facing promise: a trivial hand-rolled shim is enough."""
        class Shim:
            def emit(self, level, message=None, *, channel='general', **kw):
                return True
            def is_level_active(self, level, channel='general'):
                return True
        assert isinstance(Shim(), EmitterProtocol)


class TestNullEmitter:
    def test_emits_nothing_reports_inactive(self):
        n = NullEmitter()
        assert n.emit(0, "anything") is False
        assert n.is_level_active(-3, "error") is False

    def test_guarded_call_site_skips_collection(self):
        """The zero-cost pattern: is_level_active gates expensive collection."""
        n = NullEmitter()
        collected = []
        if n.is_level_active(2, "liveness"):
            collected.append("expensive")  # pragma: no cover
        assert collected == []


class TestCallableEmitter:
    def test_wraps_print_like_callable(self):
        out = []
        e = CallableEmitter(out.append)
        assert e.emit(1, "rows={n}", channel="scan", n=42) is True
        assert out == ["rows=42"]

    def test_no_message_no_call(self):
        out = []
        e = CallableEmitter(out.append)
        assert e.emit(1) is True
        assert out == []

    def test_everything_active(self):
        assert CallableEmitter(print).is_level_active(3, "trace") is True


class TestInjectionEndToEnd:
    def test_manager_as_injected_emitter(self):
        """A library function typed against the protocol receives a real manager."""
        def library_op(emitter: EmitterProtocol = None):
            emitter = emitter or NullEmitter()
            if emitter.is_level_active(1, "general"):
                emitter.emit(1, "did {thing}", thing="work")
            return "result"

        sink = []
        om = OutputManager(verbosity=1)
        om.default_renderer = sink.append
        assert library_op(om) == "result"
        assert sink == ["did work"]
        assert library_op() == "result"          # silent default path
        assert library_op(NullEmitter()) == "result"
