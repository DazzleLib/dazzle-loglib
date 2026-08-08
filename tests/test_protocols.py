"""LH-2 / R1-F9 / R1-F10: the emitter injection contract.

Pins the load-bearing claims: OutputManager satisfies EmitterProtocol
UNCHANGED (structural), the shims satisfy it, and NullEmitter's inactive
answer gives guarded call sites true zero cost.
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
